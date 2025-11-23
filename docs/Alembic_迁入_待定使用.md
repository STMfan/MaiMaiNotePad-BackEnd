# Alembic 接入与数据库切换指南（目前有计划，但是最终是否实现还是看各位，难度不大，主要是是否有对应需求）

本项目后端使用 SQLAlchemy 的声明式模型（`database_models.Base`），已经具备接入 Alembic 的前提条件，以下是结合SRC以及过往经验和AI辅助的文档目录：

1. 当前数据库结构概览  
2. Alembic 安装与初始化步骤  
3. 自动迁移与模型同步流程  
4. 在 SQLite / MySQL / PostgreSQL 间切换数据库的建议  
5. 常见问题与排查

---

## 1. 数据库结构概览

所有模型定义集中在 `MaiMaiNotePad-BackEnd/database_models.py`，核心表如下（仅列出主要字段，详见源码）：

- `users`：用户基础信息，UUID 主键，包含激活 / 管理员 / 版主标记及多个索引。  
- `knowledge_bases`：知识库元数据，记录描述、上传者、星标数、公开与审核状态。  
- `knowledge_base_files`：知识库文件明细，保存文件名、路径、类型、大小、时间戳。  
- `persona_cards` / `persona_card_files`：人设卡及其附件。  
- `messages`：站内信，包含发送/接收者、消息类型、状态、引用内容等。  
- `email_verifications`：邮箱验证码记录。  
- `star_records`：用户收藏记录，目前未建立物理外键（需手动维护一致性）。  
- 其他辅助表：如 `security_logs`、`audit_logs` 等（如有新增请补充至 Alembic）。

所有表共享同一个 Base Metadata，可通过 `Base.metadata.tables.keys()` 快速检查。

---

## 2. Alembic 安装与初始化

1. **安装依赖**  
   ```bash
   cd MaiMaiNotePad-BackEnd
   pip install alembic
   pip freeze | findstr alembic >> requirements.txt  # 记得排重
   ```

2. **生成 Alembic 框架**  
   ```bash
   alembic init alembic
   ```
   该命令会创建 `alembic/` 目录和顶层 `alembic.ini`。

3. **配置数据库 URL**  
   在 `alembic.ini` 中设置默认的 `sqlalchemy.url`。建议读取 `.env` 或使用自定义脚本（示例见第 4 节的多数据库配置）。

4. **绑定元数据**  
   编辑 `alembic/env.py`：
   ```python
   import os
   from dotenv import load_dotenv
   from database_models import Base
   from sqlalchemy import create_engine

   load_dotenv()
   target_metadata = Base.metadata
   # 可自定义 run_migrations_online/offline 以适配多数据库
   ```

5. **首个迁移**  
   ```bash
   alembic revision --autogenerate -m "init schema"
   alembic upgrade head
   ```
   首次执行会根据现有 SQLite 结构生成迁移脚本，请人工校验（索引/默认值/外键等）。

---

## 3. 使用 Alembic 同步模型更新

日常开发流程建议：

1. 修改 `database_models.py` 中的模型。
2. 运行 `alembic revision --autogenerate -m "describe change"`，自动生成迁移。
3. 审核 `alembic/versions/*.py`，确保：
   - SQLite 是否支持目标操作（例如修改列通常需要手工处理）。
   - 外键、索引名是否符合各数据库约束。
4. 应用迁移：`alembic upgrade head`。  
   - 可在启动脚本或 CI/CD 流程中自动执行。  
   - 若需回滚使用 `alembic downgrade <revision>`。

> 提示：若 `autogenerate` 未检测到变更，确认模型是否正确导入、MetaData 是否共享，或是否存在自定义 `__table_args__` 未被识别的情况。

---

## 4. 支持多种数据库（SQLite / MySQL / PostgreSQL）

### 4.1 统一配置思路

- 使用环境变量驱动数据库 URL，例如 `.env` 文件：  
  ```
  DATABASE_URL=sqlite:///data/maimnp.db
  DATABASE_URL_MYSQL=mysql+pymysql://user:pwd@host:3306/maimnp
  DATABASE_URL_PG=postgresql+psycopg2://user:pwd@host:5432/maimnp
  ```
- 在应用和 Alembic 中统一从 `DATABASE_URL` 读取，切换数据库时只需修改该变量。  
- 对 MySQL / PostgreSQL 额外安装驱动：`pymysql`、`mysqlclient` 或 `psycopg2-binary`。

### 4.2 Alembic 中加载 URL

在 `alembic/env.py` 中：

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from database_models import Base
from dotenv import load_dotenv
import os

load_dotenv()
config = context.config
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))
target_metadata = Base.metadata
```

### 4.3 针对不同数据库的注意事项

- **SQLite**  
  - 适合开发/测试，数据库即文件。  
  - 不支持大多数 `ALTER TABLE` 语句，复杂迁移需要创建新表复制数据。  
  - 事务中的 `DDL` 限制较多，建议使用单连接模式。

- **MySQL (InnoDB)**  
  - 需要明确字符集（推荐 `utf8mb4`）。  
  - Alembic 默认索引长度可能超过限制（尤其是 `VARCHAR(255)` + 索引，需要指定 `length` 或使用前缀索引）。  
  - 时间字段默认 `DATETIME`，若需要精度可设置 `DateTime(fsp=6)`。

- **PostgreSQL**  
  - 支持更丰富的类型（JSONB、ARRAY 等）。  
  - Alembic 可自动识别 `server_default=text(...)` 等设置。  
  - 注意保留大小写敏感的表名/列名（SQLAlchemy 默认小写）。

切换数据库时：

1. 先在目标数据库创建空库。  
2. 更新 `DATABASE_URL` 并运行 `alembic upgrade head` 构建结构。  
3. 如需迁移数据，可使用 `alembic upgrade` 后配合 ETL/导出导入工具。

---

## 5. 常见问题排查

- **`alembic` 命令找不到**：确认虚拟环境已激活且已安装 Alembic。  
- **`ModuleNotFoundError: database_models`**：检查 `env.py` 的 `sys.path`，确保能找到项目根目录。  
- **自动迁移未捕捉关系/索引**：某些逻辑（例如未声明的外键）不会被识别，需手工添加到迁移脚本。  
- **多数据库切换失败**：多处硬编码了 `sqlite:///...`，需要统一提取并使用环境变量。  
- **大表迁移耗时长**：优先在测试环境验证脚本，再在生产环境停机或使用在线 DDL（取决于数据库类型）。

---

如需进一步扩展（例如引入数据种子脚本、分库分表策略等），建议在 `docs/` 目录新增对应说明，保持与 Alembic 迁移脚本同步维护。

