/**
 * Cloudflare KV Storage Service
 * R2存储的替代方案，使用KV存储小文件（<25MB）
 * 适用于临时文件存储和快速部署
 */

export class KVStorageService {
  constructor(env, options = {}) {
    this.env = env;
    this.kv = env.MAIMAI_KV; // 使用已创建的KV命名空间
    this.maxFileSize = options.maxFileSize || 10 * 1024 * 1024; // 10MB (KV限制为25MB)
    this.allowedTypes = options.allowedTypes || [
      'image/jpeg', 'image/png', 'image/gif', 'image/webp',
      'application/pdf', 'application/msword', 
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain', 'text/csv', 'application/json'
    ];
    this.baseUrl = options.baseUrl || null;
    this.enableCompression = options.enableCompression !== false;
    this.maxStorageDays = options.maxStorageDays || 30; // 30天后自动删除
  }

  /**
   * 上传文件到KV存储
   */
  async uploadFile(file, options = {}) {
    const {
      folder = 'uploads',
      customName = null,
      metadata = {},
      isPublic = false,
      compress = this.enableCompression
    } = options;

    try {
      // 验证文件
      this.validateFile(file);

      // 生成文件名和key
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
          isDuplicate: true,
          url: this.getFileUrl(existingFile.key, isPublic)
        };
      }

      // 压缩文件数据（可选）
      let storageData = fileBuffer;
      let isCompressed = false;
      if (compress && fileBuffer.byteLength > 1024) { // 大于1KB的文件才压缩
        try {
          storageData = await this.compressData(fileBuffer);
          isCompressed = true;
        } catch (compressError) {
          console.warn('Compression failed, storing uncompressed:', compressError.message);
          storageData = fileBuffer;
          isCompressed = false;
        }
      }

      // 转换为base64存储
      const base64Data = this.arrayBufferToBase64(storageData);

      // 准备元数据
      const fileMetadata = {
        originalName: file.name,
        size: file.size,
        type: file.type,
        hash: fileHash,
        uploadedAt: new Date().toISOString(),
        isPublic,
        isCompressed,
        storageType: 'kv',
        expiresAt: new Date(Date.now() + this.maxStorageDays * 24 * 60 * 60 * 1000).toISOString(),
        ...metadata
      };

      // 准备存储数据
      const storageRecord = {
        data: base64Data,
        metadata: fileMetadata,
        size: base64Data.length,
        createdAt: new Date().toISOString()
      };

      // 存储到KV（设置过期时间）
      await this.kv.put(key, JSON.stringify(storageRecord), {
        expirationTtl: this.maxStorageDays * 24 * 60 * 60 // 秒
      });

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
        message: 'File uploaded successfully',
        storageInfo: {
          type: 'kv',
          compressed: isCompressed,
          originalSize: file.size,
          storedSize: base64Data.length
        }
      };

    } catch (error) {
      throw new Error(`File upload failed: ${error.message}`);
    }
  }

  /**
   * 上传Base64图片到KV存储
   */
  async uploadBase64Image(base64String, options = {}) {
    const {
      folder = 'images',
      customName = null,
      metadata = {},
      isPublic = true,
      compress = this.enableCompression
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
          isDuplicate: true,
          url: this.getFileUrl(existingFile.key, isPublic)
        };
      }

      // 压缩图片数据（可选）
      let storageData = imageBuffer;
      let isCompressed = false;
      if (compress && imageBuffer.byteLength > 1024) {
        try {
          storageData = await this.compressData(imageBuffer);
          isCompressed = true;
        } catch (compressError) {
          console.warn('Image compression failed, storing uncompressed:', compressError.message);
          storageData = imageBuffer;
          isCompressed = false;
        }
      }

      // 转换为base64存储
      const storageBase64 = this.arrayBufferToBase64(storageData);

      // 准备元数据
      const fileMetadata = {
        originalName: fileName,
        size: imageBuffer.byteLength,
        type: mimeType,
        hash: fileHash,
        uploadedAt: new Date().toISOString(),
        isPublic,
        isCompressed,
        storageType: 'kv',
        source: 'base64',
        expiresAt: new Date(Date.now() + this.maxStorageDays * 24 * 60 * 60 * 1000).toISOString(),
        ...metadata
      };

      // 准备存储数据
      const storageRecord = {
        data: storageBase64,
        metadata: fileMetadata,
        size: storageBase64.length,
        createdAt: new Date().toISOString()
      };

      // 存储到KV
      await this.kv.put(key, JSON.stringify(storageRecord), {
        expirationTtl: this.maxStorageDays * 24 * 60 * 60
      });

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
        message: 'Image uploaded successfully',
        storageInfo: {
          type: 'kv',
          compressed: isCompressed,
          originalSize: imageBuffer.byteLength,
          storedSize: storageBase64.length
        }
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
      // 从KV获取数据
      const storedData = await this.kv.get(key);
      
      if (!storedData) {
        throw new Error('File not found');
      }

      // 解析存储的数据
      const storageRecord = JSON.parse(storedData);
      const { data, metadata } = storageRecord;

      // 将base64数据转换回ArrayBuffer
      let fileData = this.base64ToArrayBuffer(data);

      // 如果数据被压缩，解压缩
      if (metadata.isCompressed) {
        try {
          fileData = await this.decompressData(fileData);
        } catch (decompressError) {
          console.error('Decompression failed:', decompressError.message);
          throw new Error('Failed to decompress file data');
        }
      }

      return {
        body: fileData,
        metadata: metadata,
        size: metadata.size,
        type: metadata.type,
        originalName: metadata.originalName
      };

    } catch (error) {
      throw new Error(`Failed to get file: ${error.message}`);
    }
  }

  /**
   * 获取文件URL（KV存储返回数据URL）
   */
  getFileUrl(key, isPublic = false) {
    if (isPublic) {
      // 对于公开文件，返回一个可以通过API访问的URL
      return `/api/files/kv/${key}`;
    }
    // 对于私有文件，返回一个需要认证的API端点
    return `/api/files/kv/${key}?auth=required`;
  }

  /**
   * 删除文件
   */
  async deleteFile(key) {
    try {
      // 从KV删除文件数据
      await this.kv.delete(key);
      
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
    const { prefix = '', limit = 100 } = options;

    try {
      // 从数据库获取文件列表（KV不支持直接列出键）
      const files = await this.getFileListFromDatabase(prefix, limit);
      
      return {
        files,
        total: files.length,
        storageType: 'kv'
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
        'SELECT * FROM files WHERE hash = ? AND storage_type = "kv" LIMIT 1'
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
          uploaded_by, storage_type, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
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
        fileData.uploadedBy,
        'kv'
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
   * 从数据库获取文件列表
   */
  async getFileListFromDatabase(prefix, limit) {
    try {
      let sql = 'SELECT * FROM files WHERE storage_type = "kv"';
      const params = [];

      if (prefix) {
        sql += ' AND key LIKE ?';
        params.push(`${prefix}%`);
      }

      sql += ' ORDER BY created_at DESC LIMIT ?';
      params.push(limit);

      const result = await this.env.DB.prepare(sql).bind(...params).all();
      
      return result.results || [];
    } catch (error) {
      console.error('Failed to get file list from database:', error);
      return [];
    }
  }

  /**
   * 工具方法：ArrayBuffer转Base64
   */
  arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  /**
   * 工具方法：Base64转ArrayBuffer
   */
  base64ToArrayBuffer(base64) {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  }

  /**
   * 压缩数据（简单的gzip压缩模拟）
   * 注意：在Workers环境中需要使用pako等压缩库
   */
  async compressData(buffer) {
    // 这里应该使用实际的压缩算法
    // 暂时返回原数据，建议在生产环境中使用pako库
    return buffer;
  }

  /**
   * 解压缩数据
   */
  async decompressData(buffer) {
    // 这里应该使用实际的解压缩算法
    // 暂时返回原数据，建议在生产环境中使用pako库
    return buffer;
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
        WHERE storage_type = 'kv'
      `).first();

      return result || {
        total_files: 0,
        total_size: 0,
        public_files: 0,
        private_files: 0,
        file_types: 0,
        uploaders: 0,
        storage_type: 'kv'
      };
    } catch (error) {
      console.error('Failed to get storage stats:', error);
      return {
        total_files: 0,
        total_size: 0,
        public_files: 0,
        private_files: 0,
        file_types: 0,
        uploaders: 0,
        storage_type: 'kv'
      };
    }
  }
}

/**
 * KV存储服务工厂函数
 */
export function createKVStorageService(env) {
  return new KVStorageService(env);
}