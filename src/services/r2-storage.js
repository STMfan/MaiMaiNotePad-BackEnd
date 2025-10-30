/**
 * Cloudflare R2 Storage Service
 * 适配Workers运行时的文件存储服务
 */

/**
 * R2存储服务类
 */
export class R2StorageService {
  constructor(env, options = {}) {
    this.env = env;
    this.bucket = env.FILES_BUCKET;
    this.maxFileSize = options.maxFileSize || 10 * 1024 * 1024; // 10MB
    this.allowedTypes = options.allowedTypes || [
      'image/jpeg', 'image/png', 'image/gif', 'image/webp',
      'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain', 'text/csv', 'application/json'
    ];
    this.baseUrl = options.baseUrl || null;
  }

  /**
   * 上传文件到R2
   */
  async uploadFile(file, options = {}) {
    const {
      folder = 'uploads',
      customName = null,
      metadata = {},
      isPublic = false
    } = options;

    try {
      // 验证文件
      this.validateFile(file);

      // 生成文件名
      const fileName = customName || this.generateFileName(file.name);
      const key = `${folder}/${fileName}`;

      // 准备文件数据
      const fileBuffer = await file.arrayBuffer();
      const fileHash = await this.calculateHash(fileBuffer);

      // 检查文件是否已存在
      const existingFile = await this.checkFileExists(fileHash);
      if (existingFile) {
        return {
          success: true,
          file: existingFile,
          message: 'File already exists',
          isDuplicate: true
        };
      }

      // 准备元数据
      const fileMetadata = {
        originalName: file.name,
        size: file.size,
        type: file.type,
        hash: fileHash,
        uploadedAt: new Date().toISOString(),
        isPublic,
        ...metadata
      };

      // 上传到R2
      const putOptions = {
        httpMetadata: {
          contentType: file.type,
          contentDisposition: `attachment; filename="${file.name}"`
        },
        customMetadata: fileMetadata
      };

      if (isPublic) {
        putOptions.httpMetadata.cacheControl = 'public, max-age=31536000';
      }

      await this.bucket.put(key, fileBuffer, putOptions);

      // 保存文件记录到数据库
      const fileRecord = await this.saveFileRecord({
        key,
        originalName: file.name,
        fileName,
        size: file.size,
        type: file.type,
        hash: fileHash,
        metadata: fileMetadata,
        isPublic,
        uploadedBy: metadata.uploadedBy || 'anonymous'
      });

      return {
        success: true,
        file: fileRecord,
        url: this.getFileUrl(key, isPublic),
        message: 'File uploaded successfully'
      };

    } catch (error) {
      throw new Error(`File upload failed: ${error.message}`);
    }
  }

  /**
   * 上传Base64图片
   */
  async uploadBase64Image(base64String, options = {}) {
    const {
      folder = 'images',
      customName = null,
      metadata = {},
      isPublic = true
    } = options;

    try {
      // 解析Base64字符串
      const matches = base64String.match(/^data:(.+);base64,(.+)$/);
      if (!matches) {
        throw new Error('Invalid base64 string format');
      }

      const mimeType = matches[1];
      const base64Data = matches[2];
      const imageBuffer = Uint8Array.from(atob(base64Data), c => c.charCodeAt(0));

      // 验证图片类型
      if (!mimeType.startsWith('image/')) {
        throw new Error('Invalid image type');
      }

      // 生成文件名
      const extension = mimeType.split('/')[1];
      const fileName = customName || `${crypto.randomUUID()}.${extension}`;
      const key = `${folder}/${fileName}`;

      // 计算哈希
      const fileHash = await this.calculateHash(imageBuffer);

      // 检查文件是否已存在
      const existingFile = await this.checkFileExists(fileHash);
      if (existingFile) {
        return {
          success: true,
          file: existingFile,
          message: 'Image already exists',
          isDuplicate: true
        };
      }

      // 准备元数据
      const fileMetadata = {
        originalName: fileName,
        size: imageBuffer.byteLength,
        type: mimeType,
        hash: fileHash,
        uploadedAt: new Date().toISOString(),
        isPublic,
        source: 'base64',
        ...metadata
      };

      // 上传到R2
      const putOptions = {
        httpMetadata: {
          contentType: mimeType,
          cacheControl: isPublic ? 'public, max-age=31536000' : 'private, max-age=3600'
        },
        customMetadata: fileMetadata
      };

      await this.bucket.put(key, imageBuffer, putOptions);

      // 保存文件记录
      const fileRecord = await this.saveFileRecord({
        key,
        originalName: fileName,
        fileName,
        size: imageBuffer.byteLength,
        type: mimeType,
        hash: fileHash,
        metadata: fileMetadata,
        isPublic,
        uploadedBy: metadata.uploadedBy || 'anonymous'
      });

      return {
        success: true,
        file: fileRecord,
        url: this.getFileUrl(key, isPublic),
        message: 'Image uploaded successfully'
      };

    } catch (error) {
      throw new Error(`Base64 image upload failed: ${error.message}`);
    }
  }

  /**
   * 获取文件
   */
  async getFile(key) {
    try {
      const object = await this.bucket.get(key);
      
      if (!object) {
        throw new Error('File not found');
      }

      return {
        body: object.body,
        httpMetadata: object.httpMetadata,
        customMetadata: object.customMetadata,
        size: object.size,
        etag: object.etag,
        httpEtag: object.httpEtag,
        httpLastModified: object.httpLastModified,
        range: object.range
      };
    } catch (error) {
      throw new Error(`Failed to get file: ${error.message}`);
    }
  }

  /**
   * 获取文件URL
   */
  getFileUrl(key, isPublic = false) {
    if (isPublic && this.baseUrl) {
      return `${this.baseUrl}/${key}`;
    }
    
    // 生成预签名URL（这里需要根据实际R2配置调整）
    return `/api/files/${key}`;
  }

  /**
   * 生成预签名URL
   */
  async generatePresignedUrl(key, expiresIn = 3600) {
    try {
      // R2支持预签名URL，这里需要根据实际API调整
      const expiresAt = new Date(Date.now() + expiresIn * 1000);
      
      // 这里应该调用R2的预签名URL生成API
      // 目前返回一个占位符URL
      return {
        url: `${this.baseUrl || ''}/${key}?expires=${expiresAt.getTime()}`,
        expiresAt: expiresAt.toISOString()
      };
    } catch (error) {
      throw new Error(`Failed to generate presigned URL: ${error.message}`);
    }
  }

  /**
   * 删除文件
   */
  async deleteFile(key) {
    try {
      await this.bucket.delete(key);
      
      // 删除数据库记录
      await this.deleteFileRecord(key);
      
      return {
        success: true,
        message: 'File deleted successfully'
      };
    } catch (error) {
      throw new Error(`Failed to delete file: ${error.message}`);
    }
  }

  /**
   * 批量删除文件
   */
  async deleteFiles(keys) {
    try {
      const results = await Promise.allSettled(
        keys.map(key => this.deleteFile(key))
      );
      
      const successful = results.filter(r => r.status === 'fulfilled').length;
      const failed = results.filter(r => r.status === 'rejected').length;
      
      return {
        success: true,
        successful,
        failed,
        results: results.map((r, i) => ({
          key: keys[i],
          success: r.status === 'fulfilled',
          error: r.status === 'rejected' ? r.reason.message : null
        }))
      };
    } catch (error) {
      throw new Error(`Batch delete failed: ${error.message}`);
    }
  }

  /**
   * 列出文件
   */
  async listFiles(options = {}) {
    const {
      prefix = '',
      limit = 100,
      cursor = null,
      includeMetadata = true
    } = options;

    try {
      const listOptions = {
        limit: Math.min(limit, 1000), // R2限制
        prefix
      };

      if (cursor) {
        listOptions.cursor = cursor;
      }

      const result = await this.bucket.list(listOptions);
      
      const files = await Promise.all(
        result.objects.map(async (object) => {
          const fileInfo = {
            key: object.key,
            size: object.size,
            etag: object.etag,
            lastModified: object.lastModified,
            httpMetadata: object.httpMetadata || {},
            customMetadata: object.customMetadata || {}
          };

          if (includeMetadata) {
            // 获取数据库记录
            const record = await this.getFileRecord(object.key);
            fileInfo.record = record;
          }

          return fileInfo;
        })
      );

      return {
        files,
        truncated: result.truncated,
        cursor: result.cursor,
        delimiter: result.delimiter,
        commonPrefixes: result.commonPrefixes || []
      };
    } catch (error) {
      throw new Error(`Failed to list files: ${error.message}`);
    }
  }

  /**
   * 验证文件
   */
  validateFile(file) {
    if (!file) {
      throw new Error('No file provided');
    }

    if (file.size > this.maxFileSize) {
      throw new Error(`File size exceeds maximum allowed size of ${this.maxFileSize} bytes`);
    }

    if (!this.allowedTypes.includes(file.type)) {
      throw new Error(`File type ${file.type} is not allowed`);
    }

    if (!file.name || file.name.trim() === '') {
      throw new Error('File name is required');
    }
  }

  /**
   * 生成文件名
   */
  generateFileName(originalName) {
    const timestamp = Date.now();
    const randomString = crypto.randomUUID().substring(0, 8);
    const extension = originalName.split('.').pop();
    return `${timestamp}-${randomString}.${extension}`;
  }

  /**
   * 计算文件哈希
   */
  async calculateHash(buffer) {
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  /**
   * 检查文件是否已存在
   */
  async checkFileExists(hash) {
    try {
      const result = await this.env.DB.prepare(
        'SELECT * FROM files WHERE hash = ? LIMIT 1'
      ).bind(hash).first();
      
      return result || null;
    } catch (error) {
      console.error('Failed to check file existence:', error);
      return null;
    }
  }

  /**
   * 保存文件记录到数据库
   */
  async saveFileRecord(fileData) {
    try {
      const sql = `
        INSERT INTO files (
          key, original_name, file_name, size, type, hash, metadata, is_public,
          uploaded_by, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
      `;

      const result = await this.env.DB.run(sql, [
        fileData.key,
        fileData.originalName,
        fileData.fileName,
        fileData.size,
        fileData.type,
        fileData.hash,
        JSON.stringify(fileData.metadata),
        fileData.isPublic ? 1 : 0,
        fileData.uploadedBy
      ]);

      return {
        id: result.meta.last_row_id,
        ...fileData,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
    } catch (error) {
      throw new Error(`Failed to save file record: ${error.message}`);
    }
  }

  /**
   * 获取文件记录
   */
  async getFileRecord(key) {
    try {
      const result = await this.env.DB.prepare(
        'SELECT * FROM files WHERE key = ? LIMIT 1'
      ).bind(key).first();
      
      return result || null;
    } catch (error) {
      console.error('Failed to get file record:', error);
      return null;
    }
  }

  /**
   * 删除文件记录
   */
  async deleteFileRecord(key) {
    try {
      await this.env.DB.prepare('DELETE FROM files WHERE key = ?').bind(key).run();
      return true;
    } catch (error) {
      console.error('Failed to delete file record:', error);
      return false;
    }
  }

  /**
   * 获取存储统计
   */
  async getStorageStats() {
    try {
      const result = await this.env.DB.prepare(`
        SELECT 
          COUNT(*) as total_files,
          SUM(size) as total_size,
          COUNT(CASE WHEN is_public = 1 THEN 1 END) as public_files,
          COUNT(CASE WHEN is_public = 0 THEN 1 END) as private_files,
          COUNT(DISTINCT type) as file_types,
          COUNT(DISTINCT uploaded_by) as uploaders
        FROM files
      `).first();

      return result || {
        total_files: 0,
        total_size: 0,
        public_files: 0,
        private_files: 0,
        file_types: 0,
        uploaders: 0
      };
    } catch (error) {
      console.error('Failed to get storage stats:', error);
      return {
        total_files: 0,
        total_size: 0,
        public_files: 0,
        private_files: 0,
        file_types: 0,
        uploaders: 0
      };
    }
  }
}

/**
 * 文件上传验证器
 */
export class FileValidator {
  constructor(options = {}) {
    this.maxSize = options.maxSize || 10 * 1024 * 1024; // 10MB
    this.allowedTypes = options.allowedTypes || [];
    this.allowedExtensions = options.allowedExtensions || [];
  }

  /**
   * 验证文件
   */
  validate(file) {
    const errors = [];

    // 文件大小验证
    if (file.size > this.maxSize) {
      errors.push(`File size exceeds maximum allowed size of ${this.formatBytes(this.maxSize)}`);
    }

    // 文件类型验证
    if (this.allowedTypes.length > 0 && !this.allowedTypes.includes(file.type)) {
      errors.push(`File type ${file.type} is not allowed`);
    }

    // 文件扩展名验证
    if (this.allowedExtensions.length > 0) {
      const extension = file.name.split('.').pop().toLowerCase();
      if (!this.allowedExtensions.includes(extension)) {
        errors.push(`File extension ${extension} is not allowed`);
      }
    }

    // 文件名验证
    if (!this.isValidFileName(file.name)) {
      errors.push('File name contains invalid characters');
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  /**
   * 验证文件名
   */
  isValidFileName(fileName) {
    const invalidChars = /[<>:"/\\|?*]/;
    return !invalidChars.test(fileName);
  }

  /**
   * 格式化字节数
   */
  formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  }
}