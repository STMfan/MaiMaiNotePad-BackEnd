"""
保留属性测试

此测试文件用于验证修复不会破坏已通过的测试和生产环境功能。
这些测试应该在未修复的代码上通过，并在修复后继续通过。

**重要**：遵循观察优先方法
- 在未修复代码上观察非 Bug 输入的行为
- 编写属性测试捕获来自保留需求的观察行为模式
- 属性测试生成许多测试用例以提供更强保证

**预期结果**：测试通过（这确认要保留的基线行为）

**Validates: Requirements 3.1-3.9 (Bugfix Spec)**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
import uuid
import asyncio

# 标记所有测试为串行执行
pytestmark = pytest.mark.serial


class TestPreservation_UserCreation:
    """
    保留属性 1: 用户创建功能保持正常
    
    验证正常的用户创建流程不受修复影响。
    
    **Validates: Requirements 3.1, 3.4**
    """
    
    @given(
        username_suffix=st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
            min_size=4,
            max_size=12
        ),
        email_prefix=st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
            min_size=4,
            max_size=12
        )
    )
    @settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_user_creation_with_unique_credentials(
        self, username_suffix, email_prefix, test_db
    ):
        """
        属性测试：使用唯一凭证创建用户应该成功
        
        验证用户创建的核心功能在各种有效输入下都能正常工作。
        
        **预期结果**：在未修复和修复后的代码上都应该通过
        
        **Validates: Requirements 3.1, 3.4**
        """
        from app.services.user_service import UserService
        
        # 确保生成的值有效
        assume(len(username_suffix) >= 4)
        assume(len(email_prefix) >= 4)
        
        service = UserService(test_db)
        
        # 使用 UUID 确保唯一性
        unique_id = uuid.uuid4().hex[:8]
        username = f"user_{username_suffix}_{unique_id}"
        email = f"{email_prefix}_{unique_id}@example.com"
        password = "ValidPassword123!"
        
        # 创建用户
        user = service.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # 验证用户创建成功
        assert user is not None, "用户创建应该成功"
        assert user.username == username, "用户名应该匹配"
        assert user.email == email, "邮箱应该匹配"
        assert user.id is not None, "用户应该有 ID"
        
        # 验证可以通过 ID 获取用户
        retrieved_user = service.get_user_by_id(user.id)
        assert retrieved_user is not None, "应该能够获取创建的用户"
        assert retrieved_user.username == username, "获取的用户名应该匹配"
    
    def test_user_authentication_flow_preserved(self, test_db):
        """
        测试：用户认证流程保持正常
        
        验证用户创建和认证的完整流程不受影响。
        
        **预期结果**：在未修复和修复后的代码上都应该通过
        
        **Validates: Requirements 3.1, 3.4**
        """
        from app.services.user_service import UserService
        
        service = UserService(test_db)
        
        # 创建用户
        username = f"authuser_{uuid.uuid4().hex[:8]}"
        email = f"auth_{uuid.uuid4().hex[:8]}@example.com"
        password = "TestPassword123!"
        
        user = service.create_user(
            username=username,
            email=email,
            password=password
        )
        
        assert user is not None, "用户创建应该成功"
        
        # 验证可以通过用户名获取用户
        retrieved_by_username = service.get_user_by_username(username)
        assert retrieved_by_username is not None, "应该能够通过用户名获取用户"
        assert retrieved_by_username.id == user.id, "用户 ID 应该匹配"
        
        # 验证可以通过邮箱获取用户
        retrieved_by_email = service.get_user_by_email(email)
        assert retrieved_by_email is not None, "应该能够通过邮箱获取用户"
        assert retrieved_by_email.id == user.id, "用户 ID 应该匹配"


class TestPreservation_CacheOperations:
    """
    保留属性 2: 缓存功能保持正常
    
    验证缓存系统对可序列化对象的处理不受影响。
    
    **Validates: Requirements 3.1, 3.5**
    """
    
    @given(
        cache_value=st.one_of(
            st.text(min_size=1, max_size=100),
            st.integers(min_value=-1000, max_value=1000),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans(),
            st.lists(st.text(min_size=1, max_size=20), max_size=10),
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20),
                values=st.one_of(st.text(), st.integers(), st.booleans()),
                max_size=10
            )
        )
    )
    @settings(
        max_examples=30,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_cache_operations_with_serializable_data(self, cache_value):
        """
        属性测试：缓存系统应该能够处理各种可序列化的数据类型
        
        验证缓存的核心功能（set/get）对标准 JSON 可序列化类型正常工作。
        
        **预期结果**：在未修复和修复后的代码上都应该通过
        
        **Validates: Requirements 3.1, 3.5**
        """
        from app.core.cache.manager import CacheManager
        
        cache_manager = CacheManager()
        cache_key = f"test:preservation:{uuid.uuid4().hex}"
        
        # 设置缓存
        set_result = await cache_manager.set_cached(cache_key, cache_value, ttl=60)
        
        # 验证设置成功（或者缓存被禁用）
        assert isinstance(set_result, bool), "set_cached 应该返回布尔值"
        
        # 如果缓存启用且设置成功，验证可以获取
        if set_result and cache_manager.is_enabled():
            cached_data = await cache_manager.get_cached(cache_key)
            
            # 验证缓存的数据与原始数据一致
            assert cached_data == cache_value, \
                f"缓存的数据应该与原始数据一致。原始：{cache_value}，缓存：{cached_data}"
    
    @pytest.mark.asyncio
    async def test_cache_pydantic_model_serialization(self, test_db):
        """
        测试：Pydantic 模型的缓存序列化保持正常
        
        验证缓存系统对 Pydantic 模型的处理不受影响。
        
        **预期结果**：在未修复和修复后的代码上都应该通过
        
        **Validates: Requirements 3.1, 3.5**
        """
        from app.core.cache.manager import CacheManager
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            id: int
            name: str
            active: bool
        
        cache_manager = CacheManager()
        cache_key = f"test:pydantic:{uuid.uuid4().hex}"
        
        # 创建 Pydantic 模型实例
        test_data = TestModel(id=123, name="Test", active=True)
        
        # 设置缓存
        set_result = await cache_manager.set_cached(cache_key, test_data, ttl=60)
        
        # 验证设置成功（或者缓存被禁用）
        assert isinstance(set_result, bool), "set_cached 应该返回布尔值"
        
        # 如果缓存启用且设置成功，验证可以获取
        if set_result and cache_manager.is_enabled():
            cached_data = await cache_manager.get_cached(cache_key)
            assert cached_data is not None, "应该能够获取缓存的数据"


class TestPreservation_KnowledgeBaseOperations:
    """
    保留属性 3: 知识库功能保持正常
    
    验证知识库服务的核心功能不受影响。
    
    **Validates: Requirements 3.1, 3.6**
    """
    
    @pytest.mark.asyncio
    async def test_knowledge_base_crud_operations(self, test_db, test_user):
        """
        测试：知识库 CRUD 操作保持正常
        
        验证知识库的创建和读取操作不受影响。
        
        **预期结果**：在未修复和修复后的代码上都应该通过
        
        **Validates: Requirements 3.1, 3.6**
        """
        from app.services.knowledge_service import KnowledgeService
        import tempfile
        import os
        
        service = KnowledgeService(test_db)
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 创建知识库
            kb_name = f"Preservation KB {uuid.uuid4().hex[:8]}"
            kb_data = {
                "name": kb_name,
                "description": "Test preservation",
                "uploader_id": test_user.id,
                "copyright_owner": test_user.username,
                "base_path": temp_dir,
                "is_public": True,
            }
            
            # save_knowledge_base 是同步方法，不需要 await
            kb = service.save_knowledge_base(kb_data)
            assert kb is not None, "知识库创建应该成功"
            assert kb.name == kb_name, "知识库名称应该匹配"
            
            # 读取知识库（返回对象）
            retrieved_kb = service.get_knowledge_base_by_id(kb.id)
            assert retrieved_kb is not None, "应该能够获取知识库"
            assert retrieved_kb.name == kb_name, "知识库名称应该匹配"
            
            # 删除知识库
            delete_result = service.delete_knowledge_base(kb.id)
            assert delete_result is True, "知识库删除应该成功"
            
            # 验证已删除
            deleted_kb = service.get_knowledge_base_by_id(kb.id)
            assert deleted_kb is None, "删除后应该无法获取知识库"
            
        finally:
            # 清理临时目录
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    @given(
        is_public=st.booleans(),
        description_length=st.integers(min_value=0, max_value=200)
    )
    @settings(
        max_examples=15,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_knowledge_base_creation_with_various_settings(
        self, is_public, description_length, test_db, test_user
    ):
        """
        属性测试：知识库创建应该支持各种设置
        
        验证知识库创建在不同参数组合下都能正常工作。
        
        **预期结果**：在未修复和修复后的代码上都应该通过
        
        **Validates: Requirements 3.1, 3.6**
        """
        from app.services.knowledge_service import KnowledgeService
        import tempfile
        import os
        
        service = KnowledgeService(test_db)
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 生成描述
            description = "A" * description_length if description_length > 0 else ""
            
            kb_data = {
                "name": f"KB {uuid.uuid4().hex[:8]}",
                "description": description,
                "uploader_id": test_user.id,
                "copyright_owner": test_user.username,
                "base_path": temp_dir,
                "is_public": is_public,
            }
            
            # save_knowledge_base 是同步方法
            kb = service.save_knowledge_base(kb_data)
            assert kb is not None, "知识库创建应该成功"
            assert kb.is_public == is_public, "公开状态应该匹配"
            assert kb.description == description, "描述应该匹配"
            
        finally:
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)


class TestPreservation_PersonaOperations:
    """
    保留属性 4: 人设卡功能保持正常
    
    验证人设卡服务的核心功能不受影响。
    
    **Validates: Requirements 3.1, 3.7**
    """
    
    @pytest.mark.asyncio
    async def test_persona_card_crud_operations(self, test_db, test_user):
        """
        测试：人设卡 CRUD 操作保持正常
        
        验证人设卡的创建和读取操作不受影响。
        
        **预期结果**：在未修复和修复后的代码上都应该通过
        
        **Validates: Requirements 3.1, 3.7**
        """
        from app.services.persona_service import PersonaService
        import tempfile
        import os
        
        service = PersonaService(test_db)
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 创建人设卡（设置为非公开且非审核中）
            persona_name = f"Preservation Persona {uuid.uuid4().hex[:8]}"
            persona_data = {
                "name": persona_name,
                "description": "Test preservation",
                "uploader_id": test_user.id,
                "copyright_owner": test_user.username,
                "base_path": temp_dir,
                "is_public": False,
                "is_pending": False,  # 设置为非审核中
            }
            
            persona = service.save_persona_card(persona_data)
            assert persona is not None, "人设卡创建应该成功"
            assert persona.name == persona_name, "人设卡名称应该匹配"
            
            # 读取人设卡（返回对象）
            retrieved_persona = service.get_persona_card_by_id(persona.id)
            assert retrieved_persona is not None, "应该能够获取人设卡"
            assert retrieved_persona.name == persona_name, "人设卡名称应该匹配"
            
            # 删除人设卡
            delete_result = service.delete_persona_card(persona.id)
            assert delete_result is True, "人设卡删除应该成功"
            
            # 验证已删除
            deleted_persona = service.get_persona_card_by_id(persona.id)
            assert deleted_persona is None, "删除后应该无法获取人设卡"
            
        finally:
            # 清理临时目录
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)


class TestPreservation_DatabaseOperations:
    """
    保留属性 5: 数据库操作保持正常
    
    验证数据库的基本操作不受影响。
    
    **Validates: Requirements 3.1, 3.9**
    """
    
    @pytest.mark.asyncio
    async def test_database_transaction_integrity(self, test_db):
        """
        测试：数据库事务完整性保持正常
        
        验证数据库事务的提交和回滚功能不受影响。
        
        **预期结果**：在未修复和修复后的代码上都应该通过
        
        **Validates: Requirements 3.1, 3.9**
        """
        from app.services.user_service import UserService
        
        service = UserService(test_db)
        
        # 创建用户（事务提交）
        username = f"txuser_{uuid.uuid4().hex[:8]}"
        email = f"tx_{uuid.uuid4().hex[:8]}@example.com"
        
        user = service.create_user(
            username=username,
            email=email,
            password="TestPassword123!"
        )
        
        assert user is not None, "用户创建应该成功"
        
        # 验证事务已提交（可以在新查询中找到用户）
        retrieved_user = service.get_user_by_id(user.id)
        assert retrieved_user is not None, "事务提交后应该能够获取用户"
        assert retrieved_user.username == username, "用户名应该匹配"
    
    @given(
        batch_size=st.integers(min_value=1, max_value=5)
    )
    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_batch_operations_consistency(self, batch_size, test_db):
        """
        属性测试：批量操作的一致性保持正常
        
        验证批量创建用户时数据的一致性。
        
        **预期结果**：在未修复和修复后的代码上都应该通过
        
        **Validates: Requirements 3.1, 3.9**
        """
        from app.services.user_service import UserService
        
        service = UserService(test_db)
        created_users = []
        
        # 批量创建用户
        for i in range(batch_size):
            unique_id = uuid.uuid4().hex[:8]
            user = service.create_user(
                username=f"batchuser_{unique_id}_{i}",
                email=f"batch_{unique_id}_{i}@example.com",
                password="TestPassword123!"
            )
            assert user is not None, f"第 {i+1} 个用户创建应该成功"
            created_users.append(user)
        
        # 验证所有用户都可以被检索
        for user in created_users:
            retrieved_user = service.get_user_by_id(user.id)
            assert retrieved_user is not None, f"应该能够获取用户 {user.username}"
            assert retrieved_user.username == user.username, "用户名应该匹配"


class TestPreservation_APIBehavior:
    """
    保留属性 6: API 行为保持一致
    
    验证 API 端点的行为不受影响。
    
    **Validates: Requirements 3.1, 3.4-3.9**
    """
    
    @pytest.mark.asyncio
    async def test_user_service_api_consistency(self, test_db):
        """
        测试：用户服务 API 行为一致性
        
        验证用户服务的 API 行为（返回值类型、错误处理等）保持一致。
        
        **预期结果**：在未修复和修复后的代码上都应该通过
        
        **Validates: Requirements 3.1, 3.4**
        """
        from app.services.user_service import UserService
        
        service = UserService(test_db)
        
        # 测试获取不存在的用户
        non_existent_user = service.get_user_by_id(999999)
        assert non_existent_user is None, "获取不存在的用户应该返回 None"
        
        # 测试获取所有用户
        all_users = service.get_all_users()
        assert isinstance(all_users, list), "get_all_users 应该返回列表"
        
        # 创建用户并验证返回类型
        user = service.create_user(
            username=f"apiuser_{uuid.uuid4().hex[:8]}",
            email=f"api_{uuid.uuid4().hex[:8]}@example.com",
            password="TestPassword123!"
        )
        
        assert user is not None, "用户创建应该成功"
        assert hasattr(user, "id"), "用户对象应该有 id 属性"
        assert hasattr(user, "username"), "用户对象应该有 username 属性"
        assert hasattr(user, "email"), "用户对象应该有 email 属性"
    
    @pytest.mark.asyncio
    async def test_service_error_handling_consistency(self, test_db):
        """
        测试：服务层错误处理一致性
        
        验证服务层的错误处理行为保持一致。
        
        **预期结果**：在未修复和修复后的代码上都应该通过
        
        **Validates: Requirements 3.1, 3.9**
        """
        from app.services.user_service import UserService
        
        service = UserService(test_db)
        
        # 测试无效输入的处理
        try:
            # 尝试使用 None 作为 ID
            result = service.get_user_by_id(None)
            # 应该返回 None 或抛出预期的异常
            assert result is None or isinstance(result, type(None)), \
                "无效 ID 应该返回 None 或抛出预期异常"
        except (ValueError, TypeError):
            # 这些异常是可以接受的
            pass


class TestPreservation_OverallSystemHealth:
    """
    保留属性 7: 系统整体健康状态
    
    验证系统的整体健康状态不受影响。
    
    **Validates: Requirements 3.1-3.9**
    """
    
    @pytest.mark.asyncio
    async def test_system_components_integration(self, test_db, test_user):
        """
        测试：系统组件集成保持正常
        
        验证多个系统组件的集成工作不受影响。
        
        **预期结果**：在未修复和修复后的代码上都应该通过
        
        **Validates: Requirements 3.1-3.9**
        """
        from app.services.user_service import UserService
        from app.services.knowledge_service import KnowledgeService
        from app.services.persona_service import PersonaService
        from app.core.cache.manager import CacheManager
        import tempfile
        import os
        
        # 测试用户服务
        user_service = UserService(test_db)
        new_user = user_service.create_user(
            username=f"integuser_{uuid.uuid4().hex[:8]}",
            email=f"integ_{uuid.uuid4().hex[:8]}@example.com",
            password="TestPassword123!"
        )
        assert new_user is not None, "用户创建应该成功"
        
        # 测试缓存服务
        cache_manager = CacheManager()
        cache_key = f"test:integration:{uuid.uuid4().hex}"
        cache_data = {"user_id": new_user.id, "username": new_user.username}
        cache_result = await cache_manager.set_cached(cache_key, cache_data, ttl=60)
        assert isinstance(cache_result, bool), "缓存操作应该返回布尔值"
        
        # 测试知识库服务
        kb_service = KnowledgeService(test_db)
        temp_kb_dir = tempfile.mkdtemp()
        try:
            # save_knowledge_base 是同步方法
            kb = kb_service.save_knowledge_base({
                "name": f"Integration KB {uuid.uuid4().hex[:8]}",
                "description": "Integration test",
                "uploader_id": test_user.id,
                "copyright_owner": test_user.username,
                "base_path": temp_kb_dir,
                "is_public": True,
            })
            assert kb is not None, "知识库创建应该成功"
        finally:
            if os.path.exists(temp_kb_dir):
                import shutil
                shutil.rmtree(temp_kb_dir, ignore_errors=True)
        
        # 测试人设卡服务
        persona_service = PersonaService(test_db)
        temp_persona_dir = tempfile.mkdtemp()
        try:
            persona = persona_service.save_persona_card({
                "name": f"Integration Persona {uuid.uuid4().hex[:8]}",
                "description": "Integration test",
                "uploader_id": test_user.id,
                "copyright_owner": test_user.username,
                "base_path": temp_persona_dir,
                "is_public": True,
            })
            assert persona is not None, "人设卡创建应该成功"
        finally:
            if os.path.exists(temp_persona_dir):
                import shutil
                shutil.rmtree(temp_persona_dir, ignore_errors=True)
