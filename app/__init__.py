"""
MaiMNP Backend Application Package

导出 FastAPI 应用实例和版本信息供外部使用。
"""

from app.main import app
from app.__version__ import __version__, __version_info__

__all__ = ["app", "__version__", "__version_info__"]
