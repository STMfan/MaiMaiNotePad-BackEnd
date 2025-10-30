/**
 * User Model for Cloudflare Workers
 * D1-compatible user model with authentication and profile management
 */

import { HTTPException } from 'hono/http-exception';
import { createDatabaseService } from '../services/database-workers.js';

/**
 * User Model Class
 */
export class User {
  constructor(data = {}) {
    this.id = data.id || null;
    this.username = data.username || '';
    this.email = data.email || '';
    this.password_hash = data.password_hash || '';
    this.role = data.role || 'user';
    this.profile = data.profile ? JSON.parse(data.profile) : {};
    this.preferences = data.preferences ? JSON.parse(data.preferences) : {};
    this.is_active = data.is_active !== undefined ? data.is_active : true;
    this.email_verified = data.email_verified !== undefined ? data.email_verified : false;
    this.two_factor_enabled = data.two_factor_enabled !== undefined ? data.two_factor_enabled : false;
    this.two_factor_secret = data.two_factor_secret || null;
    this.last_login = data.last_login || null;
    this.login_attempts = data.login_attempts || 0;
    this.locked_until = data.locked_until || null;
    this.created_at = data.created_at || new Date().toISOString();
    this.updated_at = data.updated_at || new Date().toISOString();
  }

  /**
   * Convert user instance to plain object
   * @returns {Object} Plain object representation
   */
  toJSON() {
    return {
      id: this.id,
      username: this.username,
      email: this.email,
      role: this.role,
      profile: this.profile,
      preferences: this.preferences,
      is_active: this.is_active,
      email_verified: this.email_verified,
      two_factor_enabled: this.two_factor_enabled,
      last_login: this.last_login,
      login_attempts: this.login_attempts,
      locked_until: this.locked_until,
      created_at: this.created_at,
      updated_at: this.updated_at
    };
  }

  /**
   * Get safe user data (without sensitive information)
   * @returns {Object} Safe user data
   */
  toSafeJSON() {
    const userData = this.toJSON();
    delete userData.password_hash;
    delete userData.two_factor_secret;
    return userData;
  }
}

/**
 * User Model Service
 */
export class UserModel {
  constructor(env) {
    this.env = env;
    this.db = createDatabaseService(env);
  }

  /**
   * Initialize user table
   */
  async initializeTable() {
    const createTableSQL = `
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin', 'moderator')),
        profile TEXT DEFAULT '{}',
        preferences TEXT DEFAULT '{}',
        is_active INTEGER DEFAULT 1,
        email_verified INTEGER DEFAULT 0,
        two_factor_enabled INTEGER DEFAULT 0,
        two_factor_secret TEXT,
        last_login TEXT,
        login_attempts INTEGER DEFAULT 0,
        locked_until TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
      )
    `;

    const createIndexesSQL = [
      'CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)',
      'CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)',
      'CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)',
      'CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)',
      'CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at)'
    ];

    try {
      await this.db.query(createTableSQL);
      
      for (const indexSQL of createIndexesSQL) {
        await this.db.query(indexSQL);
      }
      
      console.log('Users table initialized successfully');
    } catch (error) {
      console.error('Failed to initialize users table:', error);
      throw error;
    }
  }

  /**
   * Create a new user
   * @param {Object} userData - User data
   * @returns {User} Created user
   */
  async create(userData) {
    const requiredFields = ['username', 'email', 'password_hash'];
    
    for (const field of requiredFields) {
      if (!userData[field]) {
        throw new HTTPException(400, { message: `Missing required field: ${field}` });
      }
    }

    try {
      // Check if username or email already exists
      const existingUser = await this.findByUsernameOrEmail(userData.username, userData.email);
      if (existingUser) {
        if (existingUser.username === userData.username) {
          throw new HTTPException(409, { message: 'Username already exists' });
        }
        if (existingUser.email === userData.email) {
          throw new HTTPException(409, { message: 'Email already exists' });
        }
      }

      // Prepare user data
      const newUserData = {
        username: userData.username.toLowerCase(),
        email: userData.email.toLowerCase(),
        password_hash: userData.password_hash,
        role: userData.role || 'user',
        profile: JSON.stringify(userData.profile || {}),
        preferences: JSON.stringify(userData.preferences || {}),
        is_active: userData.is_active !== undefined ? userData.is_active : true,
        email_verified: userData.email_verified || false,
        two_factor_enabled: userData.two_factor_enabled || false,
        two_factor_secret: userData.two_factor_secret || null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };

      const result = await this.db.insert('users', newUserData);
      
      if (result.success) {
        const userId = result.data.meta.last_row_id;
        return await this.findById(userId);
      }

      throw new HTTPException(500, { message: 'Failed to create user' });
    } catch (error) {
      if (error.status) {
        throw error;
      }
      console.error('Create user error:', error);
      throw new HTTPException(500, { message: 'Failed to create user' });
    }
  }

  /**
   * Find user by ID
   * @param {number} id - User ID
   * @returns {User|null} User instance
   */
  async findById(id) {
    try {
      const result = await this.db.select(
        'SELECT * FROM users WHERE id = ? AND is_active = 1',
        [id]
      );
      
      if (result.length === 0) {
        return null;
      }
      
      return new User(result[0]);
    } catch (error) {
      console.error('Find user by ID error:', error);
      return null;
    }
  }

  /**
   * Find user by username
   * @param {string} username - Username
   * @returns {User|null} User instance
   */
  async findByUsername(username) {
    try {
      const result = await this.db.select(
        'SELECT * FROM users WHERE username = ? AND is_active = 1',
        [username.toLowerCase()]
      );
      
      if (result.length === 0) {
        return null;
      }
      
      return new User(result[0]);
    } catch (error) {
      console.error('Find user by username error:', error);
      return null;
    }
  }

  /**
   * Find user by email
   * @param {string} email - Email
   * @returns {User|null} User instance
   */
  async findByEmail(email) {
    try {
      const result = await this.db.select(
        'SELECT * FROM users WHERE email = ? AND is_active = 1',
        [email.toLowerCase()]
      );
      
      if (result.length === 0) {
        return null;
      }
      
      return new User(result[0]);
    } catch (error) {
      console.error('Find user by email error:', error);
      return null;
    }
  }

  /**
   * Find user by username or email
   * @param {string} username - Username
   * @param {string} email - Email
   * @returns {User|null} User instance
   */
  async findByUsernameOrEmail(username, email) {
    try {
      const result = await this.db.select(
        'SELECT * FROM users WHERE username = ? OR email = ? LIMIT 1',
        [username.toLowerCase(), email.toLowerCase()]
      );
      
      if (result.length === 0) {
        return null;
      }
      
      return new User(result[0]);
    } catch (error) {
      console.error('Find user by username or email error:', error);
      return null;
    }
  }

  /**
   * Update user
   * @param {number} id - User ID
   * @param {Object} updateData - Update data
   * @returns {User|null} Updated user
   */
  async update(id, updateData) {
    try {
      // Remove fields that shouldn't be updated directly
      const allowedFields = [
        'username', 'email', 'password_hash', 'role', 'profile', 
        'preferences', 'is_active', 'email_verified', 'two_factor_enabled', 
        'two_factor_secret', 'last_login', 'login_attempts', 'locked_until'
      ];
      
      const filteredData = {};
      for (const [key, value] of Object.entries(updateData)) {
        if (allowedFields.includes(key)) {
          if (key === 'profile' || key === 'preferences') {
            filteredData[key] = JSON.stringify(value);
          } else {
            filteredData[key] = value;
          }
        }
      }
      
      filteredData.updated_at = new Date().toISOString();
      
      const result = await this.db.update('users', filteredData, { id });
      
      if (result.success && result.data.meta.changes > 0) {
        return await this.findById(id);
      }
      
      return null;
    } catch (error) {
      console.error('Update user error:', error);
      throw new HTTPException(500, { message: 'Failed to update user' });
    }
  }

  /**
   * Delete user (soft delete)
   * @param {number} id - User ID
   * @returns {boolean} Success
   */
  async delete(id) {
    try {
      const result = await this.db.update(
        'users', 
        { is_active: false, updated_at: new Date().toISOString() }, 
        { id }
      );
      
      return result.success && result.data.meta.changes > 0;
    } catch (error) {
      console.error('Delete user error:', error);
      return false;
    }
  }

  /**
   * Get users with pagination
   * @param {Object} options - Query options
   * @returns {Object} Users and pagination info
   */
  async getUsers(options = {}) {
    const { 
      page = 1, 
      limit = 20, 
      role = null, 
      is_active = true, 
      search = null,
      sortBy = 'created_at',
      sortOrder = 'DESC'
    } = options;

    const offset = (page - 1) * limit;
    
    try {
      let whereConditions = ['is_active = ?'];
      let params = [is_active ? 1 : 0];
      
      if (role) {
        whereConditions.push('role = ?');
        params.push(role);
      }
      
      if (search) {
        whereConditions.push('(username LIKE ? OR email LIKE ?)');
        params.push(`%${search}%`, `%${search}%`);
      }
      
      const whereClause = whereConditions.join(' AND ');
      
      // Get total count
      const countResult = await this.db.select(
        `SELECT COUNT(*) as total FROM users WHERE ${whereClause}`,
        params
      );
      
      const total = countResult[0].total;
      
      // Get users
      const usersResult = await this.db.select(
        `SELECT * FROM users WHERE ${whereClause} ORDER BY ${sortBy} ${sortOrder} LIMIT ? OFFSET ?`,
        [...params, limit, offset]
      );
      
      const users = usersResult.map(user => new User(user));
      
      return {
        users: users.map(user => user.toSafeJSON()),
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
      console.error('Get users error:', error);
      throw new HTTPException(500, { message: 'Failed to get users' });
    }
  }

  /**
   * Update user login attempts
   * @param {number} id - User ID
   * @param {number} attempts - Login attempts
   * @param {Date|null} lockedUntil - Lock expiration
   * @returns {boolean} Success
   */
  async updateLoginAttempts(id, attempts, lockedUntil = null) {
    try {
      const updateData = {
        login_attempts: attempts,
        updated_at: new Date().toISOString()
      };
      
      if (lockedUntil) {
        updateData.locked_until = lockedUntil.toISOString();
      }
      
      const result = await this.db.update('users', updateData, { id });
      return result.success && result.data.meta.changes > 0;
    } catch (error) {
      console.error('Update login attempts error:', error);
      return false;
    }
  }

  /**
   * Update last login time
   * @param {number} id - User ID
   * @returns {boolean} Success
   */
  async updateLastLogin(id) {
    try {
      const result = await this.db.update(
        'users',
        {
          last_login: new Date().toISOString(),
          login_attempts: 0,
          locked_until: null,
          updated_at: new Date().toISOString()
        },
        { id }
      );
      
      return result.success && result.data.meta.changes > 0;
    } catch (error) {
      console.error('Update last login error:', error);
      return false;
    }
  }

  /**
   * Check if user is locked
   * @param {number} id - User ID
   * @returns {boolean} Is locked
   */
  async isUserLocked(id) {
    try {
      const result = await this.db.select(
        'SELECT locked_until FROM users WHERE id = ?',
        [id]
      );
      
      if (result.length === 0) {
        return false;
      }
      
      const lockedUntil = result[0].locked_until;
      if (!lockedUntil) {
        return false;
      }
      
      return new Date(lockedUntil) > new Date();
    } catch (error) {
      console.error('Check user lock status error:', error);
      return false;
    }
  }

  /**
   * Get user statistics
   * @returns {Object} User statistics
   */
  async getStats() {
    try {
      const stats = await this.db.select(`
        SELECT 
          COUNT(*) as total_users,
          COUNT(CASE WHEN role = 'admin' THEN 1 END) as admin_count,
          COUNT(CASE WHEN role = 'user' THEN 1 END) as user_count,
          COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_users,
          COUNT(CASE WHEN email_verified = 1 THEN 1 END) as verified_users,
          COUNT(CASE WHEN two_factor_enabled = 1 THEN 1 END) as two_factor_users,
          COUNT(CASE WHEN DATE(created_at) = DATE('now') THEN 1 END) as users_today,
          COUNT(CASE WHEN DATE(last_login) = DATE('now') THEN 1 END) as active_today
        FROM users
      `);
      
      return stats[0];
    } catch (error) {
      console.error('Get user statistics error:', error);
      return {
        total_users: 0,
        admin_count: 0,
        user_count: 0,
        active_users: 0,
        verified_users: 0,
        two_factor_users: 0,
        users_today: 0,
        active_today: 0
      };
    }
  }
}

/**
 * User Model Factory
 * @param {Object} env - Environment variables
 * @returns {UserModel} User model instance
 */
export function createUserModel(env) {
  return new UserModel(env);
}

export default {
  User,
  UserModel,
  createUserModel
};