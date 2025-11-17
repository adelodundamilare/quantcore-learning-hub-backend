import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
import main
from fastapi.testclient import TestClient
from app.crud.user import user as crud_user
from app.core.security import get_password_hash
from app.models.user import User
from app.models.school import School
from app.core.constants import ADMIN_SCHOOL_NAME, RoleEnum
from app.crud.school import school as crud_school
from app.crud.role import role as crud_role
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

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as test_client:
        yield test_client

@pytest.fixture
def super_admin_token(client, db_session):
    admin_school = _ensure_admin_school_exists(db_session)
    super_admin_role = _ensure_super_admin_role_exists(db_session)
    email = "superadmin@test.com"

    super_admin = crud_user.get_by_email(db_session, email=email)
    if not super_admin:
        super_admin_data = {
            "full_name": "Test Super Admin",
            "email": email,
            "hashed_password": get_password_hash("testpass123"),
            "is_active": True
        }
        super_admin = crud_user.create(db_session, obj_in=super_admin_data)
        crud_user.add_user_to_school(db_session, user=super_admin, school=admin_school, role=super_admin_role)

    response = client.post("/auth/login", json={"email": email, "password": "testpass123"})
    return response.json()["data"]["token"]["access_token"]

@pytest.fixture
def school_admin_token(client, db_session):
    admin_school = _ensure_admin_school_exists(db_session)
    school_admin_role = _ensure_school_admin_role_exists(db_session)
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

    response = client.post("/auth/login", json={"email": email, "password": "testpass123"})
    return response.json()["data"]["token"]["access_token"]

def _ensure_admin_school_exists(db):
    admin_school = crud_school.get_by_name(db, name=ADMIN_SCHOOL_NAME)
    if not admin_school:
        admin_school = crud_school.create(db, obj_in={"name": ADMIN_SCHOOL_NAME})
    return admin_school

def _ensure_super_admin_role_exists(db):
    role = crud_role.get_by_name(db, name=RoleEnum.SUPER_ADMIN)
    if not role:
        role = crud_role.create(db, obj_in={"name": RoleEnum.SUPER_ADMIN.value})
    return role

def _ensure_school_admin_role_exists(db):
    role = crud_role.get_by_name(db, name=RoleEnum.SCHOOL_ADMIN)
    if not role:
        role = crud_role.create(db, obj_in={"name": RoleEnum.SCHOOL_ADMIN.value})
    return role
