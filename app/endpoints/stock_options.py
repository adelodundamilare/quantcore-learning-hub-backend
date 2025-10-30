from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.user import UserContext
from app.schemas.stock_options import StockCategorySchema, StockCategoryExtendedSchema
from app.services.stock_options import stock_options_service

router = APIRouter()

@router.get("/options/categories", response_model=APIResponse[List[StockCategorySchema]])
async def get_all_stock_option_categories(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    categories = await stock_options_service.get_all_categories(db)
    return APIResponse(message="Stock option categories retrieved successfully", data=categories)

@router.get("/options/categories/{category_id}", response_model=APIResponse[StockCategoryExtendedSchema])
async def get_stock_option_category(
    category_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    category = await stock_options_service.get_category_by_id(db, category_id=category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock option category not found"
        )
    return APIResponse(message="Stock option category retrieved successfully", data=category)
