from app.core.constants import RoleEnum
from app.crud.user import user as crud_user
from app.crud.role import role as crud_role

import uuid

class TestAuthEndpoints:
    def test_login_smoke(self, client, super_admin_token, db_session, _ensure_admin_school_exists, _ensure_super_admin_role_exists):
        admin_school = _ensure_admin_school_exists
        super_admin_role = _ensure_super_admin_role_exists
        email = f"test.superadmin.{uuid.uuid4()}@test.com"
        
        from app.core.security import get_password_hash
        from app.models.user import User
        from app.models.user_school_association import UserSchoolAssociation
        
        test_admin = User(
            full_name="Test Super Admin",
            email=email,
            hashed_password=get_password_hash("testpass123"),
            is_active=True
        )
        db_session.add(test_admin)
        db_session.flush()
        
        user_school_assoc = UserSchoolAssociation(
            user_id=test_admin.id,
            school_id=admin_school.id,
            role_id=super_admin_role.id
        )
        db_session.add(user_school_assoc)
        db_session.commit()
        
        response = client.post("/auth/login", json={
            "email": email,
            "password": "testpass123"
        })
        assert 200 <= response.status_code < 300

    def test_logout_smoke(self, client, super_admin_token):
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = client.post("/auth/logout", headers=headers)
        assert 200 <= response.status_code < 300

    def test_request_password_reset_smoke(self, client):
        response = client.post("/auth/forgot-password", json={
            "email": "test@example.com",
            "frontend_base_url": "http://localhost:3000"
        })
        assert 200 <= response.status_code < 300

    def test_verify_account_smoke(self, client, db_session, user_factory):
        test_email = "verify.test@example.com"
        existing_user = crud_user.get_by_email(db_session, email=test_email)
        if not existing_user:
            user_factory(test_email)

        response = client.post("/auth/verify-account", json={
            "email": test_email,
            "code": "123456"
        })
        assert 200 <= response.status_code < 500

    def test_resend_verification_code_smoke(self, client, db_session, user_factory):
        test_email = "resend.test@example.com"
        existing_user = crud_user.get_by_email(db_session, email=test_email)
        if not existing_user:
            user_factory(test_email)

        response = client.post("/auth/resend-verification", json={
            "email": test_email
        })
        assert 200 <= response.status_code < 500

    def test_temp_create_super_admin_and_login(self, client, db_session):
        super_admin_role = crud_role.get_by_name(db_session, name=RoleEnum.SUPER_ADMIN)
        if not super_admin_role:
            super_admin_role = crud_role.create(db_session, obj_in={"name": RoleEnum.SUPER_ADMIN.value})
            db_session.commit()

        super_admin_email = f"temp.superadmin.{uuid.uuid4()}@test.com"
        create_response = client.post(
            "/auth/temp-create-super-admin",
            json={
                "full_name": "Temp Super Admin",
                "email": super_admin_email,
                "password": "testpass123"
            }
        )
        assert 200 <= create_response.status_code < 300

        login_response = client.post(
            "/auth/login",
            json={"email": super_admin_email, "password": "testpass123"}
        )
        assert 200 <= login_response.status_code < 300
        assert "access_token" in login_response.json()["data"]["token"]

class TestSoftDeleteIntegration:
    def test_soft_deleted_user_cannot_login(self, client, db_session, user_factory):
        unique_email = f"deleted-{uuid.uuid4()}@test.com"
        deleted_user = user_factory(unique_email, is_active=True)

        crud_user.delete(db_session, id=deleted_user.id)

        response = client.post("/auth/login", json={
            "email": unique_email,
            "password": "testpass123"
        })
        assert response.status_code == 401

        db_session.rollback()


# class TestAuthWithMultipleContexts:
#     def test_select_context_smoke(self, client, super_admin_token):  # Skipped: requires multiple contexts
#         headers = {"Authorization": f"Bearer {super_admin_token}"}
#         response = client.post("/auth/select-context", json={
#             "school_id": 999,
#             "role_id": 999
#         }, headers=headers)
#         # Would be 403 for users without multiple contexts (normal case)
#         # Only users with multiple school/role associations can select context
#         assert response.status_code in [403, 404] or 200 <= response.status_code < 300
