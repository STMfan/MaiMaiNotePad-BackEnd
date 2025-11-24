"""
头像处理工具模块
处理头像上传、图片处理、首字母头像生成等功能
"""

import os
import io
from datetime import datetime
from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import hashlib

# 头像配置
AVATAR_MAX_SIZE = 2 * 1024 * 1024  # 2MB
AVATAR_MAX_DIMENSION = 1024  # 1024x1024 像素
AVATAR_ALLOWED_FORMATS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
AVATAR_UPLOAD_DIR = "uploads/avatars"
AVATAR_THUMBNAIL_SIZE = 128  # 缩略图尺寸


def ensure_avatar_dir():
    """确保头像目录存在"""
    os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)


def validate_image_file(content: bytes, filename: str) -> Tuple[bool, str]:
    """
    验证图片文件
    
    Returns:
        (is_valid, error_message)
    """
    # 检查文件大小
    if len(content) > AVATAR_MAX_SIZE:
        return False, f"文件大小不能超过{AVATAR_MAX_SIZE // (1024*1024)}MB"
    
    # 检查文件扩展名
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in AVATAR_ALLOWED_FORMATS:
        return False, f"文件格式不支持，仅支持 {', '.join(AVATAR_ALLOWED_FORMATS)}"
    
    # 验证确实是图片文件
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()  # 验证图片完整性
    except Exception as e:
        return False, f"无效的图片文件: {str(e)}"
    
    return True, ""


def process_avatar_image(content: bytes) -> Tuple[bytes, bytes]:
    """
    处理头像图片：裁剪为正方形（取中心部分）、压缩、生成缩略图
    
    Returns:
        (processed_image_bytes, thumbnail_bytes)
    """
    # 重新打开图片（verify后需要重新打开）
    img = Image.open(io.BytesIO(content))
    
    # 转换为RGB模式（处理RGBA、P等模式）
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 获取图片尺寸
    width, height = img.size
    
    # 裁剪为正方形（取中心部分）
    if width != height:
        size = min(width, height)
        left = (width - size) // 2
        top = (height - size) // 2
        right = left + size
        bottom = top + size
        img = img.crop((left, top, right, bottom))
    
    # 调整大小（如果超过最大尺寸）
    if img.width > AVATAR_MAX_DIMENSION or img.height > AVATAR_MAX_DIMENSION:
        img.thumbnail((AVATAR_MAX_DIMENSION, AVATAR_MAX_DIMENSION), Image.Resampling.LANCZOS)
    
    # 保存处理后的图片（压缩质量85%）
    processed_buffer = io.BytesIO()
    img.save(processed_buffer, format='JPEG', quality=85, optimize=True)
    processed_bytes = processed_buffer.getvalue()
    
    # 生成缩略图
    thumbnail = img.copy()
    thumbnail.thumbnail((AVATAR_THUMBNAIL_SIZE, AVATAR_THUMBNAIL_SIZE), Image.Resampling.LANCZOS)
    thumbnail_buffer = io.BytesIO()
    thumbnail.save(thumbnail_buffer, format='JPEG', quality=85, optimize=True)
    thumbnail_bytes = thumbnail_buffer.getvalue()
    
    return processed_bytes, thumbnail_bytes


def generate_initial_avatar(username: str, size: int = 200) -> bytes:
    """
    生成首字母头像
    
    Args:
        username: 用户名
        size: 头像尺寸（默认200x200）
    
    Returns:
        头像图片的字节数据（PNG格式）
    """
    # 获取首字母（支持中文和英文）
    if username:
        initial = username[0].upper()
    else:
        initial = "?"
    
    # 根据首字母生成颜色（使用哈希确保同一字母颜色一致）
    hash_value = int(hashlib.md5(initial.encode('utf-8')).hexdigest(), 16)
    colors = [
        (52, 152, 219),   # 蓝色
        (46, 204, 113),   # 绿色
        (241, 196, 15),   # 黄色
        (231, 76, 60),    # 红色
        (155, 89, 182),   # 紫色
        (26, 188, 156),   # 青色
        (230, 126, 34),   # 橙色
        (149, 165, 166),  # 灰色
    ]
    bg_color = colors[hash_value % len(colors)]
    
    # 创建图片
    img = Image.new('RGB', (size, size), bg_color)
    draw = ImageDraw.Draw(img)
    
    # 尝试加载字体（如果系统有的话）
    try:
        # Windows字体路径
        if os.name == 'nt':
            font_path = "C:/Windows/Fonts/arial.ttf"
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, size=int(size * 0.5))
            else:
                font = ImageFont.load_default()
        else:
            # Linux/Mac字体路径
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size=int(size * 0.5))
    except:
        # 如果加载字体失败，使用默认字体
        font = ImageFont.load_default()
    
    # 计算文字位置（居中）
    bbox = draw.textbbox((0, 0), initial, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((size - text_width) // 2, (size - text_height) // 2)
    
    # 绘制文字（白色）
    draw.text(position, initial, fill=(255, 255, 255), font=font)
    
    # 转换为字节
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def save_avatar_file(user_id: str, content: bytes, file_ext: str = '.jpg') -> Tuple[str, str]:
    """
    保存头像文件
    
    Args:
        user_id: 用户ID
        content: 图片内容（字节）
        file_ext: 文件扩展名
    
    Returns:
        (file_path, thumbnail_path)
    """
    ensure_avatar_dir()
    
    # 处理图片（裁剪、压缩）
    processed_content, thumbnail_content = process_avatar_image(content)
    
    # 生成文件名（带时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{user_id}_{timestamp}{file_ext}"
    thumbnail_filename = f"{user_id}_{timestamp}_thumb{file_ext}"
    
    file_path = os.path.join(AVATAR_UPLOAD_DIR, filename)
    thumbnail_path = os.path.join(AVATAR_UPLOAD_DIR, thumbnail_filename)
    
    # 保存处理后的文件
    with open(file_path, "wb") as f:
        f.write(processed_content)
    
    # 保存缩略图
    with open(thumbnail_path, "wb") as f:
        f.write(thumbnail_content)
    
    # 统一使用正斜杠（用于URL）
    return file_path.replace("\\", "/"), thumbnail_path.replace("\\", "/")


def delete_avatar_file(file_path: str) -> bool:
    """
    删除头像文件（包括缩略图）
    
    Args:
        file_path: 头像文件路径
    
    Returns:
        是否删除成功
    """
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        # 尝试删除缩略图
        if file_path:
            # 生成缩略图路径
            dir_path = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)
            thumbnail_path = os.path.join(dir_path, f"{name}_thumb{ext}")
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
        
        return True
    except Exception as e:
        print(f"删除头像文件失败: {str(e)}")
        return False

