"""
静态文件路由模块
提供安全的静态文件服务，特别是头像文件访问
包含安全检查和审计日志功能
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pathlib import Path
import os
from typing import Optional
from logging_config import app_logger
from datetime import datetime


class StaticFileSecurity:
    """静态文件安全服务类"""
    
    def __init__(self, base_dir: Path = Path("uploads")):
        """
        初始化静态文件安全服务
        
        Args:
            base_dir: 基础上传目录路径
        """
        self.base_dir = base_dir
        self.avatars_dir = base_dir / "avatars"
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """确保必要的目录存在"""
        self.base_dir.mkdir(exist_ok=True)
        self.avatars_dir.mkdir(exist_ok=True)
        app_logger.info(f"静态文件目录已确保存在: {self.avatars_dir}")
    
    def _validate_file_path(self, file_path: str) -> Path:
        """
        验证文件路径安全性，防止路径遍历攻击
        
        Args:
            file_path: 请求的文件路径
            
        Returns:
            验证后的安全路径对象
            
        Raises:
            HTTPException: 如果路径不安全
        """
        # 安全检查1: 检查是否包含路径遍历字符
        if ".." in file_path:
            app_logger.warning(f"检测到路径遍历攻击尝试: {file_path}")
            raise HTTPException(status_code=403, detail="Invalid file path: path traversal detected")
        
        # 安全检查2: 检查是否为绝对路径
        safe_path = Path(file_path)
        if safe_path.is_absolute():
            app_logger.warning(f"检测到绝对路径攻击尝试: {file_path}")
            raise HTTPException(status_code=403, detail="Invalid file path: absolute path not allowed")
        
        # 构建完整路径
        full_path = self.avatars_dir / safe_path
        
        # 安全检查3: 确保文件在允许的目录内（防止路径遍历）
        try:
            # 使用resolve()和relative_to()确保文件在avatars目录内
            resolved_full = full_path.resolve()
            resolved_base = self.avatars_dir.resolve()
            resolved_full.relative_to(resolved_base)
        except ValueError:
            app_logger.warning(f"路径验证失败，文件不在允许目录内: {file_path}")
            raise HTTPException(status_code=403, detail="Invalid file path: file outside allowed directory")
        
        return full_path
    
    def _get_media_type(self, file_path: Path) -> str:
        """
        根据文件扩展名确定媒体类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            媒体类型字符串
        """
        ext = file_path.suffix.lower()
        if ext in ('.jpg', '.jpeg'):
            return "image/jpeg"
        elif ext == '.png':
            return "image/png"
        elif ext == '.gif':
            return "image/gif"
        elif ext == '.webp':
            return "image/webp"
        else:
            return "application/octet-stream"
    
    def serve_avatar(self, file_path: str, client_ip: Optional[str] = None) -> FileResponse:
        """
        安全地提供头像文件服务
        
        Args:
            file_path: 请求的文件路径
            client_ip: 客户端IP地址（用于审计）
            
        Returns:
            FileResponse对象
            
        Raises:
            HTTPException: 如果文件不存在或访问被拒绝
        """
        # 审计日志：记录访问请求
        timestamp = datetime.now().isoformat()
        app_logger.info(
            f"[静态文件访问] 时间: {timestamp}, "
            f"路径: {file_path}, "
            f"客户端IP: {client_ip or 'unknown'}"
        )
        
        try:
            # 验证路径安全性
            full_path = self._validate_file_path(file_path)
            
            # 检查文件是否存在
            if not full_path.exists():
                app_logger.warning(f"头像文件不存在: {file_path} (完整路径: {full_path})")
                raise HTTPException(status_code=404, detail="Avatar not found")
            
            if not full_path.is_file():
                app_logger.warning(f"请求的路径不是文件: {file_path} (完整路径: {full_path})")
                raise HTTPException(status_code=404, detail="Avatar not found")
            
            # 获取媒体类型
            media_type = self._get_media_type(full_path)
            
            # 审计日志：记录成功访问
            app_logger.info(
                f"[静态文件访问成功] 时间: {timestamp}, "
                f"路径: {file_path}, "
                f"大小: {full_path.stat().st_size} bytes, "
                f"客户端IP: {client_ip or 'unknown'}"
            )
            
            # 返回文件
            return FileResponse(
                str(full_path),
                media_type=media_type,
                headers={
                    "Cache-Control": "public, max-age=3600",  # 缓存1小时
                    "X-Content-Type-Options": "nosniff",  # 防止MIME类型嗅探
                }
            )
            
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 记录未预期的错误
            app_logger.error(
                f"[静态文件访问错误] 时间: {timestamp}, "
                f"路径: {file_path}, "
                f"错误: {str(e)}, "
                f"客户端IP: {client_ip or 'unknown'}"
            )
            raise HTTPException(status_code=500, detail="Internal server error")


# 创建全局静态文件安全服务实例
static_file_security = StaticFileSecurity()


def setup_static_routes(app: FastAPI) -> None:
    """
    设置静态文件路由
    
    Args:
        app: FastAPI应用实例
    """
    app_logger.info("设置静态文件路由...")
    
    @app.get("/uploads/avatars/{file_path:path}")
    async def serve_avatar_route(
        file_path: str,
        request: Request
    ):
        """
        头像文件服务路由
        
        Args:
            file_path: 文件路径（路径参数）
            request: FastAPI请求对象（用于获取客户端IP）
            
        Returns:
            头像文件响应
        """
        # 获取客户端IP
        client_ip = None
        if request.client:
            client_ip = request.client.host
        
        return static_file_security.serve_avatar(file_path, client_ip)
    
    app_logger.info("静态文件路由设置完成")

