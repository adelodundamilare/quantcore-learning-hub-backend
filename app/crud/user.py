from typing import Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.user import User
from app.models.school import School
from app.models.role import Role
from app.models.user_school_association import user_school_association
from typing import List

from app.schemas.user import UserCreate, UserUpdate

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    def get_user_contexts(self, db: Session, *, user_id: int) -> List[dict]:
        results = (
            db.query(School, Role)
            .join(user_school_association, School.id == user_school_association.c.school_id)
            .join(Role, Role.id == user_school_association.c.role_id)
            .filter(user_school_association.c.user_id == user_id)
            .all()
        )
        return [{"school": school, "role": role} for school, role in results]

    def add_user_to_school(self, db: Session, *, user: User, school: School, role: Role) -> None:
        stmt = user_school_association.insert().values(
            user_id=user.id,
            school_id=school.id,
            role_id=role.id
        )
        db.execute(stmt)

user = CRUDUser(User)