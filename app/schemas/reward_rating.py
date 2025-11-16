from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class CourseRewardBase(BaseModel):
    enrollment_id: int
    reward_type: str
    reward_title: str
    reward_description: Optional[str] = None
    points: int = 0
    # badge_url: Optional[str] = None
    # certificate_url: Optional[str] = None


class CourseRewardCreate(CourseRewardBase):
    awarded_at: datetime


class CourseRewardUpdate(BaseModel):
    # reward_description: Optional[str] = None
    pass



class CourseReward(CourseRewardBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    awarded_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None


class CourseRatingBase(BaseModel):
    rating: float = Field(..., ge=1.0, le=5.0)
    review: Optional[str] = None


class CourseRatingCreate(CourseRatingBase):
    course_id: int


class CourseRatingUpdate(BaseModel):
    rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    review: Optional[str] = None


class CourseRating(CourseRatingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    course_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class CourseRatingStats(BaseModel):
    average_rating: float
    total_ratings: int
    rating_distribution: dict