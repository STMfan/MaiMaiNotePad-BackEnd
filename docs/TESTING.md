# 测试与文档指南

## 测试

### 运行所有测试

```bash
python run_tests.py
```

或者直接使用pytest:

```bash
pytest tests/ -v
```

### 运行特定测试

```bash
# 只运行认证相关测试
python run_tests.py --type auth

# 只运行知识库相关测试
python run_tests.py --type knowledge
```

### 测试覆盖率

```bash
pytest tests/ --cov=. --cov-report=html
```

测试覆盖率报告将生成在 `htmlcov` 目录中。

## API文档

### 在线文档

启动服务器后，可以通过以下地址访问交互式API文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Postman集合

我们提供了Postman集合文件，方便测试API：

1. 安装Postman
2. 导入 `docs/MaiMNP_API.postman_collection.json`
3. 设置环境变量：
   - `baseUrl`: API基础URL (默认: http://localhost:8000)
   - `token`: 登录后获取的JWT令牌
   - `kb_id`: 知识库ID
   - `user_id`: 用户ID

### API文档

详细的API文档请参考 `docs/API.md`。

## 开发环境设置

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 设置环境变量：

创建 `.env` 文件：

```
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
EXTERNAL_DOMAIN=http://localhost:8000
```

3. 启动服务器：

```bash
python main.py
```

## 代码规范

项目遵循以下代码规范：

- 使用Black进行代码格式化
- 使用flake8进行代码检查
- 使用mypy进行类型检查

```bash
# 格式化代码
black .

# 代码检查
flake8 .

# 类型检查
mypy .
```

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

确保所有测试通过，并添加适当的测试用例。