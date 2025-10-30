/**
 * MongoDB to Cloudflare D1 Migration Script
 * 数据迁移脚本：从MongoDB迁移到Cloudflare D1
 */

import { MongoClient } from 'mongodb';
import { createD1Client } from '../database/d1-client.js';

/**
 * 迁移配置
 */
const MIGRATION_CONFIG = {
  batchSize: 100, // 每批处理的数据量
  maxRetries: 3, // 最大重试次数
  retryDelay: 1000, // 重试延迟(毫秒)
  dryRun: false, // 是否为试运行模式
  preserveObjectIds: true, // 是否保留MongoDB ObjectId
  transformData: true // 是否进行数据转换
};

/**
 * 数据迁移器类
 */
export class MongoDBToD1Migrator {
  constructor(mongoUri, d1Client, config = {}) {
    this.mongoUri = mongoUri;
    this.d1Client = d1Client;
    this.config = { ...MIGRATION_CONFIG, ...config };
    this.stats = {
      totalProcessed: 0,
      successful: 0,
      failed: 0,
      skipped: 0,
      startTime: null,
      endTime: null,
      collections: {}
    };
    this.errors = [];
  }

  /**
   * 连接到MongoDB
   */
  async connectMongoDB() {
    try {
      this.mongoClient = new MongoClient(this.mongoUri, {
        maxPoolSize: 10,
        serverSelectionTimeoutMS: 5000,
        socketTimeoutMS: 45000,
      });
      
      await this.mongoClient.connect();
      this.mongoDb = this.mongoClient.db();
      
      console.log('✅ Connected to MongoDB');
      return true;
    } catch (error) {
      console.error('❌ Failed to connect to MongoDB:', error.message);
      throw error;
    }
  }

  /**
   * 关闭MongoDB连接
   */
  async disconnectMongoDB() {
    if (this.mongoClient) {
      await this.mongoClient.close();
      console.log('✅ Disconnected from MongoDB');
    }
  }

  /**
   * 获取MongoDB集合列表
   */
  async getMongoCollections() {
    try {
      const collections = await this.mongoDb.listCollections().toArray();
      return collections.map(col => col.name);
    } catch (error) {
      console.error('❌ Failed to get MongoDB collections:', error.message);
      throw error;
    }
  }

  /**
   * 获取集合文档数量
   */
  async getCollectionCount(collectionName) {
    try {
      const collection = this.mongoDb.collection(collectionName);
      return await collection.countDocuments();
    } catch (error) {
      console.error(`❌ Failed to get count for ${collectionName}:`, error.message);
      return 0;
    }
  }

  /**
   * 转换MongoDB文档到D1格式
   */
  transformDocument(doc, collectionName) {
    const transformed = { ...doc };

    // 处理MongoDB ObjectId
    if (this.config.preserveObjectIds && doc._id) {
      transformed.id = doc._id.toString();
    } else {
      transformed.id = doc._id?.toString() || crypto.randomUUID();
    }

    // 删除MongoDB特有的字段
    delete transformed._id;

    // 处理日期字段
    if (doc.createdAt) {
      transformed.created_at = doc.createdAt instanceof Date ? doc.createdAt.toISOString() : doc.createdAt;
    }
    if (doc.updatedAt) {
      transformed.updated_at = doc.updatedAt instanceof Date ? doc.updatedAt.toISOString() : doc.updatedAt;
    }

    // 处理用户相关字段
    if (doc.userId) {
      transformed.user_id = doc.userId.toString();
      delete transformed.userId;
    }

    // 处理知识库相关字段
    if (collectionName === 'knowledge') {
      if (doc.categoryId) {
        transformed.category_id = doc.categoryId.toString();
        delete transformed.categoryId;
      }
      if (doc.userId) {
        transformed.user_id = doc.userId.toString();
        delete transformed.userId;
      }
      if (doc.createdAt) {
        transformed.created_at = doc.createdAt instanceof Date ? doc.createdAt.toISOString() : doc.createdAt;
      }
      if (doc.updatedAt) {
        transformed.updated_at = doc.updatedAt instanceof Date ? doc.updatedAt.toISOString() : doc.updatedAt;
      }
    }

    // 处理文件相关字段
    if (collectionName === 'files') {
      if (doc.userId) {
        transformed.user_id = doc.userId.toString();
        delete transformed.userId;
      }
      if (doc.uploadedBy) {
        transformed.uploaded_by = doc.uploadedBy.toString();
        delete transformed.uploadedBy;
      }
      if (doc.isPublic !== undefined) {
        transformed.is_public = doc.isPublic;
        delete transformed.isPublic;
      }
      if (doc.originalName) {
        transformed.original_name = doc.originalName;
        delete transformed.originalName;
      }
      if (doc.fileSize) {
        transformed.file_size = doc.fileSize;
        delete transformed.fileSize;
      }
      if (doc.mimeType) {
        transformed.mime_type = doc.mimeType;
        delete transformed.mimeType;
      }
      if (doc.storageKey) {
        transformed.storage_key = doc.storageKey;
        delete transformed.storageKey;
      }
    }

    // 处理备份相关字段
    if (collectionName === 'backups') {
      if (doc.userId) {
        transformed.user_id = doc.userId.toString();
        delete transformed.userId;
      }
      if (doc.fileSize) {
        transformed.file_size = doc.fileSize;
        delete transformed.fileSize;
      }
      if (doc.filePath) {
        transformed.file_path = doc.filePath;
        delete transformed.filePath;
      }
    }

    return transformed;
  }

  /**
   * 验证文档数据
   */
  validateDocument(doc, collectionName) {
    const errors = [];

    // 基本验证
    if (!doc.id) {
      errors.push('Missing required field: id');
    }

    // 集合特定验证
    switch (collectionName) {
      case 'users':
        if (!doc.username) errors.push('Missing required field: username');
        if (!doc.email) errors.push('Missing required field: email');
        if (!doc.password) errors.push('Missing required field: password');
        if (doc.role && !['admin', 'user', 'guest'].includes(doc.role)) {
          errors.push('Invalid role value');
        }
        break;

      case 'knowledge':
        if (!doc.title) errors.push('Missing required field: title');
        if (!doc.content) errors.push('Missing required field: content');
        if (doc.status && !['draft', 'published', 'archived'].includes(doc.status)) {
          errors.push('Invalid status value');
        }
        break;

      case 'files':
        if (!doc.original_name) errors.push('Missing required field: original_name');
        if (!doc.storage_key) errors.push('Missing required field: storage_key');
        break;

      case 'backups':
        if (!doc.file_path) errors.push('Missing required field: file_path');
        break;
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  /**
   * 迁移单个文档
   */
  async migrateDocument(doc, collectionName, retryCount = 0) {
    try {
      // 转换文档
      let transformedDoc = doc;
      if (this.config.transformData) {
        transformedDoc = this.transformDocument(doc, collectionName);
      }

      // 验证文档
      const validation = this.validateDocument(transformedDoc, collectionName);
      if (!validation.isValid) {
        return {
          success: false,
          skipped: true,
          error: `Validation failed: ${validation.errors.join(', ')}`
        };
      }

      // 检查是否已存在（基于ID）
      if (collectionName === 'users') {
        const existing = await this.d1Client.query(
          'SELECT id FROM users WHERE id = ? OR username = ? OR email = ?',
          [transformedDoc.id, transformedDoc.username, transformedDoc.email]
        );
        if (existing.results.length > 0) {
          return {
            success: false,
            skipped: true,
            error: 'User already exists'
          };
        }
      } else if (collectionName === 'knowledge') {
        const existing = await this.d1Client.query(
          'SELECT id FROM knowledge WHERE id = ?',
          [transformedDoc.id]
        );
        if (existing.results.length > 0) {
          return {
            success: false,
            skipped: true,
            error: 'Knowledge item already exists'
          };
        }
      }

      // 插入数据到D1
      let insertQuery, insertParams;

      switch (collectionName) {
        case 'users':
          insertQuery = `
            INSERT INTO users (id, username, email, password, role, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
          `;
          insertParams = [
            transformedDoc.id,
            transformedDoc.username,
            transformedDoc.email,
            transformedDoc.password,
            transformedDoc.role || 'user',
            transformedDoc.status || 'active',
            transformedDoc.created_at || new Date().toISOString(),
            transformedDoc.updated_at || new Date().toISOString()
          ];
          break;

        case 'knowledge':
          insertQuery = `
            INSERT INTO knowledge (id, title, content, category_id, user_id, status, tags, views, likes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          `;
          insertParams = [
            transformedDoc.id,
            transformedDoc.title,
            transformedDoc.content,
            transformedDoc.category_id || null,
            transformedDoc.user_id || null,
            transformedDoc.status || 'published',
            transformedDoc.tags || '',
            transformedDoc.views || 0,
            transformedDoc.likes || 0,
            transformedDoc.created_at || new Date().toISOString(),
            transformedDoc.updated_at || new Date().toISOString()
          ];
          break;

        case 'files':
          insertQuery = `
            INSERT INTO files (id, original_name, storage_key, mime_type, file_size, user_id, uploaded_by, is_public, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
          `;
          insertParams = [
            transformedDoc.id,
            transformedDoc.original_name,
            transformedDoc.storage_key,
            transformedDoc.mime_type,
            transformedDoc.file_size,
            transformedDoc.user_id || null,
            transformedDoc.uploaded_by || null,
            transformedDoc.is_public !== undefined ? transformedDoc.is_public : true,
            transformedDoc.created_at || new Date().toISOString()
          ];
          break;

        case 'backups':
          insertQuery = `
            INSERT INTO backups (id, file_path, file_size, user_id, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
          `;
          insertParams = [
            transformedDoc.id,
            transformedDoc.file_path,
            transformedDoc.file_size || 0,
            transformedDoc.user_id || null,
            transformedDoc.created_at || new Date().toISOString(),
            transformedDoc.status || 'completed'
          ];
          break;

        default:
          return {
            success: false,
            error: `Unsupported collection: ${collectionName}`
          };
      }

      if (!this.config.dryRun) {
        await this.d1Client.query(insertQuery, insertParams);
      }

      return {
        success: true,
        skipped: false,
        docId: transformedDoc.id
      };

    } catch (error) {
      // 重试机制
      if (retryCount < this.config.maxRetries) {
        console.warn(`⚠️  Retrying document migration (attempt ${retryCount + 1}/${this.config.maxRetries})`);
        await this.sleep(this.config.retryDelay * (retryCount + 1));
        return this.migrateDocument(doc, collectionName, retryCount + 1);
      }

      return {
        success: false,
        skipped: false,
        error: error.message
      };
    }
  }

  /**
   * 迁移集合
   */
  async migrateCollection(collectionName) {
    try {
      console.log(`\n📦 Starting migration of collection: ${collectionName}`);
      
      const collection = this.mongoDb.collection(collectionName);
      const totalCount = await collection.countDocuments();
      
      console.log(`📊 Total documents in ${collectionName}: ${totalCount}`);
      
      if (totalCount === 0) {
        console.log(`⏭️  Skipping empty collection: ${collectionName}`);
        this.stats.collections[collectionName] = {
          total: 0,
          migrated: 0,
          skipped: 0,
          failed: 0
        };
        return;
      }

      let processed = 0;
      let migrated = 0;
      let skipped = 0;
      let failed = 0;

      const cursor = collection.find({}).batchSize(this.config.batchSize);

      for await (const doc of cursor) {
        processed++;
        
        const result = await this.migrateDocument(doc, collectionName);
        
        if (result.success) {
          migrated++;
        } else if (result.skipped) {
          skipped++;
        } else {
          failed++;
          this.errors.push({
            collection: collectionName,
            docId: doc._id?.toString(),
            error: result.error
          });
        }

        // 进度报告
        if (processed % 100 === 0 || processed === totalCount) {
          console.log(`📈 Progress: ${processed}/${totalCount} (${Math.round((processed/totalCount) * 100)}%) - Migrated: ${migrated}, Skipped: ${skipped}, Failed: ${failed}`);
        }

        // 小延迟以避免过载
        if (processed % this.config.batchSize === 0) {
          await this.sleep(100);
        }
      }

      this.stats.collections[collectionName] = {
        total: processed,
        migrated,
        skipped,
        failed
      };

      console.log(`✅ Completed migration of ${collectionName}: ${migrated} migrated, ${skipped} skipped, ${failed} failed`);

    } catch (error) {
      console.error(`❌ Failed to migrate collection ${collectionName}:`, error.message);
      throw error;
    }
  }

  /**
   * 执行完整迁移
   */
  async migrate() {
    this.stats.startTime = new Date();
    
    try {
      console.log('🚀 Starting MongoDB to D1 migration...');
      console.log(`📋 Configuration: ${JSON.stringify(this.config, null, 2)}`);

      // 连接到MongoDB
      await this.connectMongoDB();

      // 获取集合列表
      const collections = await this.getMongoCollections();
      console.log(`📚 Found collections: ${collections.join(', ')}`);

      // 过滤需要迁移的集合
      const collectionsToMigrate = collections.filter(name => 
        ['users', 'knowledge', 'files', 'backups'].includes(name)
      );

      console.log(`🎯 Collections to migrate: ${collectionsToMigrate.join(', ')}`);

      // 迁移每个集合
      for (const collectionName of collectionsToMigrate) {
        await this.migrateCollection(collectionName);
      }

      this.stats.endTime = new Date();
      
      // 生成迁移报告
      const report = this.generateReport();
      console.log('\n📊 Migration Report:');
      console.log(report);

      return {
        success: true,
        stats: this.stats,
        report,
        errors: this.errors
      };

    } catch (error) {
      this.stats.endTime = new Date();
      
      console.error('❌ Migration failed:', error.message);
      
      return {
        success: false,
        error: error.message,
        stats: this.stats,
        errors: this.errors
      };

    } finally {
      await this.disconnectMongoDB();
    }
  }

  /**
   * 生成迁移报告
   */
  generateReport() {
    const duration = this.stats.endTime - this.stats.startTime;
    const totalProcessed = Object.values(this.stats.collections).reduce((sum, col) => sum + col.total, 0);
    const totalMigrated = Object.values(this.stats.collections).reduce((sum, col) => sum + col.migrated, 0);
    const totalFailed = Object.values(this.stats.collections).reduce((sum, col) => sum + col.failed, 0);

    return `
=====================================
🎯 MIGRATION REPORT
=====================================
📅 Start Time: ${this.stats.startTime.toISOString()}
📅 End Time: ${this.stats.endTime.toISOString()}
⏱️  Duration: ${Math.round(duration / 1000)}s

📊 Summary:
   Total Processed: ${totalProcessed}
   Successfully Migrated: ${totalMigrated}
   Failed: ${totalFailed}
   Success Rate: ${totalProcessed > 0 ? Math.round((totalMigrated / totalProcessed) * 100) : 0}%

📋 Collection Details:
${Object.entries(this.stats.collections).map(([name, stats]) => 
  `   ${name}: ${stats.migrated}/${stats.total} (${stats.failed} failed)`
).join('\n')}

${this.errors.length > 0 ? `
❌ Errors (${this.errors.length}):
${this.errors.map(err => `   - ${err.collection}: ${err.docId} - ${err.error}`).join('\n')}
` : ''}

=====================================
`;
  }

  /**
   * 延迟函数
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 验证迁移
   */
  async validateMigration() {
    console.log('\n🔍 Validating migration...');
    
    const validationResults = {};
    
    try {
      // 验证用户数据
      const userCount = await this.d1Client.query('SELECT COUNT(*) as count FROM users');
      validationResults.users = userCount.results[0].count;
      
      // 验证知识库数据
      const knowledgeCount = await this.d1Client.query('SELECT COUNT(*) as count FROM knowledge');
      validationResults.knowledge = knowledgeCount.results[0].count;
      
      // 验证文件数据
      const fileCount = await this.d1Client.query('SELECT COUNT(*) as count FROM files');
      validationResults.files = fileCount.results[0].count;
      
      // 验证备份数据
      const backupCount = await this.d1Client.query('SELECT COUNT(*) as count FROM backups');
      validationResults.backups = backupCount.results[0].count;

      console.log('✅ Validation completed:');
      Object.entries(validationResults).forEach(([table, count]) => {
        console.log(`   ${table}: ${count} records`);
      });

      return validationResults;

    } catch (error) {
      console.error('❌ Validation failed:', error.message);
      throw error;
    }
  }
}

/**
 * 主迁移函数
 */
export async function runMigration(mongoUri, d1Client, config = {}) {
  const migrator = new MongoDBToD1Migrator(mongoUri, d1Client, config);
  return await migrator.migrate();
}

/**
 * CLI执行函数
 */
export async function runMigrationCLI() {
  try {
    // 从环境变量获取配置
    const mongoUri = process.env.MONGODB_URI;
    const d1Database = process.env.D1_DATABASE;
    
    if (!mongoUri) {
      throw new Error('MONGODB_URI environment variable is required');
    }
    
    if (!d1Database) {
      throw new Error('D1_DATABASE environment variable is required');
    }

    // 创建D1客户端
    const d1Client = createD1Client(d1Database);

    // 配置选项
    const config = {
      batchSize: parseInt(process.env.BATCH_SIZE) || 100,
      maxRetries: parseInt(process.env.MAX_RETRIES) || 3,
      retryDelay: parseInt(process.env.RETRY_DELAY) || 1000,
      dryRun: process.env.DRY_RUN === 'true',
      preserveObjectIds: process.env.PRESERVE_OBJECT_IDS !== 'false',
      transformData: process.env.TRANSFORM_DATA !== 'false'
    };

    console.log('🚀 Starting MongoDB to D1 migration...');
    
    // 执行迁移
    const result = await runMigration(mongoUri, d1Client, config);
    
    if (result.success) {
      console.log('✅ Migration completed successfully!');
      
      // 验证迁移结果
      if (process.env.VALIDATE_MIGRATION !== 'false') {
        await result.migrator.validateMigration();
      }
      
      process.exit(0);
    } else {
      console.error('❌ Migration failed:', result.error);
      process.exit(1);
    }

  } catch (error) {
    console.error('❌ Migration CLI failed:', error.message);
    process.exit(1);
  }
}

// 如果直接运行此脚本
if (import.meta.url === `file://${process.argv[1]}`) {
  runMigrationCLI().catch(console.error);
}