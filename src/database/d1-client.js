/**
 * Cloudflare D1 Database Client
 * 适配Cloudflare Workers的D1数据库客户端
 */

export class D1Client {
  constructor(database) {
    this.db = database;
  }

  /**
   * 执行原始SQL查询
   */
  async query(sql, params = []) {
    try {
      const stmt = this.db.prepare(sql);
      const result = params.length > 0 ? await stmt.bind(...params).all() : await stmt.all();
      return result;
    } catch (error) {
      console.error('D1 Query Error:', error);
      throw new Error(`Database query failed: ${error.message}`);
    }
  }

  /**
   * 执行单个语句
   */
  async run(sql, params = []) {
    try {
      const stmt = this.db.prepare(sql);
      const result = params.length > 0 ? await stmt.bind(...params).run() : await stmt.run();
      return result;
    } catch (error) {
      console.error('D1 Run Error:', error);
      throw new Error(`Database operation failed: ${error.message}`);
    }
  }

  /**
   * 批量执行语句
   */
  async batch(statements) {
    try {
      const preparedStatements = statements.map(({ sql, params }) => {
        const stmt = this.db.prepare(sql);
        return params ? stmt.bind(...params) : stmt;
      });
      return await this.db.batch(preparedStatements);
    } catch (error) {
      console.error('D1 Batch Error:', error);
      throw new Error(`Database batch operation failed: ${error.message}`);
    }
  }

  /**
   * 事务处理
   */
  async transaction(callback) {
    try {
      await this.db.exec('BEGIN TRANSACTION');
      const result = await callback(this);
      await this.db.exec('COMMIT');
      return result;
    } catch (error) {
      await this.db.exec('ROLLBACK');
      console.error('D1 Transaction Error:', error);
      throw error;
    }
  }

  /**
   * 创建表结构
   */
  async createTables() {
    const createUsersTable = `
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        is_active BOOLEAN DEFAULT 1,
        preferences TEXT,
        statistics TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `;

    const createKnowledgeTable = `
      CREATE TABLE IF NOT EXISTS knowledge (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT,
        tags TEXT,
        author_id INTEGER,
        is_public BOOLEAN DEFAULT 1,
        view_count INTEGER DEFAULT 0,
        like_count INTEGER DEFAULT 0,
        version INTEGER DEFAULT 1,
        parent_id INTEGER,
        metadata TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL
      )
    `;

    const createSessionsTable = `
      CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_id INTEGER,
        data TEXT,
        expires_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `;

    const createFilesTable = `
      CREATE TABLE IF NOT EXISTS files (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        original_name TEXT NOT NULL,
        mime_type TEXT,
        size INTEGER,
        path TEXT,
        metadata TEXT,
        uploaded_by INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
      )
    `;

    const createBackupsTable = `
      CREATE TABLE IF NOT EXISTS backups (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        size INTEGER,
        path TEXT,
        metadata TEXT,
        created_by INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
      )
    `;

    try {
      await this.db.exec(createUsersTable);
      await this.db.exec(createKnowledgeTable);
      await this.db.exec(createSessionsTable);
      await this.db.exec(createFilesTable);
      await this.db.exec(createBackupsTable);
      console.log('Database tables created successfully');
    } catch (error) {
      console.error('Error creating tables:', error);
      throw error;
    }
  }

  /**
   * 初始化默认数据
   */
  async initializeDefaultData() {
    try {
      // 检查是否已有管理员用户
      const adminCheck = await this.query('SELECT id FROM users WHERE role = ?', ['admin']);
      
      if (adminCheck.results.length === 0) {
        // 创建默认管理员用户
        const bcrypt = await import('bcryptjs');
        const hashedPassword = await bcrypt.hash('admin123', 10);
        
        await this.run(
          'INSERT INTO users (username, email, password, role, is_active) VALUES (?, ?, ?, ?, ?)',
          ['admin', 'admin@example.com', hashedPassword, 'admin', 1]
        );
        
        console.log('Default admin user created (username: admin, password: admin123)');
      }
    } catch (error) {
      console.error('Error initializing default data:', error);
      throw error;
    }
  }
}

/**
 * 创建D1客户端实例
 */
export function createD1Client(database) {
  return new D1Client(database);
}