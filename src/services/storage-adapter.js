/**
 * 存储服务适配器
 * 提供统一的存储接口，支持R2和KV存储的无缝切换
 */

import { KVStorageService } from './kv-storage.js';
import { SimpleKVStorageService } from './simple-kv-storage.js';

export class StorageAdapter {
  constructor(env, options = {}) {
    this.env = env;
    this.options = options;
    // 设置KV绑定
    this.env.MAIMAI_KV = env.FILE_KV || env.MAIMAI_KV || env.KV;
    
    // 根据选项选择KV存储服务
    const useSimpleKV = options.useSimpleKV || false;
    this.kvStorage = useSimpleKV 
      ? new SimpleKVStorageService(this.env.MAIMAI_KV, options.simpleKVOptions)
      : new KVStorageService(this.env.MAIMAI_KV);
    
    this.storageType = this.determineStorageType();
    this.storageService = this.createStorageService();
  }

  /**
   * 确定使用的存储类型
   */
  determineStorageType() {
    // 如果R2存储可用，优先使用R2
    if (this.env.R2_BUCKET) {
      return 'r2';
    }
    
    // 如果KV存储可用，使用KV存储
    if (this.env.MAIMAI_KV) {
      return 'kv';
    }
    
    throw new Error('No storage service available. Please configure R2 or KV storage.');
  }

  /**
   * 创建存储服务实例
   */
  createStorageService() {
    switch (this.storageType) {
      case 'r2':
        // 如果R2存储可用，返回R2存储服务
        // 这里假设有R2StorageService类
        return this.createR2StorageService();
      
      case 'kv':
        // 根据选项选择KV存储服务
        const useSimpleKV = this.options.useSimpleKV || false;
        return useSimpleKV 
          ? new SimpleKVStorageService(this.env.MAIMAI_KV, this.options.simpleKVOptions)
          : new KVStorageService(this.env, this.options);
      
      default:
        throw new Error(`Unknown storage type: ${this.storageType}`);
    }
  }

  /**
   * 创建R2存储服务（兼容模式）
   */
  createR2StorageService() {
    // 返回一个兼容R2存储接口的对象
    return {
      uploadFile: async (file, options = {}) => {
        return await this.env.R2_BUCKET.put(file.name, file, {
          httpMetadata: {
            contentType: file.type,
            cacheControl: 'public, max-age=31536000'
          },
          customMetadata: options.metadata || {}
        });
      },
      
      getFile: async (key) => {
        return await this.env.R2_BUCKET.get(key);
      },
      
      deleteFile: async (key) => {
        return await this.env.R2_BUCKET.delete(key);
      },
      
      listFiles: async (options = {}) => {
        return await this.env.R2_BUCKET.list(options);
      },
      
      getFileUrl: (key, isPublic = false) => {
        if (isPublic) {
          return `https://pub-${this.env.R2_BUCKET.accountId}.r2.dev/${key}`;
        }
        return `/api/files/${key}`;
      }
    };
  }

  /**
   * 上传文件
   */
  async uploadFile(file, options = {}) {
    try {
      // 如果使用的是KV存储，调用KV存储的上传方法
      if (this.storageType === 'kv') {
        return await this.storageService.uploadFile(file, options);
      }
      
      // 如果使用的是R2存储，调用R2存储的上传方法
      if (this.storageType === 'r2') {
        const result = await this.storageService.uploadFile(file, options);
        return {
          success: true,
          file: {
            key: file.name,
            originalName: file.name,
            size: file.size,
            type: file.type,
            uploadedAt: new Date().toISOString(),
            etag: result.etag,
            httpEtag: result.httpEtag
          },
          url: this.getFileUrl(file.name, options.isPublic || false),
          message: 'File uploaded successfully'
        };
      }
      
      throw new Error(`Upload not supported for storage type: ${this.storageType}`);
    } catch (error) {
      throw new Error(`File upload failed: ${error.message}`);
    }
  }

  /**
   * 上传Base64图片
   */
  async uploadBase64Image(base64String, options = {}) {
    try {
      // 只有KV存储支持Base64图片上传
      if (this.storageType === 'kv') {
        return await this.storageService.uploadBase64Image(base64String, options);
      }
      
      // R2存储需要将Base64转换为文件
      if (this.storageType === 'r2') {
        // 将Base64转换为文件对象
        const file = this.base64ToFile(base64String, options.fileName || 'image.png');
        return await this.uploadFile(file, options);
      }
      
      throw new Error(`Base64 upload not supported for storage type: ${this.storageType}`);
    } catch (error) {
      throw new Error(`Base64 image upload failed: ${error.message}`);
    }
  }

  /**
   * 获取文件
   */
  async getFile(key) {
    try {
      return await this.storageService.getFile(key);
    } catch (error) {
      throw new Error(`Failed to get file: ${error.message}`);
    }
  }

  /**
   * 删除文件
   */
  async deleteFile(key) {
    try {
      return await this.storageService.deleteFile(key);
    } catch (error) {
      throw new Error(`Failed to delete file: ${error.message}`);
    }
  }

  /**
   * 批量删除文件
   */
  async deleteFiles(keys) {
    try {
      if (this.storageType === 'kv') {
        return await this.storageService.deleteFiles(keys);
      }
      
      // R2存储逐个删除
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
    try {
      return await this.storageService.listFiles(options);
    } catch (error) {
      throw new Error(`Failed to list files: ${error.message}`);
    }
  }

  /**
   * 获取文件URL
   */
  getFileUrl(key, isPublic = false) {
    try {
      return this.storageService.getFileUrl(key, isPublic);
    } catch (error) {
      // 如果getFileUrl方法不存在，返回默认URL
      return `/api/files/${key}`;
    }
  }

  /**
   * 获取存储统计
   */
  async getStorageStats() {
    try {
      if (this.storageType === 'kv' && this.storageService.getStorageStats) {
        return await this.storageService.getStorageStats();
      }
      
      // R2存储的统计信息
      if (this.storageType === 'r2') {
        // 这里可以添加R2存储的统计逻辑
        return {
          storage_type: 'r2',
          total_files: 'N/A',
          total_size: 'N/A',
          message: 'R2 storage stats not implemented'
        };
      }
      
      return {
        storage_type: this.storageType,
        total_files: 0,
        total_size: 0,
        message: 'Storage stats not available'
      };
    } catch (error) {
      return {
        storage_type: this.storageType,
        total_files: 0,
        total_size: 0,
        error: error.message
      };
    }
  }

  /**
   * 获取当前存储类型
   */
  getStorageType() {
    return this.storageType;
  }

  /**
   * 检查存储服务是否可用
   */
  isStorageAvailable() {
    return this.storageService !== null;
  }

  /**
   * Base64字符串转换为文件对象
   */
  base64ToFile(base64String, fileName) {
    const matches = base64String.match(/^data:(.+);base64,(.+)$/);
    if (!matches) {
      throw new Error('Invalid base64 string format');
    }

    const mimeType = matches[1];
    const base64Data = matches[2];
    const binaryString = atob(base64Data);
    const bytes = new Uint8Array(binaryString.length);
    
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    return new File([bytes], fileName, { type: mimeType });
  }

  /**
   * 获取存储服务实例
   */
  getStorageService() {
    return this.storageService;
  }
}

/**
 * 存储适配器工厂函数
 */
export function createStorageAdapter(env, options = {}) {
  return new StorageAdapter(env, options);
}