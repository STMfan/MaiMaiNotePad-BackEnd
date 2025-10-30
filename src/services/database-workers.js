/**
 * Cloudflare Workers Database Service
 * D1 database adapter for Cloudflare Workers with connection pooling and query optimization
 */

import { HTTPException } from 'hono/http-exception';

/**
 * Database Configuration
 */
const DB_CONFIG = {
  maxConnections: 10,
  connectionTimeout: 30000,
  queryTimeout: 10000,
  retryAttempts: 3,
  retryDelay: 1000,
  enableQueryLogging: process.env.NODE_ENV !== 'production',
  enableMetrics: true
};

/**
 * Database Connection Pool
 */
export class DatabasePool {
  constructor(env) {
    this.env = env;
    this.connections = new Map();
    this.activeConnections = 0;
    this.metrics = {
      totalQueries: 0,
      failedQueries: 0,
      averageQueryTime: 0,
      connectionPoolSize: 0
    };
  }

  /**
   * Get database connection
   * @returns {Object} Database connection
   */
  async getConnection() {
    if (!this.env.DB) {
      throw new HTTPException(500, { message: 'Database not configured' });
    }

    // For Cloudflare D1, we don't need traditional connection pooling
    // D1 handles connection management automatically
    return {
      db: this.env.DB,
      id: crypto.randomUUID(),
      createdAt: Date.now()
    };
  }

  /**
   * Release connection back to pool
   * @param {Object} connection - Database connection
   */
  releaseConnection(connection) {
    // D1 connections are automatically managed
    // This method is for compatibility with traditional pooling patterns
    if (connection && connection.id) {
      this.connections.delete(connection.id);
    }
  }

  /**
   * Get connection metrics
   * @returns {Object} Connection metrics
   */
  getMetrics() {
    return {
      ...this.metrics,
      activeConnections: this.activeConnections,
      connectionPoolSize: this.connections.size
    };
  }
}

/**
 * Database Service Class
 */
export class DatabaseService {
  constructor(env) {
    this.env = env;
    this.pool = new DatabasePool(env);
    this.queryLog = [];
    this.slowQueryThreshold = 1000; // 1 second
  }

  /**
   * Execute raw SQL query
   * @param {string} sql - SQL query
   * @param {Array} params - Query parameters
   * @param {Object} options - Query options
   * @returns {Object} Query result
   */
  async query(sql, params = [], options = {}) {
    const startTime = Date.now();
    const connection = await this.pool.getConnection();
    
    try {
      // Log query if enabled
      if (DB_CONFIG.enableQueryLogging) {
        this.logQuery(sql, params, startTime);
      }

      // Execute query using D1
      let result;
      if (sql.trim().toUpperCase().startsWith('SELECT')) {
        result = await connection.db.prepare(sql).bind(...params).all();
      } else {
        result = await connection.db.prepare(sql).bind(...params).run();
      }

      const executionTime = Date.now() - startTime;

      // Check for slow queries
      if (executionTime > this.slowQueryThreshold) {
        console.warn(`Slow query detected: ${executionTime}ms - ${sql}`);
      }

      // Update metrics
      this.pool.metrics.totalQueries++;
      this.pool.metrics.averageQueryTime = 
        (this.pool.metrics.averageQueryTime * (this.pool.metrics.totalQueries - 1) + executionTime) / 
        this.pool.metrics.totalQueries;

      return {
        success: true,
        data: result.results || result,
        meta: result.meta,
        executionTime
      };

    } catch (error) {
      this.pool.metrics.failedQueries++;
      
      console.error('Database query error:', error);
      console.error('SQL:', sql);
      console.error('Params:', params);

      throw new HTTPException(500, { 
        message: 'Database query failed',
        cause: error.message 
      });
    } finally {
      this.pool.releaseConnection(connection);
    }
  }

  /**
   * Execute SELECT query
   * @param {string} sql - SQL query
   * @param {Array} params - Query parameters
   * @returns {Array} Query results
   */
  async select(sql, params = []) {
    const result = await this.query(sql, params);
    return result.data;
  }

  /**
   * Execute INSERT query
   * @param {string} table - Table name
   * @param {Object} data - Data to insert
   * @returns {Object} Insert result
   */
  async insert(table, data) {
    const fields = Object.keys(data);
    const placeholders = fields.map(() => '?').join(', ');
    const values = Object.values(data);
    
    const sql = `INSERT INTO ${table} (${fields.join(', ')}) VALUES (${placeholders})`;
    
    return await this.query(sql, values);
  }

  /**
   * Execute UPDATE query
   * @param {string} table - Table name
   * @param {Object} data - Data to update
   * @param {Object} where - Where conditions
   * @returns {Object} Update result
   */
  async update(table, data, where = {}) {
    const setClause = Object.keys(data).map(key => `${key} = ?`).join(', ');
    const setValues = Object.values(data);
    
    const whereClause = Object.keys(where).map(key => `${key} = ?`).join(' AND ');
    const whereValues = Object.values(where);
    
    const sql = `UPDATE ${table} SET ${setClause} WHERE ${whereClause}`;
    
    return await this.query(sql, [...setValues, ...whereValues]);
  }

  /**
   * Execute DELETE query
   * @param {string} table - Table name
   * @param {Object} where - Where conditions
   * @returns {Object} Delete result
   */
  async delete(table, where = {}) {
    const whereClause = Object.keys(where).map(key => `${key} = ?`).join(' AND ');
    const whereValues = Object.values(where);
    
    const sql = `DELETE FROM ${table} WHERE ${whereClause}`;
    
    return await this.query(sql, whereValues);
  }

  /**
   * Execute transaction
   * @param {Function} callback - Transaction callback
   * @returns {Object} Transaction result
   */
  async transaction(callback) {
    // Note: D1 transactions are handled differently than traditional databases
    // This is a simplified implementation
    const connection = await this.pool.getConnection();
    
    try {
      // Begin transaction
      await this.query('BEGIN TRANSACTION');
      
      // Execute callback
      const result = await callback(this);
      
      // Commit transaction
      await this.query('COMMIT');
      
      return result;
    } catch (error) {
      // Rollback transaction
      await this.query('ROLLBACK');
      throw error;
    } finally {
      this.pool.releaseConnection(connection);
    }
  }

  /**
   * Check if table exists
   * @param {string} tableName - Table name
   * @returns {boolean} Table exists
   */
  async tableExists(tableName) {
    try {
      const result = await this.query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        [tableName]
      );
      return result.data.length > 0;
    } catch (error) {
      return false;
    }
  }

  /**
   * Get table schema
   * @param {string} tableName - Table name
   * @returns {Array} Table schema
   */
  async getTableSchema(tableName) {
    return await this.query(`PRAGMA table_info(${tableName})`);
  }

  /**
   * Get database statistics
   * @returns {Object} Database statistics
   */
  async getStats() {
    const tables = await this.query(
      "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    );
    
    const stats = {
      tables: {},
      totalSize: 0,
      connectionMetrics: this.pool.getMetrics()
    };

    for (const table of tables.data) {
      const count = await this.query(`SELECT COUNT(*) as count FROM ${table.name}`);
      stats.tables[table.name] = {
        rowCount: count.data[0].count,
        size: 0 // D1 doesn't provide table size information easily
      };
    }

    return stats;
  }

  /**
   * Log query for debugging
   * @param {string} sql - SQL query
   * @param {Array} params - Query parameters
   * @param {number} startTime - Start time
   */
  logQuery(sql, params, startTime) {
    const executionTime = Date.now() - startTime;
    const logEntry = {
      sql,
      params,
      executionTime,
      timestamp: new Date().toISOString()
    };
    
    this.queryLog.push(logEntry);
    
    // Keep only last 100 queries
    if (this.queryLog.length > 100) {
      this.queryLog.shift();
    }
    
    console.log(`[DB] ${executionTime}ms - ${sql}`);
  }

  /**
   * Get query log
   * @returns {Array} Query log
   */
  getQueryLog() {
    return this.queryLog;
  }

  /**
   * Clear query log
   */
  clearQueryLog() {
    this.queryLog = [];
  }

  /**
   * Health check
   * @returns {Object} Health status
   */
  async healthCheck() {
    try {
      const startTime = Date.now();
      await this.query('SELECT 1');
      const responseTime = Date.now() - startTime;
      
      return {
        status: 'healthy',
        responseTime,
        connectionPool: this.pool.getMetrics(),
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
 * Database Service Factory
 * @param {Object} env - Environment variables
 * @returns {DatabaseService} Database service instance
 */
export function createDatabaseService(env) {
  return new DatabaseService(env);
}

/**
 * Database utilities
 */
export const DatabaseUtils = {
  /**
   * Escape SQL identifier
   * @param {string} identifier - Identifier to escape
   * @returns {string} Escaped identifier
   */
  escapeIdentifier(identifier) {
    return `"${identifier.replace(/"/g, '""')}"`;
  },

  /**
   * Escape SQL value
   * @param {*} value - Value to escape
   * @returns {string} Escaped value
   */
  escapeValue(value) {
    if (value === null || value === undefined) {
      return 'NULL';
    }
    if (typeof value === 'string') {
      return `'${value.replace(/'/g, "''")}'`;
    }
    if (typeof value === 'number') {
      return value.toString();
    }
    if (typeof value === 'boolean') {
      return value ? '1' : '0';
    }
    if (value instanceof Date) {
      return `'${value.toISOString()}'`;
    }
    return `'${String(value)}'`;
  },

  /**
   * Build WHERE clause from conditions
   * @param {Object} conditions - Where conditions
   * @returns {Object} SQL and params
   */
  buildWhereClause(conditions) {
    if (!conditions || Object.keys(conditions).length === 0) {
      return { sql: '', params: [] };
    }

    const params = [];
    const clauses = [];

    for (const [key, value] of Object.entries(conditions)) {
      if (Array.isArray(value)) {
        const placeholders = value.map(() => '?').join(', ');
        clauses.push(`${key} IN (${placeholders})`);
        params.push(...value);
      } else if (value === null) {
        clauses.push(`${key} IS NULL`);
      } else {
        clauses.push(`${key} = ?`);
        params.push(value);
      }
    }

    return {
      sql: `WHERE ${clauses.join(' AND ')}`,
      params
    };
  }
};

export default {
  DatabaseService,
  DatabasePool,
  createDatabaseService,
  DatabaseUtils
};