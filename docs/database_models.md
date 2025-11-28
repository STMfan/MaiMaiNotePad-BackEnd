# 数据库模型说明

基于 `MaiMaiNotePad-BackEnd/database_models.py`，描述所有 SQLAlchemy 模型、字段、索引及关联关系，方便各位了解数据结构。本文档会随着数据库模型的更新而持续维护。

> 小小建议：所有模型均继承同一个 `Base`，默认主键使用 `UUID` 字符串。时间字段采用 `datetime.now` 作为默认值，除非特别注明。如果未声明 `ForeignKey`，要保证业务逻辑的一致性。
> 再次补充：PK：主键；FK：外键

---

## 目录

1. 用户与权限：`User`  
2. 知识库体系：`KnowledgeBase`、`KnowledgeBaseFile`  
3. 人设卡体系：`PersonaCard`、`PersonaCardFile`  
4. 互动/运营：`Message`、`StarRecord`  
5. 验证服务：`EmailVerification`  
6. 上传记录：`UploadRecord`  
7. 数据访问层：`SQLiteDatabaseManager`

---

## 1. `User`（表：`users`）

| 字段 | 类型 | 约束/默认值 | 说明 |
| --- | --- | --- | --- |
| `id` | `String` | PK，UUID | 用户唯一标识 |
| `username` | `String` | `unique`, `nullable=False` | 登录名/展示名 |
| `email` | `String` | `unique`, `nullable=False` | 邮箱 |
| `hashed_password` | `String` | `nullable=False` | Bcrypt 加密后的密码 |
| `is_active` | `Boolean` | `default=True` | 是否启用 |
| `is_admin` | `Boolean` | `default=False` | 管理员标志 |
| `is_moderator` | `Boolean` | `default=False` | 版主标志 |
| `created_at` | `DateTime` | `default=datetime.now` | 注册时间 |
| `failed_login_attempts` | `Integer` | `default=0` | 失败登录尝试次数（账户锁定相关） |
| `locked_until` | `DateTime` | `nullable=True` | 账户锁定到期时间 |
| `last_failed_login` | `DateTime` | `nullable=True` | 最后一次失败登录时间 |
| `avatar_path` | `String` | `nullable=True` | 头像文件路径（相对路径或URL） |
| `avatar_updated_at` | `DateTime` | `nullable=True` | 头像最后更新时间 |
| `password_version` | `Integer` | `default=0` | 密码版本号（用于Token失效机制，每次修改密码时递增） |

- **索引**：用户名、邮箱、激活状态、管理员、版主均建单列索引。  
- **关系**：与 `KnowledgeBase`、`PersonaCard`、`Message`、`StarRecord` 均保持双向 `relationship`。  
- **业务逻辑**：提供 `verify_password`、`update_password`、权限提升等辅助方法。密码修改时会自动递增 `password_version`，使所有现有Token失效。

---

## 2. 知识库体系

### 2.1 `KnowledgeBase`（表：`knowledge_bases`）

| 字段 | 类型 | 约束/默认值 | 说明 |
| --- | --- | --- | --- |
| `id` | `String` | PK | 知识库 ID |
| `name` | `String` | `nullable=False` | 名称 |
| `description` | `Text` | `nullable=False` | 描述/概要 |
| `uploader_id` | `String` | FK -> `users.id` | 上传者 |
| `copyright_owner` | `String` | 可空 | 版权声明 |
| `content` | `Text` | 可空 | 正文内容（兼容旧 metadata 文件，现改为直接入库） |
| `tags` | `Text` | 可空 | 标签，逗号分隔存储 |
| `star_count` | `Integer` | `default=0` | 收藏数 |
| `downloads` | `Integer` | `default=0` | 下载次数 |
| `base_path` | `Text` | `default="[]"` | 文件列表 JSON（字符串存储） |
| `is_public` | `Boolean` | `default=False` | 是否公开 |
| `is_pending` | `Boolean` | `default=True` | 审核状态 |
| `rejection_reason` | `Text` | 可空 | 拒绝原因 |
| `created_at` | `DateTime` | 默认当前时间 | 创建时间 |
| `updated_at` | `DateTime` | 自动更新时间 | 最后修改 |

- **索引**：上传者、公开状态、审核状态、星数、创建/更新时间。  
- **关系**：`uploader` 指回 `User`。`StarRecord` 未建立 FK（外键），需要代码层维护。  
- **补充**：`from_dict` 中 `base_path` 键名拼写为 `bast_path`（潜在 Bug）。

### 2.2 `KnowledgeBaseFile`（`knowledge_base_files`）

| 字段 | 类型 | 约束/默认值 | 说明 |
| --- | --- | --- | --- |
| `id` | `String` | PK | 文件记录 ID |
| `knowledge_base_id` | `String` | 未声明 FK | 所属知识库 |
| `file_name` | `String` | 非空 | 存储文件名 |
| `original_name` | `String` | 非空 | 原始文件名 |
| `file_path` | `String` | 非空 | 物理路径 |
| `file_type` | `String` | 非空 | MIME/扩展类型 |
| `file_size` | `Integer` | `default=0` | 大小（字节） |
| `created_at` | `DateTime` | 默认 | 上传时间 |
| `updated_at` | `DateTime` | 自动更新 | 最近操作 |

- **索引**：`knowledge_base_id`、`file_type`、`file_size`、`created_at`、`updated_at`。  
- **关系**：无

---

## 3. 人设卡体系

### 3.1 `PersonaCard`（`persona_cards`）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` (`String`, PK) | 人设卡 ID |
| `name` (`String`, 非空) | 标题 |
| `description` (`Text`, 非空) | 描述 |
| `uploader_id` (`String`, FK -> `users.id`) | 上传者 |
| `copyright_owner` (`String`, 可空) |
| `star_count` (`Integer`, 默认 0) |
| `downloads` (`Integer`, 默认 0) | 下载次数 |
| `content` (`Text`, 可空) | 正文内容 |
| `tags` (`Text`, 可空) | 标签，逗号分隔 |
| `base_path` (`String`, 非空) | 资源路径 |
| `is_public` (`Boolean`, 默认 False) |
| `is_pending` (`Boolean`, 默认 True) |
| `rejection_reason` (`Text`, 可空) |
| `created_at` / `updated_at` (`DateTime`) |

- **索引**：上传者、公开/审核状态、星数、创建/更新时间。  
- **关系**：`uploader` 指向 `User`。与 `StarRecord` 需手动维护。

### 3.2 `PersonaCardFile`（`persona_card_files`）

字段与 `KnowledgeBaseFile` 类似，只是 `persona_card_id` 指向人设卡 ID。  
- **索引**：`persona_card_id`、`file_type`、`file_size`、时间戳。  
- **关系**：无 FK。

---

## 4. 互动 / 运营

### 4.1 `Message`（`messages`）

| 字段 | 类型 | 约束/默认值 | 说明 |
| --- | --- | --- | --- |
| `id` | `String` | PK | 消息 ID |
| `recipient_id` | `String` | FK -> `users.id` | 收件人 |
| `sender_id` | `String` | FK -> `users.id` | 发件人 |
| `title` | `String` | 非空 | 标题 |
| `content` | `Text` | 非空 | 内容 |
| `summary` | `Text` | 可空 | 消息简介/摘要（可选） |
| `message_type` | `String` | 默认 `direct` | direct / announcement |
| `broadcast_scope` | `String` | 可空 | 广播范围（如 `all_users`） |
| `is_read` | `Boolean` | 默认 False | 已读标记 |
| `created_at` | `DateTime` | 默认 | 发送时间 |

- **索引**：收件人、发件人、已读状态、创建时间、复合索引 `recipient_id + is_read`。  
- **关系**：`recipient`、`sender` 与 `User` 双向绑定。

### 4.2 `StarRecord`（`star_records`）

| 字段 | 类型 | 约束/默认值 | 说明 |
| --- | --- | --- | --- |
| `id` | `String` | PK | Star 记录 |
| `user_id` | `String` | FK -> `users.id` | 创建者 |
| `target_id` | `String` | 无 FK | 目标内容 ID |
| `target_type` | `String` | 非空 | `knowledge` / `persona` |
| `created_at` | `DateTime` | 默认 | 收藏时间 |

- **索引**：用户、目标 ID、目标类型、创建时间，以及复合索引 `(user_id, target_id, target_type)` 用于快速判断是否已收藏。  
- **关系**：仅与 `User` 建立关系；目标对象需手动查询。

---

## 5. 验证服务：`EmailVerification`（`email_verifications`）

| 字段 | 类型 | 约束/默认值 | 说明 |
| --- | --- | --- | --- |
| `id` | `String` | PK |
| `email` | `String` | 非空 | 邮箱地址（统一转换为小写存储） |
| `code` | `String` | 非空 | 验证码 |
| `is_used` | `Boolean` | 默认 False | 是否已用 |
| `created_at` | `DateTime` | 默认 | 生成时间 |
| `expires_at` | `DateTime` | 非空 | 失效时间（默认2分钟后过期） |

- **索引**：邮箱、验证码、过期时间。  
- **业务**：用于限制验证码发送频率（同一邮箱1小时内最多5次）、验证注册/找回密码流程。验证码使用后自动标记为已用。

---

## 6. 上传记录：`UploadRecord`（`upload_records`）

| 字段 | 类型 | 约束/默认值 | 说明 |
| --- | --- | --- | --- |
| `id` | `String` | PK | 上传记录 ID |
| `uploader_id` | `String` | FK -> `users.id` | 上传者用户 ID |
| `target_id` | `String` | 非空 | 目标内容 ID（知识库或人设卡的ID） |
| `target_type` | `String` | 非空 | 目标类型：`knowledge` 或 `persona` |
| `name` | `String` | 非空 | 知识库或人设卡名称 |
| `description` | `Text` | 可空 | 描述信息 |
| `status` | `String` | `default="pending"` | 状态：`pending`（待审核）、`approved`（已通过）、`rejected`（已拒绝） |
| `created_at` | `DateTime` | 默认当前时间 | 创建时间 |
| `updated_at` | `DateTime` | 自动更新时间 | 最后修改时间 |

- **索引**：上传者ID、目标ID、目标类型、状态、创建时间。  
- **业务**：用于记录所有上传操作，防止恶意删除。管理员可以通过此表追踪所有上传历史，并支持恢复已删除的内容。

---

## 7. `SQLiteDatabaseManager`

虽然不对应数据表，但 `SQLiteDatabaseManager` 封装了数据库访问逻辑：

- 初始化：确保 `./data/maimnp.db` 路径存在，创建 `create_engine("sqlite:///...")`，`SessionLocal` 统一管理事务，并自动 `Base.metadata.create_all`。  
- 主要功能块：  
  - **知识库**：CRUD、审核筛选、文件同步、下载计数。  
  - **人设卡**：CRUD、文件管理、下载计数。  
  - **消息**：单发/群发/广播、会话列表、已读标记、批量操作。  
  - **收藏**：判断、增删并联动计数。  
  - **用户**：注册校验、密码更新、批量查询、账户锁定、头像管理。  
  - **邮箱验证码**：保存、验证、频控。  
  - **上传记录**：创建、更新状态、查询历史、统计。  
- 迁移与默认值：在 `_migrate_database` 中为 `knowledge_bases` / `persona_cards` 自动补充 `downloads`、`content`、`tags` 列；`save_knowledge_base` / `save_persona_card` 在写入前会将列表标签转逗号字符串

> 若未来切换到 MySQL / PostgreSQL，建议重构该管理器以接受通用 `DATABASE_URL`，并移除强制的 SQLite 依赖，配合 Alembic 迁移实现数据库统一升级。

---

## 附：维护建议

1. **字段更新**：修改模型后务必运行 Alembic 自动迁移，以保持数据库结构一致。  
2. **外键约束**：目前多个表未声明 FK（`KnowledgeBaseFile`、`PersonaCardFile` 等），在多数据库环境下可能导致数据不一致，建议尽快补齐。  
3. **索引命名**：所有索引已手动命名，跨数据库迁移时避免冲突。  
4. **时间字段**：默认使用本地时间，如需时区支持请改为 `DateTime(timezone=True)` 并统一使用 UTC。  
5. **数据体量**：`base_path` 等 JSON 字符串字段适合小规模数据，若未来增长，可考虑拆分到独立表。

---

## 📚 相关文档

- [API文档](./API.md) - 完整的API接口文档
- [端点清单](./端点清单.md) - API端点完整清单
- [更新总结](./更新总结.md) - 更新内容总结
- [CHANGELOG.md](./CHANGELOG.md) - 变更日志

---

---

## 更新日志

### 2025-11-22 更新
- 新增 `User` 模型字段：账户锁定相关（`failed_login_attempts`、`locked_until`、`last_failed_login`）、头像相关（`avatar_path`、`avatar_updated_at`）、密码版本号（`password_version`）
- 新增 `KnowledgeBase` 和 `PersonaCard` 模型的 `downloads` 字段（下载计数）
- 新增 `Message` 模型的 `summary` 字段（消息简介）
- 新增 `UploadRecord` 模型（上传记录表）
- 更新 `EmailVerification` 模型说明（邮箱统一转换为小写存储）

---

**文档版本**: 2.1  
**最后更新**: 2025-11-22  
**维护者**: 开发团队
