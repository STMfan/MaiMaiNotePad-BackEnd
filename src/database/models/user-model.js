/**
 * User Model for Cloudflare D1
 * 适配Workers运行时的用户数据模型
 */

export class UserModel {
  constructor(database) {
    this.db = database;
  }

  /**
   * 创建用户
   */
  async create(userData) {
    const {
      username,
      email,
      password,
      role = 'user',
      isActive = true,
      preferences = {},
      statistics = {}
    } = userData;

    const sql = `
      INSERT INTO users (username, email, password, role, is_active, preferences, statistics)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `;

    const result = await this.db.run(sql, [
      username,
      email,
      password,
      role,
      isActive ? 1 : 0,
      JSON.stringify(preferences),
      JSON.stringify(statistics)
    ]);

    return this.findById(result.meta.last_row_id);
  }

  /**
   * 根据ID查找用户
   */
  async findById(id) {
    const sql = 'SELECT * FROM users WHERE id = ?';
    const result = await this.db.query(sql, [id]);
    
    if (result.results.length === 0) {
      return null;
    }

    return this.formatUser(result.results[0]);
  }

  /**
   * 根据用户名查找用户
   */
  async findByUsername(username) {
    const sql = 'SELECT * FROM users WHERE username = ?';
    const result = await this.db.query(sql, [username]);
    
    if (result.results.length === 0) {
      return null;
    }

    return this.formatUser(result.results[0]);
  }

  /**
   * 根据邮箱查找用户
   */
  async findByEmail(email) {
    const sql = 'SELECT * FROM users WHERE email = ?';
    const result = await this.db.query(sql, [email]);
    
    if (result.results.length === 0) {
      return null;
    }

    return this.formatUser(result.results[0]);
  }

  /**
   * 更新用户
   */
  async update(id, updateData) {
    const fields = [];
    const values = [];

    Object.entries(updateData).forEach(([key, value]) => {
      if (key === 'preferences' || key === 'statistics') {
        fields.push(`${key} = ?`);
        values.push(JSON.stringify(value));
      } else if (key === 'isActive') {
        fields.push('is_active = ?');
        values.push(value ? 1 : 0);
      } else {
        fields.push(`${key} = ?`);
        values.push(value);
      }
    });

    if (fields.length === 0) {
      return this.findById(id);
    }

    fields.push('updated_at = CURRENT_TIMESTAMP');
    values.push(id);

    const sql = `UPDATE users SET ${fields.join(', ')} WHERE id = ?`;
    await this.db.run(sql, values);

    return this.findById(id);
  }

  /**
   * 删除用户
   */
  async delete(id) {
    const sql = 'DELETE FROM users WHERE id = ?';
    await this.db.run(sql, [id]);
    return true;
  }

  /**
   * 获取用户列表
   */
  async findAll(options = {}) {
    const {
      page = 1,
      limit = 10,
      role,
      isActive,
      search
    } = options;

    let whereClause = 'WHERE 1=1';
    const params = [];

    if (role) {
      whereClause += ' AND role = ?';
      params.push(role);
    }

    if (isActive !== undefined) {
      whereClause += ' AND is_active = ?';
      params.push(isActive ? 1 : 0);
    }

    if (search) {
      whereClause += ' AND (username LIKE ? OR email LIKE ?)';
      params.push(`%${search}%`, `%${search}%`);
    }

    const countSql = `SELECT COUNT(*) as total FROM users ${whereClause}`;
    const countResult = await this.db.query(countSql, params);
    const total = countResult.results[0].total;

    const offset = (page - 1) * limit;
    const selectSql = `
      SELECT * FROM users 
      ${whereClause} 
      ORDER BY created_at DESC 
      LIMIT ? OFFSET ?
    `;
    
    const result = await this.db.query(selectSql, [...params, limit, offset]);
    
    return {
      users: result.results.map(user => this.formatUser(user)),
      pagination: {
        page,
        limit,
        total,
        pages: Math.ceil(total / limit)
      }
    };
  }

  /**
   * 更新用户统计信息
   */
  async updateStatistics(id, statistics) {
    const user = await this.findById(id);
    if (!user) {
      throw new Error('User not found');
    }

    const updatedStatistics = {
      ...user.statistics,
      ...statistics,
      lastActivity: new Date().toISOString()
    };

    return this.update(id, { statistics: updatedStatistics });
  }

  /**
   * 验证用户密码
   */
  async validatePassword(id, password) {
    const user = await this.findById(id);
    if (!user) {
      return false;
    }

    // 在Workers环境中，密码验证应该在边缘函数中进行
    // 这里仅返回存储的密码哈希
    return user.password === password;
  }

  /**
   * 格式化用户数据
   */
  formatUser(user) {
    if (!user) return null;

    return {
      id: user.id,
      username: user.username,
      email: user.email,
      role: user.role,
      isActive: Boolean(user.is_active),
      preferences: this.safeJsonParse(user.preferences, {}),
      statistics: this.safeJsonParse(user.statistics, {}),
      createdAt: user.created_at,
      updatedAt: user.updated_at
    };
  }

  /**
   * 安全解析JSON
   */
  safeJsonParse(str, defaultValue = {}) {
    try {
      return str ? JSON.parse(str) : defaultValue;
    } catch (error) {
      console.error('JSON parse error:', error);
      return defaultValue;
    }
  }

  /**
   * 获取用户统计信息
   */
  async getStatistics() {
    const sql = `
      SELECT 
        COUNT(*) as total_users,
        COUNT(CASE WHEN role = 'admin' THEN 1 END) as admin_count,
        COUNT(CASE WHEN role = 'user' THEN 1 END) as user_count,
        COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_users,
        COUNT(CASE WHEN DATE(created_at) = DATE('now') THEN 1 END) as today_users
      FROM users
    `;

    const result = await this.db.query(sql);
    return result.results[0];
  }
}