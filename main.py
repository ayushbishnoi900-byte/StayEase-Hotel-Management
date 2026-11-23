# ==========================================
# STAYEASE - HOTEL MANAGEMENT SYSTEM
# Professional FastAPI Backend
# ==========================================

import os
import uuid
from datetime import date, datetime, timezone, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session
from sqlalchemy import func

from database.database import engine, Base, get_db
from database.models import Customer, Room, Booking, Payment, Staff, HotelSetting
from chatbot.assistant import StayEaseAssistant, rate_limiter

from pwdlib import PasswordHash
from jose import jwt, JWTError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")


# ==========================================
# 1. APPLICATION LIFESPAN & INITIALIZATION
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Safely creates tables and initializes default administrator on startup
    without dropping or modifying existing customer or booking records.
    """
    try:
        # Create missing tables safely (non-destructive)
        Base.metadata.create_all(bind=engine)

        # Check / create default administrator
        db = Session(bind=engine)
        try:
            admin_email = os.getenv("ADMIN_EMAIL", "admin@stayease.com")
            admin_pwd = os.getenv("ADMIN_PASSWORD", "admin123")
            admin_name = os.getenv("ADMIN_NAME", "StayEase Administrator")

            existing_admin = db.query(Customer).filter(
                Customer.email == admin_email
            ).first()

            if not existing_admin:
                admin_user = Customer(
                    name=admin_name,
                    email=admin_email,
                    password=password_hash.hash(admin_pwd),
                    phone="+91 98765 43210",
                    role="admin"
                )
                db.add(admin_user)
                db.commit()
                print(f"[StayEase] Default admin initialized: {admin_email}")

            # Check / create default hotel settings
            existing_settings = db.query(HotelSetting).first()
            if not existing_settings:
                settings = HotelSetting(
                    hotel_name="StayEase Hotel & Luxury Suites",
                    contact_email="contact@stayease.com",
                    contact_phone="+91 98765 43210",
                    hotel_address="124 Luxury Boulevard, Central District, New Delhi, 110001",
                    check_in_time="14:00",
                    check_out_time="11:00",
                    cancellation_policy="Free cancellation up to 24 hours prior to standard check-in time."
                )
                db.add(settings)
                db.commit()
                print("[StayEase] Default hotel settings initialized.")
        finally:
            db.close()

    except Exception as e:
        print(f"[StayEase] Startup initialization notice: {e}")

    yield


app = FastAPI(
    title="StayEase Hotel Management System",
    description="Full-featured RESTful backend API for hotel booking and management",
    version="2.0",
    lifespan=lifespan
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ==========================================
# 2. SECURITY CONFIGURATION
# ==========================================

password_hash = PasswordHash.recommended()

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    SECRET_KEY = "dev-insecure-key-set-secret-key-in-production-env"
    print("WARNING: SECRET_KEY not configured. Set SECRET_KEY in your .env file.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer()


# ==========================================
# 3. PYDANTIC REQUEST & RESPONSE SCHEMAS
# ==========================================

# Customer Schemas
class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, description="Minimum 8 characters")
    phone: str = ""


class LoginRequest(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    phone: str | None = None


# Room Schemas
class RoomCreateRequest(BaseModel):
    room_number: str = Field(min_length=1, max_length=20)
    room_type: str = Field(min_length=1, max_length=50)
    price: float = Field(gt=0, description="Price per night in INR")
    capacity: int = Field(gt=0, le=20, description="Max guests")
    description: str = ""
    image_url: str = ""
    status: str = "Available"


class RoomUpdateRequest(BaseModel):
    room_number: str | None = None
    room_type: str | None = None
    price: float | None = Field(default=None, gt=0)
    capacity: int | None = Field(default=None, gt=0, le=20)
    description: str | None = None
    image_url: str | None = None
    status: str | None = None


# Booking Schemas
class BookingCreateRequest(BaseModel):
    room_id: int
    check_in: date
    check_out: date
    guests: int = Field(default=1, ge=1, le=20)
    payment_method: str = Field(
        default="Cash at hotel",
        description="'Cash at hotel' or 'Demo Online Payment'"
    )


# Payment Schemas
class DemoPaymentRequest(BaseModel):
    payment_method: str = Field(
        default="Demo Online Payment",
        description="'Demo Online Payment' or 'Cash at hotel'"
    )
    card_last4: str = "4242"
    notes: str = ""


class PaymentStatusUpdateRequest(BaseModel):
    payment_status: str = Field(
        description="'Completed', 'Pending', 'Refunded', 'Failed'"
    )


# Staff Schemas
class StaffCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str = ""
    designation: str = Field(min_length=2, max_length=100)
    status: str = "Active"


class StaffUpdateRequest(BaseModel):
    name: str | None = None
    phone: str | None = None
    designation: str | None = None
    status: str | None = None


# Customer Management Schemas (Admin)
class AdminCustomerUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    phone: str | None = None
    role: str | None = Field(default=None, description="'customer' or 'admin'")
    status: str | None = Field(default=None, description="'Active' or 'Inactive'")


class AdminCustomerStatusUpdateRequest(BaseModel):
    status: str = Field(description="'Active' or 'Inactive'")


# Housekeeping Schemas
class HousekeepingUpdateRequest(BaseModel):
    housekeeping_status: str = Field(
        description="'Clean', 'Dirty', 'Cleaning in Progress', or 'Maintenance Required'"
    )


# Hotel Settings Schemas
class HotelSettingsUpdateRequest(BaseModel):
    hotel_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    hotel_address: str | None = None
    check_in_time: str | None = None
    check_out_time: str | None = None
    cancellation_policy: str | None = None


# Chatbot Schemas
class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500, description="Customer inquiry")
    user_name: str | None = Field(default=None, max_length=100)


# ==========================================
# 4. AUTHENTICATION & AUTHORIZATION HELPERS
# ==========================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Customer:
    """
    Extracts and validates the JWT Bearer token from request headers.
    Ensures customer identity is always sourced from the verified token.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        customer_id_str = payload.get("sub")
        if customer_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is missing user identity."
            )
        customer_id = int(customer_id_str)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token."
        )

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists."
        )

    return customer


def require_admin(
    customer: Customer = Depends(get_current_user)
) -> Customer:
    """
    Ensures that the authenticated user possesses administrator privileges.
    Customers attempting to access admin APIs receive 403 Forbidden.
    """
    if customer.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required for this operation."
        )
    return customer


# ==========================================
# 5. HOME ROUTE
# ==========================================

@app.get("/", tags=["General"])
def home():
    """Serves the frontend single-page application."""
    index_file = os.path.join(PUBLIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "StayEase API is running."}


# ==========================================
# 6. CUSTOMER AUTHENTICATION & PROFILE APIs
# ==========================================

@app.post("/register", status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new customer account.
    Validates email format and hashes password using Argon2.
    """
    existing_user = db.query(Customer).filter(Customer.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address is already registered."
        )

    hashed_password = password_hash.hash(data.password)

    new_customer = Customer(
        name=data.name,
        email=data.email,
        password=hashed_password,
        phone=data.phone,
        role="customer"
    )

    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)

    return {
        "message": "Account created successfully. Please login.",
        "customer_id": new_customer.id
    }


@app.post("/login", tags=["Authentication"])
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user credentials and return a signed JWT access token.
    """
    customer = db.query(Customer).filter(Customer.email == data.email).first()

    if not customer or not password_hash.verify(data.password, customer.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password."
        )

    now = datetime.now(timezone.utc)
    token_payload = {
        "sub": str(customer.id),
        "role": customer.role,
        "name": customer.name,
        "iat": now,
        "exp": now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    }

    token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "message": "Login successful.",
        "access_token": token,
        "token_type": "bearer",
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "role": customer.role
        }
    }


@app.get("/me", tags=["Customer Profile"])
@app.get("/customers/profile", tags=["Customer Profile"])
def get_customer_profile(customer: Customer = Depends(get_current_user)):
    """
    Retrieve profile details for the authenticated customer.
    Identity is derived directly from the verified JWT token.
    """
    return {
        "id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "role": customer.role,
        "created_at": customer.created_at.isoformat() if customer.created_at else None
    }


@app.put("/me", tags=["Customer Profile"])
@app.put("/customers/profile", tags=["Customer Profile"])
def update_customer_profile(
    data: ProfileUpdateRequest,
    customer: Customer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update profile information (name, phone) for the logged-in customer.
    """
    if data.name is not None:
        customer.name = data.name.strip()
    if data.phone is not None:
        customer.phone = data.phone.strip()

    db.commit()
    db.refresh(customer)

    return {
        "message": "Profile updated successfully.",
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "role": customer.role
        }
    }


# ==========================================
# 7. ROOM APIs
# ==========================================

AMENITIES_BY_TYPE = {
    "Standard": [
        "Queen Bed",
        "High-Speed WiFi",
        "Air Conditioning",
        "32-inch Smart TV",
        "Work Desk & Chair",
        "En-suite Bathroom",
        "Complimentary Toiletries"
    ],
    "Deluxe": [
        "King Bed",
        "High-Speed WiFi",
        "Climate Control",
        "50-inch 4K Smart TV",
        "Private Balcony with View",
        "Mini-Bar & Refrigerator",
        "Complimentary Breakfast",
        "Bathrobes & Premium Slippers"
    ],
    "Suite": [
        "Executive King Bed",
        "Separate Living & Dining Area",
        "High-Speed Premium WiFi",
        "65-inch OLED Smart TV",
        "Jacuzzi & Soaking Bathtub",
        "Panoramic Skyline View",
        "Free Gourmet Mini-Bar",
        "24/7 Dedicated Concierge",
        "Complimentary Buffet Breakfast"
    ]
}


@app.get("/rooms", tags=["Rooms"])
def get_rooms(
    room_type: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    capacity: int | None = None,
    check_in: date | None = None,
    check_out: date | None = None,
    db: Session = Depends(get_db)
):
    """
    Retrieve all hotel rooms with optional filtering by type, price range,
    minimum guest capacity, and date availability.
    """
    query = db.query(Room)

    if room_type:
        query = query.filter(Room.room_type.ilike(f"%{room_type.strip()}%"))
    if min_price is not None:
        query = query.filter(Room.price >= min_price)
    if max_price is not None:
        query = query.filter(Room.price <= max_price)
    if capacity is not None:
        query = query.filter(Room.capacity >= capacity)

    # Filter out occupied/booked rooms if date range is specified
    if check_in and check_out:
        today = date.today()
        if check_in < today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Check-in date cannot be in the past."
            )
        if check_out <= check_in:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Check-out date must be after check-in date."
            )

        # Find room IDs that have overlapping confirmed bookings
        booked_query = db.query(Booking.room_id).filter(
            Booking.status == "Confirmed",
            Booking.check_in < check_out,
            Booking.check_out > check_in
        )

        query = query.filter(~Room.id.in_(booked_query))

    rooms = query.order_by(Room.price.asc()).all()

    return [
        {
            "id": room.id,
            "room_number": room.room_number,
            "room_type": room.room_type,
            "price": room.price,
            "capacity": room.capacity,
            "status": room.status,
            "description": room.description,
            "image_url": room.image_url,
            "amenities": AMENITIES_BY_TYPE.get(
                room.room_type,
                ["High-Speed WiFi", "Air Conditioning", "Smart TV", "En-suite Bathroom"]
            )
        }
        for room in rooms
    ]


@app.get("/rooms/{room_id}", tags=["Rooms"])
def get_room_details(room_id: int, db: Session = Depends(get_db)):
    """
    Retrieve details for an individual room by ID, including its amenities.
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found."
        )

    return {
        "id": room.id,
        "room_number": room.room_number,
        "room_type": room.room_type,
        "price": room.price,
        "capacity": room.capacity,
        "status": room.status,
        "description": room.description,
        "image_url": room.image_url,
        "amenities": AMENITIES_BY_TYPE.get(
            room.room_type,
            ["High-Speed WiFi", "Air Conditioning", "Smart TV", "En-suite Bathroom"]
        )
    }


@app.post("/rooms", status_code=status.HTTP_201_CREATED, tags=["Rooms (Admin)"])
def add_room(
    data: RoomCreateRequest,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Add a new room to the hotel catalog (Admin only).
    """
    existing_room = db.query(Room).filter(
        Room.room_number == data.room_number.strip()
    ).first()

    if existing_room:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Room number {data.room_number} already exists."
        )

    new_room = Room(
        room_number=data.room_number.strip(),
        room_type=data.room_type.strip(),
        price=data.price,
        capacity=data.capacity,
        description=data.description.strip(),
        image_url=data.image_url.strip(),
        status=data.status
    )

    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    return {
        "message": "Room added successfully.",
        "room_id": new_room.id
    }


@app.put("/rooms/{room_id}", tags=["Rooms (Admin)"])
def update_room(
    room_id: int,
    data: RoomUpdateRequest,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update room information (Admin only).
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found."
        )

    if data.room_number is not None:
        # Check uniqueness if room_number changed
        duplicate = db.query(Room).filter(
            Room.room_number == data.room_number.strip(),
            Room.id != room_id
        ).first()
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room number {data.room_number} is already in use."
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
    if data.status is not None:
        room.status = data.status.strip()

    db.commit()
    db.refresh(room)

    return {
        "message": "Room updated successfully.",
        "room": {
            "id": room.id,
            "room_number": room.room_number,
            "room_type": room.room_type,
            "price": room.price,
            "capacity": room.capacity,
            "status": room.status
        }
    }


@app.delete("/rooms/{room_id}", tags=["Rooms (Admin)"])
def delete_room(
    room_id: int,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Safely delete a room (Admin only).
    Guards against deleting rooms that have active Confirmed reservations.
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found."
        )

    # Check for active bookings
    active_bookings = db.query(Booking).filter(
        Booking.room_id == room_id,
        Booking.status == "Confirmed"
    ).count()

    if active_bookings > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete room: {active_bookings} active booking(s) exist for this room."
        )

    db.delete(room)
    db.commit()

    return {"message": "Room deleted successfully."}


@app.get("/rooms/{room_id}/availability", tags=["Rooms"])
def check_availability(
    room_id: int,
    check_in: date,
    check_out: date,
    db: Session = Depends(get_db)
):
    """
    Check if a specific room is available for the given date range.
    """
    today = date.today()
    if check_in < today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-in date cannot be in the past."
        )
    if check_out <= check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-out date must be after check-in date."
        )

    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found."
        )

    # Find overlapping confirmed bookings
    overlapping = db.query(Booking).filter(
        Booking.room_id == room_id,
        Booking.status == "Confirmed",
        Booking.check_in < check_out,
        Booking.check_out > check_in
    ).first()

    return {
        "room_id": room_id,
        "room_number": room.room_number,
        "available": overlapping is None and room.status != "Maintenance",
        "room_status": room.status
    }


# ==========================================
# 8. BOOKING APIs
# ==========================================

@app.post("/bookings", status_code=status.HTTP_201_CREATED, tags=["Bookings"])
def create_booking(
    data: BookingCreateRequest,
    customer: Customer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new hotel room booking.
    - Identity strictly bound to authenticated JWT token (customer_id from frontend is never trusted).
    - Automatically calculates total price: nights × room price per night.
    - Prevents overlapping reservations and double booking.
    - Creates linked demonstration payment record.
    """
    today = date.today()
    if data.check_in < today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-in date cannot be in the past."
        )
    if data.check_out <= data.check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-out date must be after check-in date."
        )

    # Use row-level locking to prevent race conditions on concurrent bookings
    room = db.query(Room).filter(Room.id == data.room_id).with_for_update().first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected room does not exist."
        )

    if room.status == "Maintenance":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This room is currently under maintenance and cannot be reserved."
        )

    if data.guests > room.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This room accommodates a maximum of {room.capacity} guest(s)."
        )

    # Overlapping bookings check
    overlapping = db.query(Booking).filter(
        Booking.room_id == data.room_id,
        Booking.status == "Confirmed",
        Booking.check_in < data.check_out,
        Booking.check_out > data.check_in
    ).first()

    if overlapping:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room is already booked for the selected dates. Please choose different dates or another room."
        )

    # Automatic price calculation
    nights = (data.check_out - data.check_in).days
    total_price = round(room.price * nights, 2)

    # Create booking record
    new_booking = Booking(
        customer_id=customer.id,  # Authenticated user ID only
        room_id=data.room_id,
        check_in=data.check_in,
        check_out=data.check_out,
        total_price=total_price,
        guests=data.guests,
        status="Confirmed"
    )

    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    # Create associated initial demonstration payment record
    is_online = "online" in data.payment_method.lower()
    payment_status = "Completed" if is_online else "Pending"
    tx_ref = f"{'DEMO' if is_online else 'CASH'}-{uuid.uuid4().hex[:8].upper()}"

    initial_payment = Payment(
        booking_id=new_booking.id,
        amount=total_price,
        payment_method=data.payment_method,
        payment_status=payment_status,
        transaction_ref=tx_ref
    )

    db.add(initial_payment)
    db.commit()

    booking_ref = f"SE-BK-{new_booking.id:04d}"

    return {
        "message": "Booking confirmed successfully.",
        "booking": {
            "id": new_booking.id,
            "booking_reference": booking_ref,
            "room_id": room.id,
            "room_number": room.room_number,
            "room_type": room.room_type,
            "check_in": str(new_booking.check_in),
            "check_out": str(new_booking.check_out),
            "nights": nights,
            "guests": new_booking.guests,
            "total_price": new_booking.total_price,
            "status": new_booking.status,
            "payment": {
                "method": initial_payment.payment_method,
                "status": initial_payment.payment_status,
                "transaction_ref": initial_payment.transaction_ref
            }
        }
    }


@app.get("/my-bookings", tags=["Bookings"])
def get_my_bookings(
    customer: Customer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve booking history for the logged-in customer.
    Includes room details, dates, amount, payment status, and categorization
    (Upcoming, Completed, Cancelled).
    """
    bookings = db.query(Booking).filter(
        Booking.customer_id == customer.id
    ).order_by(Booking.id.desc()).all()

    today = date.today()
    result = []
    for b in bookings:
        room = db.query(Room).filter(Room.id == b.room_id).first()
        payment = db.query(Payment).filter(Payment.booking_id == b.id).order_by(Payment.id.desc()).first()

        if b.status == "Cancelled":
            timing = "Cancelled"
        elif b.check_out < today:
            timing = "Completed"
        else:
            timing = "Upcoming"

        result.append({
            "id": b.id,
            "booking_reference": f"SE-BK-{b.id:04d}",
            "room_id": b.room_id,
            "room_number": room.room_number if room else "N/A",
            "room_type": room.room_type if room else "Unknown",
            "price_per_night": room.price if room else 0.0,
            "check_in": str(b.check_in),
            "check_out": str(b.check_out),
            "nights": (b.check_out - b.check_in).days,
            "guests": b.guests,
            "total_price": b.total_price,
            "status": b.status,
            "timing_status": timing,
            "can_cancel": b.status == "Confirmed" and b.check_in >= today,
            "payment_status": payment.payment_status if payment else "Unpaid",
            "payment_method": payment.payment_method if payment else "None",
            "transaction_ref": payment.transaction_ref if payment else None
        })

    return result


@app.get("/bookings/{booking_id}", tags=["Bookings"])
def get_booking_details(
    booking_id: int,
    customer: Customer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    View individual booking details.
    Only the booking owner or an administrator can access this record.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found."
        )

    # Authorization guard: owner or admin
    if booking.customer_id != customer.id and customer.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this booking."
        )

    room = db.query(Room).filter(Room.id == booking.room_id).first()
    cust = db.query(Customer).filter(Customer.id == booking.customer_id).first()
    payments = db.query(Payment).filter(Payment.booking_id == booking_id).all()

    today = date.today()
    if booking.status == "Cancelled":
        timing = "Cancelled"
    elif booking.check_out < today:
        timing = "Completed"
    else:
        timing = "Upcoming"

    return {
        "id": booking.id,
        "booking_reference": f"SE-BK-{booking.id:04d}",
        "customer": {
            "id": cust.id if cust else None,
            "name": cust.name if cust else "Unknown",
            "email": cust.email if cust else "N/A"
        },
        "room": {
            "id": room.id if room else None,
            "room_number": room.room_number if room else "N/A",
            "room_type": room.room_type if room else "Unknown",
            "price_per_night": room.price if room else 0
        },
        "check_in": str(booking.check_in),
        "check_out": str(booking.check_out),
        "nights": (booking.check_out - booking.check_in).days,
        "guests": booking.guests,
        "total_price": booking.total_price,
        "status": booking.status,
        "timing_status": timing,
        "can_cancel": booking.status == "Confirmed" and booking.check_in >= today,
        "payments": [
            {
                "id": p.id,
                "amount": p.amount,
                "method": p.payment_method,
                "status": p.payment_status,
                "transaction_ref": p.transaction_ref,
                "date": p.payment_date.isoformat() if p.payment_date else None
            }
            for p in payments
        ]
    }


@app.get("/bookings/{booking_id}/invoice", tags=["Bookings"])
def get_booking_invoice(
    booking_id: int,
    customer: Customer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate structured invoice details for a booking.
    Accessible only by the reservation owner or an administrator.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found."
        )

    if booking.customer_id != customer.id and customer.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this invoice."
        )

    room = db.query(Room).filter(Room.id == booking.room_id).first()
    cust = db.query(Customer).filter(Customer.id == booking.customer_id).first()
    payment = db.query(Payment).filter(
        Payment.booking_id == booking_id
    ).order_by(Payment.id.desc()).first()

    nights = (booking.check_out - booking.check_in).days

    return {
        "invoice_number": f"INV-2026-{booking.id:05d}",
        "booking_reference": f"SE-BK-{booking.id:04d}",
        "issue_date": (booking.created_at or datetime.now(timezone.utc)).strftime("%B %d, %Y"),
        "hotel": {
            "name": "StayEase Hotel & Luxury Suites",
            "tagline": "Your Comfort, Our Priority",
            "address": "124 Luxury Boulevard, Central District, New Delhi, 110001",
            "contact": "support@stayease.com | +91 98765 43210",
            "gstin": "07AAAAA0000A1Z5"
        },
        "customer": {
            "id": cust.id if cust else None,
            "name": cust.name if cust else "Valued Guest",
            "email": cust.email if cust else "N/A",
            "phone": cust.phone if cust else "N/A"
        },
        "reservation": {
            "room_number": room.room_number if room else "N/A",
            "room_type": room.room_type if room else "Unknown",
            "price_per_night": room.price if room else 0.0,
            "check_in": str(booking.check_in),
            "check_out": str(booking.check_out),
            "nights": nights,
            "guests": booking.guests,
            "booking_status": booking.status
        },
        "billing": {
            "room_rate": room.price if room else 0.0,
            "nights": nights,
            "subtotal": booking.total_price,
            "taxes_and_fees": 0.0,
            "total_amount": booking.total_price,
            "payment_status": payment.payment_status if payment else "Unpaid",
            "payment_method": payment.payment_method if payment else "None",
            "transaction_reference": payment.transaction_ref if payment else None
        }
    }


@app.put("/bookings/cancel/{booking_id}", tags=["Bookings"])
def cancel_booking(
    booking_id: int,
    customer: Customer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a confirmed booking.
    - Customer can cancel their own booking.
    - Administrator can cancel any booking.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found."
        )

    if booking.customer_id != customer.id and customer.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own reservations."
        )

    if booking.status != "Confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Booking cannot be cancelled because its current status is '{booking.status}'."
        )

    booking.status = "Cancelled"

    # Mark completed payments as Refunded for demonstration
    payments = db.query(Payment).filter(
        Payment.booking_id == booking_id,
        Payment.payment_status == "Completed"
    ).all()
    for p in payments:
        p.payment_status = "Refunded"

    db.commit()

    return {
        "message": "Booking cancelled successfully.",
        "booking_id": booking_id,
        "status": "Cancelled"
    }


# ==========================================
# 9. PAYMENT MODULE (DEMONSTRATION)
# ==========================================

@app.post("/bookings/{booking_id}/pay", tags=["Payments"])
def process_demo_payment(
    booking_id: int,
    data: DemoPaymentRequest,
    customer: Customer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process a demonstration payment for a booking.
    Supports 'Demo Online Payment' and 'Cash at hotel'.
    NOTE: Simulated demonstration payment only — no real financial charge occurs.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found."
        )

    if booking.customer_id != customer.id and customer.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only process payments for your own bookings."
        )

    if booking.status != "Confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot pay for a booking that is not Confirmed."
        )

    is_online = "online" in data.payment_method.lower()
    tx_ref = f"{'DEMO' if is_online else 'CASH'}-{uuid.uuid4().hex[:8].upper()}"
    p_status = "Completed" if is_online else "Pending"

    payment = Payment(
        booking_id=booking_id,
        amount=booking.total_price,
        payment_method=data.payment_method,
        payment_status=p_status,
        transaction_ref=tx_ref
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        "message": "Demo payment processed successfully.",
        "disclaimer": "This is a simulated college demonstration payment. No financial charge was made.",
        "payment": {
            "id": payment.id,
            "booking_id": booking_id,
            "amount": payment.amount,
            "payment_method": payment.payment_method,
            "payment_status": payment.payment_status,
            "transaction_ref": payment.transaction_ref,
            "payment_date": payment.payment_date.isoformat() if payment.payment_date else None
        }
    }


@app.get("/bookings/{booking_id}/payments", tags=["Payments"])
def get_booking_payments(
    booking_id: int,
    customer: Customer = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    View payment history for a specific booking.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found."
        )

    if booking.customer_id != customer.id and customer.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view payments for this booking."
        )

    payments = db.query(Payment).filter(Payment.booking_id == booking_id).all()

    return [
        {
            "id": p.id,
            "amount": p.amount,
            "payment_method": p.payment_method,
            "payment_status": p.payment_status,
            "transaction_ref": p.transaction_ref,
            "payment_date": p.payment_date.isoformat() if p.payment_date else None
        }
        for p in payments
    ]


@app.get("/admin/payments", tags=["Payments (Admin)"])
def admin_get_all_payments(
    search: str | None = None,
    status: str | None = None,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    View all payment transactions across the hotel with optional search and status filtering (Admin only).
    """
    query = db.query(Payment)

    if status and status.strip():
        query = query.filter(Payment.payment_status == status.strip())

    payments = query.order_by(Payment.id.desc()).all()

    result = []
    search_term = search.strip().lower() if search else None

    for p in payments:
        booking = db.query(Booking).filter(Booking.id == p.booking_id).first()
        cust = db.query(Customer).filter(Customer.id == booking.customer_id).first() if booking else None
        room = db.query(Room).filter(Room.id == booking.room_id).first() if booking else None

        cust_name = cust.name if cust else "Unknown"
        cust_email = cust.email if cust else "N/A"
        room_num = room.room_number if room else "N/A"
        booking_ref = f"SE-BK-{p.booking_id:04d}"

        if search_term:
            matches = (
                search_term in p.transaction_ref.lower() or
                search_term in cust_name.lower() or
                search_term in cust_email.lower() or
                search_term in booking_ref.lower() or
                search_term == str(p.booking_id)
            )
            if not matches:
                continue

        result.append({
            "id": p.id,
            "booking_id": p.booking_id,
            "booking_reference": booking_ref,
            "customer_name": cust_name,
            "customer_email": cust_email,
            "room_number": room_num,
            "amount": p.amount,
            "payment_method": p.payment_method,
            "payment_status": p.payment_status,
            "transaction_ref": p.transaction_ref,
            "payment_date": p.payment_date.isoformat() if p.payment_date else None
        })

    return result


@app.put("/admin/payments/{payment_id}/status", tags=["Payments (Admin)"])
def admin_update_payment_status(
    payment_id: int,
    data: PaymentStatusUpdateRequest,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update payment status (e.g. mark cash payment as 'Completed' upon front desk settlement).
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found."
        )

    valid_statuses = ["Completed", "Pending", "Refunded", "Failed"]
    if data.payment_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payment status. Must be one of: {', '.join(valid_statuses)}"
        )

    payment.payment_status = data.payment_status
    db.commit()

    return {
        "message": f"Payment #{payment_id} updated to '{data.payment_status}'.",
        "payment_id": payment_id,
        "payment_status": payment.payment_status
    }


# ==========================================
# 10. STAFF MANAGEMENT APIs (ADMIN ONLY)
# ==========================================

@app.get("/admin/staff", tags=["Staff (Admin)"])
def admin_get_staff(
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List all hotel staff members (Admin only).
    """
    staff_members = db.query(Staff).order_by(Staff.id.asc()).all()

    return [
        {
            "id": s.id,
            "name": s.name,
            "email": s.email,
            "phone": s.phone,
            "designation": s.designation,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in staff_members
    ]


@app.get("/admin/staff/{staff_id}", tags=["Staff (Admin)"])
def admin_get_staff_member(
    staff_id: int,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Retrieve details for a single staff member (Admin only).
    """
    s = db.query(Staff).filter(Staff.id == staff_id).first()
    if not s:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found."
        )

    return {
        "id": s.id,
        "name": s.name,
        "email": s.email,
        "phone": s.phone,
        "designation": s.designation,
        "status": s.status,
        "created_at": s.created_at.isoformat() if s.created_at else None
    }


@app.post("/admin/staff", status_code=status.HTTP_201_CREATED, tags=["Staff (Admin)"])
def admin_add_staff(
    data: StaffCreateRequest,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Add a new staff member (Admin only).
    """
    existing = db.query(Staff).filter(Staff.email == data.email.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Staff member with email '{data.email}' already exists."
        )

    new_staff = Staff(
        name=data.name.strip(),
        email=data.email.strip(),
        phone=data.phone.strip(),
        designation=data.designation.strip(),
        status=data.status.strip()
    )

    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)

    return {
        "message": "Staff member added successfully.",
        "staff_id": new_staff.id
    }


@app.put("/admin/staff/{staff_id}", tags=["Staff (Admin)"])
def admin_update_staff(
    staff_id: int,
    data: StaffUpdateRequest,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update staff member details (Admin only).
    """
    s = db.query(Staff).filter(Staff.id == staff_id).first()
    if not s:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found."
        )

    if data.name is not None:
        s.name = data.name.strip()
    if data.phone is not None:
        s.phone = data.phone.strip()
    if data.designation is not None:
        s.designation = data.designation.strip()
    if data.status is not None:
        s.status = data.status.strip()

    db.commit()
    db.refresh(s)

    return {
        "message": "Staff details updated successfully.",
        "staff": {
            "id": s.id,
            "name": s.name,
            "email": s.email,
            "phone": s.phone,
            "designation": s.designation,
            "status": s.status
        }
    }


@app.delete("/admin/staff/{staff_id}", tags=["Staff (Admin)"])
def admin_delete_staff(
    staff_id: int,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a staff member record (Admin only).
    """
    s = db.query(Staff).filter(Staff.id == staff_id).first()
    if not s:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found."
        )

    db.delete(s)
    db.commit()

    return {"message": "Staff member deleted successfully."}


# ==========================================
# 11. ADMIN DASHBOARD & REPORTING APIs
# ==========================================

@app.get("/admin/dashboard", tags=["Admin Dashboard"])
def admin_dashboard(
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Retrieve consolidated high-level statistics for the management dashboard (Admin only).
    Returns all 8 required metrics based on actual database records:
    1. Total Rooms
    2. Available Rooms
    3. Occupied Rooms
    4. Total Customers
    5. Total Bookings
    6. Confirmed Bookings
    7. Cancelled Bookings
    8. Total Revenue from recorded payments
    """
    today = date.today()
    total_rooms = db.query(Room).count()

    # Occupied rooms: rooms with Confirmed booking where check_in <= today < check_out, or room.status == 'Occupied'
    occupied_by_booking = db.query(Booking.room_id).filter(
        Booking.status == "Confirmed",
        Booking.check_in <= today,
        Booking.check_out > today
    ).distinct().all()
    occupied_ids = {r[0] for r in occupied_by_booking}

    explicit_occupied = db.query(Room.id).filter(Room.status == "Occupied").all()
    occupied_ids.update(r[0] for r in explicit_occupied)

    occupied_rooms = len(occupied_ids)
    available_rooms = max(0, total_rooms - occupied_rooms)

    total_customers = db.query(Customer).filter(
        Customer.role == "customer"
    ).count()

    total_bookings = db.query(Booking).count()

    confirmed_bookings = db.query(Booking).filter(
        Booking.status == "Confirmed"
    ).count()

    cancelled_bookings = db.query(Booking).filter(
        Booking.status == "Cancelled"
    ).count()

    # Total Revenue from recorded completed payments for confirmed bookings
    paid_booking_ids = db.query(Payment.booking_id).filter(
        Payment.payment_status == "Completed"
    ).distinct()

    total_revenue = db.query(
        func.sum(Booking.total_price)
    ).filter(
        Booking.status == "Confirmed",
        Booking.id.in_(paid_booking_ids)
    ).scalar() or 0.0

    total_staff = db.query(Staff).count()

    pending_payments = db.query(Payment).filter(
        Payment.payment_status == "Pending"
    ).count()

    occupancy_rate = round((occupied_rooms / total_rooms * 100), 1) if total_rooms > 0 else 0.0

    return {
        "total_rooms": total_rooms,
        "available_rooms": available_rooms,
        "occupied_rooms": occupied_rooms,
        "total_customers": total_customers,
        "total_bookings": total_bookings,
        "confirmed_bookings": confirmed_bookings,
        "cancelled_bookings": cancelled_bookings,
        "total_revenue": round(float(total_revenue), 2),
        "active_bookings": confirmed_bookings,
        "total_staff": total_staff,
        "pending_payments": pending_payments,
        "occupancy_rate": occupancy_rate
    }


@app.get("/admin/bookings", tags=["Admin Dashboard"])
def admin_all_bookings(
    search: str | None = None,
    status: str | None = None,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    View all bookings across the hotel with customer, room, and payment information (Admin only).
    Supports search by booking reference / customer name / email and status filter.
    """
    query = db.query(Booking)

    if status and status.strip():
        query = query.filter(Booking.status == status.strip())

    bookings = query.order_by(Booking.id.desc()).all()

    result = []
    search_term = search.strip().lower() if search else None

    for b in bookings:
        room = db.query(Room).filter(Room.id == b.room_id).first()
        cust = db.query(Customer).filter(Customer.id == b.customer_id).first()
        p = db.query(Payment).filter(Payment.booking_id == b.id).order_by(Payment.id.desc()).first()

        booking_ref = f"SE-BK-{b.id:04d}"
        cust_name = cust.name if cust else "Unknown"
        cust_email = cust.email if cust else "N/A"
        room_num = room.room_number if room else "N/A"

        if search_term:
            matches = (
                search_term in booking_ref.lower() or
                search_term == str(b.id) or
                search_term in cust_name.lower() or
                search_term in cust_email.lower() or
                search_term in room_num.lower()
            )
            if not matches:
                continue

        result.append({
            "id": b.id,
            "booking_reference": booking_ref,
            "customer_id": b.customer_id,
            "customer_name": cust_name,
            "customer_email": cust_email,
            "room_id": b.room_id,
            "room_number": room_num,
            "room_type": room.room_type if room else "Unknown",
            "check_in": str(b.check_in),
            "check_out": str(b.check_out),
            "guests": b.guests,
            "total_price": b.total_price,
            "status": b.status,
            "payment_status": p.payment_status if p else "Unpaid",
            "payment_method": p.payment_method if p else "N/A",
            "transaction_ref": p.transaction_ref if p else "N/A",
            "created_at": b.created_at.isoformat() if b.created_at else None
        })

    return result


@app.get("/admin/customers", tags=["Admin Dashboard"])
def admin_all_customers(
    search: str | None = None,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    View registered customer accounts with booking count and status (Admin only).
    Never exposes passwords.
    """
    query = db.query(Customer)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            (Customer.name.ilike(term)) |
            (Customer.email.ilike(term)) |
            (Customer.phone.ilike(term))
        )

    customers = query.order_by(Customer.id.asc()).all()

    result = []
    for c in customers:
        booking_count = db.query(Booking).filter(Booking.customer_id == c.id).count()
        result.append({
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "role": c.role,
            "status": getattr(c, "status", "Active") or "Active",
            "total_bookings": booking_count,
            "created_at": c.created_at.isoformat() if c.created_at else None
        })

    return result


@app.get("/admin/customers/{customer_id}", tags=["Admin Dashboard"])
def admin_get_customer_detail(
    customer_id: int,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    View detailed customer profile and complete booking history (Admin only).
    """
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found."
        )

    bookings = db.query(Booking).filter(
        Booking.customer_id == customer_id
    ).order_by(Booking.id.desc()).all()

    booking_list = []
    total_spent = 0.0

    for b in bookings:
        room = db.query(Room).filter(Room.id == b.room_id).first()
        p = db.query(Payment).filter(Payment.booking_id == b.id).order_by(Payment.id.desc()).first()
        if p and p.payment_status == "Completed":
            total_spent += p.amount

        booking_list.append({
            "id": b.id,
            "booking_reference": f"SE-BK-{b.id:04d}",
            "room_number": room.room_number if room else "N/A",
            "room_type": room.room_type if room else "Unknown",
            "check_in": str(b.check_in),
            "check_out": str(b.check_out),
            "guests": b.guests,
            "total_price": b.total_price,
            "status": b.status,
            "payment_status": p.payment_status if p else "Unpaid"
        })

    return {
        "id": c.id,
        "name": c.name,
        "email": c.email,
        "phone": c.phone,
        "role": c.role,
        "status": getattr(c, "status", "Active") or "Active",
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "total_bookings": len(booking_list),
        "total_spent": round(total_spent, 2),
        "bookings": booking_list
    }


@app.put("/admin/customers/{customer_id}", tags=["Admin Dashboard"])
def admin_update_customer(
    customer_id: int,
    data: AdminCustomerUpdateRequest,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update customer details, role, or status (Admin only).
    Prevents administrators from deactivating or demoting their own account.
    """
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found."
        )

    # Protect self-demotion or self-deactivation
    if c.id == admin.id:
        if data.status and data.status.strip().lower() == "inactive":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own administrator account."
            )
        if data.role and data.role.strip().lower() != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot revoke your own administrator privileges."
            )

    if data.name is not None and data.name.strip():
        c.name = data.name.strip()
    if data.phone is not None:
        c.phone = data.phone.strip()
    if data.role is not None and data.role.strip():
        valid_roles = ["customer", "admin"]
        if data.role.strip().lower() not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be 'customer' or 'admin'."
            )
        c.role = data.role.strip().lower()
    if data.status is not None and data.status.strip():
        valid_statuses = ["Active", "Inactive"]
        if data.status.strip() not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status. Must be 'Active' or 'Inactive'."
            )
        c.status = data.status.strip()

    db.commit()
    db.refresh(c)

    return {
        "message": f"Customer account #{c.id} updated successfully.",
        "customer": {
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "role": c.role,
            "status": c.status
        }
    }


@app.put("/admin/customers/{customer_id}/status", tags=["Admin Dashboard"])
def admin_update_customer_status(
    customer_id: int,
    data: AdminCustomerStatusUpdateRequest,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Safely activate or deactivate a customer account (Admin only).
    """
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found."
        )

    if c.id == admin.id and data.status == "Inactive":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own administrator account."
        )

    valid_statuses = ["Active", "Inactive"]
    if data.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be 'Active' or 'Inactive'."
        )

    c.status = data.status
    db.commit()

    return {
        "message": f"Customer #{c.id} status changed to '{data.status}'.",
        "customer_id": c.id,
        "status": c.status
    }


# ==========================================
# 12. HOUSEKEEPING MODULE (ADMIN & STAFF)
# ==========================================

@app.get("/admin/housekeeping", tags=["Housekeeping (Admin)"])
def admin_get_housekeeping(
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List all rooms with housekeeping cleaning status, last cleaned timestamp,
    and reservation status (Admin only).
    """
    today = date.today()
    rooms = db.query(Room).order_by(Room.room_number.asc()).all()

    result = []
    for r in rooms:
        # Check if currently occupied by a confirmed reservation
        active_booking = db.query(Booking).filter(
            Booking.room_id == r.id,
            Booking.status == "Confirmed",
            Booking.check_in <= today,
            Booking.check_out > today
        ).first()

        current_guest = None
        if active_booking:
            guest = db.query(Customer).filter(Customer.id == active_booking.customer_id).first()
            current_guest = {
                "booking_id": active_booking.id,
                "booking_reference": f"SE-BK-{active_booking.id:04d}",
                "name": guest.name if guest else "Guest",
                "check_out": str(active_booking.check_out)
            }

        result.append({
            "id": r.id,
            "room_number": r.room_number,
            "room_type": r.room_type,
            "price": r.price,
            "capacity": r.capacity,
            "status": r.status,
            "housekeeping_status": getattr(r, "housekeeping_status", "Clean") or "Clean",
            "last_cleaned": r.last_cleaned.isoformat() if getattr(r, "last_cleaned", None) else None,
            "current_guest": current_guest
        })

    return result


@app.put("/admin/housekeeping/{room_id}", tags=["Housekeeping (Admin)"])
def admin_update_housekeeping(
    room_id: int,
    data: HousekeepingUpdateRequest,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update room cleaning status: Clean, Dirty, Cleaning in Progress, Maintenance Required (Admin only).
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found."
        )

    valid_statuses = ["Clean", "Dirty", "Cleaning in Progress", "Maintenance Required"]
    if data.housekeeping_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid housekeeping status. Must be one of: {', '.join(valid_statuses)}"
        )

    room.housekeeping_status = data.housekeeping_status
    room.last_cleaned = datetime.now(timezone.utc)
    db.commit()
    db.refresh(room)

    return {
        "message": f"Room {room.room_number} housekeeping updated to '{data.housekeeping_status}'.",
        "room_id": room.id,
        "room_number": room.room_number,
        "housekeeping_status": room.housekeeping_status,
        "last_cleaned": room.last_cleaned.isoformat() if room.last_cleaned else None
    }


# ==========================================
# 13. REPORTS & ANALYTICS APIs (ADMIN ONLY)
# ==========================================

@app.get("/admin/analytics", tags=["Analytics (Admin)"])
def admin_get_analytics(
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Generate comprehensive analytical reports from actual database records:
    - Monthly bookings & revenue trends (last 6 months)
    - Room occupancy statistics
    - Popular room categories
    - Customer statistics & retention
    - Payment methods breakdown
    - Housekeeping summary
    """
    today = date.today()
    total_rooms = db.query(Room).count()

    # 1. Occupancy statistics
    occupied_by_booking = db.query(Booking.room_id).filter(
        Booking.status == "Confirmed",
        Booking.check_in <= today,
        Booking.check_out > today
    ).distinct().all()
    occupied_ids = {r[0] for r in occupied_by_booking}
    explicit_occupied = db.query(Room.id).filter(Room.status == "Occupied").all()
    occupied_ids.update(r[0] for r in explicit_occupied)
    occupied_count = len(occupied_ids)
    available_count = max(0, total_rooms - occupied_count)
    occupancy_pct = round((occupied_count / total_rooms * 100), 1) if total_rooms > 0 else 0.0

    # 2. Monthly bookings and revenue (last 6 months)
    # Generate last 6 months list
    months_data = []
    for i in range(5, -1, -1):
        # Calculate month and year
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        label = f"{year:04d}-{month:02d}"

        # Bookings in this month
        month_bookings = db.query(Booking).filter(
            func.strftime("%Y-%m", Booking.created_at) == label
        ).all() if "sqlite" in str(db.bind.url) else db.query(Booking).filter(
            func.to_char(Booking.created_at, "YYYY-MM") == label
        ).all()

        count = len(month_bookings)
        rev = sum(b.total_price for b in month_bookings if b.status == "Confirmed")

        months_data.append({
            "month": label,
            "bookings": count,
            "revenue": round(rev, 2)
        })

    # 3. Popular room categories
    all_rooms = db.query(Room).all()
    categories_map = {}
    for r in all_rooms:
        if r.room_type not in categories_map:
            categories_map[r.room_type] = {"room_count": 0, "booking_count": 0, "revenue": 0.0}
        categories_map[r.room_type]["room_count"] += 1

    all_confirmed_bookings = db.query(Booking).filter(Booking.status == "Confirmed").all()
    for b in all_confirmed_bookings:
        r = db.query(Room).filter(Room.id == b.room_id).first()
        if r and r.room_type in categories_map:
            categories_map[r.room_type]["booking_count"] += 1
            categories_map[r.room_type]["revenue"] += b.total_price

    popular_categories = [
        {
            "category": cat,
            "total_rooms": data["room_count"],
            "total_bookings": data["booking_count"],
            "revenue": round(data["revenue"], 2)
        }
        for cat, data in categories_map.items()
    ]

    # 4. Customer statistics
    total_cust = db.query(Customer).filter(Customer.role == "customer").count()
    active_cust = db.query(Customer).filter(
        Customer.role == "customer",
        Customer.status == "Active"
    ).count()

    # Repeat customers (more than 1 booking)
    cust_booking_counts = db.query(
        Booking.customer_id, func.count(Booking.id)
    ).group_by(Booking.customer_id).all()
    repeat_customers = sum(1 for _, cnt in cust_booking_counts if cnt > 1)

    # 5. Payment methods breakdown
    all_payments = db.query(Payment).all()
    payment_methods_map = {}
    for p in all_payments:
        method = p.payment_method or "Unknown"
        payment_methods_map[method] = payment_methods_map.get(method, 0) + 1

    # 6. Housekeeping status breakdown
    housekeeping_counts = {
        "Clean": 0,
        "Dirty": 0,
        "Cleaning in Progress": 0,
        "Maintenance Required": 0
    }
    for r in all_rooms:
        hk_status = getattr(r, "housekeeping_status", "Clean") or "Clean"
        if hk_status in housekeeping_counts:
            housekeeping_counts[hk_status] += 1
        else:
            housekeeping_counts[hk_status] = 1

    return {
        "occupancy": {
            "total_rooms": total_rooms,
            "occupied_rooms": occupied_count,
            "available_rooms": available_count,
            "occupancy_rate": occupancy_pct
        },
        "monthly_trends": months_data,
        "popular_categories": popular_categories,
        "customer_statistics": {
            "total_customers": total_cust,
            "active_customers": active_cust,
            "repeat_customers": repeat_customers
        },
        "payment_methods": payment_methods_map,
        "housekeeping_breakdown": housekeeping_counts
    }


# ==========================================
# 14. HOTEL SETTINGS APIs (ADMIN ONLY)
# ==========================================

@app.get("/admin/settings", tags=["Settings (Admin)"])
def admin_get_settings(
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Retrieve current hotel configuration and policies (Admin only).
    """
    settings = db.query(HotelSetting).first()
    if not settings:
        settings = HotelSetting(
            hotel_name="StayEase Hotel & Luxury Suites",
            contact_email="contact@stayease.com",
            contact_phone="+91 98765 43210",
            hotel_address="124 Luxury Boulevard, Central District, New Delhi, 110001",
            check_in_time="14:00",
            check_out_time="11:00",
            cancellation_policy="Free cancellation up to 24 hours prior to standard check-in time."
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return {
        "id": settings.id,
        "hotel_name": settings.hotel_name,
        "contact_email": settings.contact_email,
        "contact_phone": settings.contact_phone,
        "hotel_address": settings.hotel_address,
        "check_in_time": settings.check_in_time,
        "check_out_time": settings.check_out_time,
        "cancellation_policy": settings.cancellation_policy,
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None
    }


@app.put("/admin/settings", tags=["Settings (Admin)"])
def admin_update_settings(
    data: HotelSettingsUpdateRequest,
    admin: Customer = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update hotel metadata, contact information, and policies (Admin only).
    """
    settings = db.query(HotelSetting).first()
    if not settings:
        settings = HotelSetting()
        db.add(settings)

    if data.hotel_name is not None and data.hotel_name.strip():
        settings.hotel_name = data.hotel_name.strip()
    if data.contact_email is not None and data.contact_email.strip():
        settings.contact_email = data.contact_email.strip()
    if data.contact_phone is not None and data.contact_phone.strip():
        settings.contact_phone = data.contact_phone.strip()
    if data.hotel_address is not None and data.hotel_address.strip():
        settings.hotel_address = data.hotel_address.strip()
    if data.check_in_time is not None and data.check_in_time.strip():
        settings.check_in_time = data.check_in_time.strip()
    if data.check_out_time is not None and data.check_out_time.strip():
        settings.check_out_time = data.check_out_time.strip()
    if data.cancellation_policy is not None and data.cancellation_policy.strip():
        settings.cancellation_policy = data.cancellation_policy.strip()

    settings.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(settings)

    return {
        "message": "Hotel settings updated successfully.",
        "settings": {
            "hotel_name": settings.hotel_name,
            "contact_email": settings.contact_email,
            "contact_phone": settings.contact_phone,
            "hotel_address": settings.hotel_address,
            "check_in_time": settings.check_in_time,
            "check_out_time": settings.check_out_time,
            "cancellation_policy": settings.cancellation_policy,
            "updated_at": settings.updated_at.isoformat() if settings.updated_at else None
        }
    }


# ==========================================
# 15. CHATBOT CUSTOMER SUPPORT ASSISTANT API
# ==========================================

@app.post("/chat", tags=["Chatbot Assistant"])
@app.post("/chatbot/message", tags=["Chatbot Assistant"])
def chat_with_assistant(
    data: ChatMessageRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Intelligent customer support chatbot assistant endpoint.
    Answers general hotel questions, room rates, live availability,
    and booking guidance using rule-based Python logic and database records.
    No paid LLM API keys required.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You are sending messages too quickly. Please wait a moment and try again."
        )

    # Optional authenticated customer detection from Bearer header
    user_name = data.user_name
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            cust_id = int(payload.get("sub"))
            cust = db.query(Customer).filter(Customer.id == cust_id).first()
            if cust:
                user_name = cust.name
        except Exception:
            pass

    response_dict = StayEaseAssistant.respond(
        message=data.message,
        user_name=user_name,
        db=db
    )
    response_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return response_dict


# ==========================================
# 16. STATIC FILES / FRONTEND MOUNT
# ==========================================

if os.path.exists(PUBLIC_DIR):
    app.mount(
        "/",
        StaticFiles(directory=PUBLIC_DIR, html=True),
        name="public"
    )
