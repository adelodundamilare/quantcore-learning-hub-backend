from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import Base
from datetime import datetime

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int
    has_next: bool
    has_previous: bool

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        query = db.query(self.model).filter(self.model.id == id)
        if hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)
        return query.first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        query = db.query(self.model)
        if hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)
        return query.offset(skip).limit(limit).all()

    def get_by_email(self, db: Session, email: str) -> Optional[ModelType]:
        query = db.query(self.model).filter(self.model.email == email)
        if hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)
        return query.first()

    def create(self, db: Session, *, obj_in: CreateSchemaType, commit: bool = True) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.flush() # Populate ID
        db.refresh(db_obj) # Refresh to get ID and other defaults
        if commit:
            db.commit()
        return db_obj

    def update(
        self, db: Session, *, db_obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: int) -> ModelType:
        obj = db.query(self.model).get(id)
        if not obj:
            return None

        if hasattr(self.model, 'deleted_at'):
            setattr(obj, 'deleted_at', datetime.utcnow())
            db.add(obj)
            db.commit()
            db.refresh(obj)
        else:
            db.delete(obj)
            db.commit()
        return obj