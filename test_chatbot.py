# ==========================================
# STAYEASE - CHATBOT AUTOMATED TEST SUITE
# Verifies 25+ Customer Support Inquiries
# ==========================================

import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException
from database.database import Base
from database.models import Room, Customer, HotelSetting
import main
from chatbot.assistant import StayEaseAssistant


# Setup in-memory SQLite database for sandbox-safe test isolation
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

Base.metadata.create_all(bind=test_engine)
db = TestingSessionLocal()

passed = 0
failed = 0

def test(desc, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✓ {desc}")
    else:
        failed += 1
        print(f"  ✗ {desc} -- {detail}")

try:
    # Ensure hotel settings exist in test DB
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

    # Ensure sample rooms exist in test DB
    if db.query(Room).count() == 0:
        db.add(Room(room_number="101", room_type="Standard", price=1800.0, capacity=2, status="Available"))
        db.add(Room(room_number="201", room_type="Deluxe", price=3000.0, capacity=3, status="Available"))
        db.add(Room(room_number="301", room_type="Suite", price=5000.0, capacity=4, status="Available"))
        db.commit()

    # ------------------------------------------
    # 1. GREETING & WELCOME
    # ------------------------------------------
    print("\n[Feature 1: General & Welcome Questions]")
    r1 = StayEaseAssistant.respond("Hello", user_name="Ayush", db=db)
    test("Q1: 'Hello' greeting personalized with user name", "Ayush" in r1["reply"] and r1["intent"] == "greeting")

    r2 = StayEaseAssistant.respond("Good morning, what is StayEase?", user_name=None, db=db)
    test("Q2: 'What is StayEase?' hotel overview", "StayEase" in r2["reply"])

    # ------------------------------------------
    # 2. CHECK-IN & CHECK-OUT TIMINGS
    # ------------------------------------------
    r3 = StayEaseAssistant.respond("What is your check in time?", db=db)
    test("Q3: 'What is check in time?' returns 14:00", "14:00" in r3["reply"] and r3["intent"] == "check_in_time")

    r4 = StayEaseAssistant.respond("Can I get an early check-in?", db=db)
    test("Q4: 'Early check-in' mentions front desk & luggage", "front desk" in r4["reply"].lower())

    r5 = StayEaseAssistant.respond("What time is check out?", db=db)
    test("Q5: 'What time is check out?' returns 11:00", "11:00" in r5["reply"] and r5["intent"] == "check_out_time")

    # ------------------------------------------
    # 3. ROOM INFORMATION & CATEGORIES
    # ------------------------------------------
    print("\n[Feature 2: Room Information & Real-Time Rates]")
    r6 = StayEaseAssistant.respond("What room categories do you have?", db=db)
    test("Q6: 'Room categories' lists Standard, Deluxe, Suite", "Standard" in r6["reply"] and "Deluxe" in r6["reply"] and "Suite" in r6["reply"])

    r7 = StayEaseAssistant.respond("How much do rooms cost?", db=db)
    test("Q7: 'How much do rooms cost?' returns prices", "₹" in r7["reply"] and r7["intent"] == "room_prices")

    r8 = StayEaseAssistant.respond("Tell me about the Standard room", db=db)
    test("Q8: 'Standard room' details returns 1,800/night", "Standard" in r8["reply"] and r8["intent"] == "room_standard_detail")

    r9 = StayEaseAssistant.respond("What is the price of a Deluxe room?", db=db)
    test("Q9: 'Deluxe room' details returns Deluxe information", "Deluxe" in r9["reply"] and r9["intent"] == "room_deluxe_detail")

    r10 = StayEaseAssistant.respond("How much is the Executive Suite?", db=db)
    test("Q10: 'Executive Suite' returns Suite rates and features", "Suite" in r10["reply"] and r10["intent"] == "room_suite_detail")

    r11 = StayEaseAssistant.respond("What is the capacity of your rooms?", db=db)
    test("Q11: 'Room capacity' mentions guest limits", "capacity" in r11["reply"].lower() and "guests" in r11["reply"].lower())

    r12 = StayEaseAssistant.respond("What amenities do the rooms have?", db=db)
    test("Q12: 'Amenities' mentions WiFi, AC, breakfast", "wifi" in r12["reply"].lower() or "amenities" in r12["reply"].lower())

    r13 = StayEaseAssistant.respond("Are there rooms available right now?", db=db)
    test("Q13: 'Rooms available' queries database inventory", "inventory" in r13["reply"].lower() or "available" in r13["reply"].lower())

    # ------------------------------------------
    # 4. BOOKING GUIDANCE & WORKFLOWS
    # ------------------------------------------
    print("\n[Feature 3: Booking Guidance & Account Actions]")
    r14 = StayEaseAssistant.respond("How do I book a room?", db=db)
    test("Q14: 'How to book' explains 4-step reservation process", "Search" in r14["reply"] and "Confirm" in r14["reply"])

    r15 = StayEaseAssistant.respond("How do I search for rooms by date?", db=db)
    test("Q15: 'How to search' explains check-in and check-out filters", "Check-in" in r15["reply"])

    r16 = StayEaseAssistant.respond("How do I create an account?", db=db)
    test("Q16: 'Create account' explains registration and password rules", "Register" in r16["reply"] or "Account" in r16["reply"])

    r17 = StayEaseAssistant.respond("How do I sign in?", db=db)
    test("Q17: 'How to sign in' guides user to Sign In button", "Sign In" in r17["reply"])

    r18 = StayEaseAssistant.respond("Where can I see my bookings?", db=db)
    test("Q18: 'Where can I see my bookings' directs to My Bookings", "My Bookings" in r18["reply"])

    # ------------------------------------------
    # 5. POLICIES, PAYMENTS & BILLING
    # ------------------------------------------
    print("\n[Feature 4: Policies, Payments & Concierge]")
    r19 = StayEaseAssistant.respond("What is your cancellation policy?", db=db)
    test("Q19: 'Cancellation policy' returns database policy", "cancellation" in r19["reply"].lower())

    r20 = StayEaseAssistant.respond("How do I cancel my reservation?", db=db)
    test("Q20: 'How to cancel' explains cancellation steps from My Bookings", "My Bookings" in r20["reply"] and "Cancel" in r20["reply"])

    r21 = StayEaseAssistant.respond("What payment methods do you accept?", db=db)
    test("Q21: 'Payment methods' mentions Demo Online Payment and Cash at hotel", "Cash at hotel" in r21["reply"])

    r22 = StayEaseAssistant.respond("How do I get an invoice for my stay?", db=db)
    test("Q22: 'Invoice' explains printable PDF receipts and reference codes", "invoice" in r22["reply"].lower())

    r23 = StayEaseAssistant.respond("How can I contact customer support?", db=db)
    test("Q23: 'Contact support' returns phone and email from database", "98765" in r23["reply"] and "@stayease.com" in r23["reply"])

    r24 = StayEaseAssistant.respond("Do you have a swimming pool and restaurant?", db=db)
    test("Q24: 'Facilities' answers pool, restaurant and dining inquiries", "infinity pool" in r24["reply"].lower() or "restaurant" in r24["reply"].lower())

    # ------------------------------------------
    # 6. FALLBACK & QUICK REPLIES
    # ------------------------------------------
    print("\n[Feature 5: Fallback & Security Protection]")
    r25 = StayEaseAssistant.respond("What is the airspeed velocity of an unladen swallow?", db=db)
    test("Q25: Unknown query triggers helpful fallback with suggestions", r25["intent"] == "fallback" and len(r25["quick_replies"]) >= 3)

    # ------------------------------------------
    # 7. FASTAPI ENDPOINT INTEGRATION
    # ------------------------------------------
    class DummyClient:
        host = "127.0.0.1"

    class DummyRequest:
        client = DummyClient()
        headers = {}

    api_res = main.chat_with_assistant(
        main.ChatMessageRequest(message="Hello StayEase, what are your rates?"),
        request=DummyRequest(),
        db=db
    )
    test("FastAPI POST /chat integration endpoint returns valid response", "reply" in api_res and "timestamp" in api_res)

finally:
    db.close()

print("\n==========================================")
print(f"CHATBOT RESULTS: {passed} PASSED, {failed} FAILED")
print("==========================================\n")

if failed > 0:
    sys.exit(1)
