# MaiMai NotePad - 后端

MaiBot的非官方知识库与人设卡分享网站后端服务

## 项目简介

这是一个基于Node.js + Express.js + MongoDB的知识库管理平台后端，提供用户认证、知识库管理、角色卡分享等核心功能。

## 技术栈

- **后端框架**: Node.js + Express.js / Cloudflare Workers
- **数据库**: MongoDB + Mongoose / Cloudflare D1 (SQLite)
- **认证**: JWT (JSON Web Token)
- **文件上传**: Multer / Cloudflare R2
- **邮件服务**: Nodemailer
- **安全防护**: Helmet, CORS, Rate Limiting / 原生Workers安全中间件
- **日志**: Winston / 原生Workers日志系统
- **测试**: Jest + Supertest
- **文档**: Swagger
- **部署**: Docker / Cloudflare Workers

## 功能特性

- 🔐 **用户认证**: 注册、登录、JWT认证、密码重置
- 📚 **知识库管理**: 创建、编辑、搜索、分类管理
- 👤 **人设卡系统**: 人设卡上传、分享、审核、管理
  - 支持多种格式：JSON、Markdown、纯文本、TOML
  - 完整审核流程：待审核、已通过、已拒绝状态
  - 文件内容优先：支持文件上传和直接内容输入
  - 邮件通知：审核结果自动通知用户
  - 统计分析：审核统计、上传趋势分析
- 📝 **版本控制**: 知识库版本历史管理
- 📢 **公告系统**: 管理员发布公告
- 🔍 **搜索功能**: 全文搜索、标签搜索
- 📊 **统计分析**: 下载统计、用户行为分析
- 👮 **权限管理**: 管理员、审核员、普通用户角色
- 📤 **文件处理**: 支持多种文档格式解析
- 📧 **邮件通知**: 注册确认、密码重置、人设卡审核通知等

## 快速开始

### 环境要求

- Node.js >= 16.0.0
- MongoDB >= 4.4
- npm >= 8.0.0

### 安装依赖

```bash
npm install
```

### 环境配置

#### 快速配置（推荐）
使用交互式配置向导：
```bash
npm run setup
```

#### 手动配置
1. 复制环境变量示例文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，配置以下关键参数：

```env
# 服务器配置
NODE_ENV=development
PORT=3001

# 数据库配置
MONGODB_URI=mongodb://localhost:27017/maimai-notepad

# JWT配置
JWT_SECRET=your-jwt-secret-key
JWT_EXPIRE=7d

# 邮件服务配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

# 文件上传配置
UPLOAD_MAX_SIZE=10485760
ALLOWED_FILE_TYPES=txt,md,pdf,doc,docx,json,toml

# Redis配置（可选）
REDIS_URL=redis://localhost:6379
```

### 启动服务

```bash
# 开发模式
npm run dev

# 生产模式
npm start
```

服务启动后，访问 http://localhost:3001/health 检查服务状态

## API文档

启动服务后，访问 http://localhost:3001/api-docs 查看完整的API文档

### 人设卡API概览

#### 公开接口
- `GET /api/character/list` - 获取公开人设卡列表（支持分页、搜索、分类）
- `GET /api/character/:id` - 获取人设卡详情

#### 用户接口（需要认证）
- `POST /api/character/upload` - 上传人设卡（支持文件上传和直接内容输入）
- `PUT /api/character/:id` - 更新人设卡
- `DELETE /api/character/:id` - 删除人设卡
- `GET /api/character/user/:userId` - 获取用户的人设卡列表

#### 管理员接口
- `GET /api/admin/characters` - 获取所有人设卡（支持状态筛选）
- `GET /api/admin/characters/pending` - 获取待审核人设卡
- `GET /api/admin/characters/:id` - 获取人设卡详情
- `PUT /api/admin/characters/:id/review` - 审核人设卡（通过/拒绝）
- `DELETE /api/admin/characters/:id` - 删除人设卡
- `GET /api/admin/characters/stats` - 获取人设卡统计信息

#### 支持格式
- JSON格式：结构化人设卡数据
- Markdown格式：格式化文本内容
- 纯文本格式：简单文本内容
- TOML格式：配置文件格式

#### 文件上传
支持直接上传文件（.json, .md, .txt, .toml）或直接在请求中提供内容，文件内容优先使用

## 项目结构

### 传统部署结构
```
backend/
├── src/
│   ├── config/          # 配置文件
│   ├── controllers/     # 控制器层
│   ├── middleware/      # 中间件
│   ├── models/          # 数据模型
│   ├── routes/          # 路由定义
│   ├── services/        # 业务逻辑
│   ├── scripts/         # 脚本工具
│   ├── utils/           # 工具函数
│   ├── uploads/         # 文件上传目录
│   ├── app.js           # Express应用配置
│   └── server.js        # 服务器入口
├── tests/               # 测试文件
├── templates/           # 模板文件
├── logs/                # 日志文件
└── backups/             # 备份文件
```

### Cloudflare Workers 结构
```
backend/
├── src/
│   ├── config/          # 配置文件
│   ├── database/        # D1数据库客户端和迁移
│   │   ├── d1-client.js
│   │   ├── migrate.js
│   │   └── migrations/
│   ├── middleware/      # Workers原生中间件
│   │   ├── auth-workers.js
│   │   ├── error-handler.js
│   │   ├── security-workers.js
│   │   └── rate-limit-workers.js
│   ├── models/          # Workers数据模型
│   │   ├── User-workers.js
│   │   ├── Note-workers.js
│   │   ├── File-workers.js
│   │   ├── Character-workers.js  # 人设卡数据模型
│   │   └── index-workers.js
│   ├── routes/          # Workers路由处理
│   │   ├── auth-workers.js
│   │   ├── knowledge-workers.js
│   │   ├── character-workers.js  # 人设卡路由
│   │   ├── admin-workers.js      # 管理员功能（含人设卡管理）
│   │   └── upload-workers.js
│   ├── services/        # Workers服务
│   │   ├── database-workers.js
│   │   ├── cache-workers.js
│   │   └── storage-workers.js
│   ├── utils/           # 工具函数
│   └── workers/         # Workers主入口
│       ├── config/
│       ├── index.js     # Workers主文件
│       └── routes/
├── scripts/             # 构建和部署脚本
├── setup-env.js         # 环境配置向导
├── test-character-api.http  # 人设卡API测试文件
├── wrangler.toml        # Workers配置文件
└── package.json
```

## 开发指南

### 运行测试

```bash
# 运行所有测试
npm test

# 运行测试覆盖率
npm run test:coverage

# 监听模式运行测试
npm run test:watch
```

### 代码规范

```bash
# 检查代码规范
npm run lint

# 自动修复代码规范问题
npm run lint:fix

# 格式化代码
npm run format
```

### 数据库操作

```bash
# 清理测试数据
npm run cleanup

# 创建测试用户
npm run create-test-user
```

### 人设卡功能测试

```bash
# 使用HTTP测试文件测试人设卡API
# 打开 test-character-api.http 文件，使用REST客户端执行测试用例
```

## 部署指南

### Cloudflare Workers 部署（推荐）

#### 环境要求
- Node.js >= 16.0.0
- Wrangler CLI >= 3.0.0
- Cloudflare 账号

#### 安装 Wrangler
```bash
npm install -g wrangler
```

#### 配置 Wrangler
```bash
# 登录 Cloudflare
wrangler login

# 初始化项目（如果尚未初始化）
wrangler init
```

#### 配置环境变量
编辑 `wrangler.toml` 文件，配置以下参数：

```toml
name = "maimai-notepad-backend"
main = "src/workers/index.js"
compatibility_date = "2024-01-01"

[env.production.vars]
# 数据库配置
DATABASE_TYPE = "d1"
D1_DATABASE_ID = "your-d1-database-id"

# 存储配置
STORAGE_TYPE = "r2"
STORAGE_BUCKET = "maimai-notepad-files"
STORAGE_REGION = "auto"
STORAGE_ENDPOINT = "https://your-r2-endpoint.r2.cloudflarestorage.com"

# 安全配置
JWT_SECRET = "your-jwt-secret-key"
ALLOWED_ORIGINS = "https://maimnp.tech,https://www.maimnp.tech"

# 邮件配置（可选）
EMAIL_ENABLED = "true"
EMAIL_PROVIDER = "sendgrid"
EMAIL_FROM = "official@maimnp.tech"
```

#### 部署到 Cloudflare
```bash
# 测试部署（干运行）
wrangler deploy --dry-run

# 正式部署
wrangler deploy

# 部署到指定环境
wrangler deploy --env production
```

#### 绑定服务
在 Cloudflare 控制台中绑定以下服务：
- **D1 Database**: 创建并绑定数据库
- **R2 Storage**: 创建并绑定存储桶
- **KV Namespace**: 用于缓存和速率限制（可选）

### Docker部署

```bash
# 构建镜像
docker build -t maimai-notepad-backend .

# 运行容器
docker run -d -p 3001:3001 --env-file .env maimai-notepad-backend
```

### PM2部署

```bash
# 安装PM2
npm install -g pm2

# 启动应用
pm2 start src/server.js --name "maimai-notepad-backend"

# 保存PM2配置
pm2 save
pm2 startup
```

## 环境变量说明

### 传统部署环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| NODE_ENV | 运行环境 | development |
| PORT | 服务端口 | 3001 |
| MONGODB_URI | MongoDB连接字符串 | mongodb://localhost:27017/maimai-notepad |
| JWT_SECRET | JWT密钥 | 必填 |
| JWT_EXPIRE | JWT过期时间 | 7d |
| SMTP_HOST | SMTP服务器地址 | smtp.gmail.com |
| SMTP_PORT | SMTP服务器端口 | 587 |
| SMTP_USER | SMTP用户名 | 必填 |
| SMTP_PASS | SMTP密码 | 必填 |
| UPLOAD_MAX_SIZE | 文件上传大小限制 | 10485760 |
| ALLOWED_FILE_TYPES | 允许的文件类型 | txt,md,pdf,doc,docx |

### Cloudflare Workers 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| DATABASE_TYPE | 数据库类型 (d1/mongodb) | d1 |
| D1_DATABASE_ID | Cloudflare D1 数据库 ID | 必填 |
| STORAGE_TYPE | 存储类型 (r2/local) | r2 |
| STORAGE_BUCKET | R2 存储桶名称 | maimai-notepad-files |
| STORAGE_REGION | 存储区域 | auto |
| STORAGE_ENDPOINT | R2 存储端点 | https://your-r2-endpoint.r2.cloudflarestorage.com |
| JWT_SECRET | JWT密钥 | 必填 |
| JWT_EXPIRE | JWT过期时间 | 7d |
| ALLOWED_ORIGINS | 允许的跨域源 | https://maimnp.tech,https://www.maimnp.tech |
| RATE_LIMIT_ENABLED | 启用速率限制 | true |
| RATE_LIMIT_STORE | 速率限制存储 (kv/memory) | kv |
| CACHE_ENABLED | 启用缓存 | true |
| CACHE_TTL | 缓存过期时间 (秒) | 3600 |
| EMAIL_ENABLED | 启用邮件服务 | false |
| EMAIL_PROVIDER | 邮件提供商 (sendgrid/smtp) | sendgrid |
| EMAIL_FROM | 发件人邮箱 | official@maimnp.tech |
| ANALYTICS_ENABLED | 启用分析 | false |
| ANALYTICS_PROVIDER | 分析提供商 | cloudflare |
| BACKUP_ENABLED | 启用备份 | false |
| BACKUP_RETENTION_DAYS | 备份保留天数 | 7 |
| MAINTENANCE_MODE | 维护模式 | false |

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情

## 免责声明

本项目是MaiBot的非官方知识库平台，与MaiBot官方无关。MaiBot是独立的项目，本项目仅作为学习和交流使用。

## 支持

如果你有任何问题或建议，请通过以下方式联系我们：

- 提交 [Issue](https://github.com/STMfan/MaiMaiNotePad-BackEnd/issues)
- 发送邮件至: official@maimnp.tech

---

**⭐ 如果这个项目对你有帮助，请给个Star支持一下！**