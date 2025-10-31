# GitHub Actions 自动部署设置指南

## 概述

本指南将帮助你设置GitHub Actions，实现当main分支更新时自动同步到Cloudflare Workers。

## 前提条件

1. GitHub仓库已连接到本项目
2. Cloudflare账户已配置Workers服务
3. 拥有管理员权限的GitHub仓库访问权限

## 步骤一：配置Cloudflare API令牌

### 1. 创建API令牌
1. 登录Cloudflare控制台
2. 进入 "My Profile" → "API Tokens"
3. 点击 "Create Token"
4. 使用 "Custom token" 模板

### 2. 配置API令牌权限
设置以下权限：
- **Account**: Account - Read (账户级别读取权限)
- **Zone**: Zone - Read (如果需要自定义域名)
- **Cloudflare Workers**: Workers Scripts - Edit (Workers脚本编辑权限)
- **Account**: R2 Storage - Edit (如果使用R2存储)
- **Account**: D1 Database - Edit (如果使用D1数据库)
- **Account**: KV Storage - Edit (如果使用KV存储)

或者使用更简单的自定义权限设置：
- **Account**: Account:Read
- **Zone**: Zone:Read (可选，用于自定义域名)
- **Workers**: Workers Scripts:Edit
- **R2**: R2 Storage:Edit (如果使用R2)
- **D1**: D1 Database:Edit (如果使用D1)
- **KV**: KV Storage:Edit (如果使用KV)

### 3. 保存API令牌
- 复制生成的API令牌（只显示一次）
- 在下一步中将其添加到GitHub Secret中

## 步骤二：配置GitHub Secrets

### 1. 进入GitHub仓库设置
1. 打开GitHub仓库页面
2. 点击 "Settings" 标签
3. 在左侧菜单中选择 "Secrets and variables" → "Actions"

### 2. 添加必需的Secrets

#### Cloudflare相关
```
CLOUDFLARE_API_TOKEN=你的Cloudflare_API令牌
CLOUDFLARE_ACCOUNT_ID=你的Cloudflare账户ID
```

#### 获取账户ID
- 登录Cloudflare控制台
- 右侧边栏会显示 "Account ID"

#### 应用配置
```
JWT_SECRET=你的JWT密钥(至少32位随机字符串)
JWT_EXPIRE=7d
ALLOWED_ORIGINS=https://maimnp.tech,https://www.maimnp.tech
```

#### 邮件配置（可选）
```
EMAIL_ENABLED=true
EMAIL_PROVIDER=sendgrid
EMAIL_FROM=official@maimnp.tech
```

#### R2存储配置（如果使用）
```
R2_ACCESS_KEY_ID=你的R2访问密钥ID
R2_SECRET_ACCESS_KEY=你的R2密钥
R2_BUCKET_NAME=你的存储桶名称
R2_ENDPOINT=https://你的端点.r2.cloudflarestorage.com
```

#### D1数据库配置（如果使用）
```
D1_DATABASE_ID=你的D1数据库ID
```

#### KV存储配置（如果使用）
```
KV_NAMESPACE_ID=你的KV命名空间ID
```

## 步骤三：验证配置

### 1. 测试自动部署
1. 推送一个小更改到main分支
2. 进入GitHub的 "Actions" 标签页
3. 查看部署工作流是否自动触发
4. 检查部署是否成功

### 2. 测试手动部署
1. 进入GitHub的 "Actions" 标签页
2. 选择 "Manual Deploy to Cloudflare Workers"
3. 点击 "Run workflow"
4. 选择 "production" 环境
5. 填写测试说明
6. 点击运行并查看结果

## 步骤四：配置分支保护（推荐）

### 1. 设置分支保护规则
1. 进入 "Settings" → "Branches"
2. 点击 "Add branch protection rule"
3. 分支名称模式: `main`
4. 启用以下选项：
   - ✅ Require a pull request before merging
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Include administrators

### 2. 添加状态检查
在状态检查中添加：
- `Test and Build (Node.js 18.x)`
- 其他相关的CI检查

## 常见问题解决

### 1. 部署失败：API令牌权限不足
**错误**: `Authentication error` 或 `Permission denied`
**解决**: 
- 检查Cloudflare API令牌是否具有足够的权限
- 确保包含 `Account:Read` 和 `Workers Scripts:Edit` 权限
- 如果使用R2/D1/KV，确保包含相应的存储权限
- 重新生成API令牌并更新GitHub Secrets

### 2. 环境变量缺失
**错误**: `Missing required environment variable`
**解决**: 确保所有必需的GitHub Secrets都已配置

### 3. 构建失败
**错误**: `Build failed`
**解决**: 
- 检查代码是否有语法错误
- 确保所有依赖都已正确安装
- 查看详细的构建日志

### 4. Workers部署失败
**错误**: `Worker deployment failed`
**解决**:
- 检查wrangler.toml配置
- 确保Workers服务已启用
- 检查资源限制（如KV、D1配额）

## 监控和维护

### 1. 设置通知
1. 在GitHub中配置通知设置
2. 可以集成Slack、邮件等通知服务

### 2. 定期检查
- 每月检查API令牌是否即将过期
- 监控部署成功率和性能
- 更新依赖和工作流版本

### 3. 安全最佳实践
- 定期轮换API令牌
- 使用最小权限原则
- 监控异常的部署活动

## 相关文件

- `.github/workflows/deploy-to-cloudflare.yml` - 自动部署工作流
- `.github/workflows/deploy-to-cloudflare-manual.yml` - 手动部署工作流
- `.github/workflows/test-and-build.yml` - 测试和构建工作流
- `.github/workflows/README.md` - 工作流说明文档

## 获取帮助

如果遇到问题：
1. 查看GitHub Actions的运行日志
2. 检查Cloudflare Workers的控制台输出
3. 参考项目的文档和故障排除指南
4. 提交Issue到项目仓库