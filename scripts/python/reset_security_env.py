import secrets
import shutil
import subprocess
import sys
from pathlib import Path


RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"


def generate_secret_key() -> str:
    return secrets.token_urlsafe(64)


def generate_password(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def update_env_file(env_path: Path) -> None:
    if not env_path.exists():
        raise SystemExit(f".env file not found at {env_path}")
    original_text = env_path.read_text(encoding="utf-8")
    backup_path = env_path.with_name(env_path.name + ".bak")
    backup_path.write_text(original_text, encoding="utf-8")
    lines = original_text.splitlines()
    jwt_secret = generate_secret_key()
    superadmin_pwd = generate_password()
    highest_pwd = generate_password()
    replacements = {
        "JWT_SECRET_KEY": jwt_secret,
        "SUPERADMIN_PWD": superadmin_pwd,
        "HIGHEST_PASSWORD": highest_pwd,
    }
    updated_lines = []
    seen_keys = set()
    for line in lines:
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            updated_lines.append(line)
            continue
        key, sep, value = line.partition("=")
        if not sep:
            updated_lines.append(line)
            continue
        key_clean = key.strip()
        if key_clean in replacements:
            updated_lines.append(f"{key_clean}={replacements[key_clean]}")
            seen_keys.add(key_clean)
        else:
            updated_lines.append(line)
    for key, value in replacements.items():
        if key not in seen_keys:
            updated_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    print("安全配置已写入 .env：")
    print(f"JWT_SECRET_KEY={jwt_secret}")
    print(f"SUPERADMIN_PWD={superadmin_pwd}")
    print(f"HIGHEST_PASSWORD={highest_pwd}")


def clear_directory(path: Path) -> None:
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)


def reset_database(root: Path) -> None:
    data_dir = root / "data"
    db_path = data_dir / "mainnp.db"
    if db_path.exists():
        db_path.unlink()
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["alembic", "upgrade", "head"], cwd=root, check=True)
        print("数据库已使用 Alembic 重新创建")
    except Exception as exc:
        print(f"数据库迁移执行失败: {exc}")


def cleanup_files(root: Path) -> None:
    uploads_dir = root / "uploads"
    logs_dir = root / "logs"
    clear_directory(uploads_dir)
    clear_directory(logs_dir)
    print("uploads 与 logs 目录内容已清空")


def confirm_reset(root: Path) -> None:
    print()
    print(f"{BOLD}{RED}⚠ 即将执行清档操作：{RESET}")
    print(f"{YELLOW}- 环境文件：{root / '.env'} 将被备份并写入新的安全配置{RESET}")
    print(f"{YELLOW}- 数据库：{root / 'data' / 'mainnp.db'} 将被删除并重新初始化{RESET}")
    print(f"{YELLOW}- 目录：{root / 'uploads'} 与 {root / 'logs'} 下的所有内容将被清空{RESET}")
    print()
    print(f"{BOLD}{RED}此操作不可撤销，仅适用于本机开发测试或上线前清档，切勿在正在运行的生产机器上执行。{RESET}")
    print()
    try:
        answer = input("请输入大写 'RESET' 以确认执行清档操作（输入其他内容取消）：").strip()
    except EOFError:
        print("未确认，已取消清档。")
        raise SystemExit(1)
    if answer != "RESET":
        print("未输入正确确认文本，已取消清档。")
        raise SystemExit(1)
    print("确认成功，开始执行清档脚本。")


def main() -> None:
    # 脚本在 scripts/python/ 目录下，需要往上两层到项目根目录
    root = Path(__file__).resolve().parents[2]
    env_path = root / ".env"
    confirm_reset(root)
    update_env_file(env_path)
    reset_database(root)
    cleanup_files(root)


if __name__ == "__main__":
    main()
