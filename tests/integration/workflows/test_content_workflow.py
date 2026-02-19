"""
Integration workflow tests for content creation and file management
Tests complete end-to-end content creation, retrieval, and file upload/download flows

Example 2: Content creation and retrieval flow
Example 3: File upload and download flow
Requirements: 9.2, 9.3

Note: These tests focus on database-level workflows to ensure data integrity
and business logic correctness across the content lifecycle.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.database import User, KnowledgeBase, KnowledgeBaseFile, PersonaCard, PersonaCardFile
from app.core.security import get_password_hash
import uuid


class TestContentCreationAndRetrievalWorkflow:
    """Test complete content creation and retrieval workflow"""
    
    def test_knowledge_base_creation_and_retrieval_flow(self, test_db: Session):
        """
        Test Example 2: Content creation and retrieval flow (Knowledge Base)
        
        Complete workflow:
        1. Create and authenticate user
        2. Create knowledge base
        3. Verify knowledge base is stored
        4. Query knowledge base
        5. Verify content is accessible
        
        **Validates: Requirements 9.2**
        """
        from app.main import app
        client = TestClient(app)
        
        # Step 1: Create user and authenticate
        user = User(
            id=str(uuid.uuid4()),
            username="contentcreator",
            email="creator@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(user)
        test_db.commit()
        
        # Login to verify authentication works
        login_response = client.post(
            "/api/auth/token",
            json={"username": "contentcreator", "password": "password123"}
        )
        assert login_response.status_code == 200
        
        # Step 2: Create knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            title="Test Knowledge Base",
            description="This is a test knowledge base for workflow testing",
            owner_id=user.id,
            is_public=True,
            status="approved",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_db.add(kb)
        test_db.commit()
        test_db.refresh(kb)
        
        # Step 3: Verify knowledge base is stored
        kb_in_db = test_db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb.id
        ).first()
        assert kb_in_db is not None
        assert kb_in_db.title == "Test Knowledge Base"
        assert kb_in_db.owner_id == user.id
        
        # Step 4: Query knowledge bases for user
        user_kbs = test_db.query(KnowledgeBase).filter(
            KnowledgeBase.owner_id == user.id
        ).all()
        assert len(user_kbs) >= 1
        assert kb.id in [k.id for k in user_kbs]
        
        # Step 5: Verify content is accessible
        retrieved_kb = test_db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb.id
        ).first()
        assert retrieved_kb.title == kb.title
        assert retrieved_kb.description == kb.description
    
    def test_persona_card_creation_and_update_flow(self, test_db: Session):
        """
        Test Example 2: Content creation and update flow (Persona Card)
        
        Complete workflow:
        1. Create user
        2. Create persona card
        3. Verify persona card is stored
        4. Update persona card
        5. Verify updates are persisted
        
        **Validates: Requirements 9.2**
        """
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            username="personacreator",
            email="persona@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(user)
        test_db.commit()
        
        # Create persona card
        persona = PersonaCard(
            id=str(uuid.uuid4()),
            name="Test Persona",
            description="A test persona for workflow testing",
            owner_id=user.id,
            is_public=True,
            status="approved",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_db.add(persona)
        test_db.commit()
        test_db.refresh(persona)
        
        # Verify in database
        persona_in_db = test_db.query(PersonaCard).filter(
            PersonaCard.id == persona.id
        ).first()
        assert persona_in_db is not None
        assert persona_in_db.name == "Test Persona"
        
        # Update persona card
        persona_in_db.name = "Updated Persona"
        persona_in_db.description = "Updated description"
        test_db.commit()
        
        # Verify updates persisted
        test_db.refresh(persona_in_db)
        assert persona_in_db.name == "Updated Persona"
        assert persona_in_db.description == "Updated description"
    
    def test_content_search_and_filter_flow(self, test_db: Session):
        """
        Test content search and filtering workflow
        
        Workflow:
        1. Create multiple knowledge bases
        2. Search by title
        3. Filter by public/private
        4. Verify search results
        
        **Validates: Requirements 9.2**
        """
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            username="searcher",
            email="searcher@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(user)
        test_db.commit()
        
        # Create multiple knowledge bases
        kb1 = KnowledgeBase(
            id=str(uuid.uuid4()),
            title="Python Programming",
            description="Learn Python",
            owner_id=user.id,
            is_public=True,
            status="approved",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        kb2 = KnowledgeBase(
            id=str(uuid.uuid4()),
            title="JavaScript Basics",
            description="Learn JS",
            owner_id=user.id,
            is_public=False,
            status="approved",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        kb3 = KnowledgeBase(
            id=str(uuid.uuid4()),
            title="Python Advanced",
            description="Advanced Python",
            owner_id=user.id,
            is_public=True,
            status="approved",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        test_db.add_all([kb1, kb2, kb3])
        test_db.commit()
        
        # Search for "Python"
        python_kbs = test_db.query(KnowledgeBase).filter(
            KnowledgeBase.owner_id == user.id,
            KnowledgeBase.title.contains("Python")
        ).all()
        
        assert len(python_kbs) == 2
        titles = [kb.title for kb in python_kbs]
        assert "Python Programming" in titles
        assert "Python Advanced" in titles
        
        # Filter by public
        public_kbs = test_db.query(KnowledgeBase).filter(
            KnowledgeBase.owner_id == user.id,
            KnowledgeBase.is_public == True
        ).all()
        
        assert len(public_kbs) == 2


class TestFileUploadAndDownloadWorkflow:
    """Test complete file upload and download workflow"""
    
    def test_knowledge_base_file_upload_flow(self, test_db: Session):
        """
        Test Example 3: File upload and download flow (Knowledge Base)
        
        Complete workflow:
        1. Create user
        2. Create knowledge base
        3. Upload file (create file record)
        4. Verify file is stored
        5. List files
        6. Verify file can be retrieved
        
        **Validates: Requirements 9.3**
        """
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            username="fileuploader",
            email="uploader@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(user)
        test_db.commit()
        
        # Create knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            title="File Test KB",
            description="For file testing",
            owner_id=user.id,
            is_public=True,
            status="approved",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_db.add(kb)
        test_db.commit()
        
        # Upload file (create file record)
        kb_file = KnowledgeBaseFile(
            id=str(uuid.uuid4()),
            knowledge_base_id=kb.id,
            filename="test_document.txt",
            file_path="uploads/test_document.txt",
            file_size=1024,
            created_at=datetime.now()
        )
        test_db.add(kb_file)
        test_db.commit()
        test_db.refresh(kb_file)
        
        # Verify file is stored
        file_in_db = test_db.query(KnowledgeBaseFile).filter(
            KnowledgeBaseFile.id == kb_file.id
        ).first()
        assert file_in_db is not None
        assert file_in_db.filename == "test_document.txt"
        assert file_in_db.knowledge_base_id == kb.id
        
        # List files
        files = test_db.query(KnowledgeBaseFile).filter(
            KnowledgeBaseFile.knowledge_base_id == kb.id
        ).all()
        
        assert len(files) >= 1
        assert any(f.id == kb_file.id for f in files)
    
    def test_file_upload_and_delete_flow(self, test_db: Session):
        """
        Test file upload and deletion workflow
        
        Workflow:
        1. Create persona card
        2. Upload file
        3. Verify file exists
        4. Delete file
        5. Verify file is removed
        
        **Validates: Requirements 9.3**
        """
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            username="filedeleter",
            email="deleter@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(user)
        test_db.commit()
        
        # Create persona card
        persona = PersonaCard(
            id=str(uuid.uuid4()),
            name="File Delete Test",
            description="Test",
            owner_id=user.id,
            is_public=True,
            status="approved",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_db.add(persona)
        test_db.commit()
        
        # Upload file
        persona_file = PersonaCardFile(
            id=str(uuid.uuid4()),
            persona_card_id=persona.id,
            filename="delete_me.txt",
            file_path="uploads/delete_me.txt",
            file_size=512,
            created_at=datetime.now()
        )
        test_db.add(persona_file)
        test_db.commit()
        
        # Verify file exists
        file_in_db = test_db.query(PersonaCardFile).filter(
            PersonaCardFile.id == persona_file.id
        ).first()
        assert file_in_db is not None
        
        # Delete file
        test_db.delete(file_in_db)
        test_db.commit()
        
        # Verify file is removed
        file_after_delete = test_db.query(PersonaCardFile).filter(
            PersonaCardFile.id == persona_file.id
        ).first()
        assert file_after_delete is None
    
    def test_multiple_file_upload_flow(self, test_db: Session):
        """
        Test uploading multiple files to same knowledge base
        
        Workflow:
        1. Create knowledge base
        2. Upload multiple files
        3. List all files
        4. Verify all files are present
        
        **Validates: Requirements 9.3**
        """
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            username="multiuploader",
            email="multi@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=False,
            is_moderator=False,
            is_super_admin=False,
            created_at=datetime.now(),
            password_version=0
        )
        test_db.add(user)
        test_db.commit()
        
        # Create knowledge base
        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            title="Multi File KB",
            description="Multiple files",
            owner_id=user.id,
            is_public=True,
            status="approved",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        test_db.add(kb)
        test_db.commit()
        
        # Upload multiple files
        file_ids = []
        for i in range(3):
            kb_file = KnowledgeBaseFile(
                id=str(uuid.uuid4()),
                knowledge_base_id=kb.id,
                filename=f"file{i+1}.txt",
                file_path=f"uploads/file{i+1}.txt",
                file_size=100 * (i+1),
                created_at=datetime.now()
            )
            test_db.add(kb_file)
            file_ids.append(kb_file.id)
        
        test_db.commit()
        
        # List all files
        files = test_db.query(KnowledgeBaseFile).filter(
            KnowledgeBaseFile.knowledge_base_id == kb.id
        ).all()
        
        assert len(files) == 3
        
        # Verify all file IDs are present
        listed_ids = [f.id for f in files]
        for file_id in file_ids:
            assert file_id in listed_ids
