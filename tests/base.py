"""
StayEase Test Base and In-Memory Database Isolation Fixture.
Provides isolated test database sessions and setup helpers.
"""

import unittest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base
from database.models import Customer, Room, Booking, Payment, Staff, HotelSetting
import main


class BaseTestCase(unittest.TestCase):
    """
    Base test case for all StayEase automated test suites.
    Uses an isolated in-memory SQLite database per test run.
    """

    @classmethod
    def setUpClass(cls):
        # Create an isolated in-memory SQLite database
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False}
        )
        cls.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=cls.engine
        )
        Base.metadata.create_all(bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()

        # Seed default hotel settings if not present
        if not self.db.query(HotelSetting).first():
            settings = HotelSetting(
                hotel_name="StayEase Hotel & Luxury Suites",
                contact_email="contact@stayease.com",
                contact_phone="+91 98765 43210",
                hotel_address="124 Luxury Boulevard, New Delhi",
                check_in_time="14:00",
                check_out_time="11:00",
                cancellation_policy="Free cancellation up to 24 hours prior to check-in."
            )
            self.db.add(settings)
            self.db.commit()

    def tearDown(self):
        self.db.rollback()
        try:
            for table in reversed(Base.metadata.sorted_tables):
                self.db.execute(table.delete())
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    def create_customer(self, name="Test Customer", email=None, password="Password123!", role="customer", phone="+91 98765 00000"):
        if email is None:
            import uuid
            email = f"user_{uuid.uuid4().hex[:6]}@example.com"
        hashed = main.password_hash.hash(password)
        cust = Customer(name=name, email=email, password=hashed, role=role, phone=phone, status="Active")
        self.db.add(cust)
        self.db.commit()
        self.db.refresh(cust)
        return cust

    def create_room(self, room_number="R101", room_type="Deluxe", price=2500.0, capacity=2, status="Available"):
        room = Room(
            room_number=room_number,
            room_type=room_type,
            price=price,
            capacity=capacity,
            status=status,
            description="Luxury room with modern amenities.",
            image_url="https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800"
        )
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        return room

    def create_booking(self, customer, room, check_in=None, check_out=None, guests=2, status="Confirmed"):
        today = date.today()
        c_in = check_in or (today + timedelta(days=2))
        c_out = check_out or (today + timedelta(days=5))
        nights = (c_out - c_in).days
        total_price = round(room.price * nights, 2)

        booking = Booking(
            customer_id=customer.id,
            room_id=room.id,
            check_in=c_in,
            check_out=c_out,
            total_price=total_price,
            guests=guests,
            status=status
        )
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)

        payment = Payment(
            booking_id=booking.id,
            amount=total_price,
            payment_method="Demo Online Payment",
            payment_status="Completed",
            transaction_ref=f"DEMO-{booking.id:04d}"
        )
        self.db.add(payment)
        self.db.commit()

        return booking
