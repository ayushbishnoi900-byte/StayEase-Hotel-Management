# ==========================================
# STAYEASE - DATABASE MODELS
# Defines all entities used in the system
# ==========================================

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from database.database import Base


# ==========================================
# 1. Room Table
# ==========================================

class Room(Base):

    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)

    room_number = Column(String, unique=True, nullable=False)

    room_type = Column(String, nullable=False)  # Standard, Deluxe, Suite

    price = Column(Float, nullable=False)

    capacity = Column(Integer, nullable=False)

    status = Column(String, default="Available")  # Available, Occupied, Maintenance

    description = Column(String, default="")

    image_url = Column(String, default="")

    # Housekeeping module status: Clean, Dirty, Cleaning in Progress, Maintenance Required
    housekeeping_status = Column(String, default="Clean")

    last_cleaned = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    bookings = relationship("Booking", back_populates="room")


# ==========================================
# 2. Customer Table (Users)
# ==========================================

class Customer(Base):

    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    email = Column(String, unique=True, nullable=False)

    password = Column(String, nullable=False)

    phone = Column(String, default="")

    role = Column(String, default="customer")  # customer, admin

    status = Column(String, default="Active")  # Active, Inactive

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    bookings = relationship("Booking", back_populates="customer")


# ==========================================
# 3. Booking Table
# ==========================================

class Booking(Base):

    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        index=True,
        nullable=False
    )

    room_id = Column(
        Integer,
        ForeignKey("rooms.id"),
        index=True,
        nullable=False
    )

    check_in = Column(Date, nullable=False)

    check_out = Column(Date, nullable=False)

    total_price = Column(Float, nullable=False)

    guests = Column(Integer, default=1)

    status = Column(String, default="Confirmed")  # Confirmed, Cancelled, Completed

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    customer = relationship("Customer", back_populates="bookings")

    room = relationship("Room", back_populates="bookings")

    payments = relationship(
        "Payment",
        back_populates="booking",
        cascade="all, delete-orphan"
    )


# ==========================================
# 4. Payment Table
# ==========================================

class Payment(Base):

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    booking_id = Column(
        Integer,
        ForeignKey("bookings.id"),
        index=True,
        nullable=False
    )

    amount = Column(Float, nullable=False)

    payment_method = Column(String, nullable=False)  # "Cash at hotel", "Demo Online Payment"

    payment_status = Column(String, default="Completed")  # "Pending", "Completed", "Refunded", "Failed"

    transaction_ref = Column(String, unique=True, index=True, nullable=False)

    payment_date = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    booking = relationship("Booking", back_populates="payments")


# ==========================================
# 5. Staff Table
# ==========================================

class Staff(Base):

    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    email = Column(String, unique=True, nullable=False)

    phone = Column(String, default="")

    designation = Column(String, nullable=False)  # "Manager", "Receptionist", "Housekeeping", "Security"

    status = Column(String, default="Active")  # "Active", "On Leave", "Inactive"

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )


# ==========================================
# 6. Hotel Settings Table
# ==========================================

class HotelSetting(Base):

    __tablename__ = "hotel_settings"

    id = Column(Integer, primary_key=True, index=True)

    hotel_name = Column(String, default="StayEase Hotel & Luxury Suites")

    contact_email = Column(String, default="contact@stayease.com")

    contact_phone = Column(String, default="+91 98765 43210")

    hotel_address = Column(String, default="124 Luxury Boulevard, Central District, New Delhi, 110001")

    check_in_time = Column(String, default="14:00")

    check_out_time = Column(String, default="11:00")

    cancellation_policy = Column(
        String,
        default="Free cancellation up to 24 hours prior to standard check-in time."
    )

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )
