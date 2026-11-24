# ==========================================
# STAYEASE - MULTI-TENANT SAAS DATABASE MODELS
# B2B Platform for Hotel Owners and Staff
# ==========================================

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship, synonym
from datetime import datetime, timezone

from database.database import Base


# ==========================================
# 1. Hotels Table (Tenants)
# ==========================================

class Hotel(Base):
    __tablename__ = "hotels"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, nullable=True, index=True)
    hotel_name = Column(String(150), nullable=False)
    address = Column(String(255), default="")
    city = Column(String(100), default="")
    state = Column(String(100), default="")
    country = Column(String(100), default="India")
    contact_number = Column(String(50), default="")
    hotel_email = Column(String(120), default="")
    hotel_category = Column(String(50), default="Boutique")  # Boutique, Luxury, Resort, Business, Budget
    total_rooms = Column(Integer, default=10)
    check_in_time = Column(String(20), default="14:00")
    check_out_time = Column(String(20), default="11:00")
    cancellation_policy = Column(
        Text,
        default="Free cancellation up to 24 hours prior to standard check-in time."
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    users = relationship("User", back_populates="hotel", cascade="all, delete-orphan", foreign_keys="User.hotel_id")
    rooms = relationship("Room", back_populates="hotel", cascade="all, delete-orphan")
    guests = relationship("Guest", back_populates="hotel", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="hotel", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="hotel", cascade="all, delete-orphan")
    housekeeping_tasks = relationship("Housekeeping", back_populates="hotel", cascade="all, delete-orphan")
    maintenance_records = relationship("Maintenance", back_populates="hotel", cascade="all, delete-orphan")

    # Synonym aliases for backwards compatibility
    contact_email = synonym("hotel_email")
    contact_phone = synonym("contact_number")
    hotel_address = synonym("address")

    def __init__(self, **kwargs):
        if "contact_email" in kwargs:
            kwargs["hotel_email"] = kwargs.pop("contact_email")
        if "contact_phone" in kwargs:
            kwargs["contact_number"] = kwargs.pop("contact_phone")
        if "hotel_address" in kwargs:
            kwargs["address"] = kwargs.pop("hotel_address")
        super().__init__(**kwargs)


# ==========================================
# 2. Users Table (Owners & Staff)
# ==========================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    phone = Column(String(50), default="")
    hashed_password = Column(String(255), nullable=True)

    # Platform roles: owner, manager, receptionist, housekeeping, accountant, maintenance
    role = Column(String(50), nullable=False, default="staff")
    designation = Column(String(100), default="")
    department = Column(String(100), default="")

    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    status = Column(String(30), default="Active")  # Active, Inactive, On Leave

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    hotel = relationship("Hotel", back_populates="users", foreign_keys=[hotel_id])

    # Backward-compatibility synonyms
    name = synonym("full_name")
    password = synonym("hashed_password")

    def __init__(self, **kwargs):
        if "name" in kwargs:
            kwargs["full_name"] = kwargs.pop("name")
        if "password" in kwargs:
            kwargs["hashed_password"] = kwargs.pop("password")
        if not kwargs.get("hashed_password"):
            from pwdlib import PasswordHash
            kwargs["hashed_password"] = PasswordHash.recommended().hash("staff123")
        if "hotel_id" not in kwargs:
            kwargs["hotel_id"] = 1
        super().__init__(**kwargs)


# ==========================================
# 3. Rooms Table
# ==========================================

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    room_number = Column(String(50), nullable=False)
    room_type = Column(String(50), nullable=False)  # Standard, Deluxe, Suite
    description = Column(Text, default="")
    price = Column(Float, nullable=False)
    capacity = Column(Integer, nullable=False, default=2)

    housekeeping_status = Column(String(50), default="Clean")  # Clean, Dirty, In Progress, Inspection Needed
    operational_status = Column(String(50), default="Available")  # Available, Occupied, Maintenance, Reserved
    status = Column(String(50), default="Available")  # Backwards compatibility alias for operational_status

    image_url = Column(Text, default="")
    last_cleaned = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    hotel = relationship("Hotel", back_populates="rooms")
    reservations = relationship("Reservation", back_populates="room", cascade="all, delete-orphan")
    housekeeping_tasks = relationship("Housekeeping", back_populates="room", cascade="all, delete-orphan")
    maintenance_records = relationship("Maintenance", back_populates="room", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        if "hotel_id" not in kwargs:
            kwargs["hotel_id"] = 1
        super().__init__(**kwargs)

    # Compatibility alias for legacy booking references
    @property
    def bookings(self):
        return self.reservations


# ==========================================
# 4. Guests Table (Hotel Guests, NOT platform users)
# ==========================================

class Guest(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name = Column(String(120), nullable=False)
    phone = Column(String(50), nullable=False)
    email = Column(String(120), default="")
    address = Column(String(255), default="")
    id_proof_type = Column(String(50), default="Government ID")  # Passport, National ID, Driver License
    id_proof_number = Column(String(100), default="")

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    hotel = relationship("Hotel", back_populates="guests")
    reservations = relationship("Reservation", back_populates="guest", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        if "name" in kwargs:
            kwargs["full_name"] = kwargs.pop("name")
        if "hotel_id" not in kwargs:
            kwargs["hotel_id"] = 1
        super().__init__(**kwargs)

    @property
    def name(self):
        return self.full_name

    @name.setter
    def name(self, val):
        self.full_name = val


# ==========================================
# 5. Reservations Table
# ==========================================

class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    guest_id = Column(Integer, ForeignKey("guests.id", ondelete="RESTRICT"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True)

    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    number_of_guests = Column(Integer, default=1)
    total_amount = Column(Float, nullable=False)

    booking_source = Column(String(50), default="Walk-in")  # Walk-in, Phone, Direct, Corporate
    status = Column(String(50), default="Confirmed")  # Confirmed, Checked In, Checked Out, Cancelled
    special_requests = Column(Text, default="")

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    hotel = relationship("Hotel", back_populates="reservations")
    guest = relationship("Guest", back_populates="reservations")
    room = relationship("Room", back_populates="reservations")
    payments = relationship("Payment", back_populates="reservation", cascade="all, delete-orphan")

    # Compatibility synonyms for legacy booking code
    customer_id = synonym("guest_id")
    total_price = synonym("total_amount")
    guests = synonym("number_of_guests")

    def __init__(self, **kwargs):
        if "customer_id" in kwargs:
            kwargs["guest_id"] = kwargs.pop("customer_id")
        if "total_price" in kwargs:
            kwargs["total_amount"] = kwargs.pop("total_price")
        if "guests" in kwargs:
            kwargs["number_of_guests"] = kwargs.pop("guests")
        if "hotel_id" not in kwargs:
            kwargs["hotel_id"] = 1
        super().__init__(**kwargs)

    @property
    def customer(self):
        return self.guest


# ==========================================
# 6. Payments Table
# ==========================================

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    reservation_id = Column(Integer, ForeignKey("reservations.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), nullable=False)  # Cash, Credit Card, Debit Card, UPI, Bank Transfer
    payment_status = Column(String(50), default="Completed")  # Completed, Pending, Refunded, Failed
    transaction_reference = Column(String(100), unique=True, index=True, nullable=False)

    payment_date = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    hotel = relationship("Hotel", back_populates="payments")
    reservation = relationship("Reservation", back_populates="payments")

    # Compatibility synonyms
    booking_id = synonym("reservation_id")
    transaction_ref = synonym("transaction_reference")

    def __init__(self, **kwargs):
        if "booking_id" in kwargs:
            kwargs["reservation_id"] = kwargs.pop("booking_id")
        if "transaction_ref" in kwargs:
            kwargs["transaction_reference"] = kwargs.pop("transaction_ref")
        if "hotel_id" not in kwargs:
            kwargs["hotel_id"] = 1
        super().__init__(**kwargs)


# ==========================================
# 7. Housekeeping Tasks Table
# ==========================================

class Housekeeping(Base):
    __tablename__ = "housekeeping"

    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_staff_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    cleaning_status = Column(String(50), default="Dirty")  # Clean, Dirty, In Progress, Inspection Needed
    notes = Column(Text, default="")
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    hotel = relationship("Hotel", back_populates="housekeeping_tasks")
    room = relationship("Room", back_populates="housekeeping_tasks")
    assigned_staff = relationship("User", foreign_keys=[assigned_staff_id])


# ==========================================
# 8. Maintenance Requests Table
# ==========================================

class Maintenance(Base):
    __tablename__ = "maintenance"

    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    reported_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    issue_description = Column(Text, nullable=False)
    priority = Column(String(30), default="Medium")  # Low, Medium, High, Urgent
    status = Column(String(50), default="Reported")  # Reported, In Progress, Resolved
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    hotel = relationship("Hotel", back_populates="maintenance_records")
    room = relationship("Room", back_populates="maintenance_records")
    reporter = relationship("User", foreign_keys=[reported_by])


# ==========================================
# 9. Backward Compatibility Aliases
# ==========================================

Customer = User
Booking = Reservation
HotelSetting = Hotel
Staff = User
