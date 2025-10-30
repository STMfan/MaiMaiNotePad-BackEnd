# Cloudflare Workers 部署指南

## 概述

本指南详细介绍了如何将 MaiMaiNotePad 后端部署到 Cloudflare Workers，包括环境配置、数据库设置、存储配置和部署流程。

## 前置要求

### 1. 开发环境
- Node.js 18+ 
- npm 或 yarn
- Wrangler CLI (`npm install -g wrangler`)
- Git

### 2. Cloudflare 账户
- Cloudflare 账户
- Workers 订阅计划
- D1 数据库访问权限
- KV 命名空间访问权限
- R2 存储访问权限

### 3. 域名配置
- 已配置的域名（可选）
- DNS 管理权限

## 项目结构

```
MaiMaiNotePad-BackEnd/
├── src/
│   ├── models/           # D1 兼容数据模型
│   │   ├── User-workers.js
│   │   ├── Note-workers.js
│   │   ├── File-workers.js
│   │   ├── Tag-workers.js
│   │   └── index-workers.js
│   ├── middleware/       # Workers 中间件
│   │   ├── auth-workers.js
│   │   ├── rate-limit-workers.js
│   │   └── security-workers.js
│   ├── workers/          # Workers 核心文件
│   │   ├── config/
│   │   │   └── workers-config.js
│   │   ├── routes/
│   │   │   └── file-upload-workers.js
│   │   └── index.js      # 主入口文件
│   └── database/
│       └── migrations/   # 数据库迁移脚本
├── wrangler.toml         # Wrangler 配置文件
├── package.json
└── README.md
```

## 初始化配置

### 1. 安装依赖

```bash
npm install
```

### 2. 登录 Wrangler

```bash
wrangler login
```

### 3. 创建 Cloudflare 资源

#### 创建 D1 数据库
```bash
wrangler d1 create maimai-note-db
```

记录返回的 `database_id`，后续配置使用。

#### 创建 KV 命名空间
```bash
wrangler kv:namespace create "MAIMAI_KV"
wrangler kv:namespace create "MAIMAI_KV" --preview
```

记录返回的 `id` 和 `preview_id`。

#### 创建 R2 存储桶
```bash
wrangler r2 bucket create maimai-files
```

### 4. 配置 Wrangler

编辑 `wrangler.toml` 文件：

```toml
name = "maimai-note-backend"
main = "src/workers/index.js"
compatibility_date = "2024-01-01"
compatibility_flags = ["nodejs_compat"]

# Environment variables
[vars]
ENVIRONMENT = "development"
API_BASE_URL = "https://your-domain.com"
ALLOWED_ORIGINS = "https://your-domain.com,https://app.your-domain.com"

# D1 Database
[[d1_databases]]
binding = "MAIMAI_DB"
database_name = "maimai-note-db"
database_id = "your-database-id"

# KV Namespaces
[[kv_namespaces]]
binding = "MAIMAI_KV"
id = "your-kv-namespace-id"
preview_id = "your-preview-kv-namespace-id"

# R2 Storage
[[r2_buckets]]
binding = "MAIMAI_R2"
bucket_name = "maimai-files"

# Scheduled triggers
[triggers]
crons = ["0 2 * * *", "0 3 * * 0", "0 4 1 * *"]
```

### 5. 设置环境变量

#### 设置密钥
```bash
wrangler secret put JWT_SECRET
wrangler secret put WEBHOOK_SECRET
```

输入安全的密钥值。

#### 环境特定配置
```bash
# 开发环境
wrangler secret put JWT_SECRET --env development
wrangler secret put WEBHOOK_SECRET --env development

# 生产环境
wrangler secret put JWT_SECRET --env production
wrangler secret put WEBHOOK_SECRET --env production
```

## 数据库迁移

### 1. 创建迁移文件

在 `src/database/migrations/` 目录下创建迁移脚本：

```sql
-- 001_create_users_table.sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 002_create_notes_table.sql
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    is_public BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 003_create_files_table.sql
CREATE TABLE IF NOT EXISTS files (
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
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 004_create_tags_table.sql
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    color TEXT DEFAULT '#007bff',
    is_system BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 005_create_note_tags_table.sql
CREATE TABLE IF NOT EXISTS note_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(note_id, tag_id)
);

-- 006_create_file_tags_table.sql
CREATE TABLE IF NOT EXISTS file_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(file_id, tag_id)
);

-- 007_create_file_shares_table.sql
CREATE TABLE IF NOT EXISTS file_shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    share_token TEXT UNIQUE NOT NULL,
    expires_at DATETIME,
    access_count INTEGER DEFAULT 0,
    max_access_count INTEGER,
    password_hash TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- 008_create_indexes.sql
CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes(user_id);
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at);
CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at);
CREATE INDEX IF NOT EXISTS idx_files_expires_at ON files(expires_at);
CREATE INDEX IF NOT EXISTS idx_note_tags_note_id ON note_tags(note_id);
CREATE INDEX IF NOT EXISTS idx_note_tags_tag_id ON note_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_file_tags_file_id ON file_tags(file_id);
CREATE INDEX IF NOT EXISTS idx_file_tags_tag_id ON file_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_file_shares_token ON file_shares(share_token);
CREATE INDEX IF NOT EXISTS idx_file_shares_expires_at ON file_shares(expires_at);
```

### 2. 执行迁移

```bash
# 应用所有迁移
wrangler d1 execute maimai-note-db --file=src/database/migrations/001_create_users_table.sql
wrangler d1 execute maimai-note-db --file=src/database/migrations/002_create_notes_table.sql
# ... 继续执行其他迁移文件

# 或使用通配符
wrangler d1 execute maimai-note-db --file=src/database/migrations/*.sql
```

### 3. 验证迁移

```bash
wrangler d1 execute maimai-note-db --command="SELECT name FROM sqlite_master WHERE type='table';"
```

## 部署流程

### 1. 本地开发测试

```bash
# 启动本地开发服务器
wrangler dev

# 或使用特定环境
wrangler dev --env development
```

### 2. 部署到预览环境

```bash
# 部署到预览环境
wrangler deploy --env staging

# 运行测试
npm run test:staging
```

### 3. 部署到生产环境

```bash
# 部署到生产环境
wrangler deploy --env production

# 验证部署
wrangler tail --env production
```

### 4. 健康检查

部署后执行健康检查：

```bash
curl https://your-domain.com/health
```

## 环境配置

### 开发环境配置

```toml
[env.development]
name = "maimai-note-backend-dev"

[env.development.vars]
ENVIRONMENT = "development"
LOG_LEVEL = "debug"
RATE_LIMIT_MAX_REQUESTS = "1000"
MAX_FILE_SIZE = "104857600"  # 100MB
```

### 预发布环境配置

```toml
[env.staging]
name = "maimai-note-backend-staging"

[env.staging.vars]
ENVIRONMENT = "staging"
LOG_LEVEL = "info"
RATE_LIMIT_MAX_REQUESTS = "200"
MAX_FILE_SIZE = "52428800"  # 50MB
```

### 生产环境配置

```toml
[env.production]
name = "maimai-note-backend"

[env.production.vars]
ENVIRONMENT = "production"
LOG_LEVEL = "warn"
RATE_LIMIT_MAX_REQUESTS = "100"
MAX_FILE_SIZE = "52428800"  # 50MB
ENABLE_ANALYTICS = "true"
ENABLE_METRICS = "true"
```

## 自定义域名配置

### 1. 配置自定义域名

在 `wrangler.toml` 中添加：

```toml
[env.production.routes]
pattern = "api.yourdomain.com/*"
zone_name = "yourdomain.com"
```

### 2. DNS 配置

在 Cloudflare DNS 中添加记录：

```
Type: A
Name: api
IPv4 Address: 192.0.2.1  # 任意值，Workers 会覆盖
Proxy status: DNS only (灰色云)
```

### 3. Workers 路由配置

在 Cloudflare 控制台中：
1. 进入 Workers & Pages
2. 选择你的 Worker
3. 点击 "Triggers" 标签
4. 添加自定义域名路由

## 监控和日志

### 1. 日志查看

```bash
# 实时日志
wrangler tail

# 特定环境日志
wrangler tail --env production

# 过滤日志
wrangler tail --format=pretty | grep ERROR
```

### 2. 性能监控

在 Cloudflare 控制台中：
1. 进入 Workers & Pages
2. 选择你的 Worker
3. 查看 "Analytics" 标签

### 3. 错误追踪

配置错误通知：

```javascript
// 在配置中启用错误通知
ERROR_NOTIFICATION_ENABLED: true
```

## 备份和恢复

### 1. 数据库备份

```bash
# 导出数据库
wrangler d1 export maimai-note-db --output=backup.sql

# 定期备份脚本
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
wrangler d1 export maimai-note-db --output="backups/backup_${DATE}.sql"
```

### 2. R2 存储备份

```bash
# 使用 rclone 备份 R2
rclone sync remote:maimai-files backup:maimai-files-backup
```

### 3. KV 数据备份

```bash
# 导出 KV 数据
wrangler kv:namespace export --namespace-id=your-kv-id --output=kv-backup.json
```

## 故障排除

### 常见错误

#### 1. 数据库连接错误
```
Error: D1_ERROR: no such table: users
```
**解决方案**: 确保数据库迁移已正确执行。

#### 2. 存储访问错误
```
Error: R2_ERROR: AccessDenied
```
**解决方案**: 检查 R2 存储桶权限和绑定配置。

#### 3. 内存限制错误
```
Error: Worker exceeded memory limit
```
**解决方案**: 优化代码，减少内存使用，考虑分块处理。

### 调试技巧

1. **启用详细日志**:
   ```javascript
   LOG_LEVEL: 'debug'
   ```

2. **本地测试**:
   ```bash
   wrangler dev --local
   ```

3. **性能分析**:
   ```bash
   wrangler dev --experimental-local
   ```

## 性能优化

### 1. 缓存策略

```javascript
// 在响应中添加缓存头
return new Response(data, {
  headers: {
    'Cache-Control': 'public, max-age=3600',
    'ETag': '"version1"'
  }
});
```

### 2. 数据库优化

- 使用索引优化查询
- 批量操作减少请求次数
- 使用预编译语句

### 3. 代码优化

- 减少依赖包大小
- 使用 Tree Shaking
- 启用压缩

## 安全最佳实践

### 1. 密钥管理

- 使用 wrangler secret 管理敏感信息
- 定期轮换密钥
- 使用强密码策略

### 2. 访问控制

- 实施速率限制
- 使用 CORS 保护
- 验证所有输入

### 3. 数据保护

- 加密敏感数据
- 定期备份
- 实施数据过期策略

## 更新和回滚

### 1. 版本管理

```bash
# 创建新版本
git tag v1.0.0
git push origin v1.0.0

# 部署特定版本
wrangler deploy --env production --compatibility-date=2024-01-01
```

### 2. 回滚策略

```bash
# 快速回滚到上一个版本
wrangler rollback --env production

# 回滚到特定版本
wrangler rollback --env production --version-id=previous-version-id
```

### 3. 蓝绿部署

1. 部署到新环境
2. 测试新环境
3. 切换流量
4. 监控性能

## 成本优化

### 1. 请求优化

- 减少不必要的请求
- 使用缓存减少数据库查询
- 批量操作

### 2. 存储优化

- 压缩文件
- 删除过期文件
- 使用 CDN 加速

### 3. 数据库优化

- 定期清理旧数据
- 优化查询
- 使用索引

## 支持

如需技术支持，请联系：
- 邮箱: support@maimainote.com
- 文档: https://docs.maimainote.com
- 社区: https://community.maimainote.com