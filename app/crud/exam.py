from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from sqlalchemy import or_, and_

from app.crud.base import CRUDBase
from app.models.exam import Exam
from app.schemas.exam import ExamCreate, ExamUpdate
from app.core.constants import CourseLevelEnum
from app.models.course import Course
from app.models.curriculum import Curriculum


class CRUDExam(CRUDBase[Exam, ExamCreate, ExamUpdate]):

    def _query_with_relationships(self, db: Session):
        return db.query(Exam).options(
            selectinload(Exam.questions),
            selectinload(Exam.course),
            selectinload(Exam.curriculum)
        )

    def _query_active(self, db: Session):
        return self._query_with_relationships(db).filter(Exam.deleted_at.is_(None))

    def get(self, db: Session, id: int):
        return self._query_active(db).filter(Exam.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[Exam]:
        return (
            self._query_active(db)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_exams_by_course_ids(self, db: Session, course_ids: List[int]) -> List[Exam]:
        if not course_ids:
            return []
        return (
            self._query_active(db)
            .filter(Exam.course_id.in_(course_ids))
            .all()
        )

    def get_exams_by_curriculum_ids(self, db: Session, curriculum_ids: List[int]) -> List[Exam]:
        if not curriculum_ids:
            return []
        return (
            self._query_active(db)
            .filter(Exam.curriculum_id.in_(curriculum_ids))
            .all()
        )

    def get_exams_by_course(self, db: Session, course_id: int, skip: int = 0, limit: int = 100) -> List[Exam]:
        return (
            self._query_active(db)
            .filter(Exam.course_id == course_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_exams_by_curriculum(self, db: Session, curriculum_id: int, skip: int = 0, limit: int = 100) -> List[Exam]:
        return (
            self._query_active(db)
            .filter(Exam.curriculum_id == curriculum_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_multi_filtered(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        level: Optional[CourseLevelEnum] = None,
        course_ids: Optional[List[int]] = None,
        curriculum_ids: Optional[List[int]] = None,
        is_super_admin: bool = False
    ) -> List[Exam]:
        query = self._query_active(db)

        # Apply level filter if provided and not CourseLevelEnum.ALL
        if level and level != CourseLevelEnum.ALL:
            query = query.outerjoin(Course, Exam.course_id == Course.id)\
                         .outerjoin(Curriculum, Exam.curriculum_id == Curriculum.id)

            level_filter_conditions = []
            level_filter_conditions.append(and_(Exam.course_id.isnot(None), Course.level == level))
            level_filter_conditions.append(and_(Exam.curriculum_id.isnot(None), Curriculum.course_id == Course.id, Course.level == level))

            query = query.filter(or_(*level_filter_conditions))

        if not is_super_admin:
            user_access_filter_conditions = []
            if course_ids:
                user_access_filter_conditions.append(Exam.course_id.in_(course_ids))
            if curriculum_ids:
                user_access_filter_conditions.append(Exam.curriculum_id.in_(curriculum_ids))

            if user_access_filter_conditions:
                query = query.filter(or_(*user_access_filter_conditions))
            else:
                return []

        return query.offset(skip).limit(limit).all()

exam = CRUDExam(Exam)