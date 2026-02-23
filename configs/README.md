# 配置文件目录

此目录包含项目的所有配置文件。

## 目录结构

```
configs/
├── README.md                  # 本文件
├── config.dev.toml            # 开发环境配置
├── config.prod.toml           # 生产环境配置
├── config.degraded.toml       # 降级模式配置（缓存禁用）
├── alembic.ini                # Alembic 数据库迁移配置
├── redis.conf                 # Redis 配置文件
└── templates/                 # 配置模板目录
    ├── config.toml.template   # 应用配置模板（已废弃）
    └── .env.template          # 环境变量模板
```

**重要变更**: 从 2026-02-23 起，项目不再使用 `config.toml`，而是直接使用三个环境配置文件。

## 配置文件说明

### 环境配置文件（新方式）

项目现在支持三种配置环境，通过 `CONFIG_ENV` 环境变量切换：

#### config.dev.toml - 开发环境配置
- **用途**: 本地开发和调试
- **特点**: 
  - 缓存 TTL 较短（5 分钟）
  - 详细的日志输出
  - 较少的 Redis 连接数
- **状态**: 提交到 Git
- **默认环境**: 如果未设置 `CONFIG_ENV`，默认使用此配置

#### config.prod.toml - 生产环境配置
- **用途**: 正式部署环境
- **特点**:
  - 缓存 TTL 较长（1 小时）
  - 更多的 Redis 连接数
  - 生产级别的日志配置
- **状态**: 提交到 Git
- **警告**: 必须通过环境变量设置所有敏感信息

#### config.degraded.toml - 降级模式配置
- **用途**: 缓存故障时的应急配置
- **特点**:
  - 缓存完全禁用（`enabled = false`）
  - 所有请求直接访问数据库
  - 适合调试和故障恢复
- **状态**: 提交到 Git
- **使用场景**:
  - Redis 服务故障
  - 排查缓存相关问题
  - 性能对比测试

### 配置切换方式

#### 方式 1: 使用 manage.sh（推荐）
```bash
# 交互式菜单
./manage.sh
# 选择 "4. 配置管理" -> "1/2/3. 切换环境"

# 命令行模式
./manage.sh config-switch dev      # 切换到开发环境
./manage.sh config-switch prod     # 切换到生产环境
./manage.sh config-switch degraded # 切换到降级模式
./manage.sh config-show            # 查看当前配置
./manage.sh config-validate        # 验证所有配置文件
```

#### 方式 2: 设置环境变量
```bash
# 设置环境变量（当前会话有效）
export CONFIG_ENV=prod

# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 9278
```

#### 方式 3: 启动时指定
```bash
# 一次性指定配置环境
CONFIG_ENV=prod python -m uvicorn app.main:app --host 0.0.0.0 --port 9278
```

### 配置加载逻辑

应用启动时，`ConfigManager` 会根据 `CONFIG_ENV` 环境变量自动选择配置文件：

```python
# app/core/config_manager.py
config_env = os.environ.get("CONFIG_ENV", "dev")  # 默认 dev

# 映射关系
env_to_file = {
    "dev": "configs/config.dev.toml",
    "prod": "configs/config.prod.toml",
    "degraded": "configs/config.degraded.toml",
}
```

### alembic.ini
Alembic 数据库迁移工具的配置文件。

**状态**: 提交到 Git

**使用方法**:
```bash
# 使用包装脚本（推荐）
./scripts/shell/alembic.sh upgrade head

# 或直接指定配置文件
alembic -c configs/alembic.ini upgrade head
```

### redis.conf
Redis 服务器配置文件，用于 Docker 部署。

**状态**: 提交到 Git

**使用方法**:
```bash
# 通过 docker-compose 使用
cd docker
docker-compose up -d redis
```

### pyproject.toml
Pytest 测试框架的配置现在位于项目根目录的 `pyproject.toml` 文件中。

**状态**: 提交到 Git

**使用方法**:
```bash
# Pytest 会自动读取 pyproject.toml
pytest
```

## 模板文件（已废弃）

### templates/config.toml.template
应用配置模板文件（已废弃）。

**状态**: 保留用于参考，但不再使用

**说明**: 现在直接使用 `config.dev.toml`、`config.prod.toml`、`config.degraded.toml`

### templates/.env.template
环境变量模板文件，包含所有需要的环境变量示例。

**用途**: 新部署时复制为项目根目录的 `.env` 并设置实际值。

**使用方法**:
```bash
cp configs/templates/.env.template .env
# 编辑 .env 文件，设置敏感信息
```

## 配置优先级

配置加载遵循以下优先级（从高到低）：

1. **环境变量** - 最高优先级，适合敏感信息
2. **配置文件** (config.dev.toml/config.prod.toml/config.degraded.toml) - 中等优先级
3. **默认值** - 最低优先级，代码中的默认值

## 敏感信息管理

敏感信息（如密钥、密码）应该：
- 存储在 `.env` 文件中（不提交到 Git）
- 通过环境变量读取
- 不要写入配置文件

敏感信息包括：
- `JWT_SECRET_KEY` - JWT 密钥
- `MAIL_USER` - 邮箱用户名
- `MAIL_PWD` - 邮箱密码
- `SUPERADMIN_PWD` - 超级管理员密码
- `HIGHEST_PASSWORD` - 最高权限密码
- `REDIS_PASSWORD` - Redis 密码（生产环境）

## 部署指南

### 1. 设置环境变量

```bash
# 复制环境变量模板
cp configs/templates/.env.template .env

# 编辑 .env 文件并设置敏感信息
vim .env
```

### 2. 选择配置环境

```bash
# 开发环境（默认）
export CONFIG_ENV=dev

# 生产环境
export CONFIG_ENV=prod

# 降级模式
export CONFIG_ENV=degraded
```

### 3. 验证配置

```bash
# 使用 manage.sh 验证
./manage.sh config-validate

# 或手动验证
python -c "from app.core.config_manager import config_manager; print(config_manager.get_current_env())"
```

### 4. 启动服务

```bash
# 开发环境
CONFIG_ENV=dev python -m uvicorn app.main:app --reload

# 生产环境
CONFIG_ENV=prod python -m uvicorn app.main:app --host 0.0.0.0 --port 9278 --workers 4
```

## 配置文件对比

| 配置项 | dev | prod | degraded |
|--------|-----|------|----------|
| 缓存启用 | ✓ | ✓ | ✗ |
| 缓存 TTL | 5 分钟 | 1 小时 | N/A |
| Redis 连接数 | 5 | 20 | N/A |
| 日志级别 | DEBUG | INFO | INFO |
| 适用场景 | 本地开发 | 生产部署 | 故障恢复 |

## 相关文档

- [配置管理文档](../docs/configuration/配置管理文档.md) - 详细的配置管理说明
- [架构文档](../docs/architecture/架构文档.md) - 项目架构说明
- [README.md](../README.md) - 项目主文档

## 注意事项

1. **不要提交敏感信息**: `.env` 文件不应提交到版本控制系统
2. **配置文件可提交**: `config.dev.toml`、`config.prod.toml`、`config.degraded.toml` 可以提交（不包含敏感信息）
3. **环境变量优先**: 敏感信息必须通过环境变量设置
4. **配置验证**: 修改配置后运行 `./manage.sh config-validate` 验证格式
5. **重启生效**: 切换配置环境后需要重启服务才能生效

## 常见问题

### Q: 如何知道当前使用的是哪个配置？
```bash
# 方式 1: 使用 manage.sh
./manage.sh config-show

# 方式 2: 检查环境变量
echo $CONFIG_ENV

# 方式 3: 在 Python 中查看
python -c "from app.core.config_manager import config_manager; print(f'环境: {config_manager.get_current_env()}, 文件: {config_manager.get_config_file_path()}')"
```

### Q: 配置切换后为什么没有生效？
配置切换只影响新启动的进程。需要重启服务才能使新配置生效。

### Q: 降级模式下性能会下降多少？
降级模式禁用缓存，所有请求直接访问数据库，响应时间会明显增加。建议仅在 Redis 故障或调试时使用。

### Q: 可以自定义配置文件吗？
可以。创建自定义配置文件后，通过代码直接指定：
```python
from app.core.config_manager import ConfigManager
config = ConfigManager(config_file="configs/my_custom.toml")
```

---

**最后更新**: 2026-02-23
