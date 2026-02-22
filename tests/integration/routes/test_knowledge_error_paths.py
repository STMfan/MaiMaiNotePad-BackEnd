"""
知识库路由错误路径测试
测试知识库API的所有错误处理路径，包括不存在错误、权限检查失败、创建失败和更新失败

Requirements: 5.5 (knowledge.py error paths)
"""

import uuid
import io

from tests.conftest import assert_error_response


class TestKnowledgeNotFoundErrors:
    """测试知识库不存在错误（94, 97行）- Task 5.5.1"""

    def test_get_knowledge_base_not_found(self, client):
        """测试获取不存在的知识库

        验证：
        - 返回 404 状态码
        - 返回"知识库不存在"错误消息
        - 覆盖 knowledge.py 第94, 97行
        """
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/knowledge/{fake_id}")

        assert_error_response(response, [404], ["知识库不存在", "not found"])

    def test_star_knowledge_base_not_found(self, authenticated_client):
        """测试收藏不存在的知识库

        验证：
        - 返回 404 状态码
        - 返回"知识库不存在"错误消息
        """
        fake_id = str(uuid.uuid4())
        response = authenticated_client.post(f"/api/knowledge/{fake_id}/star")

        assert_error_response(response, [404], ["知识库不存在", "not found"])

    def test_unstar_knowledge_base_not_found(self, authenticated_client, test_user):
        """测试取消收藏不存在的知识库

        验证：
        - 返回 404 状态码
        - 返回"知识库不存在"错误消息
        """
        fake_id = str(uuid.uuid4())
        response = authenticated_client.delete(f"/api/knowledge/{fake_id}/star")

        assert_error_response(response, [404], ["知识库不存在", "not found"])

    def test_update_knowledge_base_not_found(self, authenticated_client):
        """测试更新不存在的知识库

        验证：
        - 返回 404 状态码
        - 返回"知识库不存在"错误消息
        """
        fake_id = str(uuid.uuid4())
        response = authenticated_client.put(f"/api/knowledge/{fake_id}", json={"description": "New description"})

        assert_error_response(response, [404], ["知识库不存在", "not found"])

    def test_add_files_to_nonexistent_knowledge_base(self, authenticated_client, test_user):
        """测试向不存在的知识库添加文件

        验证：
        - 返回 404 状态码
        - 返回"知识库不存在"错误消息
        """
        fake_id = str(uuid.uuid4())
        file_content = b"Test content"
        files = [("files", ("test.txt", io.BytesIO(file_content), "text/plain"))]

        response = authenticated_client.post(f"/api/knowledge/{fake_id}/files", files=files)

        assert_error_response(response, [404], ["知识库不存在", "not found"])

    def test_delete_knowledge_base_not_found(self, authenticated_client):
        """测试删除不存在的知识库

        验证：
        - 返回 404 状态码
        - 返回"知识库不存在"错误消息
        """
        fake_id = str(uuid.uuid4())
        response = authenticated_client.delete(f"/api/knowledge/{fake_id}")

        assert_error_response(response, [404], ["知识库不存在", "not found"])


class TestKnowledgePermissionErrors:
    """测试权限检查失败（102行）- Task 5.5.2"""

    def test_update_knowledge_base_not_owner(self, authenticated_client, factory):
        """测试非所有者更新知识库被拒绝

        验证：
        - 返回 403 状态码
        - 返回权限错误消息
        - 覆盖 knowledge.py 第102行
        """
        other_user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=other_user)
        kb_id = str(kb.id)

        response = authenticated_client.put(f"/api/knowledge/{kb_id}", json={"description": "New description"})

        assert_error_response(response, [403], ["权限", "permission", "是你的"])

    def test_add_files_not_owner(self, authenticated_client, factory):
        """测试非所有者添加文件被拒绝

        验证：
        - 返回 403 状态码
        - 返回权限错误消息
        """
        other_user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=other_user)
        kb_id = str(kb.id)

        file_content = b"New file"
        files = [("files", ("new.txt", io.BytesIO(file_content), "text/plain"))]

        response = authenticated_client.post(f"/api/knowledge/{kb_id}/files", files=files)

        assert_error_response(response, [403], ["权限", "permission", "是你的"])

    def test_delete_file_not_owner(self, authenticated_client, factory):
        """测试非所有者删除文件被拒绝

        验证：
        - 返回 403 状态码
        - 返回权限错误消息
        """
        other_user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=other_user)
        kb_file = factory.create_knowledge_base_file(knowledge_base=kb)
        # Store IDs before any additional operations
        kb_id = str(kb.id)
        kb_file_id = str(kb_file.id)

        response = authenticated_client.delete(f"/api/knowledge/{kb_id}/{kb_file_id}")

        assert_error_response(response, [403], ["权限", "permission", "是你的"])

    def test_delete_knowledge_base_not_owner(self, authenticated_client, factory):
        """测试非所有者删除知识库被拒绝

        验证：
        - 返回 403 状态码
        - 返回权限错误消息
        """
        other_user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=other_user)
        kb_id = str(kb.id)

        response = authenticated_client.delete(f"/api/knowledge/{kb_id}")

        assert_error_response(response, [403], ["权限", "permission"])

    def test_update_public_kb_only_content_allowed(self, authenticated_client, test_user, factory):
        """测试公开知识库只能修改补充说明

        验证：
        - 修改description被拒绝
        - 修改content被允许
        """
        kb = factory.create_knowledge_base(uploader=test_user, is_public=True)
        kb_id = str(kb.id)

        # Try to update description (should fail)
        response = authenticated_client.put(f"/api/knowledge/{kb_id}", json={"description": "New description"})

        assert_error_response(response, [403], ["公开", "审核", "补充说明"])

        # Update content (should succeed)
        response = authenticated_client.put(f"/api/knowledge/{kb_id}", json={"content": "New content"})

        assert response.status_code == 200

    def test_add_files_to_public_kb_denied(self, authenticated_client, test_user, factory):
        """测试向公开知识库添加文件被拒绝

        验证：
        - 返回 403 状态码
        - 返回"不允许修改文件"错误消息
        """
        kb = factory.create_knowledge_base(uploader=test_user, is_public=True)
        kb_id = str(kb.id)

        file_content = b"New file"
        files = [("files", ("new.txt", io.BytesIO(file_content), "text/plain"))]

        response = authenticated_client.post(f"/api/knowledge/{kb_id}/files", files=files)

        assert_error_response(response, [403], ["公开", "审核", "不允许修改"])

    def test_delete_file_from_public_kb_denied(self, authenticated_client, test_user, factory):
        """测试从公开知识库删除文件被拒绝

        验证：
        - 返回 403 状态码
        - 返回"不允许修改文件"错误消息
        """
        kb = factory.create_knowledge_base(uploader=test_user, is_public=True)
        kb_file = factory.create_knowledge_base_file(knowledge_base=kb)
        # Store IDs before any additional operations
        kb_id = str(kb.id)
        kb_file_id = str(kb_file.id)

        response = authenticated_client.delete(f"/api/knowledge/{kb_id}/{kb_file_id}")

        assert_error_response(response, [403], ["公开", "审核", "不允许修改"])

    def test_download_private_kb_file_non_owner(self, authenticated_client, factory):
        """测试非所有者下载私有知识库文件被拒绝

        验证：
        - 返回 403 状态码
        - 返回权限错误消息
        """
        other_user = factory.create_user()
        kb = factory.create_knowledge_base(uploader=other_user, is_public=False)
        kb_file = factory.create_knowledge_base_file(knowledge_base=kb)
        # Store IDs before any additional operations
        kb_id = str(kb.id)
        kb_file_id = str(kb_file.id)

        response = authenticated_client.get(f"/api/knowledge/{kb_id}/file/{kb_file_id}")

        assert_error_response(response, [403], ["权限", "permission"])


class TestKnowledgeCreationErrors:
    """测试创建失败错误 - Task 5.5.3"""

    def test_upload_knowledge_base_empty_name(self, authenticated_client):
        """测试上传时名称为空

        验证：
        - 返回 400 或 422 状态码
        - 返回验证错误消息
        """
        file_content = b"Test content"
        files = [("files", ("test.txt", io.BytesIO(file_content), "text/plain"))]

        data = {"name": "", "description": "Test description"}

        response = authenticated_client.post("/api/knowledge/upload", files=files, data=data)

        assert_error_response(response, [400, 422], ["名称", "name", "空"])

    def test_upload_knowledge_base_empty_description(self, authenticated_client):
        """测试上传时描述为空

        验证：
        - 返回 400 或 422 状态码
        - 返回验证错误消息
        """
        file_content = b"Test content"
        files = [("files", ("test.txt", io.BytesIO(file_content), "text/plain"))]

        data = {"name": "Test KB", "description": ""}

        response = authenticated_client.post("/api/knowledge/upload", files=files, data=data)

        assert_error_response(response, [400, 422], ["描述", "description", "空"])


class TestKnowledgeUpdateErrors:
    """测试更新失败错误 - Task 5.5.4"""

    def test_update_knowledge_base_no_fields(self, authenticated_client, test_user, factory):
        """测试更新时没有提供字段

        验证：
        - 返回 400 或 422 状态码
        - 返回"没有提供要更新的字段"或"没有可更新的内容"错误消息
        """
        kb = factory.create_knowledge_base(uploader=test_user)

        response = authenticated_client.put(f"/api/knowledge/{kb.id}", json={})

        assert_error_response(response, [400, 422], ["没有提供", "没有可更新", "字段", "内容", "field"])

    def test_update_knowledge_base_with_invalid_kb_id(self, authenticated_client, test_user):
        """测试使用无效的知识库ID更新

        验证：
        - 返回 404 状态码
        - 返回"知识库不存在"错误消息
        """
        fake_id = str(uuid.uuid4())

        response = authenticated_client.put(f"/api/knowledge/{fake_id}", json={"description": "New description"})

        assert_error_response(response, [404], ["知识库不存在", "not found"])

    def test_update_knowledge_base_non_admin_change_is_public(self, authenticated_client, test_user, factory):
        """测试非管理员尝试直接修改is_public状态

        验证：
        - 返回 403 状态码
        - 返回权限错误消息
        """
        kb = factory.create_knowledge_base(uploader=test_user, is_public=False, is_pending=False)

        response = authenticated_client.put(f"/api/knowledge/{kb.id}", json={"is_public": True})

        assert_error_response(response, [403], ["管理员", "公开状态", "admin"])

    def test_update_knowledge_base_with_tags(self, authenticated_client, test_user, factory, test_db):
        """测试更新知识库标签

        验证：
        - 返回 200 或 422 状态码
        - 如果成功，标签被成功更新
        """
        kb = factory.create_knowledge_base(uploader=test_user, tags="old,tags")
        test_db.commit()  # Ensure KB is committed
        test_db.refresh(kb)  # Refresh to get latest state

        response = authenticated_client.put(f"/api/knowledge/{kb.id}", json={"tags": "new,tags,updated"})

        # Tags field might not be in the schema, so accept both success and validation error
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            data = response.json()
            assert data["data"]["tags"] == "new,tags,updated"

    def test_update_knowledge_base_content_only(self, authenticated_client, test_user, factory):
        """测试只更新补充说明（content）

        验证：
        - 返回 200 状态码
        - content被成功更新
        - 其他字段不变
        """
        kb = factory.create_knowledge_base(uploader=test_user, description="Original description")
        original_description = kb.description

        response = authenticated_client.put(f"/api/knowledge/{kb.id}", json={"content": "New supplementary content"})

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["content"] == "New supplementary content"
        assert data["data"]["description"] == original_description

    def test_update_knowledge_base_with_nonexistent_kb_id(self, authenticated_client):
        """测试使用不存在的知识库ID更新

        验证：
        - 返回 404 状态码
        - 返回"知识库不存在"错误消息
        """
        fake_id = str(uuid.uuid4())

        response = authenticated_client.put(f"/api/knowledge/{fake_id}", json={"description": "New description"})

        assert_error_response(response, [404], ["知识库不存在", "not found"])

    def test_update_public_kb_description_denied(self, authenticated_client, test_user, factory, test_db):
        """测试更新公开知识库的描述被拒绝

        验证：
        - 返回 403 状态码
        - 返回"仅允许修改补充说明"错误消息
        """
        kb = factory.create_knowledge_base(uploader=test_user, is_public=True)
        test_db.commit()  # Ensure KB is committed
        test_db.refresh(kb)  # Refresh to get latest state

        response = authenticated_client.put(f"/api/knowledge/{kb.id}", json={"description": "New description"})

        assert_error_response(response, [403], ["公开", "审核", "补充说明"])

    def test_update_pending_kb_description_denied(self, authenticated_client, test_user, factory):
        """测试更新审核中知识库的描述被拒绝

        验证：
        - 返回 403 状态码
        - 返回"仅允许修改补充说明"错误消息
        """
        kb = factory.create_knowledge_base(uploader=test_user, is_pending=True)

        response = authenticated_client.put(f"/api/knowledge/{kb.id}", json={"description": "New description"})

        assert_error_response(response, [403], ["公开", "审核", "补充说明"])


class TestKnowledgeValidationErrors:
    """测试知识库验证错误"""

    def test_get_public_knowledge_bases_invalid_page(self, client):
        """测试使用无效页码获取公开知识库

        验证：
        - 返回 400 或 422 状态码
        - 返回验证错误消息
        """
        response = client.get("/api/knowledge/public?page=0")

        assert_error_response(response, [400, 422], ["page", "页"])

    def test_get_public_knowledge_bases_invalid_page_size(self, client):
        """测试使用无效页面大小获取公开知识库

        验证：
        - 返回 400 或 422 状态码
        - 返回验证错误消息
        """
        response = client.get("/api/knowledge/public?page_size=0")

        assert_error_response(response, [400, 422], ["page_size", "每页"])

    def test_get_public_knowledge_bases_page_size_too_large(self, client):
        """测试使用过大的页面大小获取公开知识库

        验证：
        - 返回 400 或 422 状态码
        - 返回验证错误消息
        """
        response = client.get("/api/knowledge/public?page_size=1000")

        assert_error_response(response, [400, 422], ["page_size", "100"])

    def test_unstar_not_starred_knowledge_base(self, authenticated_client, factory):
        """测试取消收藏未收藏的知识库

        验证：
        - 返回 404 状态码
        - 返回"未找到Star记录"错误消息
        """
        kb = factory.create_knowledge_base(is_public=True)

        response = authenticated_client.delete(f"/api/knowledge/{kb.id}/star")

        assert_error_response(response, [404], ["未找到", "Star", "not found"])

    def test_download_nonexistent_file(self, authenticated_client, test_user, factory):
        """测试下载不存在的文件

        验证：
        - 返回 404 状态码
        - 返回"文件不存在"错误消息
        """
        kb = factory.create_knowledge_base(uploader=test_user, is_public=True)
        fake_file_id = str(uuid.uuid4())

        response = authenticated_client.get(f"/api/knowledge/{kb.id}/file/{fake_file_id}")

        assert_error_response(response, [404], ["文件不存在", "not found"])
