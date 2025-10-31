/**
 * 简化的KV存储服务 - 仅使用KV存储，不依赖数据库
 * 用于R2存储配置前的临时替代方案
 */

export class SimpleKVStorageService {
  constructor(kvBinding, options = {}) {
    this.kv = kvBinding;
    this.options = {
      maxFileSize: 25 * 1024 * 1024, // 25MB
      defaultTTL: 30 * 24 * 60 * 60, // 30天
      ...options
    };
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
      ttl = this.options.defaultTTL
    } = options;

    try {
      // 验证文件大小
      if (file.size > this.options.maxFileSize) {
        throw new Error(`File size ${file.size} exceeds maximum allowed size ${this.options.maxFileSize}`);
      }

      // 生成文件名
      const timestamp = Date.now();
      const randomId = Math.random().toString(36).substring(2, 8);
      const fileName = customName || `${timestamp}-${randomId}.${file.name.split('.').pop()}`;
      const key = `${folder}/${fileName}`;

      // 读取文件内容
      const fileBuffer = await file.arrayBuffer();
      
      // 转换为base64
      const base64Data = this.arrayBufferToBase64(fileBuffer);

      // 准备元数据
      const fileMetadata = {
        originalName: file.name,
        size: file.size,
        type: file.type,
        uploadedAt: new Date().toISOString(),
        isPublic,
        storageType: 'kv',
        ...metadata
      };

      // 准备存储数据
      const storageRecord = {
        data: base64Data,
        metadata: fileMetadata,
        size: base64Data.length,
        createdAt: new Date().toISOString()
      };

      // 存储到KV
      await this.kv.put(key, JSON.stringify(storageRecord), {
        expirationTtl: ttl
      });

      return {
        success: true,
        key: key,
        file: {
          key: key,
          originalName: file.name,
          fileName: fileName,
          size: file.size,
          type: file.type,
          uploadedAt: fileMetadata.uploadedAt,
          isPublic
        },
        url: this.getFileUrl(key, isPublic),
        message: 'File uploaded successfully',
        storageInfo: {
          type: 'kv',
          originalSize: file.size,
          storedSize: base64Data.length
        }
      };

    } catch (error) {
      throw new Error(`File upload failed: ${error.message}`);
    }
  }

  /**
   * 获取文件
   */
  async getFile(key) {
    try {
      const storedData = await this.kv.get(key);
      
      if (!storedData) {
        return null;
      }

      const record = JSON.parse(storedData);
      
      // 转换base64回ArrayBuffer
      const fileBuffer = this.base64ToArrayBuffer(record.data);
      
      return {
        key: key,
        data: fileBuffer,
        metadata: record.metadata,
        size: record.metadata.size,
        type: record.metadata.type,
        uploadedAt: record.metadata.uploadedAt
      };

    } catch (error) {
      throw new Error(`Failed to get file: ${error.message}`);
    }
  }

  /**
   * 删除文件
   */
  async deleteFile(key) {
    try {
      await this.kv.delete(key);
      return {
        success: true,
        key: key,
        message: 'File deleted successfully'
      };
    } catch (error) {
      throw new Error(`Failed to delete file: ${error.message}`);
    }
  }

  /**
   * 列出文件
   */
  async listFiles(options = {}) {
    const { prefix = '', limit = 1000 } = options;
    
    try {
      const listResult = await this.kv.list({ prefix, limit });
      
      return {
        keys: listResult.keys,
        list_complete: listResult.list_complete,
        cursor: listResult.cursor
      };
    } catch (error) {
      throw new Error(`Failed to list files: ${error.message}`);
    }
  }

  /**
   * 获取文件URL
   */
  getFileUrl(key, isPublic = false) {
    if (isPublic) {
      return `/api/files/kv/${key}`;
    }
    return `/api/files/kv/${key}`;
  }

  /**
   * 获取存储统计
   */
  async getStorageStats() {
    try {
      const listResult = await this.kv.list({ limit: 1000 });
      
      let totalSize = 0;
      let fileCount = listResult.keys.length;
      
      // 粗略估算总大小（基于key数量）
      // 实际应用中可能需要更精确的计算
      return {
        storage_type: 'kv',
        total_files: fileCount,
        total_size: totalSize,
        message: 'Simple KV storage stats'
      };
    } catch (error) {
      return {
        storage_type: 'kv',
        total_files: 0,
        total_size: 0,
        error: error.message
      };
    }
  }

  /**
   * ArrayBuffer转Base64
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
   * Base64转ArrayBuffer
   */
  base64ToArrayBuffer(base64) {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  }
}

export default SimpleKVStorageService;