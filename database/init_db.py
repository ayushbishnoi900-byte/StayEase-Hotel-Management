# ==========================================
# STAYEASE - MULTI-TENANT DATABASE INITIALIZER
# Safe initialization & seed script for SaaS Platform
# ==========================================

import os
import sys

# Ensure root project directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
from sqlalchemy import text
from database.database import engine, Base, SessionLocal
from database.models import Hotel, User, Room, Guest, Reservation, Payment, Housekeeping, Maintenance
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def initialize_database():
    """
    Safely creates multi-tenant tables and seeds initial hotel & staff accounts if missing.
    Non-destructive: preserves existing records.
    """
    print("\n=== StayEase SaaS Multi-Tenant Database Setup ===")

    # 1. Apply column migrations if using PostgreSQL
    if engine.dialect.name == "postgresql":
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS hotels (
                    id SERIAL PRIMARY KEY,
                    owner_id INTEGER,
                    hotel_name VARCHAR(150) NOT NULL,
                    address VARCHAR(255) DEFAULT '',
                    city VARCHAR(100) DEFAULT '',
                    state VARCHAR(100) DEFAULT '',
                    country VARCHAR(100) DEFAULT 'India',
                    contact_number VARCHAR(50) DEFAULT '',
                    hotel_email VARCHAR(120) DEFAULT '',
                    hotel_category VARCHAR(50) DEFAULT 'Boutique',
                    total_rooms INTEGER DEFAULT 10,
                    check_in_time VARCHAR(20) DEFAULT '14:00',
                    check_out_time VARCHAR(20) DEFAULT '11:00',
                    cancellation_policy TEXT DEFAULT 'Free cancellation up to 24 hours prior to check-in.',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(120) NOT NULL,
                    email VARCHAR(120) UNIQUE NOT NULL,
                    phone VARCHAR(50) DEFAULT '',
                    hashed_password VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'staff',
                    designation VARCHAR(100) DEFAULT '',
                    department VARCHAR(100) DEFAULT '',
                    hotel_id INTEGER REFERENCES hotels(id) ON DELETE SET NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    status VARCHAR(30) DEFAULT 'Active',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))

            conn.execute(text("ALTER TABLE rooms ADD COLUMN IF NOT EXISTS hotel_id INTEGER REFERENCES hotels(id) ON DELETE CASCADE;"))
            conn.execute(text("ALTER TABLE rooms ADD COLUMN IF NOT EXISTS operational_status VARCHAR(50) DEFAULT 'Available';"))
            conn.execute(text("ALTER TABLE rooms ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '';"))
            conn.execute(text("ALTER TABLE rooms ADD COLUMN IF NOT EXISTS image_url TEXT DEFAULT '';"))
            conn.execute(text("ALTER TABLE rooms ADD COLUMN IF NOT EXISTS housekeeping_status VARCHAR DEFAULT 'Clean';"))
            conn.execute(text("ALTER TABLE rooms ADD COLUMN IF NOT EXISTS last_cleaned TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
            conn.commit()
            print("✓ PostgreSQL schema columns verified.")

    # 2. Create tables if they do not exist
    Base.metadata.create_all(bind=engine)
    print("✓ Tables verified/created.")

    db = SessionLocal()
    try:
        # 3. Ensure Default Hotel exists
        hotel = db.query(Hotel).first()
        if not hotel:
            hotel = Hotel(
                hotel_name="Grand StayEase Palace",
                address="124 Luxury Boulevard, Central District",
                city="New Delhi",
                state="Delhi",
                country="India",
                contact_number="+91 98765 43210",
                hotel_email="contact@stayease.com",
                hotel_category="Luxury",
                total_rooms=10,
                check_in_time="14:00",
                check_out_time="11:00"
            )
            db.add(hotel)
            db.commit()
            db.refresh(hotel)
            print(f"✓ Default Hotel created: {hotel.hotel_name} (ID: {hotel.id})")

        # 4. Ensure Default Owner Account exists
        admin_email = os.getenv("ADMIN_EMAIL", "admin@stayease.com")
        owner_user = db.query(User).filter(User.email == admin_email).first()
        if not owner_user:
            owner_user = User(
                full_name=os.getenv("ADMIN_NAME", "StayEase Administrator"),
                email=admin_email,
                phone="+91 98765 43210",
                hashed_password=password_hash.hash(os.getenv("ADMIN_PASSWORD", "admin123")),
                role="owner",
                designation="Property Owner",
                department="Management",
                hotel_id=hotel.id,
                is_active=True,
                status="Active"
            )
            db.add(owner_user)
            db.commit()
            db.refresh(owner_user)
            print(f"✓ Hotel Owner account created: {admin_email}")
        else:
            if owner_user.role != "owner" or owner_user.hotel_id != hotel.id:
                owner_user.role = "owner"
                owner_user.hotel_id = hotel.id
                db.commit()

        if hotel.owner_id is None:
            hotel.owner_id = owner_user.id
            db.commit()

        # 5. Seed Demonstration Staff Accounts for all roles if not present
        staff_seed = [
            ("Rohan Mehta", "manager@stayease.com", "manager", "Operations Manager", "Front Office"),
            ("Priya Sharma", "receptionist@stayease.com", "receptionist", "Chief Receptionist", "Front Desk"),
            ("Sunita Verma", "housekeeping@stayease.com", "housekeeping", "Housekeeping Supervisor", "Housekeeping"),
            ("Anil Kapoor", "accountant@stayease.com", "accountant", "Senior Financial Auditor", "Accounts & Finance"),
            ("Rajesh Kumar", "maintenance@stayease.com", "maintenance", "Head Facility Engineer", "Maintenance")
        ]

        for s_name, s_email, s_role, s_desig, s_dept in staff_seed:
            existing_staff = db.query(User).filter(User.email == s_email).first()
            if not existing_staff:
                new_staff = User(
                    full_name=s_name,
                    email=s_email,
                    phone="+91 91234 56789",
                    hashed_password=password_hash.hash("staff123"),
                    role=s_role,
                    designation=s_desig,
                    department=s_dept,
                    hotel_id=hotel.id,
                    is_active=True,
                    status="Active"
                )
                db.add(new_staff)
                print(f"✓ Staff account seeded: {s_email} ({s_role})")
        db.commit()

        # 6. Ensure Sample Rooms exist for Hotel 1
        room_count = db.query(Room).filter(Room.hotel_id == hotel.id).count()
        if room_count == 0:
            sample_rooms = [
                Room(hotel_id=hotel.id, room_number="101", room_type="Standard", price=1800.0, capacity=2, operational_status="Available", description="Cozy queen room with high-speed WiFi and en-suite bath.", image_url="https://images.unsplash.com/photo-1616594039964-ae9021a400a0?w=700"),
                Room(hotel_id=hotel.id, room_number="102", room_type="Standard", price=1900.0, capacity=2, operational_status="Available", description="Garden view standard room with climate AC and smart TV.", image_url="https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=700"),
                Room(hotel_id=hotel.id, room_number="201", room_type="Deluxe", price=3000.0, capacity=3, operational_status="Available", description="Spacious king room with city view balcony and mini-bar.", image_url="https://images.unsplash.com/photo-1590490360182-c33d955571d7?w=700"),
                Room(hotel_id=hotel.id, room_number="202", room_type="Deluxe", price=3200.0, capacity=3, operational_status="Available", description="Designer interior with plush lounger and complimentary breakfast.", image_url="https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=700"),
                Room(hotel_id=hotel.id, room_number="301", room_type="Suite", price=5000.0, capacity=4, operational_status="Available", description="Executive suite with private living lounge and jacuzzi bath.", image_url="https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=700"),
                Room(hotel_id=hotel.id, room_number="302", room_type="Suite", price=5500.0, capacity=4, operational_status="Available", description="Presidential penthouse suite with private terrace and butler pantry.", image_url="https://images.unsplash.com/photo-1582719508461-905c673771fd?w=700")
            ]
            db.add_all(sample_rooms)
            db.commit()
            print("✓ Sample rooms seeded for Hotel.")

        # 7. Ensure Sample Guests & Walk-in Reservations exist
        guest_count = db.query(Guest).filter(Guest.hotel_id == hotel.id).count()
        if guest_count == 0:
            g1 = Guest(hotel_id=hotel.id, full_name="Arjun Varma", phone="+91 98888 12345", email="arjun.varma@example.com", address="Connaught Place, New Delhi", id_proof_type="Aadhaar Card", id_proof_number="XXXX-XXXX-4589")
            g2 = Guest(hotel_id=hotel.id, full_name="Sarah Jenkins", phone="+1 555 234 5678", email="sarah.j@example.com", address="London, UK", id_proof_type="Passport", id_proof_number="GB9876543")
            db.add_all([g1, g2])
            db.commit()
            db.refresh(g1)
            db.refresh(g2)

            r101 = db.query(Room).filter(Room.hotel_id == hotel.id, Room.room_number == "101").first()
            r201 = db.query(Room).filter(Room.hotel_id == hotel.id, Room.room_number == "201").first()

            today = date.today()
            if r101 and r201:
                res1 = Reservation(
                    hotel_id=hotel.id, guest_id=g1.id, room_id=r101.id,
                    check_in=today, check_out=today + timedelta(days=2),
                    number_of_guests=2, total_amount=3600.0, booking_source="Walk-in", status="Checked In"
                )
                res2 = Reservation(
                    hotel_id=hotel.id, guest_id=g2.id, room_id=r201.id,
                    check_in=today + timedelta(days=1), check_out=today + timedelta(days=4),
                    number_of_guests=2, total_amount=9000.0, booking_source="Phone", status="Confirmed"
                )
                db.add_all([res1, res2])
                db.commit()
                db.refresh(res1)
                db.refresh(res2)

                p1 = Payment(hotel_id=hotel.id, reservation_id=res1.id, amount=3600.0, payment_method="Cash", payment_status="Completed", transaction_reference="CASH-RES-001")
                p2 = Payment(hotel_id=hotel.id, reservation_id=res2.id, amount=9000.0, payment_method="Credit Card", payment_status="Completed", transaction_reference="CARD-RES-002")
                db.add_all([p1, p2])
                db.commit()
                print("✓ Sample guests, reservations, and payments seeded.")

        print("=== Multi-Tenant Database Initialization Complete! ===\n")
    finally:
        db.close()


if __name__ == "__main__":
    initialize_database()
