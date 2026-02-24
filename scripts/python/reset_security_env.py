import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
BLUE = "\033[34m"
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
        # 使用 configs/alembic.ini 配置文件
        subprocess.run(["alembic", "-c", "configs/alembic.ini", "upgrade", "head"], cwd=root, check=True)
        print("数据库已使用 Alembic 重新创建")
    except Exception as exc:
        print(f"数据库迁移执行失败: {exc}")


def cleanup_files(root: Path) -> None:
    uploads_dir = root / "uploads"
    logs_dir = root / "logs"
    clear_directory(uploads_dir)
    clear_directory(logs_dir)
    print("uploads 与 logs 目录内容已清空")


def init_superadmin(root: Path) -> bool:
    """初始化超级管理员账户"""
    print()
    print(f"{BOLD}{BLUE}正在初始化超级管理员...{RESET}")

    try:
        # 添加项目根目录到 Python 路径
        sys.path.insert(0, str(root))

        # 重新加载环境变量（因为刚刚更新了 .env）
        from dotenv import load_dotenv

        load_dotenv(override=True)

        from app.core.database import SessionLocal
        from app.services.user_service import UserService

        # 创建数据库会话
        db = SessionLocal()

        try:
            # 创建用户服务
            user_service = UserService(db)

            # 确保超级管理员存在
            user_service.ensure_super_admin_exists()

            superadmin_username = os.getenv("SUPERADMIN_USERNAME", "superadmin")
            superadmin_pwd = os.getenv("SUPERADMIN_PWD", "admin123456")
            external_domain = os.getenv("EXTERNAL_DOMAIN", "example.com")

            print(f"{GREEN}✅ 超级管理员创建成功{RESET}")
            print(f"   用户名: {superadmin_username}")
            print(f"   密码: {superadmin_pwd}")
            print(f"   邮箱: {superadmin_username}@{external_domain}")

            return True

        finally:
            db.close()

    except Exception as e:
        print(f"{RED}❌ 超级管理员创建失败: {e}{RESET}")
        import traceback

        traceback.print_exc()
        return False


def verify_superadmin(root: Path) -> bool:
    """验证超级管理员账户"""
    print()
    print(f"{BOLD}{BLUE}正在验证超级管理员...{RESET}")

    try:
        # 添加项目根目录到 Python 路径
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

        from dotenv import load_dotenv
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # 重新加载环境变量
        load_dotenv(override=True)

        from app.core.security import verify_password
        from app.models.database import User

        # 读取配置
        superadmin_username = os.getenv("SUPERADMIN_USERNAME", "superadmin")
        superadmin_pwd = os.getenv("SUPERADMIN_PWD", "admin123456")
        database_url = os.getenv("DATABASE_URL", "sqlite:///data/mainnp.db")

        # 连接数据库
        engine = create_engine(database_url)
        session_local = sessionmaker(bind=engine)
        db = session_local()

        try:
            # 查询超级管理员
            super_admin = db.query(User).filter(User.is_super_admin.is_(True)).first()

            if not super_admin:
                print(f"{RED}❌ 数据库中没有超级管理员账户{RESET}")
                return False

            # 验证用户名
            if super_admin.username != superadmin_username:
                print(f"⚠️  {YELLOW}警告: 用户名不匹配{RESET}")
                print(f"   期望: {superadmin_username}")
                print(f"   实际: {super_admin.username}")

            # 验证密码
            pwd_to_verify = superadmin_pwd[:72]  # bcrypt 限制

            if verify_password(pwd_to_verify, super_admin.hashed_password):
                print(f"✅ {GREEN}超级管理员验证成功{RESET}")
                print(f"   用户ID: {super_admin.id}")
                print(f"   用户名: {super_admin.username}")
                print(f"   邮箱: {super_admin.email}")
                print(f"   是否激活: {super_admin.is_active}")
                return True
            else:
                print(f"❌ {RED}密码验证失败{RESET}")
                return False

        finally:
            db.close()

    except Exception as e:
        print(f"❌ {RED}验证失败: {e}{RESET}")
        import traceback

        traceback.print_exc()
        return False


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
        raise SystemExit(1) from None
    if answer != "RESET":
        print("未输入正确确认文本，已取消清档。")
        raise SystemExit(1)
    print("确认成功，开始执行清档脚本。")


def main() -> None:
    # 脚本在 scripts/python/ 目录下，需要往上两层到项目根目录
    root = Path(__file__).resolve().parents[2]
    env_path = root / ".env"

    print()
    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}清档脚本 - 重置安全环境{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    # 1. 确认操作
    confirm_reset(root)

    print()
    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}步骤 1/5: 更新环境配置{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    # 2. 更新环境配置
    update_env_file(env_path)

    print()
    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}步骤 2/5: 重置数据库{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    # 3. 重置数据库
    reset_database(root)

    print()
    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}步骤 3/5: 清理文件{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    # 4. 清理文件
    cleanup_files(root)

    print()
    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}步骤 4/5: 初始化超级管理员{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    # 5. 初始化超级管理员
    init_success = init_superadmin(root)

    if not init_success:
        print()
        print(f"⚠️  {RED}超级管理员初始化失败，请手动运行：{RESET}")
        print("   python scripts/python/init_superadmin.py")
        sys.exit(1)

    print()
    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}步骤 5/5: 验证超级管理员{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    # 6. 验证超级管理员
    verify_success = verify_superadmin(root)

    if not verify_success:
        print()
        print(f"⚠️  {YELLOW}超级管理员验证失败，请运行诊断脚本：{RESET}")
        print("   python scripts/python/check_superadmin.py")

    # 7. 总结
    print()
    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}清档完成{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")
    print()

    if init_success and verify_success:
        print(f"✅ {GREEN}所有步骤执行成功{RESET}")
        print()
        print(f"{BOLD}登录信息：{RESET}")
        superadmin_username = os.getenv("SUPERADMIN_USERNAME", "superadmin")
        superadmin_pwd = os.getenv("SUPERADMIN_PWD", "admin123456")
        print(f"   用户名: {superadmin_username}")
        print(f"   密码: {superadmin_pwd}")
        print()
        print(f"{BOLD}下一步：{RESET}")
        print("   启动应用: python -m uvicorn app.main:app --host 0.0.0.0 --port 9278")
        print("   或使用: ./manage.sh start-dev")
    else:
        print(f"⚠️  {YELLOW}部分步骤执行失败，请检查上面的错误信息{RESET}")
        sys.exit(1)

    print()
    print(f"{BOLD}{'=' * 60}{RESET}")


if __name__ == "__main__":
    main()
