
"""FastAPI application for fitness class scheduling and booking."""

from typing import Callable, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

import models
import schemas
from database import Base, engine, get_db
from migrations import migrate_database
from security import create_access_token, decode_access_token, hash_password, verify_password
from time_utils import now_ist

Base.metadata.create_all(bind=engine)
migrate_database(engine)
app = FastAPI(title="Fitness Studio Booking API", description="Schedule classes and make secure bookings. All class times use Asia/Kolkata.", version="1.0.0")
# The static frontend is served separately in local development. Restrict browser
# access to local origins rather than accepting requests from every website.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme), db: Session = Depends(get_db)) -> models.User:
    """Return the token's user, or a generic authentication error."""
    invalid = HTTPException(status_code=401, detail="Invalid or expired authentication token", headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise invalid
    try:
        user_id = int(decode_access_token(credentials.credentials).get("sub", ""))
        if user_id < 1:
            raise ValueError
    except (JWTError, TypeError, ValueError):
        raise invalid
    user = db.get(models.User, user_id)
    if user is None:
        raise invalid
    return user


def require_roles(*roles: str) -> Callable:
    """Authorize from the current database role, never from a client or JWT claim."""
    def dependency(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action")
        return user
    return dependency


@app.get("/", tags=["status"])
def home():
    return {"message": "Fitness Booking API is running"}


@app.post("/signup", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED, tags=["authentication"])
def signup(user_data: schemas.SignupRequest, db: Session = Depends(get_db)):
    email = str(user_data.email).lower()
    if db.scalar(select(models.User).where(models.User.email == email)):
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = models.User(name=user_data.name, email=email, password_hash=hash_password(user_data.password), role="member")
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered")
    return user


@app.post("/login", response_model=schemas.TokenResponse, tags=["authentication"])
def login(login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.email == str(login_data.email).lower()))
    if user is None or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@app.get("/me", response_model=schemas.UserResponse, tags=["authentication"])
def current_user(user: models.User = Depends(get_current_user)):
    """Return the verified user's current database role for the frontend session."""
    return user


@app.post("/classes", response_model=schemas.FitnessClassResponse, status_code=status.HTTP_201_CREATED, tags=["classes"])
def create_class(class_data: schemas.FitnessClassCreate, db: Session = Depends(get_db), user: models.User = Depends(require_roles("host", "admin"))):
    if class_data.date_time <= now_ist():
        raise HTTPException(status_code=422, detail="Class date_time must be in the future")
    fitness_class = models.FitnessClass(**class_data.model_dump(), available_slots=class_data.total_slots, creator_id=user.id)
    db.add(fitness_class)
    db.commit()
    db.refresh(fitness_class)
    return fitness_class


@app.get("/classes", response_model=list[schemas.FitnessClassResponse], tags=["classes"])
def list_classes(db: Session = Depends(get_db)):
    statement = select(models.FitnessClass).where(models.FitnessClass.date_time > now_ist(), models.FitnessClass.is_cancelled.is_(False)).order_by(models.FitnessClass.date_time)
    return list(db.scalars(statement))


@app.post("/book", response_model=schemas.BookingResponse, status_code=status.HTTP_201_CREATED, tags=["bookings"])
def book_class(booking_data: schemas.BookingRequest, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    fitness_class = db.get(models.FitnessClass, booking_data.class_id)
    if fitness_class is None:
        raise HTTPException(status_code=404, detail="Fitness class not found")
    if fitness_class.is_cancelled:
        raise HTTPException(status_code=409, detail="This class has been cancelled")
    if fitness_class.date_time <= now_ist():
        raise HTTPException(status_code=409, detail="This class has already started")
    if db.scalar(select(models.Booking.id).where(models.Booking.user_id == user.id, models.Booking.class_id == booking_data.class_id)):
        raise HTTPException(status_code=409, detail="You already booked this class")
    try:
        # Atomic conditional update protects slots even with competing SQLite writers.
        result = db.execute(update(models.FitnessClass).where(models.FitnessClass.id == booking_data.class_id, models.FitnessClass.available_slots > 0, models.FitnessClass.is_cancelled.is_(False)).values(available_slots=models.FitnessClass.available_slots - 1))
        if result.rowcount != 1:
            db.rollback()
            db.expire_all()
            latest_class = db.get(models.FitnessClass, booking_data.class_id)
            if latest_class is not None and latest_class.is_cancelled:
                raise HTTPException(status_code=409, detail="This class has been cancelled")
            raise HTTPException(status_code=409, detail="No slots are available")
        booking = models.Booking(user_id=user.id, class_id=booking_data.class_id)
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return booking
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You already booked this class")


@app.get("/bookings", response_model=list[schemas.BookingListResponse], tags=["bookings"])
def list_bookings(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    statement = select(models.Booking).where(models.Booking.user_id == user.id).options(selectinload(models.Booking.fitness_class)).order_by(models.Booking.booked_at.desc())
    return list(db.scalars(statement))


@app.patch("/classes/{class_id}/cancel", response_model=schemas.FitnessClassResponse, tags=["classes"])
def cancel_class(class_id: int, db: Session = Depends(get_db), user: models.User = Depends(require_roles("host", "admin"))):
    """Cancel a class without deleting its reservation history."""
    fitness_class = db.get(models.FitnessClass, class_id)
    if fitness_class is None:
        raise HTTPException(status_code=404, detail="Fitness class not found")
    if fitness_class.is_cancelled:
        raise HTTPException(status_code=409, detail="This class has already been cancelled")
    # Legacy classes have no owner; only an admin can safely administer them.
    if user.role != "admin" and fitness_class.creator_id != user.id:
        raise HTTPException(status_code=403, detail="You can only cancel classes you created")
    fitness_class.is_cancelled = True
    fitness_class.cancelled_at = now_ist()
    db.commit()
    db.refresh(fitness_class)
    return fitness_class
