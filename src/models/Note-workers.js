/**
 * Note Model for Cloudflare Workers
 * D1-compatible note model with content management and sharing features
 */

import { HTTPException } from 'hono/http-exception';
import { createDatabaseService } from '../services/database-workers.js';

/**
 * Note Model Class
 */
export class Note {
  constructor(data = {}) {
    this.id = data.id || null;
    this.user_id = data.user_id || null;
    this.title = data.title || '';
    this.content = data.content || '';
    this.content_type = data.content_type || 'text';
    this.category = data.category || 'general';
    this.tags = data.tags ? JSON.parse(data.tags) : [];
    this.is_public = data.is_public !== undefined ? data.is_public : false;
    this.is_encrypted = data.is_encrypted !== undefined ? data.is_encrypted : false;
    this.encryption_key = data.encryption_key || null;
    this.parent_id = data.parent_id || null;
    this.version = data.version || 1;
    this.word_count = data.word_count || 0;
    this.reading_time = data.reading_time || 0;
    this.last_accessed = data.last_accessed || null;
    this.archived_at = data.archived_at || null;
    this.deleted_at = data.deleted_at || null;
    this.created_at = data.created_at || new Date().toISOString();
    this.updated_at = data.updated_at || new Date().toISOString();
  }

  /**
   * Convert note instance to plain object
   * @returns {Object} Plain object representation
   */
  toJSON() {
    return {
      id: this.id,
      user_id: this.user_id,
      title: this.title,
      content: this.content,
      content_type: this.content_type,
      category: this.category,
      tags: this.tags,
      is_public: this.is_public,
      is_encrypted: this.is_encrypted,
      parent_id: this.parent_id,
      version: this.version,
      word_count: this.word_count,
      reading_time: this.reading_time,
      last_accessed: this.last_accessed,
      archived_at: this.archived_at,
      deleted_at: this.deleted_at,
      created_at: this.created_at,
      updated_at: this.updated_at
    };
  }

  /**
   * Calculate word count and reading time
   */
  calculateStats() {
    if (this.content) {
      this.word_count = this.content.trim().split(/\s+/).filter(word => word.length > 0).length;
      this.reading_time = Math.ceil(this.word_count / 200); // Average reading speed: 200 words per minute
    }
  }
}

/**
 * Note Version Model Class
 */
export class NoteVersion {
  constructor(data = {}) {
    this.id = data.id || null;
    this.note_id = data.note_id || null;
    this.user_id = data.user_id || null;
    this.title = data.title || '';
    this.content = data.content || '';
    this.version = data.version || 1;
    this.changes = data.changes ? JSON.parse(data.changes) : {};
    this.created_at = data.created_at || new Date().toISOString();
  }

  /**
   * Convert note version instance to plain object
   * @returns {Object} Plain object representation
   */
  toJSON() {
    return {
      id: this.id,
      note_id: this.note_id,
      user_id: this.user_id,
      title: this.title,
      content: this.content,
      version: this.version,
      changes: this.changes,
      created_at: this.created_at
    };
  }
}

/**
 * Note Sharing Model Class
 */
export class NoteShare {
  constructor(data = {}) {
    this.id = data.id || null;
    this.note_id = data.note_id || null;
    this.shared_by = data.shared_by || null;
    this.shared_with = data.shared_with || null;
    this.permission = data.permission || 'read';
    this.expires_at = data.expires_at || null;
    this.access_code = data.access_code || null;
    this.is_active = data.is_active !== undefined ? data.is_active : true;
    this.created_at = data.created_at || new Date().toISOString();
  }

  /**
   * Convert note share instance to plain object
   * @returns {Object} Plain object representation
   */
  toJSON() {
    return {
      id: this.id,
      note_id: this.note_id,
      shared_by: this.shared_by,
      shared_with: this.shared_with,
      permission: this.permission,
      expires_at: this.expires_at,
      access_code: this.access_code,
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
}

/**
 * Note Model Service
 */
export class NoteModel {
  constructor(env) {
    this.env = env;
    this.db = createDatabaseService(env);
  }

  /**
   * Initialize note tables
   */
  async initializeTables() {
    const createNotesTableSQL = `
      CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        content_type TEXT DEFAULT 'text' CHECK (content_type IN ('text', 'markdown', 'html', 'json')),
        category TEXT DEFAULT 'general',
        tags TEXT DEFAULT '[]',
        is_public INTEGER DEFAULT 0,
        is_encrypted INTEGER DEFAULT 0,
        encryption_key TEXT,
        parent_id INTEGER,
        version INTEGER DEFAULT 1,
        word_count INTEGER DEFAULT 0,
        reading_time INTEGER DEFAULT 0,
        last_accessed TEXT,
        archived_at TEXT,
        deleted_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (parent_id) REFERENCES notes(id) ON DELETE CASCADE
      )
    `;

    const createNoteVersionsTableSQL = `
      CREATE TABLE IF NOT EXISTS note_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        version INTEGER NOT NULL,
        changes TEXT DEFAULT '{}',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `;

    const createNoteSharesTableSQL = `
      CREATE TABLE IF NOT EXISTS note_shares (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id INTEGER NOT NULL,
        shared_by INTEGER NOT NULL,
        shared_with INTEGER,
        permission TEXT DEFAULT 'read' CHECK (permission IN ('read', 'write', 'admin')),
        expires_at TEXT,
        access_code TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
        FOREIGN KEY (shared_by) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (shared_with) REFERENCES users(id) ON DELETE CASCADE
      )
    `;

    const createIndexesSQL = [
      'CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes(user_id)',
      'CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category)',
      'CREATE INDEX IF NOT EXISTS idx_notes_is_public ON notes(is_public)',
      'CREATE INDEX IF NOT EXISTS idx_notes_parent_id ON notes(parent_id)',
      'CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at)',
      'CREATE INDEX IF NOT EXISTS idx_notes_updated_at ON notes(updated_at)',
      'CREATE INDEX IF NOT EXISTS idx_note_versions_note_id ON note_versions(note_id)',
      'CREATE INDEX IF NOT EXISTS idx_note_shares_note_id ON note_shares(note_id)',
      'CREATE INDEX IF NOT EXISTS idx_note_shares_shared_with ON note_shares(shared_with)',
      'CREATE INDEX IF NOT EXISTS idx_note_shares_access_code ON note_shares(access_code)'
    ];

    try {
      await this.db.query(createNotesTableSQL);
      await this.db.query(createNoteVersionsTableSQL);
      await this.db.query(createNoteSharesTableSQL);
      
      for (const indexSQL of createIndexesSQL) {
        await this.db.query(indexSQL);
      }
      
      console.log('Note tables initialized successfully');
    } catch (error) {
      console.error('Failed to initialize note tables:', error);
      throw error;
    }
  }

  /**
   * Create a new note
   * @param {Object} noteData - Note data
   * @returns {Note} Created note
   */
  async create(noteData) {
    const requiredFields = ['user_id', 'title', 'content'];
    
    for (const field of requiredFields) {
      if (!noteData[field]) {
        throw new HTTPException(400, { message: `Missing required field: ${field}` });
      }
    }

    try {
      const note = new Note(noteData);
      note.calculateStats();

      const newNoteData = {
        user_id: note.user_id,
        title: note.title,
        content: note.content,
        content_type: note.content_type,
        category: note.category,
        tags: JSON.stringify(note.tags),
        is_public: note.is_public,
        is_encrypted: note.is_encrypted,
        encryption_key: note.encryption_key,
        parent_id: note.parent_id,
        version: note.version,
        word_count: note.word_count,
        reading_time: note.reading_time,
        created_at: note.created_at,
        updated_at: note.updated_at
      };

      const result = await this.db.insert('notes', newNoteData);
      
      if (result.success) {
        const noteId = result.data.meta.last_row_id;
        const createdNote = await this.findById(noteId);
        
        // Create initial version
        await this.createVersion(createdNote, createdNote.user_id, 'Initial version');
        
        return createdNote;
      }

      throw new HTTPException(500, { message: 'Failed to create note' });
    } catch (error) {
      if (error.status) {
        throw error;
      }
      console.error('Create note error:', error);
      throw new HTTPException(500, { message: 'Failed to create note' });
    }
  }

  /**
   * Find note by ID
   * @param {number} id - Note ID
   * @param {number} userId - User ID (for permission check)
   * @returns {Note|null} Note instance
   */
  async findById(id, userId = null) {
    try {
      let query = 'SELECT * FROM notes WHERE id = ? AND deleted_at IS NULL';
      let params = [id];
      
      if (userId) {
        query += ' AND (user_id = ? OR is_public = 1)';
        params.push(userId);
      }
      
      const result = await this.db.select(query, params);
      
      if (result.length === 0) {
        return null;
      }
      
      const note = new Note(result[0]);
      
      // Update last accessed time
      await this.updateLastAccessed(id);
      
      return note;
    } catch (error) {
      console.error('Find note by ID error:', error);
      return null;
    }
  }

  /**
   * Update note
   * @param {number} id - Note ID
   * @param {Object} updateData - Update data
   * @param {number} userId - User ID (for permission check)
   * @returns {Note|null} Updated note
   */
  async update(id, updateData, userId = null) {
    try {
      // Check if note exists and user has permission
      const existingNote = await this.findById(id, userId);
      if (!existingNote) {
        throw new HTTPException(404, { message: 'Note not found or access denied' });
      }

      // Remove fields that shouldn't be updated directly
      const allowedFields = [
        'title', 'content', 'content_type', 'category', 'tags',
        'is_public', 'is_encrypted', 'encryption_key', 'parent_id'
      ];
      
      const filteredData = {};
      for (const [key, value] of Object.entries(updateData)) {
        if (allowedFields.includes(key)) {
          if (key === 'tags') {
            filteredData[key] = JSON.stringify(value);
          } else {
            filteredData[key] = value;
          }
        }
      }
      
      // Calculate stats if content is updated
      if (filteredData.content) {
        const tempNote = new Note({ ...existingNote.toJSON(), ...filteredData });
        tempNote.calculateStats();
        filteredData.word_count = tempNote.word_count;
        filteredData.reading_time = tempNote.reading_time;
      }
      
      filteredData.updated_at = new Date().toISOString();
      
      // Create version before updating
      await this.createVersion(existingNote, userId, 'Note updated');
      
      const result = await this.db.update('notes', filteredData, { id });
      
      if (result.success && result.data.meta.changes > 0) {
        return await this.findById(id);
      }
      
      return null;
    } catch (error) {
      if (error.status) {
        throw error;
      }
      console.error('Update note error:', error);
      throw new HTTPException(500, { message: 'Failed to update note' });
    }
  }

  /**
   * Delete note (soft delete)
   * @param {number} id - Note ID
   * @param {number} userId - User ID (for permission check)
   * @returns {boolean} Success
   */
  async delete(id, userId = null) {
    try {
      // Check if note exists and user has permission
      const existingNote = await this.findById(id, userId);
      if (!existingNote) {
        throw new HTTPException(404, { message: 'Note not found or access denied' });
      }

      const result = await this.db.update(
        'notes',
        { deleted_at: new Date().toISOString(), updated_at: new Date().toISOString() },
        { id }
      );
      
      return result.success && result.data.meta.changes > 0;
    } catch (error) {
      if (error.status) {
        throw error;
      }
      console.error('Delete note error:', error);
      return false;
    }
  }

  /**
   * Get notes with pagination
   * @param {Object} options - Query options
   * @returns {Object} Notes and pagination info
   */
  async getNotes(options = {}) {
    const { 
      page = 1, 
      limit = 20, 
      user_id = null, 
      category = null,
      is_public = null,
      search = null,
      tags = null,
      sortBy = 'updated_at',
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
      
      if (category) {
        whereConditions.push('category = ?');
        params.push(category);
      }
      
      if (is_public !== null) {
        whereConditions.push('is_public = ?');
        params.push(is_public ? 1 : 0);
      }
      
      if (search) {
        whereConditions.push('(title LIKE ? OR content LIKE ?)');
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
        `SELECT COUNT(*) as total FROM notes ${whereClause}`,
        params
      );
      
      const total = countResult[0].total;
      
      // Get notes
      const notesResult = await this.db.select(
        `SELECT * FROM notes ${whereClause} ORDER BY ${sortBy} ${sortOrder} LIMIT ? OFFSET ?`,
        [...params, limit, offset]
      );
      
      const notes = notesResult.map(note => new Note(note));
      
      return {
        notes: notes.map(note => note.toJSON()),
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
      console.error('Get notes error:', error);
      throw new HTTPException(500, { message: 'Failed to get notes' });
    }
  }

  /**
   * Create note version
   * @param {Note} note - Note instance
   * @param {number} userId - User ID
   * @param {string} changes - Changes description
   * @returns {NoteVersion} Created version
   */
  async createVersion(note, userId, changes = '') {
    try {
      const versionData = {
        note_id: note.id,
        user_id: userId,
        title: note.title,
        content: note.content,
        version: note.version,
        changes: JSON.stringify({ description: changes })
      };

      const result = await this.db.insert('note_versions', versionData);
      
      if (result.success) {
        return new NoteVersion({
          ...versionData,
          id: result.data.meta.last_row_id,
          created_at: new Date().toISOString()
        });
      }

      throw new HTTPException(500, { message: 'Failed to create note version' });
    } catch (error) {
      console.error('Create note version error:', error);
      throw new HTTPException(500, { message: 'Failed to create note version' });
    }
  }

  /**
   * Get note versions
   * @param {number} noteId - Note ID
   * @param {number} userId - User ID (for permission check)
   * @returns {Array} Note versions
   */
  async getVersions(noteId, userId = null) {
    try {
      // Check if note exists and user has permission
      const note = await this.findById(noteId, userId);
      if (!note) {
        throw new HTTPException(404, { message: 'Note not found or access denied' });
      }

      const result = await this.db.select(
        'SELECT * FROM note_versions WHERE note_id = ? ORDER BY version DESC',
        [noteId]
      );
      
      return result.map(version => new NoteVersion(version));
    } catch (error) {
      if (error.status) {
        throw error;
      }
      console.error('Get note versions error:', error);
      throw new HTTPException(500, { message: 'Failed to get note versions' });
    }
  }

  /**
   * Share note
   * @param {number} noteId - Note ID
   * @param {number} sharedBy - User ID sharing the note
   * @param {Object} shareData - Share data
   * @returns {NoteShare} Created share
   */
  async shareNote(noteId, sharedBy, shareData) {
    try {
      // Check if note exists and user has permission
      const note = await this.findById(noteId, sharedBy);
      if (!note) {
        throw new HTTPException(404, { message: 'Note not found or access denied' });
      }

      const share = new NoteShare({
        note_id: noteId,
        shared_by: sharedBy,
        shared_with: shareData.shared_with || null,
        permission: shareData.permission || 'read',
        expires_at: shareData.expires_at || null,
        access_code: shareData.access_code || null,
        is_active: true
      });

      const shareResult = await this.db.insert('note_shares', {
        note_id: share.note_id,
        shared_by: share.shared_by,
        shared_with: share.shared_with,
        permission: share.permission,
        expires_at: share.expires_at,
        access_code: share.access_code,
        is_active: share.is_active ? 1 : 0,
        created_at: share.created_at
      });

      if (shareResult.success) {
        return new NoteShare({
          ...share,
          id: shareResult.data.meta.last_row_id
        });
      }

      throw new HTTPException(500, { message: 'Failed to share note' });
    } catch (error) {
      if (error.status) {
        throw error;
      }
      console.error('Share note error:', error);
      throw new HTTPException(500, { message: 'Failed to share note' });
    }
  }

  /**
   * Get shared note by access code
   * @param {string} accessCode - Access code
   * @returns {Note|null} Note instance
   */
  async getSharedNoteByAccessCode(accessCode) {
    try {
      const shareResult = await this.db.select(
        'SELECT * FROM note_shares WHERE access_code = ? AND is_active = 1',
        [accessCode]
      );
      
      if (shareResult.length === 0) {
        return null;
      }
      
      const share = new NoteShare(shareResult[0]);
      
      if (share.isExpired()) {
        return null;
      }
      
      return await this.findById(share.note_id);
    } catch (error) {
      console.error('Get shared note by access code error:', error);
      return null;
    }
  }

  /**
   * Update last accessed time
   * @param {number} noteId - Note ID
   * @returns {boolean} Success
   */
  async updateLastAccessed(noteId) {
    try {
      const result = await this.db.update(
        'notes',
        { last_accessed: new Date().toISOString() },
        { id: noteId }
      );
      
      return result.success && result.data.meta.changes > 0;
    } catch (error) {
      console.error('Update note last accessed error:', error);
      return false;
    }
  }

  /**
   * Get note statistics
   * @param {number} userId - User ID (optional)
   * @returns {Object} Note statistics
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
          COUNT(*) as total_notes,
          COUNT(CASE WHEN is_public = 1 THEN 1 END) as public_notes,
          COUNT(CASE WHEN is_encrypted = 1 THEN 1 END) as encrypted_notes,
          COUNT(CASE WHEN archived_at IS NOT NULL THEN 1 END) as archived_notes,
          COUNT(CASE WHEN DATE(created_at) = DATE('now') THEN 1 END) as notes_today,
          COUNT(CASE WHEN DATE(updated_at) = DATE('now') THEN 1 END) as updated_today,
          AVG(word_count) as avg_word_count,
          SUM(word_count) as total_words,
          category,
          COUNT(*) as category_count
        FROM notes ${whereClause}
        GROUP BY category
      `);
      
      const categoryStats = {};
      let totalNotes = 0;
      let totalWords = 0;
      
      for (const stat of stats) {
        categoryStats[stat.category] = {
          count: stat.category_count,
          percentage: 0 // Will be calculated below
        };
        totalNotes += stat.category_count;
        totalWords += stat.total_words || 0;
      }
      
      // Calculate percentages
      for (const [category, data] of Object.entries(categoryStats)) {
        data.percentage = totalNotes > 0 ? Math.round((data.count / totalNotes) * 100) : 0;
      }
      
      return {
        total_notes: totalNotes,
        public_notes: stats[0]?.public_notes || 0,
        encrypted_notes: stats[0]?.encrypted_notes || 0,
        archived_notes: stats[0]?.archived_notes || 0,
        notes_today: stats[0]?.notes_today || 0,
        updated_today: stats[0]?.updated_today || 0,
        avg_word_count: Math.round(stats[0]?.avg_word_count || 0),
        total_words: totalWords,
        categories: categoryStats
      };
    } catch (error) {
      console.error('Get note statistics error:', error);
      return {
        total_notes: 0,
        public_notes: 0,
        encrypted_notes: 0,
        archived_notes: 0,
        notes_today: 0,
        updated_today: 0,
        avg_word_count: 0,
        total_words: 0,
        categories: {}
      };
    }
  }
}

/**
 * Note Model Factory
 * @param {Object} env - Environment variables
 * @returns {NoteModel} Note model instance
 */
export function createNoteModel(env) {
  return new NoteModel(env);
}

export default {
  Note,
  NoteVersion,
  NoteShare,
  NoteModel,
  createNoteModel
};