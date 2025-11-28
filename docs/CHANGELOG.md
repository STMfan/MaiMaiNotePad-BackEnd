# 修改日志 (CHANGELOG)

## 2025-11-24 - 用户功能和管理员功能增强

### 新增功能

#### 1. 刷新令牌机制

**新增接口**：
- `POST /api/refresh` - 刷新访问令牌

**功能说明**：
- 登录接口现在返回 `refresh_token` 和 `expires_in` 字段
- 支持使用刷新令牌获取新的访问令牌，提升用户体验
- 访问令牌有效期15分钟，刷新令牌有效期更长

**实现位置**：
- 文件：`api_routes.py`
- 行号：`refresh_token`: 第121-180行

#### 2. 用户头像功能

**新增接口**：
- `POST /api/users/me/avatar` - 上传头像
- `DELETE /api/users/me/avatar` - 删除头像
- `GET /api/users/{user_id}/avatar` - 获取用户头像

**功能说明**：
- 支持上传、删除和获取用户头像
- 支持 JPG、JPEG、PNG、GIF、WEBP 格式
- 自动生成缩略图
- 如果用户没有上传头像，返回自动生成的头像
- 头像最大 2MB，最大尺寸 1024x1024 像素

**实现位置**：
- 文件：`api_routes.py`
- 行号：
  - `upload_avatar`: 第493-566行
  - `delete_avatar`: 第567-612行
  - `get_user_avatar`: 第614-644行
- 文件：`avatar_utils.py` - 头像处理工具

#### 3. 修改密码功能

**新增接口**：
- `PUT /api/users/me/password` - 修改密码

**功能说明**：
- 支持用户修改自己的密码
- 需要提供当前密码进行验证
- 密码修改后，所有现有Token将失效（通过password_version机制）
- 带速率限制：每分钟最多5次尝试

**实现位置**：
- 文件：`api_routes.py`
- 行号：`change_password`: 第422-490行

#### 4. 管理员功能增强

**新增接口**：
- `GET /api/admin/broadcast-messages` - 获取广播消息统计
- `GET /api/admin/stats` - 获取系统统计数据
- `GET /api/admin/recent-users` - 获取最近注册用户
- `GET /api/admin/users` - 获取用户列表（支持分页和搜索）
- `PUT /api/admin/users/{user_id}/role` - 更新用户角色
- `DELETE /api/admin/users/{user_id}` - 删除用户
- `POST /api/admin/users` - 创建新用户
- `GET /api/admin/knowledge/all` - 获取所有知识库（管理员）
- `GET /api/admin/persona/all` - 获取所有人设卡（管理员）
- `POST /api/admin/knowledge/{kb_id}/revert` - 恢复知识库审核状态
- `POST /api/admin/persona/{pc_id}/revert` - 恢复人设卡审核状态
- `GET /api/admin/upload-history` - 获取上传历史记录
- `GET /api/admin/upload-stats` - 获取上传统计数据
- `DELETE /api/admin/uploads/{upload_id}` - 删除上传记录
- `POST /api/admin/uploads/{upload_id}/reprocess` - 重新处理上传

**功能说明**：
- 提供完整的管理员管理功能
- 支持用户管理、内容管理、上传统计等
- 所有接口需要admin权限

**实现位置**：
- 文件：`api_routes.py`
- 行号：第2838-4108行

### 接口变更

#### 登录接口响应格式更新

**变更前**：
```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

**变更后**：
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "...",
    "username": "...",
    "email": "...",
    "role": "..."
  }
}
```

#### 获取用户信息接口响应格式更新

**新增字段**：
- `avatar_url`: 头像URL
- `avatar_updated_at`: 头像更新时间

### 影响范围

**新增接口**（客户端可选集成）：
- `POST /api/refresh` - 刷新访问令牌
- `PUT /api/users/me/password` - 修改密码
- `POST /api/users/me/avatar` - 上传头像
- `DELETE /api/users/me/avatar` - 删除头像
- `GET /api/users/{user_id}/avatar` - 获取用户头像
- 所有管理员接口（需要admin权限）

**接口变更**（客户端需要更新）：
- `POST /api/token` - 响应格式已更新，包含更多字段
- `GET /api/users/me` - 响应格式已更新，包含头像信息

### 相关文件

- `MaiMaiNotePad-BackEnd/api_routes.py` - API路由实现
- `MaiMaiNotePad-BackEnd/avatar_utils.py` - 头像处理工具
- `MaiMaiNotePad-BackEnd/database_models.py` - 数据库模型（User模型已包含头像字段）
- `MaiMaiNotePad-BackEnd/jwt_utils.py` - JWT工具（包含刷新令牌功能）

---

## 2025-11-22 - API Bug修复和优化

### 修复内容

主要解决了多个API的问题和优化：

#### 1. 审核API修复（知识库和人设卡审批失败）

**问题描述：**
- `approve_knowledge_base`、`reject_knowledge_base`、`approve_persona_card` 和 `reject_persona_card` 四个审核API在调用 `save_knowledge_base` 和 `save_persona_card` 时传的是对象，但这两个方法期望字典参。

**修复位置：**
- 文件：`api_routes.py`
- 行号：
  - `approve_knowledge_base`: 第1656行
  - `reject_knowledge_base`: 第1700行
  - `approve_persona_card`: 第1753行
  - `reject_persona_card`: 第1797行

**修复方法：**
在调用 `save_knowledge_base` 和 `save_persona_card` 之前，用 `to_dict()` 把对象转成字典。

**修改前：**
```python
updated_kb = db_manager.save_knowledge_base(kb)
```

**修改后：**
```python
updated_kb = db_manager.save_knowledge_base(kb.to_dict())
```

---

#### 1.1. 审核拒绝API参数传递方式优化

**问题描述：**
- `reject_knowledge_base` 和 `reject_persona_card` 接口的 `reason` 参数原本使用查询参数（Query），不符合RESTful最佳实践，且对于较长的拒绝原因不够友好。

**修复位置：**
- 文件：`api_routes.py`
- 行号：
  - `reject_knowledge_base`: 第1694行
  - `reject_persona_card`: 第1791行

**修复方法：**
将 `reason` 参数从查询参数改为请求体（Body），使用 `Body(..., embed=True)` 接收JSON格式的请求体。

**修改前：**
```python
@api_router.post("/review/knowledge/{kb_id}/reject")
async def reject_knowledge_base(
    kb_id: str,
    reason: str = Query(...),  # 查询参数
    current_user: dict = Depends(get_current_user)
):
    # ...
```

**修改后：**
```python
@api_router.post("/review/knowledge/{kb_id}/reject")
async def reject_knowledge_base(
    kb_id: str,
    reason: str = Body(..., embed=True),  # 请求体
    current_user: dict = Depends(get_current_user)
):
    # ...
```

**API调用方式变更：**

修改前（查询参数）：
```bash
POST /api/review/knowledge/{kb_id}/reject?reason=拒绝原因
```

修改后（请求体）：
```bash
POST /api/review/knowledge/{kb_id}/reject
Content-Type: application/json

{
  "reason": "拒绝原因"
}
```

**影响：**
- 客户端需要更新调用方式，将 `reason` 参数从查询字符串改为JSON请求体
- 更符合RESTful API设计规范
- 支持更长的拒绝原因文本

---

#### 2. 消息发送API修复（消息创建失败）

**问题描述：**
- `Message.to_dict()` 方法返回的 `created_at` 字段是 ISO 格式的字符串，但 `MessageResponse` Pydantic模型期望接收 `datetime` 对象（这里的ISO格式字符串我真的没懂含义，若真的要用的话此处修复可换个实现方式）。

**修复位置：**
- 文件：`database_models.py`
- 类：`Message`
- 方法：`to_dict()`
- 行号：第338-351行

**修复方法：**
修改 `Message.to_dict()` 方法，确保 `created_at` 字段返回 `datetime` 对象而不是字符串。

**修改前：**
```python
def to_dict(self):
    """将消息对象转换为字典"""
    data = {
        ...
        "created_at": self.created_at.isoformat() if self.created_at else datetime.now().isoformat()
    }
    return data
```

**修改后：**
```python
def to_dict(self):
    """将消息对象转换为字典"""
    data = {
        ...
        "created_at": self.created_at if self.created_at else datetime.now()
    }
    return data
```

---

#### 3. 消息获取API修复（获取消息列表失败）

**问题描述：**
- `api_routes.py` 中定义了重复的 `MessageResponse` 类，与 `models.py` 中的定义不一致，导致类型验证失败。

**修复位置：**
- 文件：`api_routes.py`
- 行号：第14-16行（导入语句），第1934-1942行（删除重复定义）

**修复方法：**
1. 从 `models.py` 导入 `MessageResponse`
2. 删除 `api_routes.py` 中重复的 `MessageResponse` 类定义

**修改前：**
```python
from models import (
    KnowledgeBase, PersonaCard, Message, MessageCreate, StarRecord,
    KnowledgeBaseUpdate
)

# ... 在文件中某处定义了重复的 MessageResponse
class MessageResponse(BaseModel):
    id: str
    sender_id: str
    recipient_id: str
    title: str
    content: str
    message_type: str
    broadcast_scope: Optional[str]
    is_read: bool
    created_at: str
```

**修改后：**
```python
from models import (
    KnowledgeBase, PersonaCard, Message, MessageCreate, StarRecord,
    KnowledgeBaseUpdate, MessageResponse
)

# 删除了重复的 MessageResponse 定义
```

---

#### 4. 消息API进一步修复（批量创建和查询优化）

**问题描述：**
- `bulk_create_messages` 方法在异常时只打印错误并返回空列表，导致错误信息丢失
- SQL查询中使用 `&` 和 `|` 运算符时，运算符优先级可能导致查询逻辑错误

**修复位置：**
- 文件：`database_models.py`
- 方法：
  - `bulk_create_messages`: 第681-697行
  - `get_conversation_messages`: 第699-707行
  - `get_user_messages`: 第709-714行
- 文件：`api_routes.py`
- 方法：`send_message`: 第1886-1888行

**修复方法：**

1. **改进异常处理：** `bulk_create_messages` 现在会抛出异常而不是静默失败
2. **修复SQL查询：** 使用 `and_()` 和 `or_()` 函数替代 `&` 和 `|` 运算符，确保查询逻辑正确
3. **改进错误传播：** API路由中捕获并转换异常为 `DatabaseError`

**修改前：**
```python
def bulk_create_messages(self, messages: List[dict]) -> List[Message]:
    try:
        # ... 创建消息
        return message_models
    except Exception as e:
        print(f"批量创建消息失败: {str(e)}")
        return []  # 静默失败

def get_conversation_messages(self, user_id: str, other_user_id: str, ...):
    return session.query(Message).filter(
        (Message.sender_id == user_id) & (Message.recipient_id == other_user_id) |
        (Message.sender_id == other_user_id) & (Message.recipient_id == user_id)
    ).all()  # 运算符优先级可能导致逻辑错误
```

**修改后：**
```python
def bulk_create_messages(self, messages: List[dict]) -> List[Message]:
    session = None
    try:
        with self.get_session() as session:
            # ... 创建消息
            return message_models
    except Exception as e:
        if session:
            try:
                session.rollback()
            except:
                pass
        raise Exception(f"批量创建消息失败: {str(e)}")  # 抛出异常

def get_conversation_messages(self, user_id: str, other_user_id: str, ...):
    return session.query(Message).filter(
        or_(
            and_(Message.sender_id == user_id, Message.recipient_id == other_user_id),
            and_(Message.sender_id == other_user_id, Message.recipient_id == user_id)
        )
    ).all()  # 使用明确的逻辑函数
```

---

#### 5. 数据库迁移修复（messages表缺少message_type列）

**问题描述：**
- 数据库表 `messages` 缺少 `message_type` 和 `broadcast_scope` 列，导致消息创建和查询失败
- 错误信息：`table messages has no column named message_type`

**修复位置：**
- 文件：`database_models.py`
- 类：`SQLiteDatabaseManager`
- 方法：`__init__` 和新增的 `_migrate_database`
- 行号：第437-463行

**修复方法：**
添加自动数据库迁移方法，在数据库管理器初始化时检查并添加缺失的列。

**修改前：**
```python
def __init__(self, db_path: str = "./data/maimnp.db"):
    # ...
    # 创建所有表
    Base.metadata.create_all(bind=self.engine)
    # 没有迁移逻辑，如果表已存在但缺少列，会导致错误
```

**修改后：**
```python
def __init__(self, db_path: str = "./data/maimnp.db"):
    # ...
    # 创建所有表
    Base.metadata.create_all(bind=self.engine)
    
    # 执行数据库迁移
    self._migrate_database()

def _migrate_database(self):
    """执行数据库迁移，添加缺失的列"""
    try:
        inspector = inspect(self.engine)
        if 'messages' in inspector.get_table_names():
            existing_columns = [col['name'] for col in inspector.get_columns('messages')]
            
            if 'message_type' not in existing_columns:
                with self.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE messages ADD COLUMN message_type VARCHAR DEFAULT 'direct'"))
                print("已添加 message_type 列到 messages 表")
            
            if 'broadcast_scope' not in existing_columns:
                with self.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE messages ADD COLUMN broadcast_scope VARCHAR"))
                print("已添加 broadcast_scope 列到 messages 表")
    except Exception as e:
        print(f"数据库迁移失败: {str(e)}")
```

**注意事项：**
- 迁移会在应用启动时自动执行
- 如果表已存在但缺少列，迁移会自动添加
- 迁移失败不会阻止应用启动，但会打印错误信息

---

### 影响范围

- **API端点：**
  - `POST /review/knowledge/{kb_id}/approve` - 审核通过知识库
  - `POST /review/knowledge/{kb_id}/reject` - 审核拒绝知识库（**参数传递方式变更：从查询参数改为请求体**）
  - `POST /review/persona/{pc_id}/approve` - 审核通过人设卡
  - `POST /review/persona/{pc_id}/reject` - 审核拒绝人设卡（**参数传递方式变更：从查询参数改为请求体**）
  - `POST /api/messages/send` - 发送消息（私信和公告）
  - `GET /api/messages` - 获取消息列表
  - `GET /api/messages?other_user_id={id}` - 获取与特定用户的对话

- **数据模型：**
  - `Message.to_dict()` 方法的返回值格式

- **API调用方式变更：**
  - `POST /api/review/knowledge/{kb_id}/reject` 和 `POST /api/review/persona/{pc_id}/reject` 接口的调用方式需要更新
  - 客户端需要将 `reason` 参数从查询字符串改为JSON请求体

---

### 变更总览

**代码逻辑层面的修复：**
1. 数据类型转换（对象转字典）
2. 返回格式调整（字符串转datetime对象）
3. 代码重构（删除重复定义，统一用models.py中的定义）
4. 异常处理改进（抛出异常而不是静默失败）
5. SQL查询优化（使用明确的逻辑函数确保查询正确）

**API接口优化：**
6. 审核拒绝接口参数传递方式优化（从查询参数改为请求体，更符合RESTful规范）

**数据库结构修复：**
7. 自动数据库迁移（添加缺失的 `message_type` 和 `broadcast_scope` 列）

**数据库迁移说明：**
- 迁移会在应用启动时自动执行
- 如果 `messages` 表已存在但缺少列，迁移会自动添加
- 不需要手动执行SQL脚本，重启应用即可

---

### 相关文件

- `MaiMaiNotePad-BackEnd/api_routes.py` - API路由实现
- `MaiMaiNotePad-BackEnd/database_models.py` - 数据库模型定义
- `MaiMaiNotePad-BackEnd/models.py` - Pydantic模型定义

---

## 2025-11-23 - 新增功能和接口优化

### 新增功能

#### 1. Star状态检查接口

**新增接口**：
- `GET /api/knowledge/{kb_id}/starred` - 检查知识库是否已被当前用户Star
- `GET /api/persona/{pc_id}/starred` - 检查人设卡是否已被当前用户Star

**功能说明**：
- 返回格式：`{"starred": true/false}`
- 需要用户认证
- 用于前端快速检查Star状态，避免获取所有Star记录

**实现位置**：
- 文件：`api_routes.py`
- 行号：
  - `check_knowledge_starred`: 第861-874行
  - `check_persona_starred`: 第1508-1521行

#### 2. 分页支持

**新增分页接口**：
- `GET /api/knowledge/public` - 支持分页、搜索、筛选和排序
- `GET /api/persona/public` - 支持分页、搜索、筛选和排序

**查询参数**：
- `page`: 页码（从1开始）
- `page_size`: 每页数量（1-100）
- `name`: 按名称搜索（可选）
- `uploader_id`: 按上传者ID筛选（可选）
- `sort_by`: 排序字段（created_at, updated_at, star_count）
- `sort_order`: 排序顺序（asc, desc）

**响应格式**：
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

#### 3. 用户Star记录接口增强

**接口**：`GET /api/user/stars`

**新增参数**：
- `includeDetails`: 是否包含完整详情（可选，默认false）

**功能说明**：
- 当 `includeDetails=true` 时，返回Star记录的同时包含知识库/人设卡的完整信息
- 减少前端API调用次数，从 1+N 次请求优化到 1 次请求

**实现位置**：
- 文件：`api_routes.py`
- 行号：`get_user_stars`: 第2026-2075行

### 影响范围

**新增接口**（客户端可选集成）：
- `GET /api/knowledge/{kb_id}/starred` - Star状态检查
- `GET /api/persona/{pc_id}/starred` - Star状态检查
- `GET /api/knowledge/public` - 支持分页参数
- `GET /api/persona/public` - 支持分页参数
- `GET /api/user/stars` - 支持 `includeDetails` 参数

### 相关文件

- `MaiMaiNotePad-BackEnd/api_routes.py` - API路由实现

## 2025-11-25 - 内容字段入库与列表能力增强

### 功能 / 接口
- 知识库与人设卡上传新增正文 `content`、标签 `tags`，响应带作者信息、文件列表与大小聚合，删除最后一个文件时自动删除整条知识库（返回 `knowledge_deleted` 标识）
- 用户上传记录（知识库、人设卡）支持分页、名称/标签/状态筛选与多字段排序，管理员/审核员可查看他人记录
- 用户收藏列表分页化，支持类型过滤和创建时间/收藏数排序，返回 `items/total/page/page_size` 结构
- 管理端内容列表新增上传者（ID/用户名模糊）筛选与排序字段/方向参数，日志输出补充上下文
- 上传/下载相关 CORS 暴露 `Content-Disposition` 头，前端可读取文件名

### 模型 / 存储
- `KnowledgeBase`、`PersonaCard` 模型新增 `content`、`tags` 字段；返回的作者字段回落到版权人/上传者
- SQLite 迁移补充 `content`、`tags` 列并在保存前统一将标签列表转逗号字符串

### 文档
- API 文档补充 content/tags 传参、用户上传/收藏分页参数与响应、删除文件返回字段、管理端筛选与排序参数示例
- README/TODO 同步上述行为与完成状态

---

## 2025-11-23 - 代码质量改进

### 代码质量修复

#### 1. 重复定义问题修复 ✅

**问题描述：**
- `api_routes.py` 和 `models.py` 中重复定义了相同的响应模型类
- 导致维护困难，可能出现不一致问题

**修复位置：**
- 文件：`api_routes.py`
- 行号：第15-19行（导入语句）

**修复方法：**
统一从 `models.py` 导入响应模型，删除 `api_routes.py` 中的重复定义。

**修改后：**
```python
# api_routes.py 第15-19行
from models import (
    KnowledgeBase, PersonaCard, Message, MessageCreate, MessageUpdate, StarRecord,
    KnowledgeBaseUpdate, MessageResponse, KnowledgeBaseResponse, PersonaCardResponse,
    StarResponse, KnowledgeBasePaginatedResponse, PersonaCardPaginatedResponse
)
```

**影响：**
- 代码符合DRY原则
- 减少维护成本
- 避免定义不一致问题

#### 2. 数据库管理器实例化修复 ✅

**问题描述：**
- 数据库管理器实例化问题可能导致循环导入
- 其他模块无法正常导入和使用数据库管理器

**修复位置：**
- 文件：`database_models.py`
- 行号：第1809行

**修复方法：**
创建全局实例 `sqlite_db_manager`，确保其他模块可以正常导入和使用。

**影响：**
- 解决循环导入问题
- 统一数据库管理器实例
- 提升代码可维护性

### 相关文件

- `MaiMaiNotePad-BackEnd/api_routes.py` - API路由实现
- `MaiMaiNotePad-BackEnd/database_models.py` - 数据库模型定义
- `MaiMaiNotePad-BackEnd/models.py` - Pydantic模型定义
