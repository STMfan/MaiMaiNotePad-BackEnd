# 脚本说明

本目录包含项目的辅助脚本，用于自动化常见任务。

## 脚本列表

### 1. generate_error_codes_doc.py

**功能**：自动生成错误码文档

**用途**：从 `app/error_messages.json` 自动生成 `docs/README_ERROR_CODES.md`

**使用方法**：
```bash
python scripts/generate_error_codes_doc.py
```

**工作流程**：
1. 读取 `app/error_messages.json` 中的所有错误码定义
2. 按模块分组错误码
3. 生成 Markdown 格式的文档
4. 写入 `docs/README_ERROR_CODES.md`

**输出示例**：
```
📖 加载错误消息文件: app/error_messages.json
✅ 成功加载 123 个错误码
📊 按模块分组...
✅ 分组完成，共 7 个模块
📝 生成 Markdown 文档...
💾 写入文件: docs/README_ERROR_CODES.md
✅ 成功生成文档！
```

**何时运行**：
- 添加新的错误码时
- 修改现有错误码的提示信息时
- 定期同步文档时

**相关文件**：
- 输入：`app/error_messages.json`
- 输出：`docs/README_ERROR_CODES.md`

---

### 2. api_smoke_test_1122.py

**功能**：API 烟雾测试

**用途**：快速验证 API 的基本功能是否正常

**使用方法**：
```bash
python scripts/api_smoke_test_1122.py
```

---

### 3. generate_test_templates.py

**功能**：生成测试模板

**用途**：自动生成测试文件模板

**使用方法**：
```bash
python scripts/generate_test_templates.py
```

---

### 4. prepare_test_data1122.py

**功能**：准备测试数据

**用途**：为测试环境准备初始数据

**使用方法**：
```bash
python scripts/prepare_test_data1122.py
```

---

### 5. reset_security_env.py

**功能**：重置安全环境

**用途**：清除敏感数据和重置环境配置

**使用方法**：
```bash
python scripts/reset_security_env.py
```

---

## 错误码管理工作流

### 添加新错误码

1. **编辑 `app/error_messages.json`**：
   ```json
   {
     "20001": {
       "key": "NEW_ERROR_KEY",
       "module": "new_module",
       "messages": {
         "zh-CN": "新的错误提示信息"
       }
     }
   }
   ```

2. **运行脚本生成文档**：
   ```bash
   python scripts/generate_error_codes_doc.py
   ```

3. **验证生成的文档**：
   ```bash
   cat docs/README_ERROR_CODES.md | grep NEW_ERROR_KEY
   ```

### 错误码规范

- **10000-10999**: 认证和用户相关错误
- **12000-12999**: 管理员相关错误
- **13000-13999**: 知识库相关错误
- **14000-14999**: 人设卡相关错误
- **15000-15999**: 消息相关错误
- **16000-16999**: 评论相关错误

---

## 脚本开发指南

### 创建新脚本

1. 在 `scripts/` 目录下创建新的 Python 文件
2. 添加脚本头注释说明功能
3. 实现 `main()` 函数
4. 添加错误处理和日志输出
5. 在本文件中添加脚本说明

### 脚本模板

```python
#!/usr/bin/env python3
"""
脚本功能说明

使用方法: python scripts/your_script.py
"""

import sys
from pathlib import Path


def main():
    """主函数"""
    try:
        # 实现脚本逻辑
        print("✅ 脚本执行成功")
        return True
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
```

---

## 常见问题

### Q: 脚本找不到文件怎么办？

A: 确保从项目根目录运行脚本：
```bash
cd /path/to/MaiMaiNotePad-BackEnd
python scripts/generate_error_codes_doc.py
```

### Q: 如何在 CI/CD 中自动运行脚本？

A: 在 CI/CD 配置中添加：
```yaml
- name: Generate Error Codes Documentation
  run: python scripts/generate_error_codes_doc.py
```

### Q: 脚本执行失败了怎么办？

A: 检查：
1. Python 版本是否 >= 3.8
2. 文件路径是否正确
3. 文件权限是否正确
4. 查看错误信息中的详细信息

---

**最后更新**: 2026-02-20
