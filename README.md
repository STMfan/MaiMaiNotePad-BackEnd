# MaiMai NotePad - 后端

MaiBot的非官方知识库与人设卡分享网站后端服务

## 项目简介

这是一个基于Node.js + Express.js + MongoDB的知识库管理平台后端，提供用户认证、知识库管理、角色卡分享等核心功能。

## 技术栈

- **后端框架**: Node.js + Express.js
- **数据库**: MongoDB + Mongoose
- **认证**: JWT (JSON Web Token)
- **文件上传**: Multer
- **邮件服务**: Nodemailer
- **安全防护**: Helmet, CORS, Rate Limiting
- **日志**: Winston
- **测试**: Jest + Supertest
- **文档**: Swagger

## 功能特性

- 🔐 **用户认证**: 注册、登录、JWT认证、密码重置
- 📚 **知识库管理**: 创建、编辑、搜索、分类管理
- 👤 **角色卡分享**: 角色卡上传、分享、下载、评分
- 📝 **版本控制**: 知识库版本历史管理
- 📢 **公告系统**: 管理员发布公告
- 🔍 **搜索功能**: 全文搜索、标签搜索
- 📊 **统计分析**: 下载统计、用户行为分析
- 👮 **权限管理**: 管理员、审核员、普通用户角色
- 📤 **文件处理**: 支持多种文档格式解析
- 📧 **邮件通知**: 注册确认、密码重置等

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
ALLOWED_FILE_TYPES=txt,md,pdf,doc,docx

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

## 项目结构

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

## 部署指南

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
- 发送邮件至: maimainotepad@gmail.com

---

**⭐ 如果这个项目对你有帮助，请给个Star支持一下！**