from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class StockCategory(Base):
    __tablename__ = "stock_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False, unique=True)
    
    items = relationship("StockCategoryItem", back_populates="category", cascade="all, delete-orphan")

class StockCategoryItem(Base):
    __tablename__ = "stock_category_items"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    category_id = Column(Integer, ForeignKey("stock_categories.id"), nullable=False)

    category = relationship("StockCategory", back_populates="items")
