from sqlalchemy.orm import Session, selectinload
from typing import List

from app.crud.base import CRUDBase
from app.models.exam import Exam
from app.schemas.exam import ExamCreate, ExamUpdate


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


exam = CRUDExam(Exam)