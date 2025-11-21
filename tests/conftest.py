import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.utils import deps as deps_utils
import main
from fastapi.testclient import TestClient
from app.crud.user import user as crud_user
from app.core.security import get_password_hash
from app.models.user import User
from app.models.school import School
from app.models.user_school_association import UserSchoolAssociation
from app.core.constants import ADMIN_SCHOOL_NAME, RoleEnum
from app.crud.school import school as crud_school
from app.crud.role import role as crud_role
import uuid
from app.core.config import settings

test_db_url = settings.TEST_DATABASE_URL or "sqlite:///./test.db"

@pytest.fixture(scope="session")
def database_engine():
    if test_db_url.startswith("sqlite"):
        engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(test_db_url)
    Base.metadata.create_all(bind=engine)
    yield engine
    if test_db_url.startswith("sqlite"):
        os.remove("./test.db")

@pytest.fixture(scope="function")
def db_session(database_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database_engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

@pytest.fixture(scope="function")
def client(db_session):
    # Re-initialize the app for each test function to ensure a clean state
    from importlib import reload
    reload(main)
    main.app.dependency_overrides[get_db] = lambda: db_session
    main.app.dependency_overrides[deps_utils.get_db] = lambda: db_session
    main.app.dependency_overrides[deps_utils.get_transactional_db] = lambda: db_session
    with TestClient(main.app) as test_client:
        yield test_client

@pytest.fixture
def super_admin_token(client, db_session, _ensure_admin_school_exists, _ensure_super_admin_role_exists):
    admin_school = _ensure_admin_school_exists
    super_admin_role = _ensure_super_admin_role_exists
    email = f"superadmin-{uuid.uuid4()}@test.com"

    hashed_password = get_password_hash("testpass123")
    super_admin = User(
        full_name="Test Super Admin",
        email=email,
        hashed_password=hashed_password,
        is_active=True
    )
    db_session.add(super_admin)
    db_session.flush()

    user_school_assoc = UserSchoolAssociation(
        user_id=super_admin.id,
        school_id=admin_school.id,
        role_id=super_admin_role.id
    )
    db_session.add(user_school_assoc)
    db_session.commit()
    db_session.refresh(super_admin)

    response = client.post("/auth/login", json={"email": email, "password": "testpass123"})
    body = response.json()
    token = (
        body.get("data", {}).get("token", {}).get("access_token")
        or body.get("token", {}).get("access_token")
        or body.get("access_token")
    )
    assert token, f"Login failed or token missing: {body}"
    return token

@pytest.fixture
def school_admin_token(client, db_session, _ensure_admin_school_exists, _ensure_school_admin_role_exists):
    admin_school = _ensure_admin_school_exists
    school_admin_role = _ensure_school_admin_role_exists
    email = "schooladmin@test.com"

    school_admin = crud_user.get_by_email(db_session, email=email)
    if not school_admin:
        school_admin_data = {
            "full_name": "Test School Admin",
            "email": email,
            "hashed_password": get_password_hash("testpass123"),
            "is_active": True
        }
        school_admin = crud_user.create(db_session, obj_in=school_admin_data)
        crud_user.add_user_to_school(db_session, user=school_admin, school=admin_school, role=school_admin_role)
        db_session.commit()

    response = client.post("/auth/login", json={"email": email, "password": "testpass123"})
    body = response.json()
    token = (
        body.get("data", {}).get("token", {}).get("access_token")
        or body.get("token", {}).get("access_token")
        or body.get("access_token")
    )
    assert token, f"Login failed or token missing: {body}"
    return token

@pytest.fixture(scope="function")
def _ensure_admin_school_exists(db_session):
    admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
    if not admin_school:
        admin_school = crud_school.create(db_session, obj_in={"name": ADMIN_SCHOOL_NAME})
        db_session.commit()
        print(f"Created admin school: {admin_school.name}")
    else:
        print(f"Admin school already exists: {admin_school.name}")
    return admin_school

@pytest.fixture(scope="function")
def _ensure_super_admin_role_exists(db_session):
    role = crud_role.get_by_name(db_session, name=RoleEnum.SUPER_ADMIN)
    if not role:
        role = crud_role.create(db_session, obj_in={"name": RoleEnum.SUPER_ADMIN.value})
        db_session.commit()
        print(f"Created super admin role: {role.name}")
    else:
        print(f"Super admin role already exists: {role.name}")
    return role

@pytest.fixture(scope="function")
def _ensure_school_admin_role_exists(db_session):
    role = crud_role.get_by_name(db_session, name=RoleEnum.SCHOOL_ADMIN)
    if not role:
        role = crud_role.create(db_session, obj_in={"name": RoleEnum.SCHOOL_ADMIN.value})
        db_session.commit()
        print(f"Created school admin role: {role.name}")
    else:
        print(f"School admin role already exists: {role.name}")
    return role

@pytest.fixture(scope="function")
def _ensure_teacher_role_exists(db_session):
    role = crud_role.get_by_name(db_session, name=RoleEnum.TEACHER)
    if not role:
        role = crud_role.create(db_session, obj_in={"name": RoleEnum.TEACHER.value})
        db_session.commit()
        print(f"Created teacher role: {role.name}")
    else:
        print(f"Teacher role already exists: {role.name}")
    return role

@pytest.fixture(scope="function")
def _ensure_student_role_exists(db_session):
    role = crud_role.get_by_name(db_session, name=RoleEnum.STUDENT)
    if not role:
        role = crud_role.create(db_session, obj_in={"name": RoleEnum.STUDENT.value})
        db_session.commit()
        print(f"Created student role: {role.name}")
    else:
        print(f"Student role already exists: {role.name}")
    return role


@pytest.fixture
def user_factory(db_session):
    def _user_factory(email, password="testpass123", is_active=False):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        super_admin_role = crud_role.get_by_name(db_session, name=RoleEnum.SUPER_ADMIN)

        user_data = {
            "full_name": "Test User",
            "email": email,
            "hashed_password": get_password_hash(password),
            "is_active": is_active
        }
        test_user = crud_user.create(db_session, obj_in=user_data)
        crud_user.add_user_to_school(db_session, user=test_user, school=admin_school, role=super_admin_role)
        return test_user
    return _user_factory

@pytest.fixture
def token_for_role(client, db_session, _ensure_admin_school_exists):
    """Create tokens for different roles - fixes missing fixture error"""
    admin_school = _ensure_admin_school_exists
    tokens = {}

    def _create_token_for_role(role_name: str):
        if role_name in tokens:
            return tokens[role_name]

        role = crud_role.get_by_name(db_session, name=getattr(RoleEnum, role_name.upper()))
        if not role:
            role = crud_role.create(db_session, obj_in={"name": getattr(RoleEnum, role_name.upper()).value})
            db_session.commit()

        email = f"{role_name}-{uuid.uuid4()}@test.com"
        user_data = {
            "full_name": f"Test {role_name}",
            "email": email,
            "hashed_password": get_password_hash("testpass123"),
            "is_active": True
        }
        user = crud_user.create(db_session, obj_in=user_data)
        crud_user.add_user_to_school(db_session, user=user, school=admin_school, role=role)
        db_session.commit()

        response = client.post("/auth/login", json={"email": email, "password": "testpass123"})
        body = response.json()
        token = (
            body.get("data", {}).get("token", {}).get("access_token")
            or body.get("token", {}).get("access_token")
            or body.get("access_token")
        )
        tokens[role_name] = token
        return token

    return _create_token_for_role
