import pytest
import tempfile
import os
import uuid
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _create_test_knowledge_base(authenticated_client, name: str, description: str = "测试描述"):
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp.write("这是一个测试知识库文件内容".encode("utf-8"))
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            response = authenticated_client.post(
                "/api/knowledge/upload",
                files={"files": ("test.txt", f, "text/plain")},
                data={"name": name, "description": description, "is_public": "true"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        data = body["data"]
        assert data["name"] == name
        assert data["description"] == description
        assert "id" in data
        return data["id"], name
    finally:
        os.unlink(tmp_path)


class TestKnowledgeBase:
    def test_upload_knowledge_success(self, authenticated_client, test_db):
        name = f"测试知识库_上传成功_{uuid.uuid4().hex[:8]}"
        kb_id, created_name = _create_test_knowledge_base(authenticated_client, name)
        assert isinstance(kb_id, str)
        assert created_name == name

    def test_upload_knowledge_no_file(self, authenticated_client, test_db):
        response = authenticated_client.post(
            "/api/knowledge/upload",
            data={"name": "测试知识库", "description": "测试描述", "is_public": "true"},
        )

        assert response.status_code == 422
        body = response.json()
        assert "detail" in body

    def test_upload_knowledge_invalid_file_type(self, authenticated_client, test_db):
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
            tmp.write(b"fake exe content")
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as f:
                response = authenticated_client.post(
                    "/api/knowledge/upload",
                    files={"files": ("test.exe", f, "application/octet-stream")},
                    data={
                        "name": f"测试知识库_无效类型_{uuid.uuid4().hex[:8]}",
                        "description": "测试描述",
                        "is_public": "true",
                    },
                )

            assert response.status_code == 400
            body = response.json()
            assert "不支持的文件类型" in body.get("detail", "")
        finally:
            os.unlink(tmp_path)

    def test_get_public_knowledge_bases(self, test_db):
        response = client.get("/api/knowledge/public")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)

    def test_get_knowledge_by_id(self, authenticated_client, test_db):
        name = f"测试知识库_获取详情_{uuid.uuid4().hex[:8]}"
        description = "测试描述_获取详情"
        kb_id, _ = _create_test_knowledge_base(authenticated_client, name, description)
        response = client.get(f"/api/knowledge/{kb_id}")

        assert response.status_code == 200
        body = response.json()
        data = body["data"]
        assert data["name"] == name
        assert data["description"] == description

    def test_get_knowledge_by_id_not_found(self, test_db):
        response = client.get("/api/knowledge/nonexistent_id")

        assert response.status_code == 404
        body = response.json()
        assert "知识库不存在" in body.get("error", {}).get("message", "")

    def test_get_user_knowledge_bases(self, authenticated_client, test_user, test_db):
        _ = _create_test_knowledge_base(
            authenticated_client,
            name=f"测试知识库_用户列表_{uuid.uuid4().hex[:8]}",
        )
        response = authenticated_client.get(f"/api/knowledge/user/{test_user.userID}")

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["data"], list)

    def test_star_knowledge_base(self, authenticated_client, test_db):
        kb_id, _ = _create_test_knowledge_base(
            authenticated_client,
            name=f"测试知识库_Star_{uuid.uuid4().hex[:8]}",
        )
        response = authenticated_client.post(f"/api/knowledge/{kb_id}/star")

        assert response.status_code == 200
        body = response.json()
        assert "Star成功" in body.get("message", "")

    def test_unstar_knowledge_base(self, authenticated_client, test_db):
        kb_id, _ = _create_test_knowledge_base(
            authenticated_client,
            name=f"测试知识库_Unstar_{uuid.uuid4().hex[:8]}",
        )
        response = authenticated_client.post(f"/api/knowledge/{kb_id}/star")
        assert response.status_code == 200

        response = authenticated_client.delete(f"/api/knowledge/{kb_id}/star")

        assert response.status_code == 200
        body = response.json()
        assert "取消Star成功" in body.get("message", "")

    def test_get_user_stars(self, authenticated_client, test_user, test_db):
        kb_id, _ = _create_test_knowledge_base(
            authenticated_client,
            name=f"测试知识库_Star列表_{uuid.uuid4().hex[:8]}",
        )
        response = authenticated_client.post(f"/api/knowledge/{kb_id}/star")
        assert response.status_code == 200

        response = authenticated_client.get("/api/user/stars")

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["data"], list)
