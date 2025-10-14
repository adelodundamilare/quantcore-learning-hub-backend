"""Seed default role and permission matrix

Revision ID: e6e38e7662db
Revises: 1a5bb0803204
Create Date: 2025-10-14 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from enum import Enum

# revision identifiers, used by Alembic.
revision = 'e6e38e7662db'
down_revision = 'dd0527c07892'
branch_labels = None
depends_on = None

# Define Enums and default matrix directly in the migration for portability
class RoleEnum(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MEMBER = "member"

class PermissionEnum(str, Enum):
    MANUAL_ONBOARDING = "manual_onboarding"
    APPROVE_SIGNUP = "approve_signup"
    CREATE_COURSE = "create_course"
    DELETE_COURSE = "delete_course"
    SET_EXAMS = "set_exams"
    DELETE_EXAMS = "delete_exams"
    MANUAL_ACTIVATION = "manual_activation"
    VIEW_REVENUE = "view_revenue"
    ADD_REMOVE_MEMBER = "add_remove_member"
    CHANGE_MEMBER_STATUS = "change_member_status"

ROLE_PERMISSIONS = {
    RoleEnum.SUPER_ADMIN: {
        PermissionEnum.MANUAL_ONBOARDING,
        PermissionEnum.APPROVE_SIGNUP,
        PermissionEnum.CREATE_COURSE,
        PermissionEnum.DELETE_COURSE,
        PermissionEnum.SET_EXAMS,
        PermissionEnum.DELETE_EXAMS,
        PermissionEnum.MANUAL_ACTIVATION,
        PermissionEnum.VIEW_REVENUE,
        PermissionEnum.ADD_REMOVE_MEMBER,
        PermissionEnum.CHANGE_MEMBER_STATUS,
    },
    RoleEnum.ADMIN: {
        PermissionEnum.MANUAL_ONBOARDING,
        PermissionEnum.APPROVE_SIGNUP,
        PermissionEnum.CREATE_COURSE,
        PermissionEnum.DELETE_COURSE,
        PermissionEnum.SET_EXAMS,
        PermissionEnum.VIEW_REVENUE,
        PermissionEnum.ADD_REMOVE_MEMBER,
        PermissionEnum.CHANGE_MEMBER_STATUS,
    },
    RoleEnum.MEMBER: {
        PermissionEnum.MANUAL_ONBOARDING,
        PermissionEnum.APPROVE_SIGNUP,
        PermissionEnum.CREATE_COURSE,
        PermissionEnum.SET_EXAMS,
    },
}

def upgrade():
    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)

    # Define table structure for query and insertion
    roles_table = sa.Table('roles', sa.MetaData(), sa.Column('id', sa.Integer, primary_key=True), sa.Column('name', sa.String))
    permissions_table = sa.Table('permissions', sa.MetaData(), sa.Column('id', sa.Integer, primary_key=True), sa.Column('name', sa.String))
    role_permissions_table = sa.Table('role_permissions', sa.MetaData(), sa.Column('role_id', sa.Integer), sa.Column('permission_id', sa.Integer))

    # Seed Roles
    existing_roles = [r[0] for r in session.execute(sa.select(roles_table.c.name)).fetchall()]
    roles_to_add = []
    for role in RoleEnum:
        if role.value not in existing_roles:
            roles_to_add.append({'name': role.value})
    if roles_to_add:
        op.bulk_insert(roles_table, roles_to_add)

    # Seed Permissions
    existing_permissions = [p[0] for p in session.execute(sa.select(permissions_table.c.name)).fetchall()]
    permissions_to_add = []
    for perm in PermissionEnum:
        if perm.value not in existing_permissions:
            permissions_to_add.append({'name': perm.value})
    if permissions_to_add:
        op.bulk_insert(permissions_table, permissions_to_add)

    # --- Map Permissions to Roles ---

    # Get all roles and permissions from DB into a name -> id map
    db_roles = {r.name: r.id for r in session.execute(sa.select(roles_table.c.id, roles_table.c.name)).fetchall()}
    db_permissions = {p.name: p.id for p in session.execute(sa.select(permissions_table.c.id, permissions_table.c.name)).fetchall()}

    # First, clear existing permissions for the roles we are managing to ensure idempotency
    managed_role_ids = [db_roles[role.value] for role in RoleEnum if role.value in db_roles]
    if managed_role_ids:
        op.execute(
            role_permissions_table.delete().where(role_permissions_table.c.role_id.in_(managed_role_ids))
        )

    # Prepare new role-permission mappings
    role_permissions_to_add = []
    for role_enum, perm_enums in ROLE_PERMISSIONS.items():
        role_id = db_roles.get(role_enum.value)
        if role_id:
            for perm_enum in perm_enums:
                perm_id = db_permissions.get(perm_enum.value)
                if perm_id:
                    role_permissions_to_add.append({
                        'role_id': role_id,
                        'permission_id': perm_id
                    })

    # Bulk insert the new mappings
    if role_permissions_to_add:
        op.bulk_insert(role_permissions_table, role_permissions_to_add)

def downgrade():
    # The downgrade path will only remove the associations, not the roles or permissions themselves,
    # as they might be used elsewhere. This is a non-destructive downgrade.
    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)

    roles_table = sa.Table('roles', sa.MetaData(), sa.Column('id', sa.Integer, primary_key=True), sa.Column('name', sa.String))
    role_permissions_table = sa.Table('role_permissions', sa.MetaData(), sa.Column('role_id', sa.Integer), sa.Column('permission_id', sa.Integer))

    db_roles = {r.name: r.id for r in session.execute(sa.select(roles_table.c.id, roles_table.c.name)).fetchall()}
    managed_role_ids = [db_roles[role.value] for role in RoleEnum if role.value in db_roles]

    if managed_role_ids:
        op.execute(
            role_permissions_table.delete().where(role_permissions_table.c.role_id.in_(managed_role_ids))
        )