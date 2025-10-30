# 数据库迁移指南

## 概述

本指南详细介绍了如何将现有的 MaiMaiNotePad 数据库迁移到 Cloudflare Workers 环境，包括数据模型转换、SQL 语法适配和迁移脚本。

## 迁移准备

### 1. 数据备份

在开始迁移之前，请确保备份所有现有数据：

```bash
# PostgreSQL 备份
pg_dump -h localhost -U postgres -d maimainote > backup.sql

# MySQL 备份
mysqldump -u root -p maimainote > backup.sql

# SQLite 备份
cp database.db database-backup.db
```

### 2. 环境检查

确保已安装必要的工具：

```bash
# 安装 Wrangler
npm install -g wrangler

# 登录 Cloudflare
wrangler login

# 验证 D1 访问
wrangler d1 list
```

## 数据模型转换

### 1. PostgreSQL 到 D1 (SQLite) 转换

#### 用户表转换

**PostgreSQL 原表结构:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**D1 兼容表结构:**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    TEXT DEFAULT 'user',
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 笔记表转换

**PostgreSQL 原表结构:**
```sql
CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**D1 兼容表结构:**
```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    is_public BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### 2. MySQL 到 D1 (SQLite) 转换

#### 文件表转换

**MySQL 原表结构:**
```sql
CREATE TABLE files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    expires_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**D1 兼容表结构:**
```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    original_name TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    r2_key TEXT NOT NULL,
    is_public BOOLEAN DEFAULT 0,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

## 迁移脚本

### 1. 数据导出脚本

#### PostgreSQL 数据导出
```bash
#!/bin/bash
# export-postgres-data.sh

DB_NAME="maimainote"
OUTPUT_DIR="./migration-data"

mkdir -p $OUTPUT_DIR

# 导出用户数据
psql -d $DB_NAME -c "\copy (SELECT id, username, email, password_hash, role, is_active, created_at, updated_at FROM users) TO '$OUTPUT_DIR/users.csv' WITH CSV HEADER"

# 导出笔记数据
psql -d $DB_NAME -c "\copy (SELECT id, user_id, title, content, is_public, created_at, updated_at FROM notes) TO '$OUTPUT_DIR/notes.csv' WITH CSV HEADER"

# 导出文件数据
psql -d $DB_NAME -c "\copy (SELECT id, user_id, filename, original_name, file_size, mime_type, s3_key, is_public, expires_at, created_at, updated_at FROM files) TO '$OUTPUT_DIR/files.csv' WITH CSV HEADER"

# 导出标签数据
psql -d $DB_NAME -c "\copy (SELECT id, name, color, is_system, created_at FROM tags) TO '$OUTPUT_DIR/tags.csv' WITH CSV HEADER"

# 导出关联数据
psql -d $DB_NAME -c "\copy (SELECT note_id, tag_id FROM note_tags) TO '$OUTPUT_DIR/note_tags.csv' WITH CSV HEADER"
psql -d $DB_NAME -c "\copy (SELECT file_id, tag_id FROM file_tags) TO '$OUTPUT_DIR/file_tags.csv' WITH CSV HEADER"
```

#### MySQL 数据导出
```bash
#!/bin/bash
# export-mysql-data.sh

DB_NAME="maimainote"
OUTPUT_DIR="./migration-data"

mkdir -p $OUTPUT_DIR

# 导出用户数据
mysql -e "SELECT id, username, email, password_hash, role, is_active, created_at, updated_at FROM users" -B -u root $DB_NAME > $OUTPUT_DIR/users.tsv

# 导出笔记数据
mysql -e "SELECT id, user_id, title, content, is_public, created_at, updated_at FROM notes" -B -u root $DB_NAME > $OUTPUT_DIR/notes.tsv

# 导出文件数据
mysql -e "SELECT id, user_id, filename, original_name, file_size, mime_type, s3_key, is_public, expires_at, created_at, updated_at FROM files" -B -u root $DB_NAME > $OUTPUT_DIR/files.tsv
```

### 2. 数据转换脚本

#### CSV 到 SQL 转换器
```javascript
// csv-to-sql-converter.js
const fs = require('fs');
const csv = require('csv-parser');

class CsvToSqlConverter {
  constructor(tableName, columns, outputFile) {
    this.tableName = tableName;
    this.columns = columns;
    this.outputFile = outputFile;
    this.sqlStatements = [];
  }

  convert(csvFile) {
    return new Promise((resolve, reject) => {
      const results = [];
      
      fs.createReadStream(csvFile)
        .pipe(csv())
        .on('data', (data) => results.push(data))
        .on('end', () => {
          this.generateInsertStatements(results);
          this.writeOutput();
          resolve(this.sqlStatements);
        })
        .on('error', reject);
    });
  }

  generateInsertStatements(data) {
    this.sqlStatements.push(`-- Insert statements for ${this.tableName}`);
    this.sqlStatements.push(`DELETE FROM ${this.tableName};`);
    
    data.forEach(row => {
      const values = this.columns.map(col => {
        const value = row[col.name];
        return this.formatValue(value, col.type);
      });
      
      const columnNames = this.columns.map(col => col.name).join(', ');
      const insertStatement = `INSERT INTO ${this.tableName} (${columnNames}) VALUES (${values.join(', ')});`;
      this.sqlStatements.push(insertStatement);
    });
    
    this.sqlStatements.push(`-- Total records: ${data.length}`);
  }

  formatValue(value, type) {
    if (value === null || value === undefined || value === '') {
      return 'NULL';
    }
    
    switch (type) {
      case 'INTEGER':
      case 'BOOLEAN':
        return value;
      case 'TEXT':
        return `'${value.replace(/'/g, "''")}'`;
      case 'DATETIME':
        return `'${value}'`;
      default:
        return `'${value}'`;
    }
  }

  writeOutput() {
    const content = this.sqlStatements.join('\n');
    fs.writeFileSync(this.outputFile, content, 'utf8');
  }
}

// 使用示例
async function convertData() {
  // 转换用户数据
  const userColumns = [
    { name: 'id', type: 'INTEGER' },
    { name: 'username', type: 'TEXT' },
    { name: 'email', type: 'TEXT' },
    { name: 'password_hash', type: 'TEXT' },
    { name: 'role', type: 'TEXT' },
    { name: 'is_active', type: 'BOOLEAN' },
    { name: 'created_at', type: 'DATETIME' },
    { name: 'updated_at', type: 'DATETIME' }
  ];
  
  const userConverter = new CsvToSqlConverter('users', userColumns, './migration-data/users.sql');
  await userConverter.convert('./migration-data/users.csv');
  
  // 转换笔记数据
  const noteColumns = [
    { name: 'id', type: 'INTEGER' },
    { name: 'user_id', type: 'INTEGER' },
    { name: 'title', type: 'TEXT' },
    { name: 'content', type: 'TEXT' },
    { name: 'is_public', type: 'BOOLEAN' },
    { name: 'created_at', type: 'DATETIME' },
    { name: 'updated_at', type: 'DATETIME' }
  ];
  
  const noteConverter = new CsvToSqlConverter('notes', noteColumns, './migration-data/notes.sql');
  await noteConverter.convert('./migration-data/notes.csv');
}

convertData().catch(console.error);
```

### 3. 数据导入到 D1

#### 批量导入脚本
```javascript
// import-to-d1.js
import { execSync } from 'child_process';
import fs from 'fs';

class D1Importer {
  constructor(databaseName, accountId) {
    this.databaseName = databaseName;
    this.accountId = accountId;
  }

  async importData(sqlFile) {
    try {
      console.log(`Importing ${sqlFile} to ${this.databaseName}...`);
      
      const command = `wrangler d1 execute ${this.databaseName} --file=${sqlFile}`;
      const result = execSync(command, { encoding: 'utf8' });
      
      console.log(`✅ Successfully imported ${sqlFile}`);
      return result;
    } catch (error) {
      console.error(`❌ Failed to import ${sqlFile}:`, error.message);
      throw error;
    }
  }

  async importAll(dataDir) {
    const sqlFiles = [
      'users.sql',
      'notes.sql',
      'files.sql',
      'tags.sql',
      'note_tags.sql',
      'file_tags.sql',
      'file_shares.sql'
    ];

    for (const file of sqlFiles) {
      const filePath = `${dataDir}/${file}`;
      if (fs.existsSync(filePath)) {
        await this.importData(filePath);
      } else {
        console.warn(`⚠️  File not found: ${filePath}`);
      }
    }
  }
}

// 使用示例
const importer = new D1Importer('maimai-note-db', 'your-account-id');
await importer.importAll('./migration-data');
```

## SQL 语法差异处理

### 1. 数据类型映射

| PostgreSQL | MySQL | D1 (SQLite) | 说明 |
|------------|--------|-------------|------|
| SERIAL | AUTO_INCREMENT | INTEGER PRIMARY KEY AUTOINCREMENT | 自增ID |
| VARCHAR(n) | VARCHAR(n) | TEXT | 变长字符串 |
| TEXT | TEXT | TEXT | 长文本 |
| BOOLEAN | BOOLEAN | BOOLEAN | 布尔值 |
| TIMESTAMP | TIMESTAMP | DATETIME | 时间戳 |
| JSON | JSON | TEXT | JSON 数据 |
| UUID | VARCHAR(36) | TEXT | UUID |

### 2. 函数差异

#### 当前时间函数
```sql
-- PostgreSQL
SELECT CURRENT_TIMESTAMP;

-- MySQL
SELECT NOW();

-- D1 (SQLite)
SELECT CURRENT_TIMESTAMP;
```

#### 字符串连接
```sql
-- PostgreSQL
SELECT 'Hello' || ' ' || 'World';

-- MySQL
SELECT CONCAT('Hello', ' ', 'World');

-- D1 (SQLite)
SELECT 'Hello' || ' ' || 'World';
```

#### 随机数生成
```sql
-- PostgreSQL
SELECT RANDOM();

-- MySQL
SELECT RAND();

-- D1 (SQLite)
SELECT RANDOM();
```

### 3. 索引创建

```sql
-- PostgreSQL
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);

-- MySQL
CREATE INDEX idx_users_email ON users(email);

-- D1 (SQLite)
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
```

## 数据验证

### 1. 数据完整性检查

```sql
-- 检查记录数量
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'notes' as table_name, COUNT(*) as count FROM notes
UNION ALL
SELECT 'files' as table_name, COUNT(*) as count FROM files;

-- 检查外键约束
SELECT 'Orphan notes' as issue, COUNT(*) as count
FROM notes n LEFT JOIN users u ON n.user_id = u.id
WHERE u.id IS NULL;

SELECT 'Orphan files' as issue, COUNT(*) as count
FROM files f LEFT JOIN users u ON f.user_id = u.id
WHERE u.id IS NULL;
```

### 2. 数据一致性验证

```javascript
// data-validator.js
class DataValidator {
  constructor(env) {
    this.env = env;
  }

  async validateMigration() {
    const results = {
      tableCounts: {},
      dataIntegrity: {},
      indexes: {}
    };

    // 检查表记录数
    const tables = ['users', 'notes', 'files', 'tags', 'note_tags', 'file_tags'];
    for (const table of tables) {
      const result = await this.env.MAIMAI_DB.prepare(
        `SELECT COUNT(*) as count FROM ${table}`
      ).first();
      results.tableCounts[table] = result.count;
    }

    // 检查数据完整性
    const orphanNotes = await this.env.MAIMAI_DB.prepare(`
      SELECT COUNT(*) as count
      FROM notes n LEFT JOIN users u ON n.user_id = u.id
      WHERE u.id IS NULL
    `).first();
    results.dataIntegrity.orphanNotes = orphanNotes.count;

    const orphanFiles = await this.env.MAIMAI_DB.prepare(`
      SELECT COUNT(*) as count
      FROM files f LEFT JOIN users u ON f.user_id = u.id
      WHERE u.id IS NULL
    `).first();
    results.dataIntegrity.orphanFiles = orphanFiles.count;

    // 检查索引
    const indexes = await this.env.MAIMAI_DB.prepare(`
      SELECT name FROM sqlite_master WHERE type='index'
    `).all();
    results.indexes.count = indexes.results.length;

    return results;
  }
}

// 使用示例
const validator = new DataValidator(env);
const validationResults = await validator.validateMigration();
console.log('Migration validation results:', validationResults);
```

## 文件存储迁移

### 1. S3 到 R2 迁移

```javascript
// s3-to-r2-migrator.js
import { S3Client, ListObjectsV2Command, GetObjectCommand } from '@aws-sdk/client-s3';
import { R2Storage } from '../src/models/File-workers.js';

class S3ToR2Migrator {
  constructor(s3Config, r2Config) {
    this.s3Client = new S3Client(s3Config);
    this.r2Storage = new R2Storage(r2Config);
  }

  async migrateFiles(bucketName, prefix = '') {
    try {
      const objects = await this.listS3Objects(bucketName, prefix);
      console.log(`Found ${objects.length} files to migrate`);

      for (const object of objects) {
        await this.migrateFile(bucketName, object.Key);
      }

      console.log('Migration completed successfully');
    } catch (error) {
      console.error('Migration failed:', error);
      throw error;
    }
  }

  async listS3Objects(bucketName, prefix) {
    const command = new ListObjectsV2Command({
      Bucket: bucketName,
      Prefix: prefix
    });

    const response = await this.s3Client.send(command);
    return response.Contents || [];
  }

  async migrateFile(bucketName, key) {
    try {
      console.log(`Migrating ${key}...`);

      // 从 S3 下载文件
      const getCommand = new GetObjectCommand({ Bucket: bucketName, Key: key });
      const response = await this.s3Client.send(getCommand);
      
      const fileBuffer = await this.streamToBuffer(response.Body);
      
      // 上传到 R2
      const metadata = {
        contentType: response.ContentType || 'application/octet-stream',
        contentLength: response.ContentLength,
        lastModified: response.LastModified
      };

      await this.r2Storage.put(key, fileBuffer, metadata);
      
      console.log(`✅ Migrated ${key}`);
    } catch (error) {
      console.error(`❌ Failed to migrate ${key}:`, error);
      throw error;
    }
  }

  async streamToBuffer(stream) {
    const chunks = [];
    for await (const chunk of stream) {
      chunks.push(chunk);
    }
    return Buffer.concat(chunks);
  }
}

// 使用示例
const migrator = new S3ToR2Migrator(
  {
    region: 'us-east-1',
    credentials: {
      accessKeyId: 'your-s3-access-key',
      secretAccessKey: 'your-s3-secret-key'
    }
  },
  {
    accountId: 'your-cloudflare-account-id',
    accessKeyId: 'your-r2-access-key-id',
    secretAccessKey: 'your-r2-secret-access-key',
    bucket: 'maimai-files'
  }
);

await migrator.migrateFiles('your-s3-bucket', 'files/');
```

### 2. 文件记录更新

```sql
-- 更新文件记录中的存储路径
UPDATE files 
SET r2_key = REPLACE(s3_key, 's3://old-bucket/', ''),
    updated_at = CURRENT_TIMESTAMP
WHERE s3_key IS NOT NULL;

-- 验证迁移结果
SELECT 
    COUNT(*) as total_files,
    COUNT(CASE WHEN r2_key IS NOT NULL THEN 1 END) as migrated_files,
    COUNT(CASE WHEN s3_key IS NOT NULL THEN 1 END) as remaining_s3_files
FROM files;
```

## 回滚策略

### 1. 数据回滚

```sql
-- 创建回滚点
CREATE TABLE migration_rollback_point AS 
SELECT * FROM users WHERE 1=0;

-- 备份当前数据
INSERT INTO migration_rollback_point
SELECT * FROM users;

-- 回滚操作（如果需要）
DELETE FROM users;
INSERT INTO users SELECT * FROM migration_rollback_point;
```

### 2. 文件存储回滚

保持原始存储服务运行，直到确认迁移成功：

```javascript
// 双写策略，确保数据安全
class DualStorageManager {
  constructor(primaryStorage, backupStorage) {
    this.primaryStorage = primaryStorage;
    this.backupStorage = backupStorage;
  }

  async putFile(key, data, metadata) {
    // 同时写入两个存储
    await Promise.all([
      this.primaryStorage.put(key, data, metadata),
      this.backupStorage.put(key, data, metadata)
    ]);
  }

  async getFile(key) {
    try {
      // 优先从主存储读取
      return await this.primaryStorage.get(key);
    } catch (error) {
      // 主存储失败，从备份存储读取
      console.warn('Primary storage failed, trying backup:', error);
      return await this.backupStorage.get(key);
    }
  }
}
```

## 迁移验证清单

### ✅ 数据完整性
- [ ] 所有表记录数匹配
- [ ] 外键约束有效
- [ ] 索引正确创建
- [ ] 数据类型正确转换

### ✅ 功能验证
- [ ] 用户认证功能正常
- [ ] 笔记 CRUD 操作正常
- [ ] 文件上传/下载正常
- [ ] 标签系统正常
- [ ] 文件分享功能正常

### ✅ 性能验证
- [ ] 查询响应时间合理
- [ ] 索引生效
- [ ] 并发操作正常
- [ ] 内存使用合理

### ✅ 安全验证
- [ ] 数据加密正常
- [ ] 访问控制生效
- [ ] 审计日志完整
- [ ] 备份机制正常

## 常见问题解决

### 1. 字符编码问题

```sql
-- 检查字符编码
PRAGMA encoding;

-- 设置 UTF-8 编码
PRAGMA encoding = "UTF-8";
```

### 2. 日期时间格式

```javascript
// 日期时间转换函数
function convertDateTime(dateStr) {
  // PostgreSQL: 2023-12-25 10:30:00
  // MySQL: 2023-12-25 10:30:00
  // SQLite: 2023-12-25 10:30:00
  return dateStr.replace(' ', 'T');
}
```

### 3. 布尔值转换

```javascript
// 布尔值转换函数
function convertBoolean(value) {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'string') {
    return value.toLowerCase() === 'true' || value === '1';
  }
  return Boolean(value);
}
```

### 4. 大数据集处理

```javascript
// 分批处理大数据集
async function batchProcess(data, batchSize, processor) {
  for (let i = 0; i < data.length; i += batchSize) {
    const batch = data.slice(i, i + batchSize);
    await processor(batch);
    console.log(`Processed ${i + batch.length}/${data.length} records`);
  }
}
```

## 迁移后优化

### 1. 性能优化

```sql
-- 分析查询计划
EXPLAIN QUERY PLAN SELECT * FROM notes WHERE user_id = 1;

-- 更新统计信息
ANALYZE;
```

### 2. 存储优化

```sql
-- 清理临时数据
DELETE FROM files WHERE expires_at < CURRENT_TIMESTAMP;

-- 重建索引
REINDEX;
```

### 3. 监控设置

```javascript
// 设置监控和告警
class MigrationMonitor {
  constructor(env) {
    this.env = env;
  }

  async monitorPerformance() {
    const metrics = {
      tableSizes: await this.getTableSizes(),
      queryPerformance: await this.getQueryPerformance(),
      errorRates: await this.getErrorRates()
    };
    
    if (metrics.errorRates > 0.01) { // 1% 错误率阈值
      await this.sendAlert('High error rate detected after migration');
    }
    
    return metrics;
  }

  async getTableSizes() {
    const tables = ['users', 'notes', 'files', 'tags'];
    const sizes = {};
    
    for (const table of tables) {
      const result = await this.env.MAIMAI_DB.prepare(
        `SELECT COUNT(*) as count FROM ${table}`
      ).first();
      sizes[table] = result.count;
    }
    
    return sizes;
  }
}
```