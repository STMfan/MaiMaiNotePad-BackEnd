# GitHub Secrets 配置指南

## 问题诊断

根据GitHub Actions的调试输出，您的仓库中只包含一个默认的`github_token`，而缺少部署到Cloudflare Workers所需的关键secrets：

```
Available secrets: { 
  github_token: *** 
}
```

## 解决步骤

### 1. 访问GitHub仓库设置

1. 打开您的GitHub仓库：https://github.com/STMfan/MaiMaiNotePad-BackEnd
2. 点击仓库顶部的"Settings"选项卡
3. 在左侧菜单中，找到并点击"Secrets and variables"
4. 点击"Actions"子选项

### 2. 添加必需的Repository Secrets

点击"New repository secret"按钮，逐一添加以下secrets：

#### 2.1 CLOUDFLARE_API_TOKEN

1. **Name**: `CLOUDFLARE_API_TOKEN`
2. **获取方法**:
   - 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
   - 点击右上角头像，选择"My Profile"
   - 在左侧菜单中点击"API Tokens"
   - 点击"Create Token"按钮
   - 点击"Custom token"旁边的"Use template"
   - 配置以下权限：
     - **Account**: `Cloudflare Account:Read`
     - **Zone**: `Zone:Read`
     - **Zone Resources**: `Include All zones`
   - 点击"Continue to summary"
   - 确认配置后点击"Create Token"
   - 复制生成的token
3. **Secret**: 粘贴刚刚复制的API token

#### 2.2 CLOUDFLARE_ACCOUNT_ID

1. **Name**: `CLOUDFLARE_ACCOUNT_ID`
2. **获取方法**:
   - 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
   - 在右侧边栏找到"Account ID"
   - 点击复制按钮复制该ID
3. **Secret**: 粘贴刚刚复制的Account ID

#### 2.3 JWT_SECRET

1. **Name**: `JWT_SECRET`
2. **获取方法**:
   - 这是一个用于JWT令牌签名的随机字符串
   - 您可以使用以下命令生成一个安全的随机字符串：
     ```bash
     # 在Linux/macOS上
     openssl rand -base64 32
     
     # 在Windows上
     # 或者使用在线工具如 https://www.allkeysgenerator.com/Random/Security-Encryption-Key-Generator.aspx
     ```
3. **Secret**: 粘贴生成的JWT密钥

### 3. 添加可选但推荐的Secrets

根据您的.env.local文件，您可能还需要添加以下secrets：

- `JWT_EXPIRE`
- `ALLOWED_ORIGINS`
- `EMAIL_ENABLED`
- `EMAIL_PROVIDER`
- `EMAIL_FROM`
- `ANALYTICS_ENABLED`
- `ANALYTICS_PROVIDER`
- `BACKUP_ENABLED`
- `RATE_LIMIT_ENABLED`
- `CACHE_ENABLED`
- `CACHE_TTL`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`
- `R2_ENDPOINT`
- `D1_DATABASE_ID`
- `KV_NAMESPACE_ID`

### 4. 验证配置

1. 提交并推送一个小更改到您的仓库，触发GitHub Actions
2. 查看工作流运行中的"Debug environment variables"步骤
3. 确认以下输出显示为`true`：
   ```
   CLOUDFLARE_API_TOKEN is set: true
   CLOUDFLARE_ACCOUNT_ID is set: true
   JWT_SECRET is set: true
   ```

### 5. 常见问题

#### 5.1 Fork仓库问题

如果您的仓库是fork，它不会继承原仓库的secrets。您需要在fork的仓库中重新配置所有secrets。

#### 5.2 Secrets名称区分大小写

确保secrets的名称与工作流中使用的名称完全匹配，包括大小写：
- `CLOUDFLARE_API_TOKEN` (不是 `cloudflare_api_token`)
- `CLOUDFLARE_ACCOUNT_ID` (不是 `cloudflare_account_id`)
- `JWT_SECRET` (不是 `jwt_secret`)

#### 5.3 权限问题

确保您的GitHub Actions有权限访问secrets：
1. 在仓库设置中，确保"Actions"权限已启用
2. 检查工作流文件中的`permissions`配置是否正确

### 6. 自动化配置脚本

您可以使用我们提供的脚本来自动检查配置：

```bash
# 检查本地环境变量
node check-env.js

# 获取GitHub Secrets配置指导
node setup-github-secrets.js

# 验证GitHub Actions配置
node verify-github-actions.js
```

## 完成后的预期结果

配置完成后，GitHub Actions的调试输出应该类似于：

```
=== GitHub Actions Debug Information ===

Checking required secrets...
CLOUDFLARE_API_TOKEN is set: true
CLOUDFLARE_ACCOUNT_ID is set: true
JWT_SECRET is set: true

Checking repository permissions...
Repository: STMfan/MaiMaiNotePad-BackEnd
Actor: STMfan
Ref: refs/heads/main
Event name: push
Base ref: 
Head ref: 
Is fork: false

Checking all available secrets (names only)...
Available secrets: {
  CLOUDFLARE_API_TOKEN: ***,
  CLOUDFLARE_ACCOUNT_ID: ***,
  JWT_SECRET: ***,
  github_token: ***
}

...
```

然后，部署步骤应该能够成功执行。