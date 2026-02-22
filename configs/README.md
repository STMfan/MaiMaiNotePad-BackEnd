# 配置文件目录

此目录包含项目的所有配置文件。

## 目录结构

```
configs/
├── README.md                # 本文件
├── config.toml              # 应用主配置文件（不提交到 Git）
├── alembic.ini              # Alembic 数据库迁移配置
└── templates/               # 配置模板目录
    ├── config.toml.template # 应用配置模板
    └── .env.template        # 环境变量模板
```

**注意**: Pytest 配置已移至项目根目录的 `pyproject.toml` 文件中。

## 配置文件说明

### config.toml
应用主配置文件，包含所有非敏感的应用配置。

**状态**: 不提交到 Git（已在 `.gitignore` 中）

**首次使用**:
```bash
cp configs/templates/config.toml.template configs/config.toml
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

### pyproject.toml
Pytest 测试框架的配置现在位于项目根目录的 `pyproject.toml` 文件中。

**状态**: 提交到 Git

**使用方法**:
```bash
# Pytest 会自动读取 pyproject.toml
pytest
```

## 模板文件

### templates/config.toml.template
应用配置模板文件，包含所有可配置项的示例和说明。

**用途**: 新部署时复制为 `configs/config.toml` 并根据实际情况修改。

### templates/.env.template
环境变量模板文件，包含所有需要的环境变量示例。

**用途**: 新部署时复制为项目根目录的 `.env` 并设置实际值。

## 配置优先级

配置加载遵循以下优先级（从高到低）：

1. **环境变量** - 最高优先级，适合敏感信息
2. **config.toml** - 中等优先级，适合通用配置
3. **默认值** - 最低优先级，代码中的默认值

## 敏感信息管理

敏感信息（如密钥、密码）应该：
- 存储在 `.env` 文件中（不提交到 Git）
- 通过环境变量读取
- 不要写入 `config.toml` 文件

敏感信息包括：
- `JWT_SECRET_KEY` - JWT 密钥
- `MAIL_USER` - 邮箱用户名
- `MAIL_PWD` - 邮箱密码
- `SUPERADMIN_PWD` - 超级管理员密码
- `HIGHEST_PASSWORD` - 最高权限密码

## 部署指南

### 1. 复制配置模板

```bash
# 复制应用配置模板
cp configs/templates/config.toml.template configs/config.toml

# 复制环境变量模板
cp configs/templates/.env.template .env
```

### 2. 编辑配置文件

根据实际情况修改 `configs/config.toml` 中的配置项。

### 3. 设置环境变量

编辑 `.env` 文件并设置敏感信息。

### 4. 验证配置

```bash
# 运行测试验证配置
python -m pytest tests/ -v
```

## 相关文档

- [配置管理文档](../docs/configuration/配置管理文档.md) - 详细的配置管理说明
- [架构文档](../docs/architecture/架构文档.md) - 项目架构说明
- [README.md](../README.md) - 项目主文档

## 注意事项

1. **不要提交敏感信息**: `config.toml` 和 `.env` 文件不应提交到版本控制系统
2. **使用模板文件**: 新部署时使用 `templates/` 目录中的模板文件
3. **符号链接**: 项目根目录下的某些配置文件是符号链接，不要删除
4. **配置验证**: 修改配置后运行测试验证配置是否正确

---

**最后更新**: 2026-02-22
