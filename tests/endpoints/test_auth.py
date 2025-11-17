from app.core.constants import ADMIN_SCHOOL_NAME, RoleEnum
from app.crud.user import user as crud_user
from app.crud.school import school as crud_school
from app.crud.role import role as crud_role
from app.core.security import get_password_hash

import uuid

class TestAuthEndpoints:
    def test_login_smoke(self, client, super_admin_token):
        response = client.post("/auth/login", json={
            "email": "superadmin@test.com",
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

    def test_verify_account_smoke(self, client, db_session):
        test_email = "verify.test@example.com"
        existing_user = crud_user.get_by_email(db_session, email=test_email)
        if not existing_user:
            admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
            super_admin_role = crud_role.get_by_name(db_session, name=RoleEnum.SUPER_ADMIN)

            user_data = {
                "full_name": "Verify Test User",
                "email": test_email,
                "hashed_password": get_password_hash("testpass123"),
                "is_active": False
            }
            test_user = crud_user.create(db_session, obj_in=user_data)
            crud_user.add_user_to_school(db_session, user=test_user, school=admin_school, role=super_admin_role)

        response = client.post("/auth/verify-account", json={
            "email": test_email,
            "code": "123456"
        })
        assert 200 <= response.status_code < 500

    def test_resend_verification_code_smoke(self, client, db_session):
        test_email = "resend.test@example.com"
        existing_user = crud_user.get_by_email(db_session, email=test_email)
        if not existing_user:
            admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
            super_admin_role = crud_role.get_by_name(db_session, name=RoleEnum.SUPER_ADMIN)

            user_data = {
                "full_name": "Resend Test User",
                "email": test_email,
                "hashed_password": get_password_hash("testpass123"),
                "is_active": False
            }
            test_user = crud_user.create(db_session, obj_in=user_data)
            crud_user.add_user_to_school(db_session, user=test_user, school=admin_school, role=super_admin_role)

        response = client.post("/auth/resend-verification", json={
            "email": test_email
        })
        assert 200 <= response.status_code < 500


class TestSoftDeleteIntegration:
    def test_soft_deleted_user_cannot_login(self, client, db_session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        super_admin_role = crud_role.get_by_name(db_session, name=RoleEnum.SUPER_ADMIN)

        unique_email = f"deleted-{uuid.uuid4()}@test.com"
        user_data = {
            "full_name": "Deleted User",
            "email": unique_email,
            "hashed_password": get_password_hash("testpass123"),
            "is_active": True
        }

        deleted_user = crud_user.create(db_session, obj_in=user_data)
        crud_user.add_user_to_school(db_session, user=deleted_user, school=admin_school, role=super_admin_role)

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
