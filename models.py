
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from database import Base
from time_utils import IST, now_ist, to_ist


class ISTDateTime(TypeDecorator):
    """Store IST values as SQLite-compatible naive datetimes and restore IST."""
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else to_ist(value).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return None if value is None else value.replace(tzinfo=IST)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'host', 'member')", name="valid_user_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member", server_default="member")
    created_at: Mapped[datetime] = mapped_column(ISTDateTime(), default=now_ist, nullable=False)
    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")
    created_classes: Mapped[list["FitnessClass"]] = relationship(back_populates="creator", foreign_keys="FitnessClass.creator_id")


class FitnessClass(Base):
    __tablename__ = "fitness_classes"
    __table_args__ = (
        CheckConstraint("total_slots > 0", name="positive_total_slots"),
        CheckConstraint("available_slots >= 0 AND available_slots <= total_slots", name="valid_available_slots"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    instructor: Mapped[str] = mapped_column(String(100), nullable=False)
    date_time: Mapped[datetime] = mapped_column(ISTDateTime(), nullable=False, index=True)
    total_slots: Mapped[int] = mapped_column(Integer, nullable=False)
    available_slots: Mapped[int] = mapped_column(Integer, nullable=False)
    creator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(ISTDateTime(), nullable=True)
    bookings: Mapped[list["Booking"]] = relationship(back_populates="fitness_class")
    creator: Mapped[Optional[User]] = relationship(back_populates="created_classes", foreign_keys=[creator_id])


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("fitness_classes.id"), nullable=False, index=True)
    booked_at: Mapped[datetime] = mapped_column(ISTDateTime(), default=now_ist, nullable=False)
    user: Mapped[User] = relationship(back_populates="bookings")
    fitness_class: Mapped[FitnessClass] = relationship(back_populates="bookings")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "class_id",
            name="unique_user_class_booking"
        ),
    )
