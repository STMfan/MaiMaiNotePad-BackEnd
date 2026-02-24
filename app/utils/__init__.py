"""
Utility functions and helpers
"""

# File utilities
# Avatar utilities
from app.utils.avatar import (
    AVATAR_ALLOWED_FORMATS,
    AVATAR_MAX_SIZE,
    AVATAR_UPLOAD_DIR,
    delete_avatar_file,
    ensure_avatar_dir,
    generate_initial_avatar,
    process_avatar_image,
    save_avatar_file,
    validate_image_file,
)
from app.utils.file import (
    delete_file,
    ensure_directory_exists,
    generate_unique_filename,
    get_file_extension,
    save_uploaded_file,
    save_uploaded_file_with_size,
    validate_file_content_size,
    validate_file_size,
    validate_file_type,
)

# WebSocket manager
from app.utils.websocket import (
    MessageWebSocketManager,
    message_ws_manager,
)

__all__ = [
    # File utilities
    "validate_file_type",
    "validate_file_size",
    "validate_file_content_size",
    "save_uploaded_file",
    "save_uploaded_file_with_size",
    "ensure_directory_exists",
    "delete_file",
    "get_file_extension",
    "generate_unique_filename",
    # Avatar utilities
    "ensure_avatar_dir",
    "validate_image_file",
    "process_avatar_image",
    "generate_initial_avatar",
    "save_avatar_file",
    "delete_avatar_file",
    "AVATAR_MAX_SIZE",
    "AVATAR_ALLOWED_FORMATS",
    "AVATAR_UPLOAD_DIR",
    # WebSocket manager
    "MessageWebSocketManager",
    "message_ws_manager",
]
