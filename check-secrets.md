# GitHub Secrets Configuration Checker

这个脚本用于检查本地环境变量配置，帮助您与GitHub Actions中的secrets进行比较。

## 使用方法

1. 复制 `.env.example` 文件为 `.env.local`
2. 填写您的实际配置值
3. 运行检查脚本

## 检查步骤

### 1. 检查本地环境变量

```bash
# 在项目根目录运行
node check-env.js
```

### 2. 检查GitHub Secrets配置

在GitHub Actions工作流运行后，查看"Debug environment variables"步骤的输出，比较以下内容：

- `CLOUDFLARE_API_TOKEN` 是否已设置
- `CLOUDFLARE_ACCOUNT_ID` 是否已设置
- `JWT_SECRET` 是否已设置
- 其他必需的secrets是否已设置

## 常见问题

### 1. Fork仓库问题

如果您的仓库是fork，GitHub不会继承原仓库的secrets。您需要：

1. 在fork的仓库中重新配置所有secrets
2. 或者创建一个新的仓库（不是fork）

### 2. 权限问题

确保您的GitHub Actions有权限访问secrets：

1. 检查仓库设置中的"Actions"权限
2. 确保工作流文件中的`permissions`配置正确

### 3. 环境特定secrets

如果您使用了环境特定的secrets，确保：

1. 工作流正确指定了环境
2. secrets已添加到正确的环境中

## 手动验证步骤

1. 访问您的GitHub仓库
2. 进入"Settings" > "Secrets and variables" > "Actions"
3. 确认以下secrets已正确配置：
   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_ACCOUNT_ID`
   - `JWT_SECRET`
   - 其他必需的secrets

## 获取Cloudflare信息

### 获取Account ID

1. 登录Cloudflare仪表板
2. 在右侧边栏找到"Account ID"
3. 复制该ID作为`CLOUDFLARE_ACCOUNT_ID`的值

### 创建API Token

1. 在Cloudflare中，进入"My Profile" > "API Tokens"
2. 点击"Create Token"
3. 使用"Custom token"模板
4. 配置权限：
   - Account: `Cloudflare Account:Read`
   - Zone: `Zone:Read`
   - Zone Resources: `Include All zones`
5. 复制生成的token作为`CLOUDFLARE_API_TOKEN`的值

## 联系支持

如果问题仍然存在，请提供以下信息：

1. GitHub Actions工作流的完整日志
2. 本地环境变量检查结果
3. GitHub Secrets配置截图（敏感信息请遮盖）