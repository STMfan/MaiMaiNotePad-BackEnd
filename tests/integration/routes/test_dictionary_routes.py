"""
字典路由集成测试
测试翻译字典检索和错误处理

需求: 3.7
"""

import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def mock_dict_path_empty(tmp_path, monkeypatch):
    """创建一个不存在的字典文件路径"""
    non_existent_path = tmp_path / "nonexistent" / "translation_dict.json"
    # 使用环境变量来控制字典文件路径
    monkeypatch.setenv("TRANSLATION_DICT_PATH", str(non_existent_path))
    return non_existent_path


@pytest.fixture
def mock_dict_path_invalid_json(tmp_path, monkeypatch):
    """创建一个包含无效 JSON 的字典文件"""
    dict_file = tmp_path / "translation_dict.json"
    dict_file.write_text("invalid json content")
    monkeypatch.setenv("TRANSLATION_DICT_PATH", str(dict_file))
    return dict_file


@pytest.fixture
def mock_dict_path_unreadable(tmp_path, monkeypatch):
    """创建一个无法读取的字典文件"""
    dict_file = tmp_path / "translation_dict.json"
    dict_file.write_text('{"blocks": {}, "tokens": {}}')
    dict_file.chmod(0o000)  # 移除所有权限
    monkeypatch.setenv("TRANSLATION_DICT_PATH", str(dict_file))

    yield dict_file

    # 清理：恢复权限以便删除
    try:
        dict_file.chmod(0o644)
    except Exception:
        pass


@pytest.fixture
def mock_dict_missing_blocks(tmp_path, monkeypatch):
    """创建一个缺少 blocks 字段的字典文件"""
    dict_file = tmp_path / "translation_dict.json"
    dict_file.write_text('{"tokens": {"test": "测试"}}')
    monkeypatch.setenv("TRANSLATION_DICT_PATH", str(dict_file))
    return dict_file


@pytest.fixture
def mock_dict_missing_tokens(tmp_path, monkeypatch):
    """创建一个缺少 tokens 字段的字典文件"""
    dict_file = tmp_path / "translation_dict.json"
    dict_file.write_text('{"blocks": {"test": "测试"}}')
    monkeypatch.setenv("TRANSLATION_DICT_PATH", str(dict_file))
    return dict_file


@pytest.fixture
def mock_dict_invalid_blocks_type(tmp_path, monkeypatch):
    """创建一个 blocks 类型无效的字典文件"""
    dict_file = tmp_path / "translation_dict.json"
    dict_file.write_text('{"blocks": ["not", "a", "dict"], "tokens": {"test": "测试"}}')
    monkeypatch.setenv("TRANSLATION_DICT_PATH", str(dict_file))
    return dict_file


@pytest.fixture
def mock_dict_invalid_tokens_type(tmp_path, monkeypatch):
    """创建一个 tokens 类型无效的字典文件"""
    dict_file = tmp_path / "translation_dict.json"
    dict_file.write_text('{"blocks": {"test": "测试"}, "tokens": ["not", "a", "dict"]}')
    monkeypatch.setenv("TRANSLATION_DICT_PATH", str(dict_file))
    return dict_file


class TestGetTranslationDictionary:
    """测试 GET /api/dictionary/translation 端点"""

    def test_get_translation_dictionary_success(self, client, test_db: Session):
        """测试成功检索翻译字典

        验证：
        - 返回 200 状态码
        - 返回包含 blocks 和 tokens 的数据
        - 数据格式正确
        """

        response = client.get("/api/dictionary/translation")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "blocks" in data["data"]
        assert "tokens" in data["data"]
        assert isinstance(data["data"]["blocks"], dict)
        assert isinstance(data["data"]["tokens"], dict)

    def test_get_translation_dictionary_content(self, client, test_db: Session):
        """测试翻译字典包含预期内容

        验证：
        - blocks 包含预期的翻译条目
        - tokens 包含预期的翻译条目
        - 翻译内容正确
        """

        response = client.get("/api/dictionary/translation", headers={"Cache-Control": "no-cache"})

        assert response.status_code == 200
        data = response.json()["data"]

        # Verify some expected translations exist
        blocks = data["blocks"]
        tokens = data["tokens"]

        # Check if common translations exist
        assert "bot" in blocks or "bot" in tokens
        assert "personality" in blocks or "personality" in tokens

    def test_get_translation_dictionary_file_not_found(self, mock_dict_path_empty, client, test_db: Session):
        """测试文件不存在时的翻译字典

        验证：
        - 文件不存在时返回空字典
        - 返回 200 状态码
        - 返回默认结构（空 blocks 和 tokens）
        """

        response = client.get("/api/dictionary/translation", headers={"Cache-Control": "no-cache"})

        assert response.status_code == 200
        data = response.json()["data"]
        assert data == {"blocks": {}, "tokens": {}}

    def test_get_translation_dictionary_invalid_json(self, mock_dict_path_invalid_json, client, test_db: Session):
        """测试包含无效 JSON 的翻译字典

        验证：
        - JSON 解析失败时返回空字典
        - 返回 200 状态码
        - 返回默认结构
        """

        response = client.get("/api/dictionary/translation", headers={"Cache-Control": "no-cache"})

        assert response.status_code == 200
        data = response.json()["data"]
        assert data == {"blocks": {}, "tokens": {}}

    def test_get_translation_dictionary_missing_blocks(self, mock_dict_missing_blocks, client, test_db: Session):
        """测试缺少 blocks 字段的翻译字典

        验证：
        - 缺少 blocks 字段时使用空字典
        - tokens 字段正常返回
        """

        response = client.get("/api/dictionary/translation", headers={"Cache-Control": "no-cache"})

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["blocks"] == {}
        assert data["tokens"] == {"test": "测试"}

    def test_get_translation_dictionary_missing_tokens(self, mock_dict_missing_tokens, client, test_db: Session):
        """测试缺少 tokens 字段的翻译字典

        验证：
        - 缺少 tokens 字段时使用空字典
        - blocks 字段正常返回
        """

        response = client.get("/api/dictionary/translation", headers={"Cache-Control": "no-cache"})

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["blocks"] == {"test": "测试"}
        assert data["tokens"] == {}

    def test_get_translation_dictionary_invalid_blocks_type(
        self, mock_dict_invalid_blocks_type, client, test_db: Session
    ):
        """测试 blocks 类型无效的翻译字典

        验证：
        - blocks 不是字典时使用空字典
        - 系统不会崩溃
        """

        response = client.get("/api/dictionary/translation", headers={"Cache-Control": "no-cache"})

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["blocks"] == {}
        assert data["tokens"] == {"test": "测试"}

    def test_get_translation_dictionary_invalid_tokens_type(
        self, mock_dict_invalid_tokens_type, client, test_db: Session
    ):
        """测试 tokens 类型无效的翻译字典

        验证：
        - tokens 不是字典时使用空字典
        - 系统不会崩溃
        """

        response = client.get("/api/dictionary/translation", headers={"Cache-Control": "no-cache"})

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["blocks"] == {"test": "测试"}
        assert data["tokens"] == {}

    def test_get_translation_dictionary_file_read_error(self, mock_dict_path_unreadable, client, test_db: Session):
        """测试文件读取失败时的翻译字典

        验证：
        - 文件读取失败时返回空字典
        - 系统不会崩溃
        - 返回 200 状态码
        """

        response = client.get("/api/dictionary/translation", headers={"Cache-Control": "no-cache"})

        assert response.status_code == 200
        data = response.json()["data"]
        assert data == {"blocks": {}, "tokens": {}}


class TestDictionaryPermissions:
    """测试字典端点权限"""

    def test_get_translation_dictionary_no_auth_required(self, client, test_db: Session):
        """测试翻译字典不需要身份验证

        验证：
        - 未认证用户可以访问
        - 返回正常数据
        """

        # Access without authentication
        response = client.get("/api/dictionary/translation")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "blocks" in data["data"]
        assert "tokens" in data["data"]
