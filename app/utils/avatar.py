"""
头像处理工具模块

提供头像上传、图片处理、首字母头像生成等功能。
"""

import os
import io
from datetime import datetime
from typing import Tuple, Union
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont, ImageFont as DefaultImageFont
import hashlib

from app.core.config_manager import config_manager

# 头像配置（从配置管理器读取）
AVATAR_MAX_SIZE = config_manager.get_int("upload.avatar.max_size_mb", 2) * 1024 * 1024
AVATAR_MAX_DIMENSION = config_manager.get_int("upload.avatar.max_dimension", 1024)
AVATAR_ALLOWED_FORMATS = config_manager.get_list(
    "upload.avatar.allowed_formats", [".jpg", ".jpeg", ".png", ".gif", ".webp"]
)

# 动态获取上传目录，支持测试环境
_BASE_UPLOAD_DIR = os.getenv("UPLOAD_DIR") or config_manager.get("upload.base_dir", "uploads")
AVATAR_UPLOAD_DIR = os.path.join(_BASE_UPLOAD_DIR, "avatars")

AVATAR_THUMBNAIL_SIZE = config_manager.get_int("upload.avatar.thumbnail_size", 128)


def ensure_avatar_dir() -> None:
    """
    确保头像目录存在

    如果目录不存在，则创建头像上传目录。

    Example:
        >>> ensure_avatar_dir()
    """
    os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)


def validate_image_file(content: bytes, filename: str) -> Tuple[bool, str]:
    """
    验证图片文件的有效性

    检查文件大小、格式和完整性。

    Args:
        content: 图片文件的字节内容
        filename: 文件名

    Returns:
        Tuple[bool, str]: (是否有效, 错误信息)
        如果有效，错误信息为空字符串

    Example:
        >>> is_valid, error = validate_image_file(image_bytes, "avatar.jpg")
        >>> if not is_valid:
        ...     print(f"Validation failed: {error}")
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
    处理头像图片

    执行以下操作：
    1. 裁剪为正方形（取中心部分）
    2. 调整大小（如果超过最大尺寸）
    3. 压缩图片
    4. 生成缩略图

    Args:
        content: 原始图片的字节内容

    Returns:
        Tuple[bytes, bytes]: (处理后的图片字节, 缩略图字节)

    Example:
        >>> processed, thumbnail = process_avatar_image(original_image_bytes)
    """
    # 重新打开图片（verify后需要重新打开）
    img: Image.Image = Image.open(io.BytesIO(content))

    # 转换为RGB模式（处理RGBA、P等模式）
    if img.mode != "RGB":
        img = img.convert("RGB")

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
    img.save(processed_buffer, format="JPEG", quality=85, optimize=True)
    processed_bytes = processed_buffer.getvalue()

    # 生成缩略图
    thumbnail = img.copy()
    thumbnail.thumbnail((AVATAR_THUMBNAIL_SIZE, AVATAR_THUMBNAIL_SIZE), Image.Resampling.LANCZOS)
    thumbnail_buffer = io.BytesIO()
    thumbnail.save(thumbnail_buffer, format="JPEG", quality=85, optimize=True)
    thumbnail_bytes = thumbnail_buffer.getvalue()

    return processed_bytes, thumbnail_bytes


def generate_initial_avatar(username: str, size: int = 200) -> bytes:
    if username:
        initial = username[0].upper()
    else:
        initial = "?"

    base_hash = int(hashlib.md5(initial.encode("utf-8")).hexdigest(), 16)
    colors = [
        (52, 152, 219),
        (46, 204, 113),
        (241, 196, 15),
        (231, 76, 60),
        (155, 89, 182),
        (26, 188, 156),
        (230, 126, 34),
        (149, 165, 166),
    ]
    bg_color = colors[base_hash % len(colors)]

    img = Image.new("RGB", (size, size), bg_color)
    draw = ImageDraw.Draw(img)

    pattern_seed = username or initial
    pattern_hash = hashlib.md5(pattern_seed.encode("utf-8")).hexdigest()
    grid_size = 5
    margin = int(size * 0.15)
    cell_size = (size - margin * 2) // grid_size if grid_size > 0 else size
    pattern_color = tuple(min(255, int(c * 1.2)) for c in bg_color)
    index = 0
    for col in range((grid_size + 1) // 2):
        for row in range(grid_size):
            bit = int(pattern_hash[index % len(pattern_hash)], 16)
            index += 1
            if bit % 2 == 0:
                continue
            x0 = margin + col * cell_size
            y0 = margin + row * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            draw.rectangle((x0, y0, x1, y1), fill=pattern_color)
            mirror_col = grid_size - 1 - col
            if mirror_col != col:
                mx0 = margin + mirror_col * cell_size
                mx1 = mx0 + cell_size
                draw.rectangle((mx0, y0, mx1, y1), fill=pattern_color)

    try:
        font: Union[FreeTypeFont, DefaultImageFont]
        if os.name == "nt":
            font_path = "C:/Windows/Fonts/arial.ttf"
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, size=int(size * 0.5))
            else:
                font = ImageFont.load_default()
        else:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size=int(size * 0.5))
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), initial, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((size - text_width) // 2, (size - text_height) // 2)

    draw.text(position, initial, fill=(255, 255, 255), font=font)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def save_avatar_file(user_id: str, content: bytes, file_ext: str = ".jpg") -> Tuple[str, str]:
    """
    保存头像文件

    处理并保存头像图片及其缩略图。
    文件名包含用户ID和时间戳以确保唯一性。

    Args:
        user_id: 用户ID
        content: 图片内容（字节）
        file_ext: 文件扩展名（默认 '.jpg'）

    Returns:
        Tuple[str, str]: (头像文件路径, 缩略图文件路径)
        路径使用正斜杠分隔符，适用于URL

    Example:
        >>> avatar_path, thumb_path = save_avatar_file("user123", image_bytes, ".jpg")
        >>> print(f"Avatar saved to: {avatar_path}")
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

    同时删除主头像文件和对应的缩略图文件。

    Args:
        file_path: 头像文件路径

    Returns:
        bool: 是否删除成功

    Example:
        >>> success = delete_avatar_file("uploads/avatars/user123_20240101_120000.jpg")
        >>> if success:
        ...     print("Avatar deleted successfully")
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
