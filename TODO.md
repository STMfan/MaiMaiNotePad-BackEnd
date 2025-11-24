# MaiMNP-rereremake-Flutter 后端项目任务清单

## 已完成任务

1. ✅ **实现知识库上传路由和元数据管理**
   - 完成知识库文件上传功能
   - 实现知识库元数据存储和管理
   - 添加文件路径验证和存储

2. ✅ **实现人设卡上传路由和元数据管理**
   - 完成人设卡文件上传功能
   - 实现人设卡元数据存储和管理
   - 添加文件路径验证和存储

3. ✅ **实现审核功能（admin和moderator权限）**
   - 实现知识库和人设卡的审核流程
   - 添加审核通过/拒绝功能
   - 实现审核权限控制

4. ✅ **实现用户个人上传记录查看路由（带身份验证）**
   - 完成用户上传记录查询功能
   - 实现身份验证和权限控制
   - 添加分页和筛选功能

5. ✅ **实现用户已star的知识库/人设卡查看路由（带身份验证）**
   - 完成用户Star记录查询功能
   - 实现Star/取消Star功能
   - 添加身份验证和权限控制

6. ✅ **实现信箱功能和拒绝原因通知**
   - 完成消息系统实现
   - 添加审核拒绝通知功能
   - 实现消息读取状态管理

7. ✅ **实现获取所有公共知识库接口**
   - 完成公共知识库查询功能
   - 添加分页和排序功能
   - 实现搜索和筛选功能

8. ✅ **实现获取所有公共人设卡接口**
   - 完成人设卡查询功能
   - 添加分页和排序功能
   - 实现搜索和筛选功能

9. ✅ **修复循环导入问题**
   - 解决api_routes.py和main.py之间的循环导入
   - 重构代码结构，优化模块依赖关系
   - 添加数据库管理器实例初始化

10. ✅ **安装缺失的依赖包**
    - 安装toml模块支持配置文件解析
    - 安装python-multipart模块支持表单数据处理
    - 更新requirements.txt文件

11. ✅ **在正确端口9278上启动FastAPI服务器并测试API接口**
    - 成功终止占用端口的进程
    - 在端口9278上启动FastAPI服务器
    - 测试API接口基本功能正常
    - 验证服务器运行状态稳定

12. ✅ **清除测试脚本并生成README.md**
    - 删除了test_main.py测试脚本文件
    - 创建了详细的README.md文档
    - 包含项目介绍、功能特性、API文档等内容
    - 提供了完整的使用说明和常见问题解答

13. ✅ **将数据库从JSON文件迁移到SQLite**
    - 创建SQLite数据库模型和表结构
    - 实现数据迁移脚本migrate_to_sqlite.py
    - 修复用户数据字段映射问题(userID -> id, pwdHash -> hashed_password)
    - 成功迁移用户数据到SQLite数据库
    - 验证API接口正常工作，数据库连接正常

14. ✅ **检查API接口与README.md文档一致性**
    - 检查main.py和api_routes.py中的实际API接口
    - 对比README.md中描述的API接口
    - 发现并修复了API路径前缀不一致问题
    - 确保文档与实际实现保持一致

15. ✅ **更新README.md文档以反映SQLite数据库实现**
   - 更新技术栈部分，将"JSON文件存储"改为"SQLite数据库"
   - 添加SQLAlchemy ORM框架说明
   - 更新项目结构，将JSON文件改为SQLite数据库文件
   - 更新数据存储说明，描述SQLite表结构

16. ✅ **修复登录接口422错误：添加/api前缀，更新JWT库为PyJWT**
    - 在main.py中为API路由添加/api前缀，使API路径与前端请求一致
    - 将requirements.txt中的jwt更改为PyJWT，使用正确的JWT库名称
    - 修复登录接口/api/token的422错误，确保JWT令牌正常返回
    - 验证受保护的API端点（如/api/users/me）可以正常访问

17. ✅ **修复API接口路径问题：personas应为persona**
    - 发现/api/personas接口返回404错误，检查代码发现实际路径为/api/persona
    - 验证/api/persona/public和/api/knowledge/public接口正常工作
    - 确认所有API接口都使用了正确的/api前缀，并且JWT认证正常工作

18. ✅ **修复登录接口JSON格式支持问题**
    - 重新设计登录接口，使用Request对象手动解析JSON和表单数据
    - 支持application/json和application/x-www-form-urlencoded两种Content-Type
    - 测试验证JSON格式和表单格式都能正常工作
    - 添加适当的错误处理和验证

19. ✅ **修复审核API和消息API的Bug**
    - 修复审核通过/拒绝接口的对象转字典问题
    - 优化审核拒绝接口参数传递方式（从查询参数改为请求体）
    - 修复消息创建和获取API的类型验证问题
    - 改进消息批量创建和查询的异常处理
    - 添加自动数据库迁移功能

20. ✅ **新增Star状态检查接口**
    - 实现 `GET /api/knowledge/{kb_id}/starred` 接口
    - 实现 `GET /api/persona/{pc_id}/starred` 接口
    - 优化Star状态检查性能，从O(N)优化到O(1)

21. ✅ **添加分页支持**
    - 为公开知识库接口添加分页、搜索、筛选和排序功能
    - 为公开人设卡接口添加分页、搜索、筛选和排序功能
    - 优化列表查询性能

22. ✅ **增强用户Star记录接口**
    - 为 `GET /api/user/stars` 接口添加 `includeDetails` 参数
    - 支持返回Star记录的同时包含完整详情
    - 减少前端API调用次数

23. ✅ **实现刷新令牌机制**
    - 登录接口返回 refresh_token 和 expires_in
    - 实现 `POST /api/refresh` 接口用于刷新访问令牌
    - 提升用户体验，减少频繁登录

24. ✅ **实现用户头像功能**
    - 实现头像上传、删除、获取功能
    - 支持多种图片格式（JPG、JPEG、PNG、GIF、WEBP）
    - 自动生成缩略图和默认头像
    - 添加头像处理工具模块

25. ✅ **实现修改密码功能**
    - 实现 `PUT /api/users/me/password` 接口
    - 支持用户修改自己的密码
    - 密码修改后自动使所有现有Token失效
    - 添加速率限制防止暴力破解

26. ✅ **实现管理员功能**
    - 实现用户管理接口（查看、创建、更新、删除用户）
    - 实现内容管理接口（查看所有知识库和人设卡）
    - 实现上传统计和历史记录接口
    - 实现审核状态恢复功能
    - 实现系统统计接口

## 待完成任务

1. 🔄 **添加API文档和测试用例**
   - 完善API接口文档
   - 编写单元测试和集成测试
   - 添加API使用示例

2. 🔄 **优化数据库查询性能**
   - 优化数据库查询语句
   - 添加数据库索引
   - 实现查询缓存机制

3. 🔄 **实现文件上传大小限制和类型检查**
   - 添加文件大小限制
   - 实现文件类型检查
   - 添加文件内容验证

4. 🔄 **添加日志记录和错误处理**
   - 完善日志记录系统
   - 优化错误处理机制
   - 添加性能监控

## 项目结构

```
backend-python-remake/
├── api_routes.py         # API路由定义
├── database_models.py    # SQLite数据库模型和管理器
├── file_upload.py        # 文件上传服务
├── logger.py            # 日志记录模块
├── main.py              # 主应用入口
├── migrate_to_sqlite.py # 数据迁移脚本
├── models.py            # 数据模型定义
├── user_management.py   # 用户管理模块
├── data/                # 原始JSON数据存储目录（已迁移到SQLite）
│   ├── knowledge_bases.json
│   ├── messages.json
│   ├── persona_cards.json
│   ├── stars.json
│   └── users.json
├── uploads/             # 文件上传目录
│   ├── knowledge/
│   └── persona/
├── database.db          # SQLite数据库文件
└── requirements.txt     # 项目依赖
```

## API接口概览

### 认证相关
- `POST /api/token` - 用户登录获取token
- `POST /api/send_verification_code` - 发送注册验证码
- `POST /api/send_reset_password_code` - 发送重置密码验证码
- `POST /api/reset_password` - 重置密码
- `POST /api/user/register` - 用户注册
- `GET /api/users/me` - 获取当前用户信息

### 知识库相关
- `POST /api/knowledge/upload` - 上传知识库
- `GET /api/knowledge/public` - 获取公开知识库
- `GET /api/knowledge/{kb_id}` - 获取指定知识库详情
- `GET /api/knowledge/user/{user_id}` - 获取用户知识库
- `PUT /api/knowledge/{kb_id}` - 更新知识库信息
- `POST /api/knowledge/{kb_id}/files` - 添加知识库文件
- `DELETE /api/knowledge/{kb_id}/{file_id}` - 删除知识库文件
- `GET /api/knowledge/{kb_id}/download` - 下载知识库全部文件（ZIP）
- `GET /api/knowledge/{kb_id}/file/{file_id}` - 下载知识库单个文件
- `DELETE /api/knowledge/{kb_id}` - 删除知识库
- `POST /api/knowledge/{kb_id}/star` - Star知识库
- `DELETE /api/knowledge/{kb_id}/star` - 取消Star知识库

### 人设卡相关
- `POST /api/persona/upload` - 上传人设卡
- `GET /api/persona/public` - 获取公开人设卡
- `GET /api/persona/{pc_id}` - 获取指定人设卡详情
- `GET /api/persona/user/{user_id}` - 获取用户人设卡
- `PUT /api/persona/{pc_id}` - 更新人设卡信息
- `POST /api/persona/{pc_id}/files` - 添加人设卡文件
- `DELETE /api/persona/{pc_id}/{file_id}` - 删除人设卡文件
- `GET /api/persona/{pc_id}/download` - 下载人设卡全部文件（ZIP）
- `GET /api/persona/{pc_id}/file/{file_id}` - 下载人设卡单个文件
- `DELETE /api/persona/{pc_id}` - 删除人设卡
- `POST /api/persona/{pc_id}/star` - Star人设卡
- `DELETE /api/persona/{pc_id}/star` - 取消Star人设卡

### 审核相关
- `GET /api/review/knowledge/pending` - 获取待审核知识库
- `GET /api/review/persona/pending` - 获取待审核人设卡
- `POST /api/review/knowledge/{kb_id}/approve` - 审核通过知识库
- `POST /api/review/knowledge/{kb_id}/reject` - 审核拒绝知识库（需在请求体中传递 `{"reason": "拒绝原因"}`）
- `POST /api/review/persona/{pc_id}/approve` - 审核通过人设卡
- `POST /api/review/persona/{pc_id}/reject` - 审核拒绝人设卡（需在请求体中传递 `{"reason": "拒绝原因"}`）

### 消息相关
- `POST /api/messages/send` - 发送消息
- `GET /api/messages` - 获取用户消息
- `POST /api/messages/{message_id}/read` - 标记消息为已读

### 用户相关
- `GET /api/user/stars` - 获取用户Star的知识库和人设卡

## 运行说明

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 数据迁移（首次运行或从JSON迁移到SQLite）：
   ```bash
   python migrate_to_sqlite.py
   ```

3. 启动服务器：
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 9278 --reload
   ```

4. 访问API文档：
   ```
   http://localhost:9278/docs
   ```

## 注意事项

- 服务器默认运行在9278端口
- 文件上传路径为`uploads/knowledge/`和`uploads/persona/`
- 数据已从JSON文件迁移到SQLite数据库（database.db）
- 原始JSON数据文件保留在`data/`目录作为备份
- 用户认证使用JWT token
- 审核功能需要admin或moderator权限