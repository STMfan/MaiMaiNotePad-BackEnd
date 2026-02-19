"""
文件处理工具模块

提供通用的文件处理功能，包括文件验证、保存、删除等操作。
"""

import os
from datetime import datetime
from typing import Tuple
from werkzeug.utils import secure_filename
from fastapi import UploadFile, HTTPException, status


def validate_file_type(file: UploadFile, allowed_types: list[str]) -> bool:
    """
    验证文件类型是否在允许的类型列表中
    
    Args:
        file: 上传的文件对象
        allowed_types: 允许的文件扩展名列表，如 ['.txt', '.json']
    
    Returns:
        bool: 文件类型是否有效
    
    Example:
        >>> validate_file_type(file, ['.txt', '.json'])
        True
    """
    if not file.filename:
        return False

    file_ext = os.path.splitext(file.filename)[1].lower()
    return file_ext in allowed_types


def validate_file_size(file: UploadFile, max_size: int) -> bool:
    """
    验证文件大小是否在允许的范围内
    
    Args:
        file: 上传的文件对象
        max_size: 最大文件大小（字节）
    
    Returns:
        bool: 文件大小是否有效
    
    Example:
        >>> validate_file_size(file, 10 * 1024 * 1024)  # 10MB
        True
    """
    if not file.size:
        return True  # 如果无法获取大小，暂时允许

    return file.size <= max_size


async def validate_file_content_size(file: UploadFile, max_size: int) -> bool:
    """
    验证文件内容的实际大小
    
    通过读取文件内容来验证实际大小，比 file.size 更准确。
    注意：此函数会重置文件指针到开始位置。
    
    Args:
        file: 上传的文件对象
        max_size: 最大文件大小（字节）
    
    Returns:
        bool: 文件内容大小是否有效
    
    Example:
        >>> await validate_file_content_size(file, 10 * 1024 * 1024)
        True
    """
    # 读取文件内容以验证实际大小
    content = await file.read()
    await file.seek(0)  # 重置文件指针

    return len(content) <= max_size


async def save_uploaded_file(file: UploadFile, target_dir: str) -> str:
    """
    保存上传的文件到目标目录
    
    文件名会添加时间戳前缀以避免冲突。
    
    Args:
        file: 上传的文件对象
        target_dir: 目标目录路径
    
    Returns:
        str: 保存后的文件完整路径
    
    Raises:
        HTTPException: 文件保存失败时抛出
    
    Example:
        >>> file_path = await save_uploaded_file(file, "uploads/knowledge")
    """
    try:
        # 创建唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{timestamp}_{file.filename}"
        file_path = os.path.join(target_dir, file_name)

        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        return file_path
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件保存失败: {str(e)}"
        )


async def save_uploaded_file_with_size(file: UploadFile, directory: str) -> Tuple[str, int]:
    """
    保存上传的文件到指定目录，并返回文件路径和文件大小
    
    如果文件已存在，会自动添加时间戳避免冲突。
    
    Args:
        file: 上传的文件对象
        directory: 目标目录路径
    
    Returns:
        Tuple[str, int]: (文件完整路径, 文件大小（字节）)
    
    Raises:
        HTTPException: 文件保存失败时抛出
    
    Example:
        >>> file_path, file_size = await save_uploaded_file_with_size(file, "uploads/knowledge")
        >>> print(f"Saved {file_size} bytes to {file_path}")
    """
    try:
        # 确保目录存在
        os.makedirs(directory, exist_ok=True)

        # 生成安全的文件名
        filename = secure_filename(file.filename)
        file_path = os.path.join(directory, filename)

        # 如果文件已存在，添加时间戳
        if os.path.exists(file_path):
            name, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}{ext}"
            file_path = os.path.join(directory, filename)

        # 保存文件并计算大小
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 计算文件大小（字节）
        file_size_b = len(content)

        return file_path, file_size_b
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件保存失败: {str(e)}"
        )


def ensure_directory_exists(directory: str) -> None:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
    
    Example:
        >>> ensure_directory_exists("uploads/avatars")
    """
    os.makedirs(directory, exist_ok=True)


def delete_file(file_path: str) -> bool:
    """
    删除指定的文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        bool: 是否删除成功
    
    Example:
        >>> delete_file("uploads/temp/file.txt")
        True
    """
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        print(f"删除文件失败: {str(e)}")
        return False


def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名（小写）
    
    Args:
        filename: 文件名
    
    Returns:
        str: 文件扩展名（包含点号，如 '.txt'）
    
    Example:
        >>> get_file_extension("document.PDF")
        '.pdf'
    """
    return os.path.splitext(filename)[1].lower()


def generate_unique_filename(original_filename: str, prefix: str = "") -> str:
    """
    生成唯一的文件名（添加时间戳）
    
    Args:
        original_filename: 原始文件名
        prefix: 可选的前缀
    
    Returns:
        str: 唯一的文件名
    
    Example:
        >>> generate_unique_filename("document.txt", "user123")
        'user123_20240101_120000_document.txt'
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if prefix:
        return f"{prefix}_{timestamp}_{original_filename}"
    return f"{timestamp}_{original_filename}"
