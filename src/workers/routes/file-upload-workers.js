/**
 * Cloudflare Workers File Upload Routes
 * Handles file uploads, R2 storage integration, and file management
 */

import { Hono } from 'hono';
import { HTTPException } from 'hono/http-exception';
import { bearerAuth } from 'hono/bearer-auth';
import { getModels } from '../models/index-workers.js';
import { createAuthMiddleware } from '../middleware/auth-workers.js';
import { createRateLimitMiddleware } from '../middleware/rate-limit-workers.js';

/**
 * File upload configuration
 */
const UPLOAD_CONFIG = {
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
  ALLOWED_FILE_TYPES: [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
    'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain', 'text/csv', 'text/markdown',
    'application/json', 'application/xml', 'text/xml',
    'application/zip', 'application/x-zip-compressed', 'application/x-rar-compressed'
  ],
  ALLOWED_EXTENSIONS: [
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'txt', 'csv', 'md',
    'json', 'xml',
    'zip', 'rar'
  ],
  R2_BUCKET_PATH: 'files',
  CHUNK_SIZE: 5 * 1024 * 1024, // 5MB chunks
  MAX_CHUNKS: 10 // Maximum 50MB total
};

/**
 * File upload utilities
 */
class FileUploadUtils {
  
  /**
   * Validate file type and extension
   * @param {string} mimeType - File MIME type
   * @param {string} fileName - Original file name
   * @returns {boolean} - Validation result
   */
  static validateFileType(mimeType, fileName) {
    // Check MIME type
    if (!UPLOAD_CONFIG.ALLOWED_FILE_TYPES.includes(mimeType)) {
      return false;
    }
    
    // Check file extension
    const extension = fileName.split('.').pop().toLowerCase();
    if (!UPLOAD_CONFIG.ALLOWED_EXTENSIONS.includes(extension)) {
      return false;
    }
    
    return true;
  }
  
  /**
   * Generate unique file name
   * @param {string} originalName - Original file name
   * @param {string} userId - User ID
   * @returns {string} - Unique file name
   */
  static generateFileName(originalName, userId) {
    const timestamp = Date.now();
    const randomString = Math.random().toString(36).substring(2, 15);
    const extension = originalName.split('.').pop().toLowerCase();
    const sanitizedName = originalName.replace(/[^a-zA-Z0-9.-]/g, '_');
    
    return `${userId}/${timestamp}-${randomString}.${extension}`;
  }
  
  /**
   * Calculate file hash
   * @param {ArrayBuffer} buffer - File buffer
   * @returns {Promise<string>} - File hash
   */
  static async calculateFileHash(buffer) {
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }
  
  /**
   * Get file metadata
   * @param {File} file - File object
   * @param {string} userId - User ID
   * @returns {Object} - File metadata
   */
  static getFileMetadata(file, userId) {
    return {
      name: file.name,
      size: file.size,
      type: file.type,
      lastModified: file.lastModified,
      extension: file.name.split('.').pop().toLowerCase(),
      userId: userId,
      uploadedAt: new Date().toISOString()
    };
  }
  
  /**
   * Check for duplicate files
   * @param {string} hash - File hash
   * @param {string} userId - User ID
   * @param {Object} models - Database models
   * @returns {Promise<Object|null>} - Existing file or null
   */
  static async checkDuplicate(hash, userId, models) {
    try {
      const existingFile = await models.FileModel.findByHash(hash, userId);
      return existingFile;
    } catch (error) {
      console.error('Error checking duplicate file:', error);
      return null;
    }
  }
}

/**
 * Create file upload routes
 * @param {Object} env - Environment variables
 * @returns {Hono} - File upload router
 */
export function createFileUploadRoutes(env) {
  const router = new Hono();
  const models = getModels(env);
  const auth = createAuthMiddleware(env);
  const rateLimit = createRateLimitMiddleware(env);
  
  /**
   * Upload file endpoint
   * POST /api/files/upload
   */
  router.post('/upload', 
    auth.authenticate,
    rateLimit.createUploadLimit(),
    async (c) => {
      try {
        const userId = c.get('userId');
        const formData = await c.req.formData();
        const file = formData.get('file');
        const folderId = formData.get('folderId') || null;
        const tags = formData.get('tags') ? JSON.parse(formData.get('tags')) : [];
        const isPublic = formData.get('isPublic') === 'true';
        const expiresAt = formData.get('expiresAt') || null;
        
        // Validate file
        if (!file || !(file instanceof File)) {
          throw new HTTPException(400, { message: 'No file provided' });
        }
        
        // Validate file size
        if (file.size > UPLOAD_CONFIG.MAX_FILE_SIZE) {
          throw new HTTPException(413, { 
            message: `File size exceeds ${UPLOAD_CONFIG.MAX_FILE_SIZE / (1024 * 1024)}MB limit` 
          });
        }
        
        // Validate file type
        if (!FileUploadUtils.validateFileType(file.type, file.name)) {
          throw new HTTPException(415, { 
            message: 'File type not allowed',
            allowedTypes: UPLOAD_CONFIG.ALLOWED_FILE_TYPES
          });
        }
        
        // Read file content
        const buffer = await file.arrayBuffer();
        const fileHash = await FileUploadUtils.calculateFileHash(buffer);
        
        // Check for duplicate files
        const existingFile = await FileUploadUtils.checkDuplicate(fileHash, userId, models);
        if (existingFile) {
          return c.json({
            success: true,
            message: 'File already exists',
            file: existingFile.toJSON(),
            duplicate: true
          });
        }
        
        // Generate unique file name
        const fileName = FileUploadUtils.generateFileName(file.name, userId);
        const metadata = FileUploadUtils.getFileMetadata(file, userId);
        
        // Upload to R2
        const r2Key = `${UPLOAD_CONFIG.R2_BUCKET_PATH}/${fileName}`;
        await env.MAIMAI_R2.put(r2Key, buffer, {
          httpMetadata: {
            contentType: file.type,
            cacheControl: 'public, max-age=31536000'
          },
          customMetadata: {
            userId: userId,
            originalName: file.name,
            fileHash: fileHash,
            uploadedAt: metadata.uploadedAt
          }
        });
        
        // Create database record
        const fileRecord = await models.FileModel.create({
          userId: userId,
          name: file.name,
          fileName: fileName,
          originalName: file.name,
          mimeType: file.type,
          size: file.size,
          extension: metadata.extension,
          folderId: folderId,
          storagePath: r2Key,
          fileHash: fileHash,
          isPublic: isPublic,
          expiresAt: expiresAt,
          status: 'active'
        });
        
        // Add tags if provided
        if (tags.length > 0) {
          for (const tagName of tags) {
            await models.TagModel.addFileTag(fileRecord.id, tagName, userId);
          }
        }
        
        return c.json({
          success: true,
          message: 'File uploaded successfully',
          file: fileRecord.toJSON(),
          metadata: metadata
        });
        
      } catch (error) {
        console.error('File upload error:', error);
        
        if (error instanceof HTTPException) {
          throw error;
        }
        
        throw new HTTPException(500, {
          message: 'File upload failed',
          error: error.message
        });
      }
    }
  );
  
  /**
   * Chunked upload initialization
   * POST /api/files/upload/chunk/init
   */
  router.post('/upload/chunk/init',
    auth.authenticate,
    rateLimit.createUploadLimit(),
    async (c) => {
      try {
        const userId = c.get('userId');
        const { fileName, fileSize, fileType, chunkSize = UPLOAD_CONFIG.CHUNK_SIZE } = await c.req.json();
        
        // Validate parameters
        if (!fileName || !fileSize || !fileType) {
          throw new HTTPException(400, { message: 'Missing required parameters' });
        }
        
        // Validate file size
        if (fileSize > UPLOAD_CONFIG.MAX_FILE_SIZE) {
          throw new HTTPException(413, { 
            message: `File size exceeds ${UPLOAD_CONFIG.MAX_FILE_SIZE / (1024 * 1024)}MB limit` 
          });
        }
        
        // Validate file type
        if (!FileUploadUtils.validateFileType(fileType, fileName)) {
          throw new HTTPException(415, { message: 'File type not allowed' });
        }
        
        // Calculate chunks
        const totalChunks = Math.ceil(fileSize / chunkSize);
        if (totalChunks > UPLOAD_CONFIG.MAX_CHUNKS) {
          throw new HTTPException(400, { 
            message: 'File too large for chunked upload' 
          });
        }
        
        // Generate upload session ID
        const uploadId = `${userId}-${Date.now()}-${Math.random().toString(36).substring(7)}`;
        
        // Store upload session in KV
        const sessionData = {
          userId,
          fileName,
          fileSize,
          fileType,
          chunkSize,
          totalChunks,
          uploadId,
          createdAt: new Date().toISOString(),
          uploadedChunks: []
        };
        
        await env.MAIMAI_KV.put(`upload_session:${uploadId}`, JSON.stringify(sessionData), {
          expirationTtl: 3600 // 1 hour
        });
        
        return c.json({
          success: true,
          uploadId,
          totalChunks,
          chunkSize,
          sessionData
        });
        
      } catch (error) {
        console.error('Chunked upload initialization error:', error);
        
        if (error instanceof HTTPException) {
          throw error;
        }
        
        throw new HTTPException(500, {
          message: 'Failed to initialize chunked upload',
          error: error.message
        });
      }
    }
  );
  
  /**
   * Upload chunk
   * POST /api/files/upload/chunk/:uploadId/:chunkIndex
   */
  router.post('/upload/chunk/:uploadId/:chunkIndex',
    auth.authenticate,
    rateLimit.createUploadLimit(),
    async (c) => {
      try {
        const userId = c.get('userId');
        const { uploadId, chunkIndex } = c.req.param();
        const chunkIndexNum = parseInt(chunkIndex);
        
        // Get upload session
        const sessionData = await env.MAIMAI_KV.get(`upload_session:${uploadId}`);
        if (!sessionData) {
          throw new HTTPException(404, { message: 'Upload session not found' });
        }
        
        const session = JSON.parse(sessionData);
        
        // Validate user ownership
        if (session.userId !== userId) {
          throw new HTTPException(403, { message: 'Access denied' });
        }
        
        // Validate chunk index
        if (chunkIndexNum < 0 || chunkIndexNum >= session.totalChunks) {
          throw new HTTPException(400, { message: 'Invalid chunk index' });
        }
        
        // Get chunk data
        const formData = await c.req.formData();
        const chunk = formData.get('chunk');
        
        if (!chunk || !(chunk instanceof File)) {
          throw new HTTPException(400, { message: 'No chunk data provided' });
        }
        
        // Store chunk in R2
        const chunkKey = `upload_chunks/${uploadId}/chunk_${chunkIndexNum}`;
        const buffer = await chunk.arrayBuffer();
        
        await env.MAIMAI_R2.put(chunkKey, buffer, {
          httpMetadata: {
            contentType: 'application/octet-stream'
          }
        });
        
        // Update session
        session.uploadedChunks.push(chunkIndexNum);
        await env.MAIMAI_KV.put(`upload_session:${uploadId}`, JSON.stringify(session), {
          expirationTtl: 3600
        });
        
        return c.json({
          success: true,
          message: 'Chunk uploaded successfully',
          chunkIndex: chunkIndexNum,
          uploadedChunks: session.uploadedChunks.length,
          totalChunks: session.totalChunks
        });
        
      } catch (error) {
        console.error('Chunk upload error:', error);
        
        if (error instanceof HTTPException) {
          throw error;
        }
        
        throw new HTTPException(500, {
          message: 'Chunk upload failed',
          error: error.message
        });
      }
    }
  );
  
  /**
   * Complete chunked upload
   * POST /api/files/upload/chunk/complete/:uploadId
   */
  router.post('/upload/chunk/complete/:uploadId',
    auth.authenticate,
    async (c) => {
      try {
        const userId = c.get('userId');
        const { uploadId } = c.req.param();
        const { folderId, tags, isPublic, expiresAt } = await c.req.json();
        
        // Get upload session
        const sessionData = await env.MAIMAI_KV.get(`upload_session:${uploadId}`);
        if (!sessionData) {
          throw new HTTPException(404, { message: 'Upload session not found' });
        }
        
        const session = JSON.parse(sessionData);
        
        // Validate user ownership
        if (session.userId !== userId) {
          throw new HTTPException(403, { message: 'Access denied' });
        }
        
        // Check if all chunks are uploaded
        if (session.uploadedChunks.length !== session.totalChunks) {
          throw new HTTPException(400, { 
            message: 'Not all chunks are uploaded',
            uploaded: session.uploadedChunks.length,
            total: session.totalChunks
          });
        }
        
        // Combine chunks
        const chunks = [];
        for (let i = 0; i < session.totalChunks; i++) {
          const chunkKey = `upload_chunks/${uploadId}/chunk_${i}`;
          const chunk = await env.MAIMAI_R2.get(chunkKey);
          
          if (!chunk) {
            throw new HTTPException(500, { 
              message: `Chunk ${i} not found` 
            });
          }
          
          chunks.push(await chunk.arrayBuffer());
        }
        
        // Combine all chunks
        const totalSize = chunks.reduce((sum, chunk) => sum + chunk.byteLength, 0);
        const combinedBuffer = new Uint8Array(totalSize);
        
        let offset = 0;
        for (const chunk of chunks) {
          combinedBuffer.set(new Uint8Array(chunk), offset);
          offset += chunk.byteLength;
        }
        
        // Calculate file hash
        const fileHash = await FileUploadUtils.calculateFileHash(combinedBuffer.buffer);
        
        // Check for duplicate files
        const existingFile = await FileUploadUtils.checkDuplicate(fileHash, userId, models);
        if (existingFile) {
          // Clean up chunks
          await cleanupChunks(env, uploadId, session.totalChunks);
          
          return c.json({
            success: true,
            message: 'File already exists',
            file: existingFile.toJSON(),
            duplicate: true
          });
        }
        
        // Generate unique file name
        const fileName = FileUploadUtils.generateFileName(session.fileName, userId);
        const metadata = {
          name: session.fileName,
          size: totalSize,
          type: session.fileType,
          extension: session.fileName.split('.').pop().toLowerCase(),
          userId: userId,
          uploadedAt: new Date().toISOString()
        };
        
        // Upload to R2
        const r2Key = `${UPLOAD_CONFIG.R2_BUCKET_PATH}/${fileName}`;
        await env.MAIMAI_R2.put(r2Key, combinedBuffer, {
          httpMetadata: {
            contentType: session.fileType,
            cacheControl: 'public, max-age=31536000'
          },
          customMetadata: {
            userId: userId,
            originalName: session.fileName,
            fileHash: fileHash,
            uploadedAt: metadata.uploadedAt
          }
        });
        
        // Create database record
        const fileRecord = await models.FileModel.create({
          userId: userId,
          name: session.fileName,
          fileName: fileName,
          originalName: session.fileName,
          mimeType: session.fileType,
          size: totalSize,
          extension: metadata.extension,
          folderId: folderId || null,
          storagePath: r2Key,
          fileHash: fileHash,
          isPublic: isPublic || false,
          expiresAt: expiresAt || null,
          status: 'active'
        });
        
        // Add tags if provided
        if (tags && tags.length > 0) {
          for (const tagName of tags) {
            await models.TagModel.addFileTag(fileRecord.id, tagName, userId);
          }
        }
        
        // Clean up chunks
        await cleanupChunks(env, uploadId, session.totalChunks);
        
        // Remove upload session
        await env.MAIMAI_KV.delete(`upload_session:${uploadId}`);
        
        return c.json({
          success: true,
          message: 'File uploaded successfully',
          file: fileRecord.toJSON(),
          metadata: metadata
        });
        
      } catch (error) {
        console.error('Chunked upload completion error:', error);
        
        if (error instanceof HTTPException) {
          throw error;
        }
        
        throw new HTTPException(500, {
          message: 'Failed to complete chunked upload',
          error: error.message
        });
      }
    }
  );
  
  /**
   * Get upload progress
   * GET /api/files/upload/progress/:uploadId
   */
  router.get('/upload/progress/:uploadId',
    auth.authenticate,
    async (c) => {
      try {
        const userId = c.get('userId');
        const { uploadId } = c.req.param();
        
        // Get upload session
        const sessionData = await env.MAIMAI_KV.get(`upload_session:${uploadId}`);
        if (!sessionData) {
          throw new HTTPException(404, { message: 'Upload session not found' });
        }
        
        const session = JSON.parse(sessionData);
        
        // Validate user ownership
        if (session.userId !== userId) {
          throw new HTTPException(403, { message: 'Access denied' });
        }
        
        return c.json({
          success: true,
          uploadId,
          progress: {
            uploadedChunks: session.uploadedChunks.length,
            totalChunks: session.totalChunks,
            percentage: Math.round((session.uploadedChunks.length / session.totalChunks) * 100)
          },
          sessionData: {
            fileName: session.fileName,
            fileSize: session.fileSize,
            fileType: session.fileType
          }
        });
        
      } catch (error) {
        console.error('Upload progress check error:', error);
        
        if (error instanceof HTTPException) {
          throw error;
        }
        
        throw new HTTPException(500, {
          message: 'Failed to get upload progress',
          error: error.message
        });
      }
    }
  );
  
  /**
   * Download file
   * GET /api/files/download/:fileId
   */
  router.get('/download/:fileId',
    auth.optionalAuthenticate,
    async (c) => {
      try {
        const userId = c.get('userId');
        const { fileId } = c.req.param();
        
        // Get file record
        const file = await models.FileModel.findById(fileId);
        if (!file) {
          throw new HTTPException(404, { message: 'File not found' });
        }
        
        // Check access permissions
        if (!file.isPublic && file.userId !== userId) {
          throw new HTTPException(403, { message: 'Access denied' });
        }
        
        // Check if file is expired
        if (file.expiresAt && new Date(file.expiresAt) < new Date()) {
          throw new HTTPException(410, { message: 'File has expired' });
        }
        
        // Get file from R2
        const object = await env.MAIMAI_R2.get(file.storagePath);
        if (!object) {
          throw new HTTPException(404, { message: 'File not found in storage' });
        }
        
        // Update download count
        await models.FileModel.updateDownloads(fileId, file.downloads + 1);
        
        // Return file with proper headers
        const headers = new Headers();
        headers.set('Content-Type', file.mimeType);
        headers.set('Content-Disposition', `attachment; filename="${file.originalName}"`);
        headers.set('Cache-Control', 'public, max-age=31536000');
        
        return new Response(object.body, {
          headers,
          status: 200
        });
        
      } catch (error) {
        console.error('File download error:', error);
        
        if (error instanceof HTTPException) {
          throw error;
        }
        
        throw new HTTPException(500, {
          message: 'File download failed',
          error: error.message
        });
      }
    }
  );
  
  /**
   * Get file URL (for public files)
   * GET /api/files/url/:fileId
   */
  router.get('/url/:fileId',
    auth.optionalAuthenticate,
    async (c) => {
      try {
        const userId = c.get('userId');
        const { fileId } = c.req.param();
        
        // Get file record
        const file = await models.FileModel.findById(fileId);
        if (!file) {
          throw new HTTPException(404, { message: 'File not found' });
        }
        
        // Check access permissions
        if (!file.isPublic && file.userId !== userId) {
          throw new HTTPException(403, { message: 'Access denied' });
        }
        
        // Check if file is expired
        if (file.expiresAt && new Date(file.expiresAt) < new Date()) {
          throw new HTTPException(410, { message: 'File has expired' });
        }
        
        // Generate signed URL (valid for 1 hour)
        const signedUrl = await env.MAIMAI_R2.createSignedUrl(file.storagePath, {
          expiresIn: 3600 // 1 hour
        });
        
        return c.json({
          success: true,
          url: signedUrl,
          expiresAt: new Date(Date.now() + 3600 * 1000).toISOString(),
          file: {
            id: file.id,
            name: file.name,
            mimeType: file.mimeType,
            size: file.size
          }
        });
        
      } catch (error) {
        console.error('File URL generation error:', error);
        
        if (error instanceof HTTPException) {
          throw error;
        }
        
        throw new HTTPException(500, {
          message: 'Failed to generate file URL',
          error: error.message
        });
      }
    }
  );
  
  return router;
}

/**
 * Helper function to cleanup upload chunks
 * @param {Object} env - Environment variables
 * @param {string} uploadId - Upload session ID
 * @param {number} totalChunks - Total number of chunks
 */
async function cleanupChunks(env, uploadId, totalChunks) {
  try {
    const deletePromises = [];
    
    for (let i = 0; i < totalChunks; i++) {
      const chunkKey = `upload_chunks/${uploadId}/chunk_${i}`;
      deletePromises.push(env.MAIMAI_R2.delete(chunkKey));
    }
    
    await Promise.all(deletePromises);
  } catch (error) {
    console.error('Error cleaning up chunks:', error);
  }
}

/**
 * Create file upload routes with environment
 * @param {Object} env - Environment variables
 * @returns {Hono} - File upload router
 */
export default function createFileUploadRouter(env) {
  return createFileUploadRoutes(env);
}