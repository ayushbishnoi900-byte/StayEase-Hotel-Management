# ==========================================
# STAYEASE - DATABASE INITIALIZER
# Safe initialization & seed script
# Preserves existing customers and bookings
# ==========================================

import os
from sqlalchemy import text
from database.database import engine, Base, SessionLocal
from database.models import Room, Customer, Booking, Payment, Staff, HotelSetting
from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


def initialize_database():
    """
    Safely creates tables and seeds initial data if missing.
    NEVER deletes or drops existing customer, room, or booking data.
    """
    print("\n=== StayEase Safe Database Setup ===")

    # 1. Apply column migrations if using PostgreSQL
    if engine.dialect.name == "postgresql":
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'customer';"))
            conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'Active';"))
            conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
            conn.execute(text("ALTER TABLE rooms ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '';"))
            conn.execute(text("ALTER TABLE rooms ADD COLUMN IF NOT EXISTS image_url TEXT DEFAULT '';"))
            conn.execute(text("ALTER TABLE rooms ADD COLUMN IF NOT EXISTS housekeeping_status VARCHAR DEFAULT 'Clean';"))
            conn.execute(text("ALTER TABLE rooms ADD COLUMN IF NOT EXISTS last_cleaned TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
            conn.execute(text("ALTER TABLE rooms ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS guests INTEGER DEFAULT 1;"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
            conn.commit()
            print("✓ PostgreSQL schema columns verified and updated.")

    # 2. Create tables if they do not exist (non-destructive)
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables verified and created if missing.")

    db = SessionLocal()

    try:
        # 2. Ensure initial administrator exists
        admin_email = os.getenv("ADMIN_EMAIL", "admin@stayease.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        admin_name = os.getenv("ADMIN_NAME", "StayEase Administrator")

        existing_admin = db.query(Customer).filter(
            Customer.email == admin_email
        ).first()

        if not existing_admin:
            admin = Customer(
                name=admin_name,
                email=admin_email,
                password=password_hash.hash(admin_password),
                phone="+91 98765 43210",
                role="admin"
            )
            db.add(admin)
            db.commit()
            print(f"✓ Administrator account created: {admin_email}")
        else:
            print(f"✓ Administrator already exists: {admin_email}")

        # 3. Add sample rooms ONLY if the room catalog is completely empty
        room_count = db.query(Room).count()
        if room_count == 0:
            sample_rooms = [
                Room(
                    room_number="101",
                    room_type="Standard",
                    price=1800.0,
                    capacity=2,
                    description="Cozy room with queen bed, high-speed WiFi, work desk, and en-suite bathroom.",
                    image_url="https://images.unsplash.com/photo-1616594039964-ae9021a400a0?w=700",
                    status="Available"
                ),
                Room(
                    room_number="102",
                    room_type="Standard",
                    price=1800.0,
                    capacity=2,
                    description="Peaceful standard room facing the inner garden with air conditioning and smart TV.",
                    image_url="https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=700",
                    status="Available"
                ),
                Room(
                    room_number="201",
                    room_type="Deluxe",
                    price=3000.0,
                    capacity=3,
                    description="Spacious deluxe room with king bed, private balcony, mini-bar, and city view.",
                    image_url="https://images.unsplash.com/photo-1590490360182-c33d955571d7?w=700",
                    status="Available"
                ),
                Room(
                    room_number="202",
                    room_type="Deluxe",
                    price=3200.0,
                    capacity=3,
                    description="Premium deluxe room featuring modern interior, sofa lounger, and complimentary breakfast.",
                    image_url="https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=700",
                    status="Available"
                ),
                Room(
                    room_number="301",
                    room_type="Suite",
                    price=5000.0,
                    capacity=4,
                    description="Executive luxury suite with separated living room, jacuzzi tub, and panoramic skyline views.",
                    image_url="https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=700",
                    status="Available"
                ),
                Room(
                    room_number="302",
                    room_type="Suite",
                    price=5500.0,
                    capacity=5,
                    description="Presidential family suite with two bedrooms, dining space, and dedicated concierge access.",
                    image_url="https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=700",
                    status="Available"
                )
            ]
            db.add_all(sample_rooms)
            db.commit()
            print(f"✓ Added {len(sample_rooms)} sample rooms.")
        else:
            print(f"✓ Rooms already exist ({room_count} found). Kept existing rooms.")

        # 4. Add sample staff ONLY if staff directory is empty
        staff_count = db.query(Staff).count()
        if staff_count == 0:
            sample_staff = [
                Staff(
                    name="Rajesh Sharma",
                    email="rajesh.manager@stayease.com",
                    phone="+91 98111 22334",
                    designation="General Manager",
                    status="Active"
                ),
                Staff(
                    name="Priya Patel",
                    email="priya.reception@stayease.com",
                    phone="+91 98222 33445",
                    designation="Front Desk Receptionist",
                    status="Active"
                ),
                Staff(
                    name="Amit Verma",
                    email="amit.housekeeping@stayease.com",
                    phone="+91 98333 44556",
                    designation="Head of Housekeeping",
                    status="Active"
                ),
                Staff(
                    name="Sunil Kumar",
                    email="sunil.security@stayease.com",
                    phone="+91 98444 55667",
                    designation="Security Supervisor",
                    status="Active"
                )
            ]
            db.add_all(sample_staff)
            db.commit()
            print(f"✓ Added {len(sample_staff)} initial staff members.")
        else:
            print(f"✓ Staff members already exist ({staff_count} found).")

        # 5. Ensure default hotel settings exist
        if db.query(HotelSetting).count() == 0:
            default_setting = HotelSetting()
            db.add(default_setting)
            db.commit()
            print("✓ Default hotel settings initialized.")

        print("=== Setup Completed Successfully (No data was deleted) ===\n")

    except Exception as e:
        db.rollback()
        print(f"✗ Setup failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    initialize_database()
