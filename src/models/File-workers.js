/**
 * File Model for Cloudflare Workers
 * D1-compatible file model with R2 storage integration
 */

import { HTTPException } from 'hono/http-exception';
import { createDatabaseService } from '../services/database-workers.js';

/**
 * File Model Class
 */
export class File {
  constructor(data = {}) {
    this.id = data.id || null;
    this.user_id = data.user_id || null;
    this.note_id = data.note_id || null;
    this.filename = data.filename || '';
    this.original_name = data.original_name || '';
    this.mime_type = data.mime_type || 'application/octet-stream';
    this.file_size = data.file_size || 0;
    this.file_path = data.file_path || '';
    this.r2_key = data.r2_key || '';
    this.r2_bucket = data.r2_bucket || '';
    this.r2_url = data.r2_url || '';
    this.checksum = data.checksum || '';
    this.encryption_key = data.encryption_key || null;
    this.is_encrypted = data.is_encrypted !== undefined ? data.is_encrypted : false;
    this.is_public = data.is_public !== undefined ? data.is_public : false;
    this.is_thumbnail = data.is_thumbnail !== undefined ? data.is_thumbnail : false;
    this.parent_file_id = data.parent_file_id || null;
    this.metadata = data.metadata ? JSON.parse(data.metadata) : {};
    this.tags = data.tags ? JSON.parse(data.tags) : [];
    this.download_count = data.download_count || 0;
    this.last_accessed = data.last_accessed || null;
    this.expires_at = data.expires_at || null;
    this.deleted_at = data.deleted_at || null;
    this.created_at = data.created_at || new Date().toISOString();
    this.updated_at = data.updated_at || new Date().toISOString();
  }

  /**
   * Convert file instance to plain object
   * @returns {Object} Plain object representation
   */
  toJSON() {
    return {
      id: this.id,
      user_id: this.user_id,
      note_id: this.note_id,
      filename: this.filename,
      original_name: this.original_name,
      mime_type: this.mime_type,
      file_size: this.file_size,
      file_path: this.file_path,
      r2_key: this.r2_key,
      r2_bucket: this.r2_bucket,
      r2_url: this.r2_url,
      checksum: this.checksum,
      is_encrypted: this.is_encrypted,
      is_public: this.is_public,
      is_thumbnail: this.is_thumbnail,
      parent_file_id: this.parent_file_id,
      metadata: this.metadata,
      tags: this.tags,
      download_count: this.download_count,
      last_accessed: this.last_accessed,
      expires_at: this.expires_at,
      deleted_at: this.deleted_at,
      created_at: this.created_at,
      updated_at: this.updated_at
    };
  }

  /**
   * Get file size in human readable format
   * @returns {string} Human readable file size
   */
  getHumanReadableSize() {
    const bytes = this.file_size;
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * Check if file is expired
   * @returns {boolean} Is expired
   */
  isExpired() {
    if (!this.expires_at) {
      return false;
    }
    return new Date(this.expires_at) < new Date();
  }

  /**
   * Check if file is an image
   * @returns {boolean} Is image
   */
  isImage() {
    return this.mime_type.startsWith('image/');
  }

  /**
   * Check if file is a video
   * @returns {boolean} Is video
   */
  isVideo() {
    return this.mime_type.startsWith('video/');
  }

  /**
   * Check if file is a document
   * @returns {boolean} Is document
   */
  isDocument() {
    const documentTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-powerpoint',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'text/plain',
      'text/csv'
    ];
    return documentTypes.includes(this.mime_type);
  }
}

/**
 * File Share Model Class
 */
export class FileShare {
  constructor(data = {}) {
    this.id = data.id || null;
    this.file_id = data.file_id || null;
    this.shared_by = data.shared_by || null;
    this.shared_with = data.shared_with || null;
    this.permission = data.permission || 'read';
    this.expires_at = data.expires_at || null;
    this.access_code = data.access_code || null;
    this.download_limit = data.download_limit || null;
    this.download_count = data.download_count || 0;
    this.is_active = data.is_active !== undefined ? data.is_active : true;
    this.created_at = data.created_at || new Date().toISOString();
  }

  /**
   * Convert file share instance to plain object
   * @returns {Object} Plain object representation
   */
  toJSON() {
    return {
      id: this.id,
      file_id: this.file_id,
      shared_by: this.shared_by,
      shared_with: this.shared_with,
      permission: this.permission,
      expires_at: this.expires_at,
      access_code: this.access_code,
      download_limit: this.download_limit,
      download_count: this.download_count,
      is_active: this.is_active,
      created_at: this.created_at
    };
  }

  /**
   * Check if share is expired
   * @returns {boolean} Is expired
   */
  isExpired() {
    if (!this.expires_at) {
      return false;
    }
    return new Date(this.expires_at) < new Date();
  }

  /**
   * Check if download limit is reached
   * @returns {boolean} Is limit reached
   */
  isDownloadLimitReached() {
    if (!this.download_limit) {
      return false;
    }
    return this.download_count >= this.download_limit;
  }
}

/**
 * File Model Service
 */
export class FileModel {
  constructor(env) {
    this.env = env;
    this.db = createDatabaseService(env);
  }

  /**
   * Initialize file tables
   */
  async initializeTables() {
    const createFilesTableSQL = `
      CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        note_id INTEGER,
        filename TEXT NOT NULL,
        original_name TEXT NOT NULL,
        mime_type TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        r2_key TEXT NOT NULL,
        r2_bucket TEXT NOT NULL,
        r2_url TEXT,
        checksum TEXT,
        encryption_key TEXT,
        is_encrypted INTEGER DEFAULT 0,
        is_public INTEGER DEFAULT 0,
        is_thumbnail INTEGER DEFAULT 0,
        parent_file_id INTEGER,
        metadata TEXT DEFAULT '{}',
        tags TEXT DEFAULT '[]',
        download_count INTEGER DEFAULT 0,
        last_accessed TEXT,
        expires_at TEXT,
        deleted_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
        FOREIGN KEY (parent_file_id) REFERENCES files(id) ON DELETE CASCADE
      )
    `;

    const createFileSharesTableSQL = `
      CREATE TABLE IF NOT EXISTS file_shares (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER NOT NULL,
        shared_by INTEGER NOT NULL,
        shared_with INTEGER,
        permission TEXT DEFAULT 'read' CHECK (permission IN ('read', 'write', 'admin')),
        expires_at TEXT,
        access_code TEXT,
        download_limit INTEGER,
        download_count INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
        FOREIGN KEY (shared_by) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (shared_with) REFERENCES users(id) ON DELETE CASCADE
      )
    `;

    const createIndexesSQL = [
      'CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id)',
      'CREATE INDEX IF NOT EXISTS idx_files_note_id ON files(note_id)',
      'CREATE INDEX IF NOT EXISTS idx_files_is_public ON files(is_public)',
      'CREATE INDEX IF NOT EXISTS idx_files_is_thumbnail ON files(is_thumbnail)',
      'CREATE INDEX IF NOT EXISTS idx_files_mime_type ON files(mime_type)',
      'CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at)',
      'CREATE INDEX IF NOT EXISTS idx_files_expires_at ON files(expires_at)',
      'CREATE INDEX IF NOT EXISTS idx_file_shares_file_id ON file_shares(file_id)',
      'CREATE INDEX IF NOT EXISTS idx_file_shares_shared_with ON file_shares(shared_with)',
      'CREATE INDEX IF NOT EXISTS idx_file_shares_access_code ON file_shares(access_code)',
      'CREATE INDEX IF NOT EXISTS idx_file_shares_is_active ON file_shares(is_active)'
    ];

    try {
      await this.db.query(createFilesTableSQL);
      await this.db.query(createFileSharesTableTableSQL);
      
      for (const indexSQL of createIndexesSQL) {
        await this.db.query(indexSQL);
      }
      
      console.log('File tables initialized successfully');
    } catch (error) {
      console.error('Failed to initialize file tables:', error);
      throw error;
    }
  }

  /**
   * Create a new file record
   * @param {Object} fileData - File data
   * @returns {File} Created file
   */
  async create(fileData) {
    const requiredFields = ['user_id', 'filename', 'original_name', 'mime_type', 'file_size', 'file_path', 'r2_key', 'r2_bucket'];
    
    for (const field of requiredFields) {
      if (!fileData[field]) {
        throw new HTTPException(400, { message: `Missing required field: ${field}` });
      }
    }

    try {
      const file = new File(fileData);

      const newFileData = {
        user_id: file.user_id,
        note_id: file.note_id,
        filename: file.filename,
        original_name: file.original_name,
        mime_type: file.mime_type,
        file_size: file.file_size,
        file_path: file.file_path,
        r2_key: file.r2_key,
        r2_bucket: file.r2_bucket,
        r2_url: file.r2_url,
        checksum: file.checksum,
        encryption_key: file.encryption_key,
        is_encrypted: file.is_encrypted ? 1 : 0,
        is_public: file.is_public ? 1 : 0,
        is_thumbnail: file.is_thumbnail ? 1 : 0,
        parent_file_id: file.parent_file_id,
        metadata: JSON.stringify(file.metadata),
        tags: JSON.stringify(file.tags),
        download_count: file.download_count,
        expires_at: file.expires_at,
        created_at: file.created_at,
        updated_at: file.updated_at
      };

      const result = await this.db.insert('files', newFileData);
      
      if (result.success) {
        const fileId = result.data.meta.last_row_id;
        return await this.findById(fileId);
      }

      throw new HTTPException(500, { message: 'Failed to create file record' });
    } catch (error) {
      if (error.status) {
        throw error;
      }
      console.error('Create file error:', error);
      throw new HTTPException(500, { message: 'Failed to create file record' });
    }
  }

  /**
   * Find file by ID
   * @param {number} id - File ID
   * @param {number} userId - User ID (for permission check)
   * @returns {File|null} File instance
   */
  async findById(id, userId = null) {
    try {
      let query = 'SELECT * FROM files WHERE id = ? AND deleted_at IS NULL';
      let params = [id];
      
      if (userId) {
        query += ' AND (user_id = ? OR is_public = 1)';
        params.push(userId);
      }
      
      const result = await this.db.select(query, params);
      
      if (result.length === 0) {
        return null;
      }
      
      const file = new File(result[0]);
      
      // Update last accessed time
      await this.updateLastAccessed(id);
      
      return file;
    } catch (error) {
      console.error('Find file by ID error:', error);
      return null;
    }
  }

  /**
   * Find file by R2 key
   * @param {string} r2Key - R2 key
   * @param {number} userId - User ID (for permission check)
   * @returns {File|null} File instance
   */
  async findByR2Key(r2Key, userId = null) {
    try {
      let query = 'SELECT * FROM files WHERE r2_key = ? AND deleted_at IS NULL';
      let params = [r2Key];
      
      if (userId) {
        query += ' AND (user_id = ? OR is_public = 1)';
        params.push(userId);
      }
      
      const result = await this.db.select(query, params);
      
      if (result.length === 0) {
        return null;
      }
      
      return new File(result[0]);
    } catch (error) {
      console.error('Find file by R2 key error:', error);
      return null;
    }
  }

  /**
   * Update file
   * @param {number} id - File ID
   * @param {Object} updateData - Update data
   * @param {number} userId - User ID (for permission check)
   * @returns {File|null} Updated file
   */
  async update(id, updateData, userId = null) {
    try {
      // Check if file exists and user has permission
      const existingFile = await this.findById(id, userId);
      if (!existingFile) {
        throw new HTTPException(404, { message: 'File not found or access denied' });
      }

      // Remove fields that shouldn't be updated directly
      const allowedFields = [
        'note_id', 'filename', 'original_name', 'mime_type', 'file_size',
        'file_path', 'r2_key', 'r2_bucket', 'r2_url', 'checksum',
        'encryption_key', 'is_encrypted', 'is_public', 'is_thumbnail',
        'parent_file_id', 'metadata', 'tags', 'download_count', 'expires_at'
      ];
      
      const filteredData = {};
      for (const [key, value] of Object.entries(updateData)) {
        if (allowedFields.includes(key)) {
          if (key === 'metadata' || key === 'tags') {
            filteredData[key] = JSON.stringify(value);
          } else {
            filteredData[key] = value;
          }
        }
      }
      
      filteredData.updated_at = new Date().toISOString();
      
      const result = await this.db.update('files', filteredData, { id });
      
      if (result.success && result.data.meta.changes > 0) {
        return await this.findById(id);
      }
      
      return null;
    } catch (error) {
      if (error.status) {
        throw error;
      }
      console.error('Update file error:', error);
      throw new HTTPException(500, { message: 'Failed to update file' });
    }
  }

  /**
   * Delete file (soft delete)
   * @param {number} id - File ID
   * @param {number} userId - User ID (for permission check)
   * @returns {boolean} Success
   */
  async delete(id, userId = null) {
    try {
      // Check if file exists and user has permission
      const existingFile = await this.findById(id, userId);
      if (!existingFile) {
        throw new HTTPException(404, { message: 'File not found or access denied' });
      }

      const result = await this.db.update(
        'files',
        { deleted_at: new Date().toISOString(), updated_at: new Date().toISOString() },
        { id }
      );
      
      return result.success && result.data.meta.changes > 0;
    } catch (error) {
      if (error.status) {
        throw error;
      }
      console.error('Delete file error:', error);
      return false;
    }
  }

  /**
   * Get files with pagination
   * @param {Object} options - Query options
   * @returns {Object} Files and pagination info
   */
  async getFiles(options = {}) {
    const { 
      page = 1, 
      limit = 20, 
      user_id = null, 
      note_id = null,
      mime_type = null,
      is_public = null,
      is_thumbnail = null,
      search = null,
      tags = null,
      sortBy = 'created_at',
      sortOrder = 'DESC',
      include_deleted = false
    } = options;

    const offset = (page - 1) * limit;
    
    try {
      let whereConditions = [];
      let params = [];
      
      if (!include_deleted) {
        whereConditions.push('deleted_at IS NULL');
      }
      
      if (user_id) {
        whereConditions.push('(user_id = ? OR is_public = 1)');
        params.push(user_id);
      }
      
      if (note_id) {
        whereConditions.push('note_id = ?');
        params.push(note_id);
      }
      
      if (mime_type) {
        whereConditions.push('mime_type = ?');
        params.push(mime_type);
      }
      
      if (is_public !== null) {
        whereConditions.push('is_public = ?');
        params.push(is_public ? 1 : 0);
      }
      
      if (is_thumbnail !== null) {
        whereConditions.push('is_thumbnail = ?');
        params.push(is_thumbnail ? 1 : 0);
      }
      
      if (search) {
        whereConditions.push('(filename LIKE ? OR original_name LIKE ?)');
        params.push(`%${search}%`, `%${search}%`);
      }
      
      if (tags && tags.length > 0) {
        const tagConditions = tags.map(() => 'tags LIKE ?').join(' AND ');
        whereConditions.push(`(${tagConditions})`);
        tags.forEach(tag => params.push(`%"${tag}"%`));
      }
      
      const whereClause = whereConditions.length > 0 ? `WHERE ${whereConditions.join(' AND ')}` : '';
      
      // Get total count
      const countResult = await this.db.select(
        `SELECT COUNT(*) as total FROM files ${whereClause}`,
        params
      );
      
      const total = countResult[0].total;
      
      // Get files
      const filesResult = await this.db.select(
        `SELECT * FROM files ${whereClause} ORDER BY ${sortBy} ${sortOrder} LIMIT ? OFFSET ?`,
        [...params, limit, offset]
      );
      
      const files = filesResult.map(file => new File(file));
      
      return {
        files: files.map(file => file.toJSON()),
        pagination: {
          page,
          limit,
          total,
          pages: Math.ceil(total / limit),
          hasNext: page < Math.ceil(total / limit),
          hasPrev: page > 1
        }
      };
    } catch (error) {
      console.error('Get files error:', error);
      throw new HTTPException(500, { message: 'Failed to get files' });
    }
  }

  /**
   * Get files by note ID
   * @param {number} noteId - Note ID
   * @param {number} userId - User ID (for permission check)
   * @returns {Array} Files
   */
  async getFilesByNoteId(noteId, userId = null) {
    try {
      let query = 'SELECT * FROM files WHERE note_id = ? AND deleted_at IS NULL';
      let params = [noteId];
      
      if (userId) {
        query += ' AND (user_id = ? OR is_public = 1)';
        params.push(userId);
      }
      
      query += ' ORDER BY created_at DESC';
      
      const result = await this.db.select(query, params);
      
      return result.map(file => new File(file));
    } catch (error) {
      console.error('Get files by note ID error:', error);
      throw new HTTPException(500, { message: 'Failed to get files by note ID' });
    }
  }

  /**
   * Share file
   * @param {number} fileId - File ID
   * @param {number} sharedBy - User ID sharing the file
   * @param {Object} shareData - Share data
   * @returns {FileShare} Created share
   */
  async shareFile(fileId, sharedBy, shareData) {
    try {
      // Check if file exists and user has permission
      const file = await this.findById(fileId, sharedBy);
      if (!file) {
        throw new HTTPException(404, { message: 'File not found or access denied' });
      }

      const share = new FileShare({
        file_id: fileId,
        shared_by: sharedBy,
        shared_with: shareData.shared_with || null,
        permission: shareData.permission || 'read',
        expires_at: shareData.expires_at || null,
        access_code: shareData.access_code || null,
        download_limit: shareData.download_limit || null,
        is_active: true
      });

      const shareResult = await this.db.insert('file_shares', {
        file_id: share.file_id,
        shared_by: share.shared_by,
        shared_with: share.shared_with,
        permission: share.permission,
        expires_at: share.expires_at,
        access_code: share.access_code,
        download_limit: share.download_limit,
        download_count: share.download_count,
        is_active: share.is_active ? 1 : 0,
        created_at: share.created_at
      });

      if (shareResult.success) {
        return new FileShare({
          ...share,
          id: shareResult.data.meta.last_row_id
        });
      }

      throw new HTTPException(500, { message: 'Failed to share file' });
    } catch (error) {
      if (error.status) {
        throw error;
      }
      console.error('Share file error:', error);
      throw new HTTPException(500, { message: 'Failed to share file' });
    }
  }

  /**
   * Get shared file by access code
   * @param {string} accessCode - Access code
   * @returns {File|null} File instance
   */
  async getSharedFileByAccessCode(accessCode) {
    try {
      const shareResult = await this.db.select(
        'SELECT * FROM file_shares WHERE access_code = ? AND is_active = 1',
        [accessCode]
      );
      
      if (shareResult.length === 0) {
        return null;
      }
      
      const share = new FileShare(shareResult[0]);
      
      if (share.isExpired() || share.isDownloadLimitReached()) {
        return null;
      }
      
      return await this.findById(share.file_id);
    } catch (error) {
      console.error('Get shared file by access code error:', error);
      return null;
    }
  }

  /**
   * Increment download count
   * @param {number} fileId - File ID
   * @returns {boolean} Success
   */
  async incrementDownloadCount(fileId) {
    try {
      const result = await this.db.query(
        'UPDATE files SET download_count = download_count + 1, last_accessed = CURRENT_TIMESTAMP WHERE id = ?',
        [fileId]
      );
      
      return result.success && result.data.meta.changes > 0;
    } catch (error) {
      console.error('Increment download count error:', error);
      return false;
    }
  }

  /**
   * Update last accessed time
   * @param {number} fileId - File ID
   * @returns {boolean} Success
   */
  async updateLastAccessed(fileId) {
    try {
      const result = await this.db.update(
        'files',
        { last_accessed: new Date().toISOString() },
        { id: fileId }
      );
      
      return result.success && result.data.meta.changes > 0;
    } catch (error) {
      console.error('Update file last accessed error:', error);
      return false;
    }
  }

  /**
   * Get file statistics
   * @param {number} userId - User ID (optional)
   * @returns {Object} File statistics
   */
  async getStats(userId = null) {
    try {
      let whereClause = 'WHERE deleted_at IS NULL';
      let params = [];
      
      if (userId) {
        whereClause += ' AND user_id = ?';
        params.push(userId);
      }
      
      const stats = await this.db.select(`
        SELECT 
          COUNT(*) as total_files,
          COUNT(CASE WHEN is_public = 1 THEN 1 END) as public_files,
          COUNT(CASE WHEN is_encrypted = 1 THEN 1 END) as encrypted_files,
          COUNT(CASE WHEN is_thumbnail = 1 THEN 1 END) as thumbnail_files,
          COUNT(CASE WHEN DATE(created_at) = DATE('now') THEN 1 END) as files_today,
          SUM(file_size) as total_size,
          AVG(file_size) as avg_size,
          mime_type,
          COUNT(*) as mime_type_count
        FROM files ${whereClause}
        GROUP BY mime_type
      `);
      
      const mimeTypeStats = {};
      let totalFiles = 0;
      let totalSize = 0;
      
      for (const stat of stats) {
        mimeTypeStats[stat.mime_type] = {
          count: stat.mime_type_count,
          percentage: 0,
          total_size: stat.total_size || 0
        };
        totalFiles += stat.mime_type_count;
        totalSize += stat.total_size || 0;
      }
      
      // Calculate percentages
      for (const [mimeType, data] of Object.entries(mimeTypeStats)) {
        data.percentage = totalFiles > 0 ? Math.round((data.count / totalFiles) * 100) : 0;
      }
      
      return {
        total_files: totalFiles,
        public_files: stats[0]?.public_files || 0,
        encrypted_files: stats[0]?.encrypted_files || 0,
        thumbnail_files: stats[0]?.thumbnail_files || 0,
        files_today: stats[0]?.files_today || 0,
        total_size: totalSize,
        avg_size: Math.round(stats[0]?.avg_size || 0),
        mime_types: mimeTypeStats
      };
    } catch (error) {
      console.error('Get file statistics error:', error);
      return {
        total_files: 0,
        public_files: 0,
        encrypted_files: 0,
        thumbnail_files: 0,
        files_today: 0,
        total_size: 0,
        avg_size: 0,
        mime_types: {}
      };
    }
  }

  /**
   * Clean up expired files
   * @param {number} userId - User ID (optional)
   * @returns {Object} Cleanup result
   */
  async cleanupExpiredFiles(userId = null) {
    try {
      let whereClause = 'WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP AND deleted_at IS NULL';
      let params = [];
      
      if (userId) {
        whereClause += ' AND user_id = ?';
        params.push(userId);
      }
      
      const expiredFiles = await this.db.select(
        `SELECT id, r2_key, r2_bucket FROM files ${whereClause}`,
        params
      );
      
      const deletedCount = expiredFiles.length;
      
      // Mark as deleted
      if (deletedCount > 0) {
        await this.db.query(
          `UPDATE files SET deleted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP ${whereClause}`,
          params
        );
      }
      
      return {
        deleted_count: deletedCount,
        expired_files: expiredFiles.map(file => ({
          id: file.id,
          r2_key: file.r2_key,
          r2_bucket: file.r2_bucket
        }))
      };
    } catch (error) {
      console.error('Cleanup expired files error:', error);
      return {
        deleted_count: 0,
        expired_files: []
      };
    }
  }
}

/**
 * File Model Factory
 * @param {Object} env - Environment variables
 * @returns {FileModel} File model instance
 */
export function createFileModel(env) {
  return new FileModel(env);
}

export default {
  File,
  FileShare,
  FileModel,
  createFileModel
};