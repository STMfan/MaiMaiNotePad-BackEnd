/**
 * Tag Model for Cloudflare Workers
 * D1-compatible tag model with note and file associations
 */

import { HTTPException } from 'hono/http-exception';
import { createDatabaseService } from '../services/database-workers.js';

/**
 * Tag Model Class
 */
export class Tag {
  constructor(data = {}) {
    this.id = data.id || null;
    this.name = data.name || '';
    this.color = data.color || '#6B7280';
    this.description = data.description || '';
    this.is_system = data.is_system !== undefined ? data.is_system : false;
    this.usage_count = data.usage_count || 0;
    this.created_by = data.created_by || null;
    this.created_at = data.created_at || new Date().toISOString();
    this.updated_at = data.updated_at || new Date().toISOString();
  }

  /**
   * Convert tag instance to plain object
   * @returns {Object} Plain object representation
   */
  toJSON() {
    return {
      id: this.id,
      name: this.name,
      color: this.color,
      description: this.description,
      is_system: this.is_system,
      usage_count: this.usage_count,
      created_by: this.created_by,
      created_at: this.created_at,
      updated_at: this.updated_at
    };
  }

  /**
   * Generate a random color for the tag
   * @returns {string} Hex color code
   */
  static generateRandomColor() {
    const colors = [
      '#EF4444', '#F97316', '#F59E0B', '#10B981', '#06B6D4',
      '#3B82F6', '#6366F1', '#8B5CF6', '#EC4899', '#6B7280'
    ];
    return colors[Math.floor(Math.random() * colors.length)];
  }

  /**
   * Validate tag name
   * @param {string} name - Tag name
   * @returns {boolean} Is valid
   */
  static isValidName(name) {
    if (!name || typeof name !== 'string') {
      return false;
    }
    
    // Check length (1-50 characters)
    if (name.length < 1 || name.length > 50) {
      return false;
    }
    
    // Check allowed characters (alphanumeric, spaces, hyphens, underscores)
    const validPattern = /^[a-zA-Z0-9\s\-_]+$/;
    return validPattern.test(name);
  }

  /**
   * Normalize tag name
   * @param {string} name - Tag name
   * @returns {string} Normalized name
   */
  static normalizeName(name) {
    if (!name) return '';
    
    return name
      .trim()
      .toLowerCase()
      .replace(/\s+/g, ' ') // Replace multiple spaces with single space
      .replace(/[^a-z0-9\s\-_]/g, ''); // Remove invalid characters
  }
}

/**
 * Note-Tag Association Model Class
 */
export class NoteTag {
  constructor(data = {}) {
    this.id = data.id || null;
    this.note_id = data.note_id || null;
    this.tag_id = data.tag_id || null;
    this.created_at = data.created_at || new Date().toISOString();
  }

  /**
   * Convert note-tag association instance to plain object
   * @returns {Object} Plain object representation
   */
  toJSON() {
    return {
      id: this.id,
      note_id: this.note_id,
      tag_id: this.tag_id,
      created_at: this.created_at
    };
  }
}

/**
 * File-Tag Association Model Class
 */
export class FileTag {
  constructor(data = {}) {
    this.id = data.id || null;
    this.file_id = data.file_id || null;
    this.tag_id = data.tag_id || null;
    this.created_at = data.created_at || new Date().toISOString();
  }

  /**
   * Convert file-tag association instance to plain object
   * @returns {Object} Plain object representation
   */
  toJSON() {
    return {
      id: this.id,
      file_id: this.file_id,
      tag_id: this.tag_id,
      created_at: this.created_at
    };
  }
}

/**
 * Tag Model Service
 */
export class TagModel {
  constructor(env) {
    this.env = env;
    this.db = createDatabaseService(env);
  }

  /**
   * Initialize tag tables
   */
  async initializeTables() {
    const createTagsTableSQL = `
      CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        color TEXT DEFAULT '#6B7280',
        description TEXT DEFAULT '',
        is_system INTEGER DEFAULT 0,
        usage_count INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
      )
    `;

    const createNoteTagsTableSQL = `
      CREATE TABLE IF NOT EXISTS note_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id INTEGER NOT NULL,
        tag_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
        FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
        UNIQUE(note_id, tag_id)
      )
    `;

    const createFileTagsTableSQL = `
      CREATE TABLE IF NOT EXISTS file_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER NOT NULL,
        tag_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
        FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
        UNIQUE(file_id, tag_id)
      )
    `;

    const createIndexesSQL = [
      'CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)',
      'CREATE INDEX IF NOT EXISTS idx_tags_is_system ON tags(is_system)',
      'CREATE INDEX IF NOT EXISTS idx_tags_usage_count ON tags(usage_count)',
      'CREATE INDEX IF NOT EXISTS idx_tags_created_by ON tags(created_by)',
      'CREATE INDEX IF NOT EXISTS idx_note_tags_note_id ON note_tags(note_id)',
      'CREATE INDEX IF NOT EXISTS idx_note_tags_tag_id ON note_tags(tag_id)',
      'CREATE INDEX IF NOT EXISTS idx_file_tags_file_id ON file_tags(file_id)',
      'CREATE INDEX IF NOT EXISTS idx_file_tags_tag_id ON file_tags(tag_id)'
    ];

    try {
      await this.db.query(createTagsTableSQL);
      await this.db.query(createNoteTagsTableSQL);
      await this.db.query(createFileTagsTableSQL);
      
      for (const indexSQL of createIndexesSQL) {
        await this.db.query(indexSQL);
      }
      
      console.log('Tag tables initialized successfully');
    } catch (error) {
      console.error('Failed to initialize tag tables:', error);
      throw error;
    }
  }

  /**
   * Create a new tag
   * @param {Object} tagData - Tag data
   * @returns {Tag} Created tag
   */
  async create(tagData) {
    if (!tagData.name) {
      throw new HTTPException(400, { message: 'Tag name is required' });
    }

    const normalizedName = Tag.normalizeName(tagData.name);
    if (!Tag.isValidName(normalizedName)) {
      throw new HTTPException(400, { message: 'Invalid tag name' });
    }

    try {
      const tag = new Tag({
        ...tagData,
        name: normalizedName,
        color: tagData.color || Tag.generateRandomColor()
      });

      const newTagData = {
        name: tag.name,
        color: tag.color,
        description: tag.description,
        is_system: tag.is_system ? 1 : 0,
        usage_count: tag.usage_count,
        created_by: tag.created_by,
        created_at: tag.created_at,
        updated_at: tag.updated_at
      };

      const result = await this.db.insert('tags', newTagData);
      
      if (result.success) {
        const tagId = result.data.meta.last_row_id;
        return await this.findById(tagId);
      }

      throw new HTTPException(500, { message: 'Failed to create tag' });
    } catch (error) {
      if (error.status) {
        throw error;
      }
      console.error('Create tag error:', error);
      throw new HTTPException(500, { message: 'Failed to create tag' });
    }
  }

  /**
   * Find tag by ID
   * @param {number} id - Tag ID
   * @returns {Tag|null} Tag instance
   */
  async findById(id) {
    try {
      const result = await this.db.select(
        'SELECT * FROM tags WHERE id = ?',
        [id]
      );
      
      if (result.length === 0) {
        return null;
      }
      
      return new Tag(result[0]);
    } catch (error) {
      console.error('Find tag by ID error:', error);
      return null;
    }
  }

  /**
   * Find tag by name
   * @param {string} name - Tag name
   * @returns {Tag|null} Tag instance
   */
  async findByName(name) {
    try {
      const normalizedName = Tag.normalizeName(name);
      const result = await this.db.select(
        'SELECT * FROM tags WHERE name = ?',
        [normalizedName]
      );
      
      if (result.length === 0) {
        return null;
      }
      
      return new Tag(result[0]);
    } catch (error) {
      console.error('Find tag by name error:', error);
      return null;
    }
  }

  /**
   * Update tag
   * @param {number} id - Tag ID
   * @param {Object} updateData - Update data
   * @returns {Tag|null} Updated tag
   */
  async update(id, updateData) {
    try {
      // Check if tag exists
      const existingTag = await this.findById(id);
      if (!existingTag) {
        throw new HTTPException(404, { message: 'Tag not found' });
      }

      // Handle name normalization if name is being updated
      if (updateData.name) {
        const normalizedName = Tag.normalizeName(updateData.name);
        if (!Tag.isValidName(normalizedName)) {
          throw new HTTPException(400, { message: 'Invalid tag name' });
        }
        updateData.name = normalizedName;
      }

      const allowedFields = ['name', 'color', 'description', 'usage_count'];
      const filteredData = {};
      
      for (const [key, value] of Object.entries(updateData)) {
        if (allowedFields.includes(key)) {
          filteredData[key] = value;
        }
      }
      
      filteredData.updated_at = new Date().toISOString();
      
      const result = await this.db.update('tags', filteredData, { id });
      
      if (result.success && result.data.meta.changes > 0) {
        return await this.findById(id);
      }
      
      return null;
    } catch (error) {
      if (error.status) {
        throw error;
      }
      console.error('Update tag error:', error);
      throw new HTTPException(500, { message: 'Failed to update tag' });
    }
  }

  /**
   * Delete tag
   * @param {number} id - Tag ID
   * @returns {boolean} Success
   */
  async delete(id) {
    try {
      // Check if tag exists
      const existingTag = await this.findById(id);
      if (!existingTag) {
        throw new HTTPException(404, { message: 'Tag not found' });
      }

      // Don't allow deletion of system tags
      if (existingTag.is_system) {
        throw new HTTPException(403, { message: 'Cannot delete system tag' });
      }

      const result = await this.db.delete('tags', { id });
      
      return result.success && result.data.meta.changes > 0;
    } catch (error) {
      if (error.status) {
        throw error;
      }
      console.error('Delete tag error:', error);
      return false;
    }
  }

  /**
   * Get tags with pagination and filtering
   * @param {Object} options - Query options
   * @returns {Object} Tags and pagination info
   */
  async getTags(options = {}) {
    const { 
      page = 1, 
      limit = 50, 
      search = null,
      is_system = null,
      sortBy = 'usage_count',
      sortOrder = 'DESC',
      created_by = null
    } = options;

    const offset = (page - 1) * limit;
    
    try {
      let whereConditions = [];
      let params = [];
      
      if (search) {
        whereConditions.push('(name LIKE ? OR description LIKE ?)');
        params.push(`%${search}%`, `%${search}%`);
      }
      
      if (is_system !== null) {
        whereConditions.push('is_system = ?');
        params.push(is_system ? 1 : 0);
      }
      
      if (created_by !== null) {
        whereConditions.push('created_by = ?');
        params.push(created_by);
      }
      
      const whereClause = whereConditions.length > 0 ? `WHERE ${whereConditions.join(' AND ')}` : '';
      
      // Get total count
      const countResult = await this.db.select(
        `SELECT COUNT(*) as total FROM tags ${whereClause}`,
        params
      );
      
      const total = countResult[0].total;
      
      // Get tags
      const tagsResult = await this.db.select(
        `SELECT * FROM tags ${whereClause} ORDER BY ${sortBy} ${sortOrder} LIMIT ? OFFSET ?`,
        [...params, limit, offset]
      );
      
      const tags = tagsResult.map(tag => new Tag(tag));
      
      return {
        tags: tags.map(tag => tag.toJSON()),
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
      console.error('Get tags error:', error);
      throw new HTTPException(500, { message: 'Failed to get tags' });
    }
  }

  /**
   * Add tag to note
   * @param {number} noteId - Note ID
   * @param {number} tagId - Tag ID
   * @returns {NoteTag|null} Created association
   */
  async addTagToNote(noteId, tagId) {
    try {
      // Check if note exists
      const noteExists = await this.db.select('SELECT id FROM notes WHERE id = ?', [noteId]);
      if (noteExists.length === 0) {
        throw new HTTPException(404, { message: 'Note not found' });
      }

      // Check if tag exists
      const tagExists = await this.db.select('SELECT id FROM tags WHERE id = ?', [tagId]);
      if (tagExists.length === 0) {
        throw new HTTPException(404, { message: 'Tag not found' });
      }

      // Check if association already exists
      const existingAssociation = await this.db.select(
        'SELECT id FROM note_tags WHERE note_id = ? AND tag_id = ?',
        [noteId, tagId]
      );
      
      if (existingAssociation.length > 0) {
        throw new HTTPException(409, { message: 'Tag already associated with note' });
      }

      const result = await this.db.insert('note_tags', {
        note_id: noteId,
        tag_id: tagId,
        created_at: new Date().toISOString()
      });

      if (result.success) {
        // Update tag usage count
        await this.incrementUsageCount(tagId);
        
        return new NoteTag({
          id: result.data.meta.last_row_id,
          note_id: noteId,
          tag_id: tagId,
          created_at: new Date().toISOString()
        });
      }

      throw new HTTPException(500, { message: 'Failed to add tag to note' });
    } catch (error) {
      if (error.status) {
        throw error;
      }
      console.error('Add tag to note error:', error);
      throw new HTTPException(500, { message: 'Failed to add tag to note' });
    }
  }

  /**
   * Remove tag from note
   * @param {number} noteId - Note ID
   * @param {number} tagId - Tag ID
   * @returns {boolean} Success
   */
  async removeTagFromNote(noteId, tagId) {
    try {
      const result = await this.db.delete('note_tags', { note_id: noteId, tag_id: tagId });
      
      if (result.success && result.data.meta.changes > 0) {
        // Update tag usage count
        await this.decrementUsageCount(tagId);
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Remove tag from note error:', error);
      return false;
    }
  }

  /**
   * Add tag to file
   * @param {number} fileId - File ID
   * @param {number} tagId - Tag ID
   * @returns {FileTag|null} Created association
   */
  async addTagToFile(fileId, tagId) {
    try {
      // Check if file exists
      const fileExists = await this.db.select('SELECT id FROM files WHERE id = ?', [fileId]);
      if (fileExists.length === 0) {
        throw new HTTPException(404, { message: 'File not found' });
      }

      // Check if tag exists
      const tagExists = await this.db.select('SELECT id FROM tags WHERE id = ?', [tagId]);
      if (tagExists.length === 0) {
        throw new HTTPException(404, { message: 'Tag not found' });
      }

      // Check if association already exists
      const existingAssociation = await this.db.select(
        'SELECT id FROM file_tags WHERE file_id = ? AND tag_id = ?',
        [fileId, tagId]
      );
      
      if (existingAssociation.length > 0) {
        throw new HTTPException(409, { message: 'Tag already associated with file' });
      }

      const result = await this.db.insert('file_tags', {
        file_id: fileId,
        tag_id: tagId,
        created_at: new Date().toISOString()
      });

      if (result.success) {
        // Update tag usage count
        await this.incrementUsageCount(tagId);
        
        return new FileTag({
          id: result.data.meta.last_row_id,
          file_id: fileId,
          tag_id: tagId,
          created_at: new Date().toISOString()
        });
      }

      throw new HTTPException(500, { message: 'Failed to add tag to file' });
    } catch (error) {
      if (error.status) {
        throw error;
      }
      console.error('Add tag to file error:', error);
      throw new HTTPException(500, { message: 'Failed to add tag to file' });
    }
  }

  /**
   * Remove tag from file
   * @param {number} fileId - File ID
   * @param {number} tagId - Tag ID
   * @returns {boolean} Success
   */
  async removeTagFromFile(fileId, tagId) {
    try {
      const result = await this.db.delete('file_tags', { file_id: fileId, tag_id: tagId });
      
      if (result.success && result.data.meta.changes > 0) {
        // Update tag usage count
        await this.decrementUsageCount(tagId);
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Remove tag from file error:', error);
      return false;
    }
  }

  /**
   * Get tags for a note
   * @param {number} noteId - Note ID
   * @returns {Array} Tags
   */
  async getTagsForNote(noteId) {
    try {
      const result = await this.db.select(`
        SELECT t.* FROM tags t
        INNER JOIN note_tags nt ON t.id = nt.tag_id
        WHERE nt.note_id = ?
        ORDER BY t.name ASC
      `, [noteId]);
      
      return result.map(tag => new Tag(tag));
    } catch (error) {
      console.error('Get tags for note error:', error);
      return [];
    }
  }

  /**
   * Get tags for a file
   * @param {number} fileId - File ID
   * @returns {Array} Tags
   */
  async getTagsForFile(fileId) {
    try {
      const result = await this.db.select(`
        SELECT t.* FROM tags t
        INNER JOIN file_tags ft ON t.id = ft.tag_id
        WHERE ft.file_id = ?
        ORDER BY t.name ASC
      `, [fileId]);
      
      return result.map(tag => new Tag(tag));
    } catch (error) {
      console.error('Get tags for file error:', error);
      return [];
    }
  }

  /**
   * Get notes with a specific tag
   * @param {number} tagId - Tag ID
   * @param {number} userId - User ID (for permission check)
   * @returns {Array} Note IDs
   */
  async getNotesWithTag(tagId, userId = null) {
    try {
      let query = `
        SELECT DISTINCT n.id FROM notes n
        INNER JOIN note_tags nt ON n.id = nt.note_id
        WHERE nt.tag_id = ? AND n.deleted_at IS NULL
      `;
      let params = [tagId];
      
      if (userId) {
        query += ' AND (n.user_id = ? OR n.is_public = 1)';
        params.push(userId);
      }
      
      query += ' ORDER BY n.created_at DESC';
      
      const result = await this.db.select(query, params);
      
      return result.map(row => row.id);
    } catch (error) {
      console.error('Get notes with tag error:', error);
      return [];
    }
  }

  /**
   * Get files with a specific tag
   * @param {number} tagId - Tag ID
   * @param {number} userId - User ID (for permission check)
   * @returns {Array} File IDs
   */
  async getFilesWithTag(tagId, userId = null) {
    try {
      let query = `
        SELECT DISTINCT f.id FROM files f
        INNER JOIN file_tags ft ON f.id = ft.file_id
        WHERE ft.tag_id = ? AND f.deleted_at IS NULL
      `;
      let params = [tagId];
      
      if (userId) {
        query += ' AND (f.user_id = ? OR f.is_public = 1)';
        params.push(userId);
      }
      
      query += ' ORDER BY f.created_at DESC';
      
      const result = await this.db.select(query, params);
      
      return result.map(row => row.id);
    } catch (error) {
      console.error('Get files with tag error:', error);
      return [];
    }
  }

  /**
   * Increment tag usage count
   * @param {number} tagId - Tag ID
   * @returns {boolean} Success
   */
  async incrementUsageCount(tagId) {
    try {
      const result = await this.db.query(
        'UPDATE tags SET usage_count = usage_count + 1 WHERE id = ?',
        [tagId]
      );
      
      return result.success && result.data.meta.changes > 0;
    } catch (error) {
      console.error('Increment usage count error:', error);
      return false;
    }
  }

  /**
   * Decrement tag usage count
   * @param {number} tagId - Tag ID
   * @returns {boolean} Success
   */
  async decrementUsageCount(tagId) {
    try {
      const result = await this.db.query(
        'UPDATE tags SET usage_count = usage_count - 1 WHERE id = ? AND usage_count > 0',
        [tagId]
      );
      
      return result.success && result.data.meta.changes > 0;
    } catch (error) {
      console.error('Decrement usage count error:', error);
      return false;
    }
  }

  /**
   * Get popular tags
   * @param {number} limit - Limit number of tags
   * @param {number} userId - User ID (optional)
   * @returns {Array} Popular tags
   */
  async getPopularTags(limit = 20, userId = null) {
    try {
      let query = `
        SELECT t.*, 
               (SELECT COUNT(*) FROM note_tags nt WHERE nt.tag_id = t.id) as note_count,
               (SELECT COUNT(*) FROM file_tags ft WHERE ft.tag_id = t.id) as file_count
        FROM tags t
        WHERE t.usage_count > 0
      `;
      let params = [];
      
      if (userId) {
        query += ' AND t.created_by = ?';
        params.push(userId);
      }
      
      query += ' ORDER BY t.usage_count DESC, t.name ASC LIMIT ?';
      params.push(limit);
      
      const result = await this.db.select(query, params);
      
      return result.map(tag => ({
        ...new Tag(tag).toJSON(),
        note_count: tag.note_count,
        file_count: tag.file_count
      }));
    } catch (error) {
      console.error('Get popular tags error:', error);
      return [];
    }
  }

  /**
   * Get tag statistics
   * @param {number} userId - User ID (optional)
   * @returns {Object} Tag statistics
   */
  async getStats(userId = null) {
    try {
      let whereClause = '';
      let params = [];
      
      if (userId) {
        whereClause = 'WHERE created_by = ?';
        params.push(userId);
      }
      
      const stats = await this.db.select(`
        SELECT 
          COUNT(*) as total_tags,
          COUNT(CASE WHEN is_system = 1 THEN 1 END) as system_tags,
          COUNT(CASE WHEN is_system = 0 THEN 1 END) as custom_tags,
          COUNT(CASE WHEN usage_count = 0 THEN 1 END) as unused_tags,
          COUNT(CASE WHEN DATE(created_at) = DATE('now') THEN 1 END) as tags_today,
          AVG(usage_count) as avg_usage_count,
          MAX(usage_count) as max_usage_count
        FROM tags ${whereClause}
      `);
      
      return {
        total_tags: stats[0]?.total_tags || 0,
        system_tags: stats[0]?.system_tags || 0,
        custom_tags: stats[0]?.custom_tags || 0,
        unused_tags: stats[0]?.unused_tags || 0,
        tags_today: stats[0]?.tags_today || 0,
        avg_usage_count: Math.round(stats[0]?.avg_usage_count || 0),
        max_usage_count: stats[0]?.max_usage_count || 0
      };
    } catch (error) {
      console.error('Get tag statistics error:', error);
      return {
        total_tags: 0,
        system_tags: 0,
        custom_tags: 0,
        unused_tags: 0,
        tags_today: 0,
        avg_usage_count: 0,
        max_usage_count: 0
      };
    }
  }

  /**
   * Create system tags
   * @param {Array} systemTags - System tags data
   * @returns {Array} Created system tags
   */
  async createSystemTags(systemTags) {
    try {
      const createdTags = [];
      
      for (const tagData of systemTags) {
        try {
          const existingTag = await this.findByName(tagData.name);
          if (!existingTag) {
            const tag = await this.create({
              ...tagData,
              is_system: true
            });
            createdTags.push(tag);
          }
        } catch (error) {
          console.error(`Failed to create system tag "${tagData.name}":`, error);
        }
      }
      
      return createdTags;
    } catch (error) {
      console.error('Create system tags error:', error);
      return [];
    }
  }
}

/**
 * Tag Model Factory
 * @param {Object} env - Environment variables
 * @returns {TagModel} Tag model instance
 */
export function createTagModel(env) {
  return new TagModel(env);
}

export default {
  Tag,
  NoteTag,
  FileTag,
  TagModel,
  createTagModel
};