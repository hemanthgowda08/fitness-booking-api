
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from time_utils import to_ist


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class FitnessClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    instructor: str = Field(min_length=1, max_length=100)
    date_time: datetime
    total_slots: int = Field(gt=0)

    @field_validator("name", "instructor")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("date_time")
    @classmethod
    def normalise_to_ist(cls, value: datetime) -> datetime:
        return to_ist(value)


class FitnessClassResponse(BaseModel):
    id: int
    name: str
    instructor: str
    date_time: datetime
    total_slots: int
    available_slots: int
    creator_id: Optional[int]
    is_cancelled: bool
    cancelled_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class BookingRequest(BaseModel):
    class_id: int = Field(gt=0)


class BookingResponse(BaseModel):
    id: int
    class_id: int
    user_id: int
    booked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookingListResponse(BookingResponse):
    fitness_class: FitnessClassResponse
