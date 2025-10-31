# GitHub Actions 工作流文档

## 工作流概览

本项目包含以下GitHub Actions工作流，用于自动化部署和测试：

### 1. 自动部署工作流
**文件**: `deploy-to-cloudflare.yml`

**触发条件**:
- 推送到 `main` 分支
- 向 `main` 分支提交Pull Request

**功能**:
- 自动部署到Cloudflare Workers
- 配置环境变量
- 部署成功/失败通知

### 2. 手动部署工作流
**文件**: `deploy-to-cloudflare-manual.yml`

**触发条件**:
- 手动触发（通过GitHub界面）
- 可选择部署环境（production/staging/development）

**功能**:
- 手动控制部署时机
- 支持多环境部署
- 部署前运行测试
- 自定义部署说明

### 3. 测试和构建工作流
**文件**: `test-and-build.yml`

**触发条件**:
- 推送到 `main` 或 `develop` 分支
- 向这些分支提交Pull Request

**功能**:
- 多Node.js版本测试（16.x, 18.x, 20.x）
- 代码lint检查
- 运行测试套件
- 构建项目
- 安全审计
- 环境配置验证

## 环境变量配置

要使用这些工作流，需要在GitHub仓库中配置以下Secret：

### Cloudflare相关
- `CLOUDFLARE_API_TOKEN`: Cloudflare API令牌
- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare账户ID

#### Cloudflare API令牌权限

创建API令牌时需要设置以下权限：
- **Account**: Account - Read (账户级别读取权限)
- **Zone**: Zone - Read (可选，用于自定义域名)
- **Cloudflare Workers**: Workers Scripts - Edit (Workers脚本编辑权限)
- **Account**: R2 Storage - Edit (如果使用R2存储)
- **Account**: D1 Database - Edit (如果使用D1数据库)
- **Account**: KV Storage - Edit (如果使用KV存储)

### 应用配置
- `JWT_SECRET`: JWT密钥
- `JWT_EXPIRE`: JWT过期时间
- `ALLOWED_ORIGINS`: 允许的跨域源

### 邮件配置
- `EMAIL_ENABLED`: 是否启用邮件
- `EMAIL_PROVIDER`: 邮件提供商
- `EMAIL_FROM`: 发件人邮箱

### 存储配置
- `R2_ACCESS_KEY_ID`: R2存储访问密钥
- `R2_SECRET_ACCESS_KEY`: R2存储密钥
- `R2_BUCKET_NAME`: R2存储桶名称
- `R2_ENDPOINT`: R2端点

### 数据库配置
- `D1_DATABASE_ID`: D1数据库ID
- `KV_NAMESPACE_ID`: KV命名空间ID

## 使用方法

### 自动部署
1. 推送代码到 `main` 分支
2. 工作流会自动触发并部署到Cloudflare Workers

### 手动部署
1. 进入GitHub仓库的 "Actions" 标签页
2. 选择 "Manual Deploy to Cloudflare Workers"
3. 点击 "Run workflow"
4. 选择目标环境
5. 填写部署说明（可选）
6. 点击 "Run workflow" 按钮

### 查看部署状态
- 在GitHub的 "Actions" 标签页查看工作流运行状态
- 点击具体的工作流运行可查看详细日志

## 故障排除

### 部署失败常见原因
1. **环境变量缺失**: 检查是否配置了所有必需的Secret
2. **Cloudflare API令牌无效**: 确保API令牌具有足够的权限
3. **构建错误**: 检查代码是否有语法错误或依赖问题
4. **环境配置错误**: 验证环境变量值是否正确

### 检查日志
1. 进入GitHub的 "Actions" 标签页
2. 点击失败的工作流运行
3. 查看具体步骤的日志输出
4. 根据错误信息进行修复

## 安全建议

1. **保护Secret**: 不要在代码中硬编码敏感信息
2. **使用环境**: 利用GitHub Environments功能管理不同环境的部署
3. **审查工作流**: 定期检查和更新工作流配置
4. **监控部署**: 关注部署状态和性能指标