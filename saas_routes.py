# ==========================================
# STAYEASE - MULTI-TENANT SAAS ROUTER
# Dedicated B2B APIs for Hotel Owners and Staff
# ==========================================

import os
import uuid
from datetime import date, datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from pwdlib import PasswordHash
from jose import jwt, JWTError

from database.database import get_db
from database.models import (
    Hotel, User, Room, Guest, Reservation, Payment, Housekeeping, Maintenance
)

# Shared security settings
password_hash = PasswordHash.recommended()
SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-key-set-secret-key-in-production-env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
security = HTTPBearer()

saas_router = APIRouter(tags=["StayEase SaaS Platform"])


# ==========================================
# 1. PYDANTIC SCHEMAS
# ==========================================

class OwnerRegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str = Field(default="", max_length=50)
    password: str = Field(min_length=8)
    confirm_password: str
    hotel_name: str = Field(min_length=2, max_length=150)
    address: str = Field(default="", max_length=255)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=100)
    country: str = Field(default="India", max_length=100)
    contact_number: str = Field(default="", max_length=50)
    hotel_email: str = Field(default="", max_length=120)
    total_rooms: int = Field(default=10, ge=1, le=5000)
    hotel_category: str = Field(default="Boutique", max_length=50)


class UnifiedLoginRequest(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str


class GuestCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=5, max_length=50)
    email: str = ""
    address: str = ""
    id_proof_type: str = "Government ID"
    id_proof_number: str = ""


class GuestUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    id_proof_type: Optional[str] = None
    id_proof_number: Optional[str] = None


class FrontDeskReservationCreateRequest(BaseModel):
    # If guest_id is provided, link to existing guest; otherwise create guest inline
    guest_id: Optional[int] = None
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    guest_email: Optional[str] = ""
    guest_id_proof_type: Optional[str] = "Government ID"
    guest_id_proof_number: Optional[str] = ""
    guest_address: Optional[str] = ""

    room_id: int
    check_in: date
    check_out: date
    number_of_guests: int = Field(default=1, ge=1, le=20)
    booking_source: str = Field(default="Walk-in", description="Walk-in, Phone, Direct, Corporate")
    payment_method: str = Field(default="Cash", description="Cash, Credit Card, Debit Card, UPI, Bank Transfer")
    payment_status: str = Field(default="Completed", description="Completed, Pending")
    special_requests: str = ""


class ReservationStatusUpdateRequest(BaseModel):
    status: str = Field(description="Confirmed, Checked In, Checked Out, Cancelled")


class StaffAccountCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str = ""
    role: str = Field(default="receptionist", description="manager, receptionist, housekeeping, accountant, maintenance")
    designation: str = ""
    department: str = ""
    password: str = Field(default="staff123", min_length=6)


class StaffAccountUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None
    status: Optional[str] = None
    password: Optional[str] = None


class StaffResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=6)


class HousekeepingTaskUpdateRequest(BaseModel):
    cleaning_status: str = Field(description="Clean, Dirty, In Progress, Inspection Needed")
    notes: str = ""
    assigned_staff_id: Optional[int] = None


class MaintenanceTicketCreateRequest(BaseModel):
    room_id: int
    issue_description: str = Field(min_length=3)
    priority: str = Field(default="Medium", description="Low, Medium, High, Urgent")


class MaintenanceTicketUpdateRequest(BaseModel):
    status: str = Field(description="Reported, In Progress, Resolved")
    notes: str = ""


class RecordPaymentRequest(BaseModel):
    reservation_id: int
    amount: float = Field(gt=0)
    payment_method: str = Field(default="Cash", description="Cash, Credit Card, Debit Card, UPI, Bank Transfer")
    payment_status: str = Field(default="Completed", description="Completed, Pending")


class SaaSHotelSettingsUpdateRequest(BaseModel):
    hotel_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    contact_number: Optional[str] = None
    hotel_email: Optional[str] = None
    hotel_category: Optional[str] = None
    total_rooms: Optional[int] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    cancellation_policy: Optional[str] = None


# ==========================================
# 2. AUTHENTICATION & MULTI-TENANT HELPERS
# ==========================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Extract and verify user identity and hotel association from JWT token."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is missing user identity."
            )
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists."
        )
    if not user.is_active or user.status == "Inactive":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact your hotel owner."
        )

    return user


def require_roles(*allowed_roles: str):
    """Factory dependency for role-based access control. Owners & Admins have super-access."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role in ["owner", "admin"] or current_user.role in allowed_roles:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied for role '{current_user.role}'. Required one of: {list(allowed_roles)}"
        )
    return role_checker


# ==========================================
# 3. HOTEL OWNER REGISTRATION & UNIFIED LOGIN
# ==========================================

@saas_router.post("/auth/register-owner", status_code=status.HTTP_201_CREATED)
def register_hotel_owner(data: OwnerRegisterRequest, db: Session = Depends(get_db)):
    """
    Dedicated registration endpoint for Hotel Owners.
    Creates the Hotel tenant, creates the Owner User, links them,
    and returns an authenticated session with JWT token.
    """
    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password and confirmation password do not match."
        )

    existing_user = db.query(User).filter(User.email == data.email.lower().strip()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # 1. Create Hotel
    new_hotel = Hotel(
        hotel_name=data.hotel_name.strip(),
        address=data.address.strip(),
        city=data.city.strip(),
        state=data.state.strip(),
        country=data.country.strip(),
        contact_number=data.contact_number.strip() or data.phone.strip(),
        hotel_email=data.hotel_email.strip() or data.email.lower().strip(),
        total_rooms=data.total_rooms,
        hotel_category=data.hotel_category.strip()
    )
    db.add(new_hotel)
    db.flush()

    # 2. Create Owner User
    hashed_pwd = password_hash.hash(data.password)
    owner_user = User(
        full_name=data.full_name.strip(),
        email=data.email.lower().strip(),
        phone=data.phone.strip(),
        hashed_password=hashed_pwd,
        role="owner",
        designation="Hotel Owner",
        department="Executive Management",
        hotel_id=new_hotel.id,
        is_active=True,
        status="Active"
    )
    db.add(owner_user)
    db.flush()

    new_hotel.owner_id = owner_user.id

    # 3. Auto-seed standard starter rooms for the new hotel
    starter_rooms = [
        Room(
            hotel_id=new_hotel.id,
            room_number="101",
            room_type="Standard",
            price=1800.0,
            capacity=2,
            description="Cozy starter room with queen bed, high-speed WiFi, work desk, and en-suite bath.",
            image_url="https://images.unsplash.com/photo-1616594039964-ae9021a400a0?w=700",
            operational_status="Available",
            housekeeping_status="Clean"
        ),
        Room(
            hotel_id=new_hotel.id,
            room_number="201",
            room_type="Deluxe",
            price=3200.0,
            capacity=3,
            description="Spacious deluxe room with king bed, balcony, mini-bar, and city view.",
            image_url="https://images.unsplash.com/photo-1590490360182-c33d955571d7?w=700",
            operational_status="Available",
            housekeeping_status="Clean"
        ),
        Room(
            hotel_id=new_hotel.id,
            room_number="301",
            room_type="Suite",
            price=5500.0,
            capacity=4,
            description="Executive luxury suite with separated living room, jacuzzi tub, and skyline view.",
            image_url="https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=700",
            operational_status="Available",
            housekeeping_status="Clean"
        )
    ]
    db.add_all(starter_rooms)
    db.commit()
    db.refresh(owner_user)
    db.refresh(new_hotel)

    # 4. Generate JWT
    now = datetime.now(timezone.utc)
    token_payload = {
        "sub": str(owner_user.id),
        "email": owner_user.email,
        "role": owner_user.role,
        "name": owner_user.full_name,
        "hotel_id": new_hotel.id,
        "iat": now,
        "exp": now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    }
    access_token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "message": "Hotel and Owner account registered successfully.",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": owner_user.id,
            "name": owner_user.full_name,
            "email": owner_user.email,
            "phone": owner_user.phone,
            "role": owner_user.role,
            "designation": owner_user.designation,
            "hotel_id": new_hotel.id
        },
        "hotel": {
            "id": new_hotel.id,
            "hotel_name": new_hotel.hotel_name,
            "hotel_category": new_hotel.hotel_category,
            "city": new_hotel.city
        }
    }


@saas_router.post("/auth/login")
def unified_login(data: UnifiedLoginRequest, db: Session = Depends(get_db)):
    """
    Unified Login for Hotel Owners and Staff.
    Validates credentials, retrieves role and tenant hotel, and generates JWT.
    """
    email = data.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    if not user or not user.hashed_password or not password_hash.verify(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password."
        )

    if not user.is_active or user.status == "Inactive":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Please contact your hotel owner or administrator."
        )

    # Ensure user has a valid hotel_id
    hotel_id = user.hotel_id or 1
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()

    now = datetime.now(timezone.utc)
    token_payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "name": user.full_name,
        "hotel_id": hotel_id,
        "iat": now,
        "exp": now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    }
    access_token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "message": "Login successful.",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "designation": user.designation,
            "department": user.department,
            "hotel_id": hotel_id
        },
        "hotel": {
            "id": hotel.id if hotel else hotel_id,
            "hotel_name": hotel.hotel_name if hotel else "StayEase Hotel",
            "category": hotel.hotel_category if hotel else "Boutique",
            "city": hotel.city if hotel else ""
        } if hotel else None
    }


@saas_router.get("/api/me")
def get_current_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve session details for the authenticated user and hotel tenant."""
    hotel = db.query(Hotel).filter(Hotel.id == (current_user.hotel_id or 1)).first()
    return {
        "user": {
            "id": current_user.id,
            "name": current_user.full_name,
            "email": current_user.email,
            "phone": current_user.phone,
            "role": current_user.role,
            "designation": current_user.designation,
            "department": current_user.department,
            "status": current_user.status,
            "hotel_id": current_user.hotel_id
        },
        "hotel": {
            "id": hotel.id if hotel else None,
            "hotel_name": hotel.hotel_name if hotel else "StayEase Hotel",
            "address": hotel.address if hotel else "",
            "city": hotel.city if hotel else "",
            "state": hotel.state if hotel else "",
            "contact_number": hotel.contact_number if hotel else "",
            "hotel_email": hotel.hotel_email if hotel else "",
            "hotel_category": hotel.hotel_category if hotel else "Boutique",
            "check_in_time": hotel.check_in_time if hotel else "14:00",
            "check_out_time": hotel.check_out_time if hotel else "11:00",
            "cancellation_policy": hotel.cancellation_policy if hotel else ""
        } if hotel else None
    }


# ==========================================
# 4. MULTI-TENANT DASHBOARD OVERVIEW METRICS
# ==========================================

@saas_router.get("/api/dashboard")
def get_hotel_dashboard_metrics(
    current_user: User = Depends(require_roles("owner", "manager", "receptionist", "accountant")),
    db: Session = Depends(get_db)
):
    """
    Consolidated KPI metrics strictly scoped to current_user.hotel_id.
    Never exposes or mixes data from other hotel tenants.
    """
    hotel_id = current_user.hotel_id or 1
    today = date.today()

    # 1. Room Metrics
    rooms = db.query(Room).filter(Room.hotel_id == hotel_id).all()
    total_rooms = len(rooms)

    # Active reservations occupying rooms today
    occupied_by_res = db.query(Reservation.room_id).filter(
        Reservation.hotel_id == hotel_id,
        Reservation.status.in_(["Confirmed", "Checked In"]),
        Reservation.check_in <= today,
        Reservation.check_out > today
    ).distinct().all()
    occupied_room_ids = {r[0] for r in occupied_by_res}

    # Add explicitly marked rooms
    for r in rooms:
        if r.operational_status == "Occupied":
            occupied_room_ids.add(r.id)

    occupied_count = len(occupied_room_ids)
    maintenance_count = sum(1 for r in rooms if r.operational_status == "Maintenance")
    available_count = max(0, total_rooms - occupied_count - maintenance_count)

    # Housekeeping stats
    clean_count = sum(1 for r in rooms if r.housekeeping_status == "Clean")
    dirty_count = sum(1 for r in rooms if r.housekeeping_status == "Dirty")
    in_progress_count = sum(1 for r in rooms if r.housekeeping_status == "In Progress")

    # 2. Reservation Metrics
    reservations = db.query(Reservation).filter(Reservation.hotel_id == hotel_id).all()
    total_reservations = len(reservations)
    confirmed_count = sum(1 for res in reservations if res.status == "Confirmed")
    checked_in_count = sum(1 for res in reservations if res.status == "Checked In")
    checked_out_count = sum(1 for res in reservations if res.status == "Checked Out")
    cancelled_count = sum(1 for res in reservations if res.status == "Cancelled")

    today_checkins = sum(1 for res in reservations if res.check_in == today and res.status in ["Confirmed", "Checked In"])
    today_checkouts = sum(1 for res in reservations if res.check_out == today and res.status in ["Confirmed", "Checked In"])

    # 3. Guests & Staff
    total_guests = db.query(Guest).filter(Guest.hotel_id == hotel_id).count()
    staff_roles = ["staff", "manager", "receptionist", "housekeeping", "accountant", "maintenance"]
    total_staff = db.query(User).filter(User.hotel_id == hotel_id, User.role.in_(staff_roles)).count()
    active_staff = db.query(User).filter(User.hotel_id == hotel_id, User.is_active == True, User.role.in_(staff_roles)).count()

    # 4. Revenue & Payments
    completed_payments = db.query(Payment).filter(
        Payment.hotel_id == hotel_id,
        Payment.payment_status == "Completed"
    ).all()
    total_revenue = sum(p.amount for p in completed_payments)

    # 5. Maintenance Tickets
    tickets = db.query(Maintenance).filter(Maintenance.hotel_id == hotel_id).all()
    pending_tickets = sum(1 for t in tickets if t.status in ["Reported", "In Progress"])
    urgent_tickets = sum(1 for t in tickets if t.priority == "Urgent" and t.status != "Resolved")

    # 6. Recent Reservations
    recent_res = db.query(Reservation).filter(
        Reservation.hotel_id == hotel_id
    ).order_by(Reservation.id.desc()).limit(5).all()

    recent_list = []
    for r in recent_res:
        g = r.guest
        rm = r.room
        recent_list.append({
            "id": r.id,
            "reference": f"SE-RES-{r.id:04d}",
            "guest_name": g.full_name if g else "Guest",
            "room_number": rm.room_number if rm else "N/A",
            "room_type": rm.room_type if rm else "Room",
            "check_in": str(r.check_in),
            "check_out": str(r.check_out),
            "total_amount": r.total_amount,
            "status": r.status,
            "booking_source": r.booking_source
        })

    occupancy_rate = round((occupied_count / total_rooms * 100), 1) if total_rooms > 0 else 0.0

    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()

    return {
        "hotel_name": hotel.hotel_name if hotel else "StayEase Hotel",
        "total_rooms": total_rooms,
        "available_rooms": available_count,
        "occupied_rooms": occupied_count,
        "maintenance_rooms": maintenance_count,
        "occupancy_rate": occupancy_rate,
        "total_guests": total_guests,
        "total_reservations": total_reservations,
        "confirmed_reservations": confirmed_count,
        "checked_in_reservations": checked_in_count,
        "checked_out_reservations": checked_out_count,
        "cancelled_reservations": cancelled_count,
        "today_checkins": today_checkins,
        "today_checkouts": today_checkouts,
        "total_revenue": round(float(total_revenue), 2),
        "total_staff": total_staff,
        "active_staff": active_staff,
        "clean_rooms": clean_count,
        "dirty_rooms": dirty_count,
        "in_progress_rooms": in_progress_count,
        "pending_tickets": pending_tickets,
        "urgent_tickets": urgent_tickets,
        "recent_reservations": recent_list
    }


# ==========================================
# 5. MULTI-TENANT ROOM MANAGEMENT APIs
# ==========================================

class SaaSCreateRoomRequest(BaseModel):
    room_number: str = Field(min_length=1, max_length=20)
    room_type: str = Field(min_length=1, max_length=50)
    price: float = Field(gt=0)
    capacity: int = Field(gt=0, le=20)
    description: str = ""
    image_url: str = ""
    operational_status: str = "Available"
    housekeeping_status: str = "Clean"


class SaaSUpdateRoomRequest(BaseModel):
    room_number: Optional[str] = None
    room_type: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    capacity: Optional[int] = Field(default=None, gt=0, le=20)
    description: Optional[str] = None
    image_url: Optional[str] = None
    operational_status: Optional[str] = None
    housekeeping_status: Optional[str] = None


@saas_router.get("/api/rooms")
def list_hotel_rooms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all rooms belonging strictly to current_user.hotel_id."""
    hotel_id = current_user.hotel_id or 1
    rooms = db.query(Room).filter(Room.hotel_id == hotel_id).order_by(Room.room_number.asc()).all()

    return [
        {
            "id": r.id,
            "room_number": r.room_number,
            "room_type": r.room_type,
            "price": r.price,
            "capacity": r.capacity,
            "description": r.description or "",
            "image_url": r.image_url or "",
            "operational_status": r.operational_status or r.status or "Available",
            "status": r.operational_status or r.status or "Available",
            "housekeeping_status": r.housekeeping_status or "Clean",
            "last_cleaned": r.last_cleaned.isoformat() if r.last_cleaned else None
        }
        for r in rooms
    ]


@saas_router.post("/api/rooms", status_code=status.HTTP_201_CREATED)
def create_hotel_room(
    data: SaaSCreateRoomRequest,
    current_user: User = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db)
):
    """Add a new room scoped to current_user.hotel_id."""
    hotel_id = current_user.hotel_id or 1

    # Check for duplicate room number in this hotel
    existing = db.query(Room).filter(
        Room.hotel_id == hotel_id,
        Room.room_number == data.room_number.strip()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room number '{data.room_number}' already exists in your hotel."
        )

    new_room = Room(
        hotel_id=hotel_id,
        room_number=data.room_number.strip(),
        room_type=data.room_type.strip(),
        price=data.price,
        capacity=data.capacity,
        description=data.description.strip(),
        image_url=data.image_url.strip() or "https://images.unsplash.com/photo-1590490360182-c33d955571d7?w=700",
        operational_status=data.operational_status,
        status=data.operational_status,
        housekeeping_status=data.housekeeping_status
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    return {
        "message": f"Room {new_room.room_number} created successfully.",
        "room": {
            "id": new_room.id,
            "room_number": new_room.room_number,
            "room_type": new_room.room_type,
            "price": new_room.price,
            "capacity": new_room.capacity,
            "operational_status": new_room.operational_status,
            "housekeeping_status": new_room.housekeeping_status
        }
    }


@saas_router.put("/api/rooms/{room_id}")
def update_hotel_room(
    room_id: int,
    data: SaaSUpdateRoomRequest,
    current_user: User = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db)
):
    """Update room details scoped to current_user.hotel_id."""
    hotel_id = current_user.hotel_id or 1
    room = db.query(Room).filter(Room.id == room_id, Room.hotel_id == hotel_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found in your hotel."
        )

    if data.room_number is not None:
        duplicate = db.query(Room).filter(
            Room.hotel_id == hotel_id,
            Room.room_number == data.room_number.strip(),
            Room.id != room_id
        ).first()
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room number '{data.room_number}' is already assigned to another room."
            )
        room.room_number = data.room_number.strip()

    if data.room_type is not None:
        room.room_type = data.room_type.strip()
    if data.price is not None:
        room.price = data.price
    if data.capacity is not None:
        room.capacity = data.capacity
    if data.description is not None:
        room.description = data.description.strip()
    if data.image_url is not None:
        room.image_url = data.image_url.strip()
    if data.operational_status is not None:
        room.operational_status = data.operational_status
        room.status = data.operational_status
    if data.housekeeping_status is not None:
        room.housekeeping_status = data.housekeeping_status
        if data.housekeeping_status == "Clean":
            room.last_cleaned = datetime.now(timezone.utc)

    db.commit()
    db.refresh(room)

    return {
        "message": f"Room {room.room_number} updated successfully.",
        "room": {
            "id": room.id,
            "room_number": room.room_number,
            "room_type": room.room_type,
            "price": room.price,
            "capacity": room.capacity,
            "operational_status": room.operational_status,
            "housekeeping_status": room.housekeeping_status
        }
    }


@saas_router.delete("/api/rooms/{room_id}")
def delete_hotel_room(
    room_id: int,
    current_user: User = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db)
):
    """Safely delete a room if it has no active reservations."""
    hotel_id = current_user.hotel_id or 1
    room = db.query(Room).filter(Room.id == room_id, Room.hotel_id == hotel_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found in your hotel."
        )

    # Check for active reservations
    active_res = db.query(Reservation).filter(
        Reservation.room_id == room_id,
        Reservation.status.in_(["Confirmed", "Checked In"])
    ).first()
    if active_res:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete Room {room.room_number} because it has active reservations."
        )

    db.delete(room)
    db.commit()
    return {"message": f"Room {room.room_number} deleted successfully."}


# ==========================================
# 6. GUEST DIRECTORY (STAFF OPERATIONAL RECORDS)
# ==========================================

@saas_router.get("/api/guests")
def list_hotel_guests(
    search: Optional[str] = None,
    current_user: User = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db)
):
    """List registered hotel guests for current_user.hotel_id."""
    hotel_id = current_user.hotel_id or 1
    query = db.query(Guest).filter(Guest.hotel_id == hotel_id)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Guest.full_name.ilike(s),
                Guest.phone.ilike(s),
                Guest.email.ilike(s),
                Guest.id_proof_number.ilike(s)
            )
        )

    guests = query.order_by(Guest.id.desc()).all()
    result = []
    for g in guests:
        res_count = db.query(Reservation).filter(Reservation.guest_id == g.id).count()
        result.append({
            "id": g.id,
            "full_name": g.full_name,
            "phone": g.phone,
            "email": g.email or "",
            "address": g.address or "",
            "id_proof_type": g.id_proof_type,
            "id_proof_number": g.id_proof_number,
            "total_reservations": res_count,
            "created_at": g.created_at.isoformat() if g.created_at else None
        })

    return result


@saas_router.post("/api/guests", status_code=status.HTTP_201_CREATED)
def create_hotel_guest(
    data: GuestCreateRequest,
    current_user: User = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db)
):
    """Add a new guest record to the hotel's operational directory."""
    hotel_id = current_user.hotel_id or 1

    new_guest = Guest(
        hotel_id=hotel_id,
        full_name=data.full_name.strip(),
        phone=data.phone.strip(),
        email=data.email.lower().strip() if data.email else "",
        address=data.address.strip(),
        id_proof_type=data.id_proof_type.strip(),
        id_proof_number=data.id_proof_number.strip()
    )
    db.add(new_guest)
    db.commit()
    db.refresh(new_guest)

    return {
        "message": f"Guest '{new_guest.full_name}' added to directory.",
        "guest": {
            "id": new_guest.id,
            "full_name": new_guest.full_name,
            "phone": new_guest.phone,
            "email": new_guest.email
        }
    }


@saas_router.get("/api/guests/{guest_id}")
def get_guest_profile(
    guest_id: int,
    current_user: User = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db)
):
    """View guest profile and their complete reservation history in this hotel."""
    hotel_id = current_user.hotel_id or 1
    guest = db.query(Guest).filter(Guest.id == guest_id, Guest.hotel_id == hotel_id).first()
    if not guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest record not found.")

    reservations = db.query(Reservation).filter(
        Reservation.guest_id == guest.id,
        Reservation.hotel_id == hotel_id
    ).order_by(Reservation.id.desc()).all()

    res_history = []
    total_spent = 0.0
    for r in reservations:
        p = db.query(Payment).filter(Payment.reservation_id == r.id, Payment.payment_status == "Completed").first()
        if p:
            total_spent += p.amount
        rm = r.room
        res_history.append({
            "id": r.id,
            "reference": f"SE-RES-{r.id:04d}",
            "room_number": rm.room_number if rm else "N/A",
            "room_type": rm.room_type if rm else "Room",
            "check_in": str(r.check_in),
            "check_out": str(r.check_out),
            "total_amount": r.total_amount,
            "status": r.status,
            "booking_source": r.booking_source
        })

    return {
        "id": guest.id,
        "full_name": guest.full_name,
        "phone": guest.phone,
        "email": guest.email,
        "address": guest.address,
        "id_proof_type": guest.id_proof_type,
        "id_proof_number": guest.id_proof_number,
        "total_spent": round(total_spent, 2),
        "reservations": res_history
    }


@saas_router.put("/api/guests/{guest_id}")
def update_guest_profile(
    guest_id: int,
    data: GuestUpdateRequest,
    current_user: User = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db)
):
    """Update guest profile information."""
    hotel_id = current_user.hotel_id or 1
    guest = db.query(Guest).filter(Guest.id == guest_id, Guest.hotel_id == hotel_id).first()
    if not guest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest record not found.")

    if data.full_name is not None:
        guest.full_name = data.full_name.strip()
    if data.phone is not None:
        guest.phone = data.phone.strip()
    if data.email is not None:
        guest.email = data.email.lower().strip()
    if data.address is not None:
        guest.address = data.address.strip()
    if data.id_proof_type is not None:
        guest.id_proof_type = data.id_proof_type.strip()
    if data.id_proof_number is not None:
        guest.id_proof_number = data.id_proof_number.strip()

    db.commit()
    db.refresh(guest)
    return {"message": "Guest profile updated successfully.", "guest": {"id": guest.id, "full_name": guest.full_name}}


# ==========================================
# 7. FRONT DESK & RESERVATIONS WORKFLOW
# ==========================================

@saas_router.get("/api/reservations")
def list_hotel_reservations(
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_roles("owner", "manager", "receptionist", "accountant")),
    db: Session = Depends(get_db)
):
    """List reservations scoped to current_user.hotel_id with search & status filters."""
    hotel_id = current_user.hotel_id or 1
    query = db.query(Reservation).filter(Reservation.hotel_id == hotel_id)

    if status_filter and status_filter.lower() != "all":
        query = query.filter(Reservation.status == status_filter)

    reservations = query.order_by(Reservation.id.desc()).all()
    results = []

    for r in reservations:
        g = r.guest
        rm = r.room
        p = db.query(Payment).filter(Payment.reservation_id == r.id).order_by(Payment.id.desc()).first()

        # Apply search if provided
        if search:
            s = search.lower().strip()
            g_name = (g.full_name if g else "").lower()
            ref = f"se-res-{r.id:04d}"
            rm_no = (rm.room_number if rm else "").lower()
            if s not in g_name and s not in ref and s not in rm_no:
                continue

        results.append({
            "id": r.id,
            "reference": f"SE-RES-{r.id:04d}",
            "guest": {
                "id": g.id if g else None,
                "name": g.full_name if g else "Guest",
                "phone": g.phone if g else "",
                "email": g.email if g else ""
            },
            "room": {
                "id": rm.id if rm else None,
                "room_number": rm.room_number if rm else "N/A",
                "room_type": rm.room_type if rm else "Room"
            },
            "check_in": str(r.check_in),
            "check_out": str(r.check_out),
            "number_of_guests": r.number_of_guests,
            "total_amount": r.total_amount,
            "booking_source": r.booking_source,
            "status": r.status,
            "payment_status": p.payment_status if p else "Unpaid",
            "payment_method": p.payment_method if p else "N/A",
            "created_at": r.created_at.isoformat() if r.created_at else None
        })

    return results


@saas_router.post("/api/reservations", status_code=status.HTTP_201_CREATED)
def create_front_desk_reservation(
    data: FrontDeskReservationCreateRequest,
    current_user: User = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db)
):
    """
    Create a new front-desk reservation (walk-in, phone, corporate).
    Resolves or creates the Guest record, verifies room availability,
    computes pricing, creates the reservation, and optionally records payment.
    """
    hotel_id = current_user.hotel_id or 1

    # 1. Validate dates
    today = date.today()
    if data.check_in < today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-in date cannot be in the past."
        )
    if data.check_out <= data.check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-out date must be strictly after check-in date."
        )

    # 2. Verify Room belongs to this hotel
    room = db.query(Room).filter(Room.id == data.room_id, Room.hotel_id == hotel_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found in this hotel."
        )

    # 3. Check for overlapping reservations
    conflict = db.query(Reservation).filter(
        Reservation.room_id == room.id,
        Reservation.hotel_id == hotel_id,
        Reservation.status.in_(["Confirmed", "Checked In"]),
        Reservation.check_in < data.check_out,
        Reservation.check_out > data.check_in
    ).first()
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Room {room.room_number} is already booked from {conflict.check_in} to {conflict.check_out}."
        )

    # 4. Resolve or Create Guest
    if data.guest_id:
        guest = db.query(Guest).filter(Guest.id == data.guest_id, Guest.hotel_id == hotel_id).first()
        if not guest:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified guest not found.")
    else:
        if not data.guest_name or not data.guest_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Guest full name and phone number are required for new reservations."
            )
        guest = Guest(
            hotel_id=hotel_id,
            full_name=data.guest_name.strip(),
            phone=data.guest_phone.strip(),
            email=data.guest_email.strip() if data.guest_email else "",
            address=data.guest_address.strip() if data.guest_address else "",
            id_proof_type=data.guest_id_proof_type or "Government ID",
            id_proof_number=data.guest_id_proof_number or ""
        )
        db.add(guest)
        db.flush()

    # 5. Calculate total
    nights = (data.check_out - data.check_in).days
    total_amount = round(room.price * nights, 2)

    # 6. Create Reservation
    new_res = Reservation(
        hotel_id=hotel_id,
        guest_id=guest.id,
        room_id=room.id,
        check_in=data.check_in,
        check_out=data.check_out,
        number_of_guests=data.number_of_guests,
        total_amount=total_amount,
        booking_source=data.booking_source or "Walk-in",
        status="Confirmed" if data.check_in > today else "Checked In",
        special_requests=data.special_requests or ""
    )
    db.add(new_res)
    db.flush()

    # If checking in today, mark room as Occupied
    if new_res.status == "Checked In":
        room.operational_status = "Occupied"
        room.status = "Occupied"

    # 7. Record payment if marked as completed
    tx_ref = f"TXN-{uuid.uuid4().hex[:10].upper()}"
    payment = Payment(
        hotel_id=hotel_id,
        reservation_id=new_res.id,
        amount=total_amount,
        payment_method=data.payment_method,
        payment_status=data.payment_status,
        transaction_reference=tx_ref
    )
    db.add(payment)

    db.commit()
    db.refresh(new_res)

    return {
        "message": f"Reservation created successfully for Room {room.room_number}.",
        "reservation_id": new_res.id,
        "reference": f"SE-RES-{new_res.id:04d}",
        "guest_name": guest.full_name,
        "room_number": room.room_number,
        "nights": nights,
        "total_amount": total_amount,
        "status": new_res.status,
        "transaction_ref": tx_ref
    }


@saas_router.put("/api/reservations/{reservation_id}/status")
def update_reservation_status(
    reservation_id: int,
    data: ReservationStatusUpdateRequest,
    current_user: User = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db)
):
    """
    Update reservation status: Confirmed, Checked In, Checked Out, Cancelled.
    Synchronizes room operational status and triggers housekeeping upon check-out.
    """
    hotel_id = current_user.hotel_id or 1
    res = db.query(Reservation).filter(Reservation.id == reservation_id, Reservation.hotel_id == hotel_id).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")

    new_status = data.status
    old_status = res.status
    res.status = new_status
    room = res.room

    if room:
        if new_status == "Checked In":
            room.operational_status = "Occupied"
            room.status = "Occupied"
        elif new_status == "Checked Out":
            room.operational_status = "Available"
            room.status = "Available"
            room.housekeeping_status = "Dirty"
            # Create housekeeping task
            hk_task = Housekeeping(
                hotel_id=hotel_id,
                room_id=room.id,
                cleaning_status="Dirty",
                notes=f"Auto-generated on guest check-out (Reservation #{res.id})"
            )
            db.add(hk_task)
        elif new_status == "Cancelled":
            room.operational_status = "Available"
            room.status = "Available"

    db.commit()
    return {
        "message": f"Reservation SE-RES-{res.id:04d} updated from {old_status} to {new_status}.",
        "status": res.status
    }


@saas_router.put("/api/reservations/{reservation_id}/cancel")
def cancel_hotel_reservation(
    reservation_id: int,
    current_user: User = Depends(require_roles("owner", "manager", "receptionist")),
    db: Session = Depends(get_db)
):
    """Cancel a reservation and release the room."""
    hotel_id = current_user.hotel_id or 1
    res = db.query(Reservation).filter(Reservation.id == reservation_id, Reservation.hotel_id == hotel_id).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")

    if res.status == "Cancelled":
        return {"message": "Reservation is already cancelled."}

    res.status = "Cancelled"
    if res.room and res.room.operational_status == "Occupied":
        res.room.operational_status = "Available"
        res.room.status = "Available"

    db.commit()
    return {"message": f"Reservation SE-RES-{res.id:04d} has been cancelled."}


@saas_router.get("/api/reservations/{reservation_id}/invoice")
def get_reservation_invoice(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate printable invoice data for a reservation."""
    hotel_id = current_user.hotel_id or 1
    res = db.query(Reservation).filter(Reservation.id == reservation_id, Reservation.hotel_id == hotel_id).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")

    hotel = res.hotel
    guest = res.guest
    room = res.room
    payment = db.query(Payment).filter(Payment.reservation_id == res.id).order_by(Payment.id.desc()).first()

    nights = max(1, (res.check_out - res.check_in).days)
    subtotal = round(res.total_amount / 1.12, 2)  # 12% GST breakdown
    gst_amount = round(res.total_amount - subtotal, 2)

    return {
        "invoice_number": f"INV-{res.id:05d}",
        "date": res.created_at.strftime("%B %d, %Y") if res.created_at else str(date.today()),
        "hotel": {
            "name": hotel.hotel_name if hotel else "StayEase Hotel",
            "address": hotel.address if hotel else "",
            "city": hotel.city if hotel else "",
            "state": hotel.state if hotel else "",
            "contact_number": hotel.contact_number if hotel else "",
            "email": hotel.hotel_email if hotel else ""
        },
        "guest": {
            "name": guest.full_name if guest else "Guest",
            "phone": guest.phone if guest else "",
            "email": guest.email if guest else "",
            "id_proof": f"{guest.id_proof_type} ({guest.id_proof_number})" if guest and guest.id_proof_number else "N/A"
        },
        "reservation": {
            "reference": f"SE-RES-{res.id:04d}",
            "check_in": str(res.check_in),
            "check_out": str(res.check_out),
            "nights": nights,
            "room_number": room.room_number if room else "N/A",
            "room_type": room.room_type if room else "Room",
            "rate_per_night": room.price if room else 0.0,
            "status": res.status
        },
        "financials": {
            "subtotal": subtotal,
            "tax_rate": "12% GST",
            "tax_amount": gst_amount,
            "total_amount": res.total_amount,
            "payment_status": payment.payment_status if payment else "Pending",
            "payment_method": payment.payment_method if payment else "N/A",
            "transaction_ref": payment.transaction_reference if payment else "N/A"
        }
    }


# ==========================================
# 8. STAFF ACCOUNT MANAGEMENT (OWNER & MANAGER)
# ==========================================

@saas_router.get("/api/staff")
def list_hotel_staff(
    current_user: User = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db)
):
    """List all staff accounts belonging to current_user.hotel_id."""
    hotel_id = current_user.hotel_id or 1
    staff_roles = ["staff", "manager", "receptionist", "housekeeping", "accountant", "maintenance"]
    staff_members = db.query(User).filter(
        User.hotel_id == hotel_id,
        User.role.in_(staff_roles)
    ).order_by(User.id.asc()).all()

    return [
        {
            "id": s.id,
            "full_name": s.full_name,
            "name": s.full_name,
            "email": s.email,
            "phone": s.phone or "",
            "role": s.role,
            "designation": s.designation or s.role.title(),
            "department": s.department or "",
            "is_active": s.is_active,
            "status": s.status or ("Active" if s.is_active else "Inactive"),
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in staff_members
    ]


@saas_router.post("/api/staff", status_code=status.HTTP_201_CREATED)
def create_staff_account(
    data: StaffAccountCreateRequest,
    current_user: User = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db)
):
    """Create a new staff login account under current_user.hotel_id."""
    hotel_id = current_user.hotel_id or 1
    email = data.email.lower().strip()

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    # Valid roles: manager, receptionist, housekeeping, accountant, maintenance
    valid_roles = ["manager", "receptionist", "housekeeping", "accountant", "maintenance"]
    role = data.role.lower().strip()
    if role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid staff role '{data.role}'. Allowed roles: {valid_roles}"
        )

    # Managers cannot create other managers unless authorized
    if current_user.role == "manager" and role == "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only hotel owners can create Manager accounts."
        )

    hashed_pwd = password_hash.hash(data.password)
    new_staff = User(
        full_name=data.full_name.strip(),
        email=email,
        phone=data.phone.strip(),
        hashed_password=hashed_pwd,
        role=role,
        designation=data.designation.strip() or role.title(),
        department=data.department.strip() or role.title(),
        hotel_id=hotel_id,
        is_active=True,
        status="Active"
    )
    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)

    return {
        "message": f"Staff account created for {new_staff.full_name} ({new_staff.role}).",
        "staff": {
            "id": new_staff.id,
            "full_name": new_staff.full_name,
            "email": new_staff.email,
            "role": new_staff.role,
            "designation": new_staff.designation
        }
    }


@saas_router.put("/api/staff/{staff_id}")
def update_staff_account(
    staff_id: int,
    data: StaffAccountUpdateRequest,
    current_user: User = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db)
):
    """Update staff details, role, department, or status."""
    hotel_id = current_user.hotel_id or 1
    staff = db.query(User).filter(User.id == staff_id, User.hotel_id == hotel_id).first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff account not found.")

    if staff.role == "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify hotel owner account.")

    if data.full_name is not None and data.full_name.strip():
        staff.full_name = data.full_name.strip()
    elif data.name is not None and data.name.strip():
        staff.full_name = data.name.strip()
    if data.phone is not None:
        staff.phone = data.phone.strip()
    if data.role is not None:
        valid_roles = ["manager", "receptionist", "housekeeping", "accountant", "maintenance", "staff"]
        if data.role.lower() not in valid_roles:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role '{data.role}'.")
        staff.role = data.role.lower().strip()
    if data.designation is not None:
        staff.designation = data.designation.strip()
    if data.department is not None:
        staff.department = data.department.strip()
    if data.status is not None:
        staff.status = data.status.strip()
        staff.is_active = (data.status.strip().lower() == "active")
    if data.password is not None and data.password.strip():
        staff.hashed_password = password_hash.hash(data.password.strip())

    db.commit()
    db.refresh(staff)
    return {"message": "Staff details updated successfully.", "staff": {"id": staff.id, "full_name": staff.full_name}}


@saas_router.put("/api/staff/{staff_id}/status")
def toggle_staff_status(
    staff_id: int,
    current_user: User = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db)
):
    """Toggle staff account status between Active and Inactive."""
    hotel_id = current_user.hotel_id or 1
    staff = db.query(User).filter(User.id == staff_id, User.hotel_id == hotel_id).first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff account not found.")

    if staff.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account.")

    staff.is_active = not staff.is_active
    staff.status = "Active" if staff.is_active else "Inactive"
    db.commit()

    return {
        "message": f"Staff member '{staff.full_name}' is now {staff.status}.",
        "is_active": staff.is_active,
        "status": staff.status
    }


@saas_router.post("/api/staff/{staff_id}/reset-password")
def reset_staff_password(
    staff_id: int,
    data: StaffResetPasswordRequest,
    current_user: User = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db)
):
    """Reset password for a staff member."""
    hotel_id = current_user.hotel_id or 1
    staff = db.query(User).filter(User.id == staff_id, User.hotel_id == hotel_id).first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff account not found.")

    staff.hashed_password = password_hash.hash(data.new_password)
    db.commit()

    return {"message": f"Password reset successfully for {staff.full_name}."}


@saas_router.delete("/api/staff/{staff_id}")
def delete_staff_account(
    staff_id: int,
    current_user: User = Depends(require_roles("owner")),
    db: Session = Depends(get_db)
):
    """Delete a staff member account (Owner only)."""
    hotel_id = current_user.hotel_id or 1
    staff = db.query(User).filter(User.id == staff_id, User.hotel_id == hotel_id).first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff account not found.")

    if staff.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account.")

    db.delete(staff)
    db.commit()
    return {"message": f"Staff account '{staff.full_name}' deleted."}


# ==========================================
# 9. HOUSEKEEPING OPERATIONS
# ==========================================

@saas_router.get("/api/housekeeping")
def get_housekeeping_board(
    current_user: User = Depends(require_roles("owner", "manager", "housekeeping", "receptionist")),
    db: Session = Depends(get_db)
):
    """Retrieve all rooms with cleaning statuses and assigned staff for this hotel."""
    hotel_id = current_user.hotel_id or 1
    rooms = db.query(Room).filter(Room.hotel_id == hotel_id).order_by(Room.room_number.asc()).all()

    result = []
    for r in rooms:
        # Get latest housekeeping task
        task = db.query(Housekeeping).filter(
            Housekeeping.room_id == r.id,
            Housekeeping.hotel_id == hotel_id
        ).order_by(Housekeeping.id.desc()).first()

        assigned_user = task.assigned_staff if task else None

        result.append({
            "room_id": r.id,
            "room_number": r.room_number,
            "room_type": r.room_type,
            "housekeeping_status": r.housekeeping_status or "Clean",
            "operational_status": r.operational_status or "Available",
            "last_cleaned": r.last_cleaned.isoformat() if r.last_cleaned else None,
            "task_id": task.id if task else None,
            "notes": task.notes if task else "",
            "assigned_staff_id": assigned_user.id if assigned_user else None,
            "assigned_staff_name": assigned_user.full_name if assigned_user else "Unassigned"
        })

    return result


@saas_router.put("/api/housekeeping/{room_id}")
def update_room_cleaning_status(
    room_id: int,
    data: HousekeepingTaskUpdateRequest,
    current_user: User = Depends(require_roles("owner", "manager", "housekeeping", "receptionist")),
    db: Session = Depends(get_db)
):
    """Update cleaning status (Clean, Dirty, In Progress, Inspection Needed) and log task."""
    hotel_id = current_user.hotel_id or 1
    room = db.query(Room).filter(Room.id == room_id, Room.hotel_id == hotel_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")

    valid_statuses = ["Clean", "Dirty", "In Progress", "Inspection Needed"]
    if data.cleaning_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )

    room.housekeeping_status = data.cleaning_status
    if data.cleaning_status == "Clean":
        room.last_cleaned = datetime.now(timezone.utc)

    # Record or update task
    new_task = Housekeeping(
        hotel_id=hotel_id,
        room_id=room.id,
        assigned_staff_id=data.assigned_staff_id or current_user.id,
        cleaning_status=data.cleaning_status,
        notes=data.notes.strip()
    )
    db.add(new_task)
    db.commit()

    return {
        "message": f"Room {room.room_number} status updated to {data.cleaning_status}.",
        "room_number": room.room_number,
        "housekeeping_status": room.housekeeping_status
    }


# ==========================================
# 10. MAINTENANCE TRACKER
# ==========================================

@saas_router.get("/api/maintenance")
def list_maintenance_tickets(
    current_user: User = Depends(require_roles("owner", "manager", "maintenance", "housekeeping", "receptionist")),
    db: Session = Depends(get_db)
):
    """List maintenance requests for current_user.hotel_id."""
    hotel_id = current_user.hotel_id or 1
    tickets = db.query(Maintenance).filter(
        Maintenance.hotel_id == hotel_id
    ).order_by(Maintenance.id.desc()).all()

    result = []
    for t in tickets:
        rm = t.room
        rep = t.reporter
        result.append({
            "id": t.id,
            "room_id": t.room_id,
            "room_number": rm.room_number if rm else "N/A",
            "issue_description": t.issue_description,
            "priority": t.priority,
            "status": t.status,
            "reported_by_id": rep.id if rep else None,
            "reported_by_name": rep.full_name if rep else "Staff",
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None
        })

    return result


@saas_router.post("/api/maintenance", status_code=status.HTTP_201_CREATED)
def report_maintenance_ticket(
    data: MaintenanceTicketCreateRequest,
    current_user: User = Depends(require_roles("owner", "manager", "maintenance", "housekeeping", "receptionist")),
    db: Session = Depends(get_db)
):
    """File a maintenance issue for a room in this hotel."""
    hotel_id = current_user.hotel_id or 1
    room = db.query(Room).filter(Room.id == data.room_id, Room.hotel_id == hotel_id).first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")

    ticket = Maintenance(
        hotel_id=hotel_id,
        room_id=room.id,
        reported_by=current_user.id,
        issue_description=data.issue_description.strip(),
        priority=data.priority,
        status="Reported"
    )
    db.add(ticket)

    # If priority is Urgent or High, set room to Maintenance
    if data.priority in ["Urgent", "High"]:
        room.operational_status = "Maintenance"
        room.status = "Maintenance"

    db.commit()
    db.refresh(ticket)

    return {
        "message": f"Maintenance ticket #{ticket.id} filed for Room {room.room_number}.",
        "ticket_id": ticket.id
    }


@saas_router.put("/api/maintenance/{ticket_id}")
def update_maintenance_ticket_status(
    ticket_id: int,
    data: MaintenanceTicketUpdateRequest,
    current_user: User = Depends(require_roles("owner", "manager", "maintenance")),
    db: Session = Depends(get_db)
):
    """Update status of a maintenance ticket (Reported, In Progress, Resolved)."""
    hotel_id = current_user.hotel_id or 1
    ticket = db.query(Maintenance).filter(Maintenance.id == ticket_id, Maintenance.hotel_id == hotel_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")

    ticket.status = data.status
    if data.status == "Resolved":
        ticket.resolved_at = datetime.now(timezone.utc)
        # Restore room status if no other active tickets
        other_active = db.query(Maintenance).filter(
            Maintenance.room_id == ticket.room_id,
            Maintenance.id != ticket.id,
            Maintenance.status.in_(["Reported", "In Progress"])
        ).first()
        if not other_active and ticket.room and ticket.room.operational_status == "Maintenance":
            ticket.room.operational_status = "Available"
            ticket.room.status = "Available"

    db.commit()
    return {"message": f"Ticket #{ticket.id} updated to {ticket.status}."}


# ==========================================
# 11. BILLING & RECORDED PAYMENTS
# ==========================================

@saas_router.get("/api/payments")
def list_hotel_payments(
    current_user: User = Depends(require_roles("owner", "manager", "accountant", "receptionist")),
    db: Session = Depends(get_db)
):
    """List all recorded payments for current_user.hotel_id."""
    hotel_id = current_user.hotel_id or 1
    payments = db.query(Payment).filter(
        Payment.hotel_id == hotel_id
    ).order_by(Payment.id.desc()).all()

    result = []
    for p in payments:
        res = p.reservation
        g = res.guest if res else None
        rm = res.room if res else None
        result.append({
            "id": p.id,
            "transaction_reference": p.transaction_reference,
            "reservation_id": p.reservation_id,
            "reservation_reference": f"SE-RES-{res.id:04d}" if res else "N/A",
            "guest_name": g.full_name if g else "Guest",
            "room_number": rm.room_number if rm else "N/A",
            "amount": p.amount,
            "payment_method": p.payment_method,
            "payment_status": p.payment_status,
            "payment_date": p.payment_date.isoformat() if p.payment_date else None
        })

    return result


@saas_router.post("/api/payments", status_code=status.HTTP_201_CREATED)
def record_hotel_payment(
    data: RecordPaymentRequest,
    current_user: User = Depends(require_roles("owner", "manager", "accountant", "receptionist")),
    db: Session = Depends(get_db)
):
    """Record an offline or counter payment for a reservation."""
    hotel_id = current_user.hotel_id or 1
    res = db.query(Reservation).filter(Reservation.id == data.reservation_id, Reservation.hotel_id == hotel_id).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")

    tx_ref = f"TXN-{uuid.uuid4().hex[:10].upper()}"
    payment = Payment(
        hotel_id=hotel_id,
        reservation_id=res.id,
        amount=data.amount,
        payment_method=data.payment_method,
        payment_status=data.payment_status,
        transaction_reference=tx_ref
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        "message": f"Payment of ₹{payment.amount:,.2f} recorded.",
        "transaction_reference": tx_ref,
        "payment_id": payment.id
    }


# ==========================================
# 12. HOTEL SETTINGS MANAGEMENT
# ==========================================

@saas_router.get("/api/hotel/settings")
def get_hotel_settings(
    current_user: User = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db)
):
    """Retrieve profile and operational policies for current_user.hotel_id."""
    hotel_id = current_user.hotel_id or 1
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel record not found.")

    return {
        "id": hotel.id,
        "hotel_name": hotel.hotel_name,
        "address": hotel.address or "",
        "city": hotel.city or "",
        "state": hotel.state or "",
        "country": hotel.country or "India",
        "contact_number": hotel.contact_number or "",
        "hotel_email": hotel.hotel_email or "",
        "hotel_category": hotel.hotel_category or "Boutique",
        "total_rooms": hotel.total_rooms or 10,
        "check_in_time": hotel.check_in_time or "14:00",
        "check_out_time": hotel.check_out_time or "11:00",
        "cancellation_policy": hotel.cancellation_policy or ""
    }


@saas_router.put("/api/hotel/settings")
def update_hotel_settings(
    data: SaaSHotelSettingsUpdateRequest,
    current_user: User = Depends(require_roles("owner", "manager")),
    db: Session = Depends(get_db)
):
    """Update profile and operational policies for current_user.hotel_id."""
    hotel_id = current_user.hotel_id or 1
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel record not found.")

    if data.hotel_name is not None:
        hotel.hotel_name = data.hotel_name.strip()
    if data.address is not None:
        hotel.address = data.address.strip()
    if data.city is not None:
        hotel.city = data.city.strip()
    if data.state is not None:
        hotel.state = data.state.strip()
    if data.country is not None:
        hotel.country = data.country.strip()
    if data.contact_number is not None:
        hotel.contact_number = data.contact_number.strip()
    if data.hotel_email is not None:
        hotel.hotel_email = data.hotel_email.strip()
    if data.hotel_category is not None:
        hotel.hotel_category = data.hotel_category.strip()
    if data.total_rooms is not None:
        hotel.total_rooms = data.total_rooms
    if data.check_in_time is not None:
        hotel.check_in_time = data.check_in_time.strip()
    if data.check_out_time is not None:
        hotel.check_out_time = data.check_out_time.strip()
    if data.cancellation_policy is not None:
        hotel.cancellation_policy = data.cancellation_policy.strip()

    db.commit()
    db.refresh(hotel)

    return {
        "message": "Hotel settings saved successfully.",
        "hotel_name": hotel.hotel_name
    }
