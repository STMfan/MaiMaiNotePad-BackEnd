/**
 * Cloudflare Workers File Upload Routes - Native Implementation
 * Handles file uploads, R2 storage integration, and file management
 * No Hono framework dependencies
 */

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
}

/**
 * Handle file upload request
 * @param {Request} request - HTTP request
 * @param {Object} env - Environment variables
 * @param {string} userId - User ID
 * @returns {Response} - HTTP response
 */
export async function handleFileUpload(request, env, userId) {
  try {
    const formData = await request.formData();
    const file = formData.get('file');
    const folderId = formData.get('folderId') || null;
    const tags = formData.get('tags') ? JSON.parse(formData.get('tags')) : [];
    const isPublic = formData.get('isPublic') === 'true';
    const expiresAt = formData.get('expiresAt') || null;
    
    // Validate file
    if (!file || !(file instanceof File)) {
      return new Response(JSON.stringify({
        success: false,
        error: 'No file provided'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Validate file size
    if (file.size > UPLOAD_CONFIG.MAX_FILE_SIZE) {
      return new Response(JSON.stringify({
        success: false,
        error: `File size exceeds ${UPLOAD_CONFIG.MAX_FILE_SIZE / (1024 * 1024)}MB limit`
      }), {
        status: 413,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Validate file type
    if (!FileUploadUtils.validateFileType(file.type, file.name)) {
      return new Response(JSON.stringify({
        success: false,
        error: 'File type not allowed',
        allowedTypes: UPLOAD_CONFIG.ALLOWED_FILE_TYPES
      }), {
        status: 415,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Read file content
    const buffer = await file.arrayBuffer();
    const fileHash = await FileUploadUtils.calculateFileHash(buffer);
    
    // Generate unique file name
    const fileName = FileUploadUtils.generateFileName(file.name, userId);
    const metadata = FileUploadUtils.getFileMetadata(file, userId);
    
    // Upload to R2
    const r2Key = `${UPLOAD_CONFIG.R2_BUCKET_PATH}/${fileName}`;
    await env.STORAGE.put(r2Key, buffer, {
      httpMetadata: {
        contentType: file.type,
        cacheControl: 'public, max-age=31536000'
      },
      customMetadata: {
        userId: userId,
        originalName: file.name,
        fileHash: fileHash,
        uploadedAt: metadata.uploadedAt,
        folderId: folderId || '',
        tags: JSON.stringify(tags),
        isPublic: isPublic.toString(),
        expiresAt: expiresAt || ''
      }
    });
    
    // Generate file record for database (simplified)
    const fileRecord = {
      id: crypto.randomUUID(),
      name: file.name,
      originalName: file.name,
      fileName: fileName,
      filePath: r2Key,
      fileSize: file.size,
      mimeType: file.type,
      extension: metadata.extension,
      fileHash: fileHash,
      userId: userId,
      folderId: folderId,
      isPublic: isPublic,
      tags: tags,
      expiresAt: expiresAt,
      uploadedAt: metadata.uploadedAt,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    
    // Store file record in D1 database (simplified)
    try {
      await env.DB.prepare(`
        INSERT INTO files (
          id, name, original_name, file_name, file_path, file_size, 
          mime_type, extension, file_hash, user_id, folder_id, 
          is_public, tags, expires_at, uploaded_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).bind(
        fileRecord.id,
        fileRecord.name,
        fileRecord.originalName,
        fileRecord.fileName,
        fileRecord.filePath,
        fileRecord.fileSize,
        fileRecord.mimeType,
        fileRecord.extension,
        fileRecord.fileHash,
        fileRecord.userId,
        fileRecord.folderId,
        fileRecord.isPublic ? 1 : 0,
        JSON.stringify(fileRecord.tags),
        fileRecord.expiresAt,
        fileRecord.uploadedAt,
        fileRecord.createdAt,
        fileRecord.updatedAt
      ).run();
    } catch (dbError) {
      console.error('Database error:', dbError);
      // Don't fail the upload if database fails, but log it
    }
    
    return new Response(JSON.stringify({
      success: true,
      message: 'File uploaded successfully',
      file: {
        id: fileRecord.id,
        name: file.name,
        size: file.size,
        type: file.type,
        uploadedAt: metadata.uploadedAt,
        url: `/api/files/${fileRecord.id}`
      }
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    console.error('File upload error:', error);
    return new Response(JSON.stringify({
      success: false,
      error: 'Internal server error during file upload'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Handle file download request
 * @param {Request} request - HTTP request
 * @param {Object} env - Environment variables
 * @param {string} fileId - File ID
 * @returns {Response} - HTTP response
 */
export async function handleFileDownload(request, env, fileId) {
  try {
    // Get file record from database (simplified)
    const fileRecord = await env.DB.prepare(`
      SELECT * FROM files WHERE id = ? AND (is_public = 1 OR user_id = ?)
    `).bind(fileId, 'current-user-id').first();
    
    if (!fileRecord) {
      return new Response(JSON.stringify({
        success: false,
        error: 'File not found or access denied'
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Get file from R2
    const object = await env.STORAGE.get(fileRecord.file_path);
    
    if (!object) {
      return new Response(JSON.stringify({
        success: false,
        error: 'File not found in storage'
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Return file with appropriate headers
    const headers = new Headers();
    headers.set('Content-Type', fileRecord.mime_type);
    headers.set('Content-Length', fileRecord.file_size.toString());
    headers.set('Content-Disposition', `attachment; filename="${fileRecord.original_name}"`);
    headers.set('Cache-Control', 'public, max-age=31536000');
    
    return new Response(object.body, {
      status: 200,
      headers: headers
    });
    
  } catch (error) {
    console.error('File download error:', error);
    return new Response(JSON.stringify({
      success: false,
      error: 'Internal server error during file download'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Handle file list request
 * @param {Request} request - HTTP request
 * @param {Object} env - Environment variables
 * @param {string} userId - User ID
 * @returns {Response} - HTTP response
 */
export async function handleFileList(request, env, userId) {
  try {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || '20');
    const folderId = url.searchParams.get('folderId');
    const search = url.searchParams.get('search');
    
    const offset = (page - 1) * limit;
    
    // Build query
    let query = 'SELECT * FROM files WHERE user_id = ?';
    let params = [userId];
    
    if (folderId) {
      query += ' AND folder_id = ?';
      params.push(folderId);
    }
    
    if (search) {
      query += ' AND (name LIKE ? OR original_name LIKE ?)';
      params.push(`%${search}%`, `%${search}%`);
    }
    
    query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?';
    params.push(limit, offset);
    
    // Execute query
    const result = await env.DB.prepare(query).bind(...params).all();
    
    // Get total count
    let countQuery = 'SELECT COUNT(*) as total FROM files WHERE user_id = ?';
    let countParams = [userId];
    
    if (folderId) {
      countQuery += ' AND folder_id = ?';
      countParams.push(folderId);
    }
    
    if (search) {
      countQuery += ' AND (name LIKE ? OR original_name LIKE ?)';
      countParams.push(`%${search}%`, `%${search}%`);
    }
    
    const countResult = await env.DB.prepare(countQuery).bind(...countParams).first();
    const total = countResult.total;
    const totalPages = Math.ceil(total / limit);
    
    return new Response(JSON.stringify({
      success: true,
      files: result.results,
      pagination: {
        page,
        limit,
        total,
        totalPages,
        hasNext: page < totalPages,
        hasPrev: page > 1
      }
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    console.error('File list error:', error);
    return new Response(JSON.stringify({
      success: false,
      error: 'Internal server error during file listing'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Handle file delete request
 * @param {Request} request - HTTP request
 * @param {Object} env - Environment variables
 * @param {string} fileId - File ID
 * @param {string} userId - User ID
 * @returns {Response} - HTTP response
 */
export async function handleFileDelete(request, env, fileId, userId) {
  try {
    // Get file record
    const fileRecord = await env.DB.prepare(`
      SELECT * FROM files WHERE id = ? AND user_id = ?
    `).bind(fileId, userId).first();
    
    if (!fileRecord) {
      return new Response(JSON.stringify({
        success: false,
        error: 'File not found or access denied'
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Delete from R2
    await env.STORAGE.delete(fileRecord.file_path);
    
    // Delete from database
    await env.DB.prepare(`DELETE FROM files WHERE id = ?`).bind(fileId).run();
    
    return new Response(JSON.stringify({
      success: true,
      message: 'File deleted successfully'
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    console.error('File delete error:', error);
    return new Response(JSON.stringify({
      success: false,
      error: 'Internal server error during file deletion'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}