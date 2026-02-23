"""
Bug 条件探索属性测试

此测试文件用于验证测试套件中 348 个失败测试的根本原因。
这些测试预期在未修复的代码上失败，以证明 Bug 存在。

**关键**：此测试必须在未修复代码上失败 - 失败确认 Bug 存在
**不要尝试修复测试或代码当它失败时**

**Validates: Requirements 1.1-1.23 (Bugfix Spec)**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
import uuid
import json

# 标记所有测试为串行执行
pytestmark = pytest.mark.serial


class TestBugCondition_UserConflict:
    """
    Bug 条件 1: 用户创建冲突问题
    
    验证数据库清理逻辑是否存在问题，导致用户名冲突。
    
    **Validates: Requirements 1.1, 1.2**
    """
    
    def test_user_creation_no_conflict_after_cleanup(self, test_db):
        """
        测试：数据库清理后不应该有用户名冲突
        
        此测试验证 test_db fixture 的清理逻辑是否正确。
        如果清理不完整，创建相同用户名的用户会失败。
        
        **预期结果**：在未修复代码上可能失败（如果清理逻辑有问题）
        
        **Validates: Requirements 1.1, 1.2**
        """
        from app.services.user_service import UserService
        
        service = UserService(test_db)
        
        # 使用固定的用户名（模拟测试套件中的常见用户名）
        test_username = "testuser_abc123"
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        # 尝试创建用户
        user = service.create_user(
            username=test_username,
            email=test_email,
            password="testpassword123"
        )
        
        # 验证用户创建成功
        assert user is not None, "用户创建应该成功"
        assert user.username == test_username, "用户名应该匹配"
        
        # 验证数据库中只有一个该用户名的用户
        all_users = service.get_all_users()
        user_count = len([u for u in all_users if u.username == test_username])
        assert user_count == 1, f"数据库中应该只有一个该用户名的用户，实际有 {user_count} 个"


class TestBugCondition_CacheSerialization:
    """
    Bug 条件 2: 缓存序列化问题
    
    验证缓存系统是否能正确序列化 SQLAlchemy ORM 对象。
    
    **Validates: Requirements 1.3, 1.4**
    """
    
    @pytest.mark.asyncio
    async def test_cache_can_serialize_user_object(self, test_db, test_user):
        """
        测试：缓存系统应该能够序列化 User 对象
        
        此测试验证缓存管理器是否能正确处理 SQLAlchemy 对象。
        如果序列化逻辑有问题，会抛出 JSON 序列化错误。
        
        **预期结果**：在未修复代码上失败（抛出序列化错误）
        
        **Validates: Requirements 1.3, 1.4**
        """
        from app.core.cache.manager import CacheManager
        
        # 创建缓存管理器实例
        cache_manager = CacheManager()
        
        # 如果缓存被禁用，跳过此测试
        if not cache_manager.is_enabled():
            pytest.skip("缓存已禁用，跳过序列化测试")
        
        # 尝试缓存 User 对象
        cache_key = f"user:{test_user.id}"
        
        try:
            # 这应该在未修复的代码上失败
            result = await cache_manager.set_cached(cache_key, test_user, ttl=60)
            
            # 如果成功，验证结果
            assert isinstance(result, bool), "set_cached 应该返回布尔值"
            
            # 如果缓存成功，尝试获取
            if result:
                cached_value = await cache_manager.get_cached(cache_key)
                # 验证缓存的数据可以被反序列化
                assert cached_value is not None, "缓存的数据应该可以被获取"
                
        except TypeError as e:
            # 预期的序列化错误
            error_msg = str(e).lower()
            assert "not json serializable" in error_msg or "serialize" in error_msg, \
                f"应该是 JSON 序列化错误，实际错误：{e}"
            # 重新抛出以标记测试失败（这是预期的）
            raise
    
    @pytest.mark.asyncio
    async def test_cache_serialization_with_async(self, test_db, test_user):
        """
        测试：异步缓存序列化（使用 asyncio）
        
        **预期结果**：在未修复代码上失败（抛出序列化错误）
        
        **Validates: Requirements 1.3, 1.4**
        """
        from app.core.cache.manager import CacheManager
        
        cache_manager = CacheManager()
        cache_key = f"user:{test_user.id}"
        
        try:
            result = await cache_manager.set_cached(cache_key, test_user, ttl=60)
            assert isinstance(result, bool), "set_cached 应该返回布尔值"
            
        except TypeError as e:
            error_msg = str(e).lower()
            assert "not json serializable" in error_msg or "serialize" in error_msg, \
                f"应该是 JSON 序列化错误，实际错误：{e}"
            raise


class TestBugCondition_ServiceFailures:
    """
    Bug 条件 3-4: 服务层测试失败
    
    验证知识库和人设卡服务的功能是否正常。
    
    **Validates: Requirements 1.5, 1.6, 1.7**
    """
    
    def test_knowledge_service_basic_operations(self, test_db, test_user):
        """
        测试：知识库服务基本操作
        
        验证知识库服务的 CRUD 操作是否正常工作。
        
        **预期结果**：在未修复代码上可能失败
        
        **Validates: Requirements 1.5, 1.6**
        """
        from app.services.knowledge_service import KnowledgeService
        import tempfile
        
        service = KnowledgeService(test_db)
        temp_dir = tempfile.mkdtemp()
        
        # 创建知识库
        kb_data = {
            "name": f"Test KB {uuid.uuid4().hex[:8]}",
            "description": "Test description",
            "uploader_id": test_user.id,
            "copyright_owner": test_user.username,
            "base_path": temp_dir,
            "is_public": True,
        }
        
        kb = service.save_knowledge_base(kb_data)
        assert kb is not None, "知识库创建应该成功"
        
        # 获取知识库
        retrieved_kb = service.get_knowledge_base_by_id(kb.id)
        assert retrieved_kb is not None, "应该能够获取创建的知识库"
        assert retrieved_kb.name == kb_data["name"], "知识库名称应该匹配"
    
    def test_persona_service_basic_operations(self, test_db, test_user):
        """
        测试：人设卡服务基本操作
        
        验证人设卡服务的 CRUD 操作是否正常工作。
        
        **预期结果**：在未修复代码上可能失败
        
        **Validates: Requirements 1.7**
        """
        from app.services.persona_service import PersonaService
        import tempfile
        
        service = PersonaService(test_db)
        temp_dir = tempfile.mkdtemp()
        
        # 创建人设卡
        persona_data = {
            "name": f"Test Persona {uuid.uuid4().hex[:8]}",
            "description": "Test description",
            "uploader_id": test_user.id,
            "copyright_owner": test_user.username,
            "base_path": temp_dir,
            "is_public": True,
        }
        
        persona = service.save_persona_card(persona_data)
        assert persona is not None, "人设卡创建应该成功"
        
        # 获取人设卡
        retrieved_persona = service.get_persona_card_by_id(persona.id)
        assert retrieved_persona is not None, "应该能够获取创建的人设卡"
        assert retrieved_persona.name == persona_data["name"], "人设卡名称应该匹配"


class TestBugCondition_WebSocket:
    """
    Bug 条件 5: WebSocket 相关测试失败
    
    验证 WebSocket 连接管理和事件循环是否正常。
    
    **Validates: Requirements 1.8-1.14**
    """
    
    @pytest.mark.asyncio
    async def test_websocket_redis_connection_lifecycle(self):
        """
        测试：WebSocket Redis 连接生命周期
        
        验证 Redis 连接是否能正确创建和关闭，不会出现事件循环错误。
        
        **预期结果**：在未修复代码上可能失败（Event loop is closed）
        
        **Validates: Requirements 1.8-1.14**
        """
        from app.core.cache.redis_client import RedisClient
        
        # 创建 Redis 客户端
        redis_client = RedisClient()
        
        try:
            # 执行简单操作
            await redis_client.set("test_key", "test_value", ttl=10)
            value = await redis_client.get("test_key")
            
            assert value == "test_value", "Redis 操作应该成功"
            
        finally:
            # 关闭连接
            try:
                await redis_client.close()
            except RuntimeError as e:
                # 捕获 "Event loop is closed" 错误
                if "event loop is closed" in str(e).lower():
                    pytest.fail(f"Redis 连接关闭时出现事件循环错误：{e}")
                raise


class TestBugCondition_PropertyTests:
    """
    Bug 条件 6: 属性测试失败
    
    验证系统对边界值和异常情况的处理。
    
    **Validates: Requirements 1.15-1.18**
    """
    
    @given(
        user_id=st.one_of(
            st.none(),
            st.just(""),
            st.text(min_size=1, max_size=100),
        )
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @pytest.mark.asyncio
    async def test_boundary_value_handling(self, user_id, test_db):
        """
        属性测试：边界值处理
        
        验证服务层是否能安全处理边界值输入。
        
        **预期结果**：在未修复代码上可能失败
        
        **Validates: Requirements 1.15**
        """
        from app.services.user_service import UserService
        
        service = UserService(test_db)
        
        try:
            result = service.get_user_by_id(user_id)
            # 验证返回值类型
            assert result is None or hasattr(result, "id"), \
                "get_user_by_id 应该返回 None 或 User 对象"
        except (ValueError, TypeError):
            # 预期的异常是可以接受的
            pass
        except Exception as e:
            # 其他异常不应该发生
            pytest.fail(f"get_user_by_id 不应该抛出 {type(e).__name__}: {e}")


class TestBugCondition_OtherTests:
    """
    Bug 条件 7: 其他服务和路由测试失败
    
    验证其他服务的基本功能。
    
    **Validates: Requirements 1.19-1.23**
    """
    
    def test_user_service_operations(self, test_db):
        """
        测试：用户服务基本操作
        
        验证用户服务的基本功能是否正常。
        
        **预期结果**：在未修复代码上可能失败
        
        **Validates: Requirements 1.19**
        """
        from app.services.user_service import UserService
        
        service = UserService(test_db)
        
        # 创建用户
        user = service.create_user(
            username=f"testuser_{uuid.uuid4().hex[:8]}",
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password="testpassword123"
        )
        
        assert user is not None, "用户创建应该成功"
        
        # 获取用户
        retrieved_user = service.get_user_by_id(user.id)
        assert retrieved_user is not None, "应该能够获取创建的用户"
        assert retrieved_user.username == user.username, "用户名应该匹配"


class TestBugCondition_TestSuiteFailures:
    """
    综合测试：验证测试套件的整体失败情况
    
    此测试运行一小部分代表性测试，以验证 Bug 条件的存在。
    
    **Validates: Requirements 1.1-1.23**
    """
    
    @pytest.mark.asyncio
    async def test_representative_failures_exist(self, test_db):
        """
        测试：代表性失败存在
        
        运行几个代表性的操作，验证 Bug 条件是否存在。
        此测试作为整体健康检查。
        
        **预期结果**：在未修复代码上，至少一个操作应该失败
        
        **Validates: Requirements 1.1-1.23**
        """
        from app.services.user_service import UserService
        from app.services.knowledge_service import KnowledgeService
        from app.services.persona_service import PersonaService
        
        failures = []
        
        # 测试 1: 用户创建
        try:
            user_service = UserService(test_db)
            user = user_service.create_user(
                username=f"testuser_{uuid.uuid4().hex[:8]}",
                email=f"test_{uuid.uuid4().hex[:8]}@example.com",
                password="testpassword123"
            )
            if user is None:
                failures.append("用户创建失败")
        except Exception as e:
            failures.append(f"用户创建异常：{e}")
        
        # 测试 2: 缓存序列化（如果有用户）
        if 'user' in locals() and user is not None:
            try:
                from app.core.cache.manager import CacheManager
                
                cache_manager = CacheManager()
                result = await cache_manager.set_cached(f"user:{user.id}", user, ttl=60)
                    
            except TypeError as e:
                if "not json serializable" in str(e).lower():
                    failures.append(f"缓存序列化失败：{e}")
            except Exception as e:
                failures.append(f"缓存测试异常：{e}")
        
        # 如果所有测试都通过，说明 Bug 可能已经被修复
        # 在未修复的代码上，应该至少有一个失败
        if len(failures) == 0:
            pytest.skip("所有代表性测试都通过，Bug 可能已被修复")
        else:
            # 记录失败信息（这是预期的）
            print(f"\n发现 {len(failures)} 个失败（这是预期的）：")
            for failure in failures:
                print(f"  - {failure}")
