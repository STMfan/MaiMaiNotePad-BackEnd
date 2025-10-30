/**
 * Cloudflare Workers Storage Service
 * R2 storage adapter for Cloudflare Workers with file management and CDN features
 */

import { HTTPException } from 'hono/http-exception';

/**
 * Storage Configuration
 */
const STORAGE_CONFIG = {
  maxFileSize: 100 * 1024 * 1024, // 100MB
  maxFilesPerRequest: 10,
  allowedMimeTypes: [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
    'application/pdf', 'application/json', 'text/plain', 'text/markdown',
    'application/octet-stream'
  ],
  defaultCacheControl: 'public, max-age=31536000', // 1 year
  enableVirusScan: false,
  enableImageProcessing: true,
  bucketName: 'maimai-storage',
  cdnDomain: null,
  enableSignedUrls: true,
  signedUrlExpiry: 3600 // 1 hour
};

/**
 * File Metadata Class
 */
export class FileMetadata {
  constructor(file) {
    this.name = file.name;
    this.size = file.size;
    this.type = file.type;
    this.lastModified = file.lastModified;
    this.hash = null;
    this.metadata = {};
  }

  /**
   * Generate file hash
   * @param {File} file - File object
   * @returns {string} File hash
   */
  static async generateHash(file) {
    const buffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  /**
   * Validate file
   * @param {Object} options - Validation options
   * @returns {Object} Validation result
   */
  validate(options = {}) {
    const { maxFileSize = STORAGE_CONFIG.maxFileSize, allowedMimeTypes = STORAGE_CONFIG.allowedMimeTypes } = options;
    
    const errors = [];

    if (this.size > maxFileSize) {
      errors.push(`File size exceeds maximum allowed size of ${maxFileSize} bytes`);
    }

    if (!allowedMimeTypes.includes(this.type)) {
      errors.push(`File type ${this.type} is not allowed`);
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }
}

/**
 * Storage Service Class
 */
export class StorageService {
  constructor(env) {
    this.env = env;
    this.bucket = env.STORAGE;
    this.config = { ...STORAGE_CONFIG, ...env.STORAGE_CONFIG };
  }

  /**
   * Validate storage configuration
   * @throws {HTTPException} If configuration is invalid
   */
  validateConfiguration() {
    if (!this.bucket) {
      throw new HTTPException(500, { message: 'Storage bucket not configured' });
    }
  }

  /**
   * Generate unique file key
   * @param {string} originalName - Original file name
   * @param {string} prefix - File prefix
   * @returns {string} Unique file key
   */
  generateFileKey(originalName, prefix = '') {
    const timestamp = Date.now();
    const randomString = crypto.randomUUID().split('-')[0];
    const sanitizedName = originalName.replace(/[^a-zA-Z0-9.-]/g, '_');
    
    return `${prefix}${timestamp}_${randomString}_${sanitizedName}`;
  }

  /**
   * Upload file to storage
   * @param {File} file - File to upload
   * @param {Object} options - Upload options
   * @returns {Object} Upload result
   */
  async uploadFile(file, options = {}) {
    this.validateConfiguration();

    const { prefix = '', metadata = {}, overwrite = false } = options;
    
    try {
      // Validate file
      const fileMetadata = new FileMetadata(file);
      const validation = fileMetadata.validate();
      
      if (!validation.valid) {
        throw new HTTPException(400, { message: `File validation failed: ${validation.errors.join(', ')}` });
      }

      // Generate file hash for deduplication
      const fileHash = await FileMetadata.generateHash(file);
      fileMetadata.hash = fileHash;

      // Generate file key
      const fileKey = this.generateFileKey(file.name, prefix);
      
      // Check if file already exists
      if (!overwrite) {
        try {
          const existingFile = await this.bucket.head(fileKey);
          if (existingFile) {
            throw new HTTPException(409, { message: 'File already exists' });
          }
        } catch (error) {
          if (error.status !== 404) {
            throw error;
          }
        }
      }

      // Prepare upload options
      const uploadOptions = {
        httpMetadata: {
          contentType: file.type,
          contentLength: file.size,
          cacheControl: this.config.defaultCacheControl,
          contentDisposition: `inline; filename="${file.name}"`
        },
        customMetadata: {
          originalName: file.name,
          fileHash,
          uploadTimestamp: Date.now().toString(),
          ...metadata
        }
      };

      // Upload file
      const result = await this.bucket.put(fileKey, file.stream(), uploadOptions);

      return {
        success: true,
        key: fileKey,
        etag: result.etag,
        size: file.size,
        type: file.type,
        url: this.getPublicUrl(fileKey),
        metadata: fileMetadata,
        uploadedAt: new Date().toISOString()
      };

    } catch (error) {
      console.error('File upload error:', error);
      throw new HTTPException(500, { 
        message: 'File upload failed',
        cause: error.message 
      });
    }
  }

  /**
   * Download file from storage
   * @param {string} fileKey - File key
   * @param {Object} options - Download options
   * @returns {Object} File data
   */
  async downloadFile(fileKey, options = {}) {
    this.validateConfiguration();

    try {
      const { asAttachment = false, filename = null } = options;
      
      // Get file from storage
      const file = await this.bucket.get(fileKey);
      
      if (!file) {
        throw new HTTPException(404, { message: 'File not found' });
      }

      // Prepare response headers
      const headers = new Headers();
      
      if (file.httpMetadata) {
        if (file.httpMetadata.contentType) {
          headers.set('Content-Type', file.httpMetadata.contentType);
        }
        if (file.httpMetadata.contentLength) {
          headers.set('Content-Length', file.httpMetadata.contentLength.toString());
        }
        if (file.httpMetadata.cacheControl) {
          headers.set('Cache-Control', file.httpMetadata.cacheControl);
        }
      }

      if (asAttachment) {
        const downloadFilename = filename || fileKey.split('_').pop() || 'download';
        headers.set('Content-Disposition', `attachment; filename="${downloadFilename}"`);
      }

      return {
        success: true,
        file: file.body,
        headers,
        metadata: file.customMetadata,
        httpMetadata: file.httpMetadata
      };

    } catch (error) {
      console.error('File download error:', error);
      throw new HTTPException(500, { 
        message: 'File download failed',
        cause: error.message 
      });
    }
  }

  /**
   * Get file metadata
   * @param {string} fileKey - File key
   * @returns {Object} File metadata
   */
  async getFileMetadata(fileKey) {
    this.validateConfiguration();

    try {
      const metadata = await this.bucket.head(fileKey);
      
      if (!metadata) {
        throw new HTTPException(404, { message: 'File not found' });
      }

      return {
        success: true,
        key: fileKey,
        size: metadata.size,
        etag: metadata.etag,
        uploaded: metadata.uploaded,
        httpMetadata: metadata.httpMetadata,
        customMetadata: metadata.customMetadata,
        url: this.getPublicUrl(fileKey)
      };

    } catch (error) {
      console.error('Get file metadata error:', error);
      throw new HTTPException(500, { 
        message: 'Failed to get file metadata',
        cause: error.message 
      });
    }
  }

  /**
   * Delete file from storage
   * @param {string} fileKey - File key
   * @returns {Object} Delete result
   */
  async deleteFile(fileKey) {
    this.validateConfiguration();

    try {
      await this.bucket.delete(fileKey);
      
      return {
        success: true,
        key: fileKey,
        deletedAt: new Date().toISOString()
      };

    } catch (error) {
      console.error('File delete error:', error);
      throw new HTTPException(500, { 
        message: 'File deletion failed',
        cause: error.message 
      });
    }
  }

  /**
   * List files in storage
   * @param {Object} options - List options
   * @returns {Object} List result
   */
  async listFiles(options = {}) {
    this.validateConfiguration();

    const { prefix = '', limit = 100, cursor = null } = options;
    
    try {
      const listOptions = {
        prefix,
        limit: Math.min(limit, 1000) // R2 limit
      };

      if (cursor) {
        listOptions.cursor = cursor;
      }

      const result = await this.bucket.list(listOptions);
      
      return {
        success: true,
        files: result.objects.map(obj => ({
          key: obj.key,
          size: obj.size,
          etag: obj.etag,
          uploaded: obj.uploaded,
          httpMetadata: obj.httpMetadata,
          customMetadata: obj.customMetadata,
          url: this.getPublicUrl(obj.key)
        })),
        truncated: result.truncated,
        cursor: result.cursor,
        delimiter: result.delimiter,
        commonPrefixes: result.commonPrefixes
      };

    } catch (error) {
      console.error('List files error:', error);
      throw new HTTPException(500, { 
        message: 'Failed to list files',
        cause: error.message 
      });
    }
  }

  /**
   * Get public URL for file
   * @param {string} fileKey - File key
   * @returns {string} Public URL
   */
  getPublicUrl(fileKey) {
    if (this.config.cdnDomain) {
      return `https://${this.config.cdnDomain}/${fileKey}`;
    }
    
    // Generate signed URL if enabled
    if (this.config.enableSignedUrls) {
      return this.generateSignedUrl(fileKey);
    }
    
    return `/api/storage/file/${fileKey}`;
  }

  /**
   * Generate signed URL for file
   * @param {string} fileKey - File key
   * @param {Object} options - URL options
   * @returns {string} Signed URL
   */
  generateSignedUrl(fileKey, options = {}) {
    const expiry = options.expiry || this.config.signedUrlExpiry;
    const expires = Math.floor(Date.now() / 1000) + expiry;
    
    // Simple signed URL implementation
    const signature = this.generateSignature(fileKey, expires);
    
    return `/api/storage/file/${fileKey}?expires=${expires}&signature=${signature}`;
  }

  /**
   * Generate signature for signed URL
   * @param {string} fileKey - File key
   * @param {number} expires - Expiration timestamp
   * @returns {string} Signature
   */
  generateSignature(fileKey, expires) {
    const data = `${fileKey}:${expires}`;
    
    // Simple HMAC-like signature (in production, use proper crypto)
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(data);
    
    // Use a simple hash for now (in production, use proper HMAC)
    const hashBuffer = crypto.subtle.digest('SHA-256', dataBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('').substring(0, 32);
  }

  /**
   * Validate signed URL
   * @param {string} fileKey - File key
   * @param {string} signature - Signature
   * @param {number} expires - Expiration timestamp
   * @returns {boolean} Valid signature
   */
  validateSignature(fileKey, signature, expires) {
    const now = Math.floor(Date.now() / 1000);
    
    if (now > expires) {
      return false;
    }
    
    const expectedSignature = this.generateSignature(fileKey, expires);
    return signature === expectedSignature;
  }

  /**
   * Copy file
   * @param {string} sourceKey - Source file key
   * @param {string} destinationKey - Destination file key
   * @returns {Object} Copy result
   */
  async copyFile(sourceKey, destinationKey) {
    this.validateConfiguration();

    try {
      const result = await this.bucket.copy(sourceKey, destinationKey);
      
      return {
        success: true,
        sourceKey,
        destinationKey,
        etag: result.etag
      };

    } catch (error) {
      console.error('File copy error:', error);
      throw new HTTPException(500, { 
        message: 'File copy failed',
        cause: error.message 
      });
    }
  }

  /**
   * Move file (copy and delete)
   * @param {string} sourceKey - Source file key
   * @param {string} destinationKey - Destination file key
   * @returns {Object} Move result
   */
  async moveFile(sourceKey, destinationKey) {
    try {
      const copyResult = await this.copyFile(sourceKey, destinationKey);
      await this.deleteFile(sourceKey);
      
      return {
        success: true,
        sourceKey,
        destinationKey,
        etag: copyResult.etag
      };

    } catch (error) {
      console.error('File move error:', error);
      throw new HTTPException(500, { 
        message: 'File move failed',
        cause: error.message 
      });
    }
  }

  /**
   * Get storage statistics
   * @returns {Object} Storage statistics
   */
  async getStats() {
    this.validateConfiguration();

    try {
      // List all files to calculate statistics
      let totalFiles = 0;
      let totalSize = 0;
      let cursor = null;
      
      do {
        const result = await this.listFiles({ cursor, limit: 1000 });
        totalFiles += result.files.length;
        
        for (const file of result.files) {
          totalSize += file.size;
        }
        
        cursor = result.cursor;
      } while (cursor);

      return {
        success: true,
        totalFiles,
        totalSize,
        averageFileSize: totalFiles > 0 ? Math.round(totalSize / totalFiles) : 0,
        config: this.config
      };

    } catch (error) {
      console.error('Get storage stats error:', error);
      throw new HTTPException(500, { 
        message: 'Failed to get storage statistics',
        cause: error.message 
      });
    }
  }

  /**
   * Health check
   * @returns {Object} Health status
   */
  async healthCheck() {
    try {
      this.validateConfiguration();
      
      // Test with a small file
      const testKey = `health/${crypto.randomUUID()}.txt`;
      const testContent = 'health check';
      
      // Upload test file
      const testFile = new File([testContent], 'test.txt', { type: 'text/plain' });
      await this.bucket.put(testKey, testFile.stream());
      
      // Verify file exists
      const metadata = await this.bucket.head(testKey);
      
      // Clean up
      await this.bucket.delete(testKey);
      
      return {
        status: metadata ? 'healthy' : 'unhealthy',
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      return {
        status: 'unhealthy',
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  }
}

/**
 * Storage Service Factory
 * @param {Object} env - Environment variables
 * @returns {StorageService} Storage service instance
 */
export function createStorageService(env) {
  return new StorageService(env);
}

/**
 * Storage utilities
 */
export const StorageUtils = {
  /**
   * Extract file extension from filename
   * @param {string} filename - Filename
   * @returns {string} File extension
   */
  getFileExtension(filename) {
    const parts = filename.split('.');
    return parts.length > 1 ? parts.pop().toLowerCase() : '';
  },

  /**
   * Get MIME type from file extension
   * @param {string} extension - File extension
   * @returns {string} MIME type
   */
  getMimeType(extension) {
    const mimeTypes = {
      'jpg': 'image/jpeg',
      'jpeg': 'image/jpeg',
      'png': 'image/png',
      'gif': 'image/gif',
      'webp': 'image/webp',
      'svg': 'image/svg+xml',
      'pdf': 'application/pdf',
      'json': 'application/json',
      'txt': 'text/plain',
      'md': 'text/markdown',
      'zip': 'application/zip',
      'mp4': 'video/mp4',
      'mp3': 'audio/mpeg'
    };
    
    return mimeTypes[extension.toLowerCase()] || 'application/octet-stream';
  },

  /**
   * Generate human-readable file size
   * @param {number} bytes - File size in bytes
   * @returns {string} Human-readable size
   */
  formatFileSize(bytes) {
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${size.toFixed(2)} ${units[unitIndex]}`;
  },

  /**
   * Validate filename
   * @param {string} filename - Filename to validate
   * @returns {Object} Validation result
   */
  validateFilename(filename) {
    const errors = [];
    
    if (!filename || filename.length === 0) {
      errors.push('Filename cannot be empty');
    }
    
    if (filename.length > 255) {
      errors.push('Filename too long (max 255 characters)');
    }
    
    if (filename.includes('..')) {
      errors.push('Filename cannot contain ".."');
    }
    
    if (filename.includes('\0')) {
      errors.push('Filename cannot contain null characters');
    }
    
    return {
      valid: errors.length === 0,
      errors
    };
  }
};

export default {
  StorageService,
  FileMetadata,
  createStorageService,
  StorageUtils
};