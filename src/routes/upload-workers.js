/**
 * File Upload Routes for Cloudflare Workers
 * 适配Workers运行时的文件上传路由
 */

import { R2StorageService, FileValidator } from '../services/r2-storage.js';
import { createAuthMiddleware } from '../middleware/auth-workers.js';
import { createLoggerMiddleware } from '../middleware/logger-workers.js';

/**
 * 创建文件上传路由
 */
export function createUploadRoutes(env) {
  const storageService = new R2StorageService(env);
  const fileValidator = new FileValidator({
    maxSize: 10 * 1024 * 1024, // 10MB
    allowedTypes: [
      'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain', 'text/csv', 'text/markdown',
      'application/json', 'application/xml'
    ],
    allowedExtensions: ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'pdf', 'doc', 'docx', 'txt', 'csv', 'md', 'json', 'xml']
  });

  const { authMiddleware, requireAdmin } = createAuthMiddleware(env);

  /**
   * 单文件上传
   */
  const uploadSingle = async (c) => {
    try {
      const formData = await c.req.formData();
      const file = formData.get('file');
      const folder = formData.get('folder') || 'uploads';
      const isPublic = formData.get('isPublic') === 'true';
      
      if (!file || !(file instanceof File)) {
        return c.json({
          success: false,
          error: 'No file provided',
          code: 'NO_FILE'
        }, 400);
      }

      // 获取用户信息
      const user = c.get('user');
      const uploadedBy = user ? user.id : 'anonymous';

      // 验证文件
      const validation = fileValidator.validate(file);
      if (!validation.isValid) {
        return c.json({
          success: false,
          error: 'File validation failed',
          code: 'VALIDATION_FAILED',
          details: validation.errors
        }, 400);
      }

      // 上传文件
      const result = await storageService.uploadFile(file, {
        folder,
        isPublic,
        metadata: {
          uploadedBy,
          originalName: file.name
        }
      });

      return c.json({
        success: true,
        data: {
          file: result.file,
          url: result.url,
          isDuplicate: result.isDuplicate || false
        },
        message: result.message
      });

    } catch (error) {
      c.get('logger')?.error('File upload failed', {
        error: error.message,
        userId: c.get('user')?.id
      });

      return c.json({
        success: false,
        error: 'File upload failed',
        code: 'UPLOAD_FAILED',
        details: error.message
      }, 500);
    }
  };

  /**
   * 多文件上传
   */
  const uploadMultiple = async (c) => {
    try {
      const formData = await c.req.formData();
      const files = formData.getAll('files');
      const folder = formData.get('folder') || 'uploads';
      const isPublic = formData.get('isPublic') === 'true';

      if (!files || files.length === 0) {
        return c.json({
          success: false,
          error: 'No files provided',
          code: 'NO_FILES'
        }, 400);
      }

      if (files.length > 10) {
        return c.json({
          success: false,
          error: 'Too many files. Maximum 10 files allowed',
          code: 'TOO_MANY_FILES'
        }, 400);
      }

      // 获取用户信息
      const user = c.get('user');
      const uploadedBy = user ? user.id : 'anonymous';

      // 验证所有文件
      const validationResults = files.map(file => ({
        file,
        validation: fileValidator.validate(file)
      }));

      const invalidFiles = validationResults.filter(r => !r.validation.isValid);
      if (invalidFiles.length > 0) {
        return c.json({
          success: false,
          error: 'Some files failed validation',
          code: 'VALIDATION_FAILED',
          details: invalidFiles.map(r => ({
            fileName: r.file.name,
            errors: r.validation.errors
          }))
        }, 400);
      }

      // 并行上传所有文件
      const uploadPromises = files.map(file =>
        storageService.uploadFile(file, {
          folder,
          isPublic,
          metadata: {
            uploadedBy,
            originalName: file.name
          }
        })
      );

      const results = await Promise.allSettled(uploadPromises);

      const successful = results
        .filter(r => r.status === 'fulfilled')
        .map(r => r.value);

      const failed = results
        .filter(r => r.status === 'rejected')
        .map((r, index) => ({
          fileName: files[index].name,
          error: r.reason.message
        }));

      return c.json({
        success: failed.length === 0,
        data: {
          successful: successful.map(r => ({
            file: r.file,
            url: r.url,
            isDuplicate: r.isDuplicate
          })),
          failed
        },
        message: `Uploaded ${successful.length} files successfully${failed.length > 0 ? `, ${failed.length} failed` : ''}`
      });

    } catch (error) {
      c.get('logger')?.error('Multiple file upload failed', {
        error: error.message,
        userId: c.get('user')?.id
      });

      return c.json({
        success: false,
        error: 'Multiple file upload failed',
        code: 'UPLOAD_FAILED',
        details: error.message
      }, 500);
    }
  };

  /**
   * Base64图片上传
   */
  const uploadBase64Image = async (c) => {
    try {
      const { image, folder = 'images', customName = null, isPublic = true } = await c.req.json();

      if (!image) {
        return c.json({
          success: false,
          error: 'No image data provided',
          code: 'NO_IMAGE_DATA'
        }, 400);
      }

      // 获取用户信息
      const user = c.get('user');
      const uploadedBy = user ? user.id : 'anonymous';

      // 上传图片
      const result = await storageService.uploadBase64Image(image, {
        folder,
        customName,
        isPublic,
        metadata: {
          uploadedBy,
          source: 'base64-upload'
        }
      });

      return c.json({
        success: true,
        data: {
          file: result.file,
          url: result.url,
          isDuplicate: result.isDuplicate || false
        },
        message: result.message
      });

    } catch (error) {
      c.get('logger')?.error('Base64 image upload failed', {
        error: error.message,
        userId: c.get('user')?.id
      });

      return c.json({
        success: false,
        error: 'Image upload failed',
        code: 'UPLOAD_FAILED',
        details: error.message
      }, 500);
    }
  };

  /**
   * 获取文件
   */
  const getFile = async (c) => {
    try {
      const { key } = c.req.param();
      const download = c.req.query('download') === 'true';

      if (!key) {
        return c.json({
          success: false,
          error: 'File key is required',
          code: 'NO_FILE_KEY'
        }, 400);
      }

      // 获取文件记录
      const fileRecord = await storageService.getFileRecord(key);
      if (!fileRecord) {
        return c.json({
          success: false,
          error: 'File not found',
          code: 'FILE_NOT_FOUND'
        }, 404);
      }

      // 检查权限
      if (!fileRecord.is_public) {
        const user = c.get('user');
        if (!user || (user.id !== fileRecord.uploaded_by && user.role !== 'admin')) {
          return c.json({
            success: false,
            error: 'Access denied',
            code: 'ACCESS_DENIED'
          }, 403);
        }
      }

      // 获取文件
      const file = await storageService.getFile(key);
      
      // 设置响应头
      const headers = new Headers();
      headers.set('Content-Type', file.httpMetadata.contentType || 'application/octet-stream');
      
      if (download) {
        headers.set('Content-Disposition', `attachment; filename="${fileRecord.original_name}"`);
      } else {
        headers.set('Content-Disposition', `inline; filename="${fileRecord.original_name}"`);
      }

      if (file.httpMetadata.cacheControl) {
        headers.set('Cache-Control', file.httpMetadata.cacheControl);
      }

      return new Response(file.body, { headers });

    } catch (error) {
      c.get('logger')?.error('File retrieval failed', {
        error: error.message,
        key: c.req.param('key'),
        userId: c.get('user')?.id
      });

      return c.json({
        success: false,
        error: 'File retrieval failed',
        code: 'RETRIEVAL_FAILED',
        details: error.message
      }, 500);
    }
  };

  /**
   * 删除文件
   */
  const deleteFile = async (c) => {
    try {
      const { key } = c.req.param();
      
      if (!key) {
        return c.json({
          success: false,
          error: 'File key is required',
          code: 'NO_FILE_KEY'
        }, 400);
      }

      // 获取文件记录
      const fileRecord = await storageService.getFileRecord(key);
      if (!fileRecord) {
        return c.json({
          success: false,
          error: 'File not found',
          code: 'FILE_NOT_FOUND'
        }, 404);
      }

      // 检查权限
      const user = c.get('user');
      if (!user || (user.id !== fileRecord.uploaded_by && user.role !== 'admin')) {
        return c.json({
          success: false,
          error: 'Access denied',
          code: 'ACCESS_DENIED'
        }, 403);
      }

      // 删除文件
      await storageService.deleteFile(key);

      c.get('logger')?.info('File deleted successfully', {
        key,
        userId: user.id,
        username: user.username
      });

      return c.json({
        success: true,
        message: 'File deleted successfully'
      });

    } catch (error) {
      c.get('logger')?.error('File deletion failed', {
        error: error.message,
        key: c.req.param('key'),
        userId: c.get('user')?.id
      });

      return c.json({
        success: false,
        error: 'File deletion failed',
        code: 'DELETION_FAILED',
        details: error.message
      }, 500);
    }
  };

  /**
   * 获取文件列表
   */
  const listFiles = async (c) => {
    try {
      const folder = c.req.query('folder') || '';
      const limit = parseInt(c.req.query('limit')) || 50;
      const cursor = c.req.query('cursor') || null;
      const includeMetadata = c.req.query('includeMetadata') !== 'false';

      const user = c.get('user');
      const isAdmin = user && user.role === 'admin';

      // 获取文件列表
      const result = await storageService.listFiles({
        prefix: folder,
        limit,
        cursor,
        includeMetadata
      });

      // 过滤权限
      const filteredFiles = result.files.filter(file => {
        if (!file.record) return false;
        
        // 管理员可以看到所有文件
        if (isAdmin) return true;
        
        // 公开文件
        if (file.record.is_public) return true;
        
        // 自己的文件
        return user && file.record.uploaded_by === user.id;
      });

      return c.json({
        success: true,
        data: {
          files: filteredFiles,
          pagination: {
            truncated: result.truncated,
            cursor: result.cursor,
            limit
          }
        }
      });

    } catch (error) {
      c.get('logger')?.error('File list retrieval failed', {
        error: error.message,
        userId: c.get('user')?.id
      });

      return c.json({
        success: false,
        error: 'File list retrieval failed',
        code: 'LIST_FAILED',
        details: error.message
      }, 500);
    }
  };

  /**
   * 获取存储统计
   */
  const getStorageStats = async (c) => {
    try {
      const user = c.get('user');
      const isAdmin = user && user.role === 'admin';

      if (!isAdmin) {
        return c.json({
          success: false,
          error: 'Admin access required',
          code: 'ADMIN_REQUIRED'
        }, 403);
      }

      const stats = await storageService.getStorageStats();

      return c.json({
        success: true,
        data: stats
      });

    } catch (error) {
      c.get('logger')?.error('Storage stats retrieval failed', {
        error: error.message,
        userId: c.get('user')?.id
      });

      return c.json({
        success: false,
        error: 'Storage stats retrieval failed',
        code: 'STATS_FAILED',
        details: error.message
      }, 500);
    }
  };

  /**
   * 生成预签名URL
   */
  const generatePresignedUrl = async (c) => {
    try {
      const { key } = c.req.param();
      const { expiresIn = 3600 } = await c.req.json();

      if (!key) {
        return c.json({
          success: false,
          error: 'File key is required',
          code: 'NO_FILE_KEY'
        }, 400);
      }

      // 获取文件记录
      const fileRecord = await storageService.getFileRecord(key);
      if (!fileRecord) {
        return c.json({
          success: false,
          error: 'File not found',
          code: 'FILE_NOT_FOUND'
        }, 404);
      }

      // 检查权限
      const user = c.get('user');
      if (!user || (user.id !== fileRecord.uploaded_by && user.role !== 'admin')) {
        return c.json({
          success: false,
          error: 'Access denied',
          code: 'ACCESS_DENIED'
        }, 403);
      }

      // 生成预签名URL
      const presignedUrl = await storageService.generatePresignedUrl(key, expiresIn);

      return c.json({
        success: true,
        data: presignedUrl
      });

    } catch (error) {
      c.get('logger')?.error('Presigned URL generation failed', {
        error: error.message,
        key: c.req.param('key'),
        userId: c.get('user')?.id
      });

      return c.json({
        success: false,
        error: 'Presigned URL generation failed',
        code: 'PRESIGNED_URL_FAILED',
        details: error.message
      }, 500);
    }
  };

  // 返回路由处理器
  return {
    uploadSingle,
    uploadMultiple,
    uploadBase64Image,
    getFile,
    deleteFile,
    listFiles,
    getStorageStats,
    generatePresignedUrl
  };
}

/**
 * 创建文件上传路由配置
 */
export function createUploadRouter(env) {
  const routes = createUploadRoutes(env);
  const { authMiddleware, optionalAuthMiddleware, requireAdmin } = createAuthMiddleware(env);
  const loggerMiddleware = createLoggerMiddleware(env);

  return {
    // 文件上传路由
    '/upload/single': ['POST', loggerMiddleware, authMiddleware, routes.uploadSingle],
    '/upload/multiple': ['POST', loggerMiddleware, authMiddleware, routes.uploadMultiple],
    '/upload/base64': ['POST', loggerMiddleware, authMiddleware, routes.uploadBase64Image],
    
    // 文件管理路由
    '/files': ['GET', loggerMiddleware, authMiddleware, routes.listFiles],
    '/files/stats': ['GET', loggerMiddleware, requireAdmin, routes.getStorageStats],
    '/files/:key': ['GET', loggerMiddleware, optionalAuthMiddleware, routes.getFile],
    '/files/:key': ['DELETE', loggerMiddleware, authMiddleware, routes.deleteFile],
    '/files/:key/presigned-url': ['POST', loggerMiddleware, authMiddleware, routes.generatePresignedUrl]
  };
}