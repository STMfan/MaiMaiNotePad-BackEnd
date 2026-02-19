"""
向后兼容的入口文件

此文件保留用于向后兼容，实际应用已迁移到 app/main.py
建议使用新的启动方式：
    python -m uvicorn app.main:app --host 0.0.0.0 --port 9278
或使用启动脚本：
    ./start_backend.sh
"""

import sys
import warnings

# 显示弃用警告
warnings.warn(
    "直接运行 main.py 已弃用，请使用 'python -m uvicorn app.main:app' 或 './start_backend.sh'",
    DeprecationWarning,
    stacklevel=2
)

# 导入新的应用入口
from app.main import app

if __name__ == '__main__':
    import uvicorn
    from app.core.config import settings
    from app.core.logging import app_logger
    
    app_logger.warning("使用旧的入口文件 main.py，建议更新为新的启动方式")
    app_logger.info(f'🌐 访问地址: http://{settings.HOST}:{settings.PORT}')
    
    try:
        uvicorn.run(
            app,
            host=settings.HOST,
            port=settings.PORT,
            log_level="critical"
        )
    except Exception as e:
        app_logger.error(f"启动失败: {str(e)}")
        sys.exit(1)

