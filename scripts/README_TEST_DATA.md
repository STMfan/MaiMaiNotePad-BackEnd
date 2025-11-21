# 测试数据准备脚本使用说明

## 概述

`prepare_test_data.py` 脚本用于准备API烟测所需的测试数据，包括：
1. 注册验证码（发送并获取）
2. 重置密码验证码（发送并获取）
3. 待审核的人设卡（自动创建）

## 使用方法

### 基本用法

```bash
python scripts/prepare_test_data.py \
    --base-url http://localhost:9278 \
    --username your-username \
    --password your-password \
    --email your-email@example.com \
    --registration-email newuser@example.com
```

### 参数说明

- `--base-url`: API基础URL（默认: http://0.0.0.0:9278）
- `--username`: 已存在的用户名（用于登录和创建人设卡）
- `--password`: 已存在用户的密码
- `--email`: 已注册用户的邮箱（用于重置密码测试）
- `--registration-email`: 新用户邮箱（用于注册测试，如果未提供则使用 --email）

### 环境变量

也可以通过环境变量设置：

```bash
export MAIMNP_BASE_URL=http://localhost:9278
export MAIMNP_USERNAME=your-username
export MAIMNP_PASSWORD=your-password
export MAIMNP_EMAIL=your-email@example.com

python scripts/prepare_test_data.py --registration-email newuser@example.com
```

## 输出说明

脚本会：
1. 发送注册验证码并显示验证码
2. 发送重置密码验证码并显示验证码
3. 创建待审核的人设卡并显示ID
4. 生成完整的测试命令，包含所有必要的参数

## 完整测试流程示例

### 步骤1: 准备测试数据

```bash
python scripts/prepare_test_data.py \
    --base-url http://localhost:9278 \
    --username admin \
    --password admin123 \
    --email admin@example.com \
    --registration-email testuser@example.com
```

### 步骤2: 运行完整测试

复制脚本输出的测试命令，例如：

```bash
python scripts/api_smoke_test.py \
    --base-url http://localhost:9278 \
    --username admin \
    --password admin123 \
    --email admin@example.com \
    --run-registration \
    --registration-username testuser1234567890 \
    --registration-password testpass123 \
    --registration-email testuser@example.com \
    --registration-code 123456 \
    --run-password-reset \
    --reset-code 654321 \
    --new-password newpass123 \
    --verbose
```

## 注意事项

1. **验证码有效期**: 验证码有效期为2分钟，请尽快使用
2. **频率限制**: 同一邮箱1小时内最多发送5次验证码
3. **人设卡审核**: 创建的人设卡默认是待审核状态（`is_pending=True`）
4. **邮箱要求**: 
   - 注册测试需要未注册的邮箱
   - 重置密码测试需要已注册的邮箱
5. **权限要求**: 创建人设卡需要登录，审核人设卡需要admin或moderator权限

## 故障排除

### 验证码获取失败
- 检查数据库连接是否正常
- 确认验证码是否已过期（2分钟有效期）
- 检查是否超过频率限制（1小时5次）

### 人设卡创建失败
- 确认用户名和密码正确
- 检查用户是否有上传权限
- 查看服务器日志获取详细错误信息

### 重置密码验证码发送失败
- 确认邮箱已注册
- 检查邮箱格式是否正确
- 确认未超过频率限制

