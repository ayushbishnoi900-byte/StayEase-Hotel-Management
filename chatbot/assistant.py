# ==========================================
# STAYEASE - CHATBOT ASSISTANT ENGINE
# Rule-Based Customer Support Assistant
# No external LLM credits required
# ==========================================

import re
import time
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.models import Room, HotelSetting


class RateLimiter:
    """
    Sliding-window in-memory rate limiter to prevent message flooding and spam.
    Tracks timestamps per client IP.
    """
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.client_records = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        timestamps = self.client_records[client_ip]
        # Purge timestamps outside the window
        self.client_records[client_ip] = [t for t in timestamps if now - t < self.window_seconds]
        if len(self.client_records[client_ip]) >= self.max_requests:
            return False
        self.client_records[client_ip].append(now)
        return True


rate_limiter = RateLimiter(max_requests=35, window_seconds=60)


class StayEaseAssistant:
    """
    Intelligent rule-based virtual concierge for StayEase.
    Identifies customer intents, extracts entities, queries live database records,
    and returns informative, context-aware responses with quick replies.
    """

    @classmethod
    def get_hotel_settings(cls, db: Session) -> dict:
        """
        Fetches current hotel details from the database.
        """
        settings = db.query(HotelSetting).first()
        if not settings:
            return {
                "hotel_name": "StayEase Hotel & Luxury Suites",
                "contact_email": "contact@stayease.com",
                "contact_phone": "+91 98765 43210",
                "hotel_address": "124 Luxury Boulevard, Central District, New Delhi, 110001",
                "check_in_time": "14:00",
                "check_out_time": "11:00",
                "cancellation_policy": "Free cancellation up to 24 hours prior to standard check-in time."
            }
        return {
            "hotel_name": settings.hotel_name or "StayEase Hotel & Luxury Suites",
            "contact_email": settings.contact_email or "contact@stayease.com",
            "contact_phone": settings.contact_phone or "+91 98765 43210",
            "hotel_address": settings.hotel_address or "124 Luxury Boulevard, Central District, New Delhi",
            "check_in_time": settings.check_in_time or "14:00",
            "check_out_time": settings.check_out_time or "11:00",
            "cancellation_policy": settings.cancellation_policy or "Free cancellation up to 24 hours prior to check-in."
        }

    @classmethod
    def get_room_summary(cls, db: Session) -> dict:
        """
        Queries live room data from the database.
        """
        rooms = db.query(Room).all()
        categories = sorted(list({r.room_type for r in rooms}))
        available_count = sum(1 for r in rooms if r.status == "Available")

        rates = {}
        capacities = {}
        for r in rooms:
            if r.room_type not in rates:
                rates[r.room_type] = []
                capacities[r.room_type] = r.capacity
            rates[r.room_type].append(r.price)

        rate_summary = {}
        for cat, prices in rates.items():
            min_p = min(prices)
            max_p = max(prices)
            if min_p == max_p:
                rate_summary[cat] = f"₹{int(min_p):,}"
            else:
                rate_summary[cat] = f"₹{int(min_p):,} – ₹{int(max_p):,}"

        return {
            "total_rooms": len(rooms),
            "available_count": available_count,
            "categories": categories,
            "rates": rate_summary,
            "capacities": capacities
        }

    @classmethod
    def respond(cls, message: str, user_name: str | None = None, db: Session = None) -> dict:
        """
        Analyzes customer query, detects intent, queries DB where needed,
        and constructs an appropriate response.
        """
        text = message.strip().lower()
        # Clean special chars for matching
        clean_text = re.sub(r"[^\w\s-]", " ", text)
        words = set(clean_text.split())

        hotel = cls.get_hotel_settings(db) if db else {
            "hotel_name": "StayEase Hotel & Luxury Suites",
            "contact_email": "contact@stayease.com",
            "contact_phone": "+91 98765 43210",
            "hotel_address": "124 Luxury Boulevard, Central District, New Delhi",
            "check_in_time": "14:00",
            "check_out_time": "11:00",
            "cancellation_policy": "Free cancellation up to 24 hours prior to check-in."
        }

        rooms_info = cls.get_room_summary(db) if db else {
            "total_rooms": 5,
            "available_count": 5,
            "categories": ["Standard", "Deluxe", "Suite"],
            "rates": {"Standard": "₹1,800", "Deluxe": "₹3,000 – ₹3,200", "Suite": "₹5,000"},
            "capacities": {"Standard": 2, "Deluxe": 3, "Suite": 4}
        }

        name_greeting = f" {user_name}" if user_name else ""

        # ----------------------------------------------------
        # 1. GREETING & WELCOME
        # ----------------------------------------------------
        greeting_words = {"hello", "hi", "hey", "greetings", "namaste", "good morning", "good evening", "good afternoon"}
        if any(w in clean_text for w in greeting_words) and len(words) <= 5:
            return {
                "reply": f"Hello{name_greeting}! Welcome to {hotel['hotel_name']}. I am your automated virtual concierge. How may I assist your stay today? You can ask about our room categories, rates, availability, booking process, or hotel policies.",
                "intent": "greeting",
                "quick_replies": ["Explore Rooms", "Check Prices", "How to Book", "Check-in Times"],
                "action": "none"
            }

        # ----------------------------------------------------
        # 2. CHECK-IN TIMINGS
        # ----------------------------------------------------
        if any(p in clean_text for p in ["check-in", "check in", "checkin", "arrival time", "when can i arrive", "early check"]):
            return {
                "reply": f"Standard check-in begins at {hotel['check_in_time']}. If you anticipate arriving earlier, our 24/7 front desk can hold your luggage safely until your suite is prepared.",
                "intent": "check_in_time",
                "quick_replies": ["Check-out Time", "Explore Rooms", "Contact Concierge"],
                "action": "none"
            }

        # ----------------------------------------------------
        # 3. CHECK-OUT TIMINGS
        # ----------------------------------------------------
        if any(p in clean_text for p in ["check-out", "check out", "checkout", "departure time", "when to leave", "late checkout", "leave room"]):
            return {
                "reply": f"Standard check-out is until {hotel['check_out_time']}. Express digital check-out is supported. If you require a late departure, please inquire with our front desk in advance.",
                "intent": "check_out_time",
                "quick_replies": ["Check-in Time", "My Bookings", "Contact Front Desk"],
                "action": "none"
            }

        # ----------------------------------------------------
        # 4. SPECIFIC ROOM TYPE INQUIRY (Standard / Deluxe / Suite)
        # ----------------------------------------------------
        if "suite" in clean_text or "executive suite" in clean_text or "penthouse" in clean_text:
            rate = rooms_info["rates"].get("Suite", "₹5,000")
            cap = rooms_info["capacities"].get("Suite", 4)
            return {
                "reply": f"Our Executive Luxury Suites are priced at {rate}/night with capacity for up to {cap} guests. They feature panoramic skyline views, a separate private living lounge, jacuzzi spa bath, and complimentary breakfast.",
                "intent": "room_suite_detail",
                "quick_replies": ["Explore Rooms", "Deluxe Room Rates", "How to Book"],
                "action": "navigate:rooms"
            }

        if "deluxe" in clean_text:
            rate = rooms_info["rates"].get("Deluxe", "₹3,000")
            cap = rooms_info["capacities"].get("Deluxe", 3)
            return {
                "reply": f"Our Deluxe Rooms are priced at {rate}/night and accommodate up to {cap} guests. They feature king bedding, a private balcony with city or garden views, mini-bar, and high-speed WiFi.",
                "intent": "room_deluxe_detail",
                "quick_replies": ["Explore Rooms", "Suite Rates", "How to Book"],
                "action": "navigate:rooms"
            }

        if "standard" in clean_text:
            rate = rooms_info["rates"].get("Standard", "₹1,800")
            cap = rooms_info["capacities"].get("Standard", 2)
            return {
                "reply": f"Our Standard Rooms are priced at {rate}/night and accommodate up to {cap} guests. They provide queen bedding, climate AC, dedicated work desk, smart TV, and complimentary breakfast.",
                "intent": "room_standard_detail",
                "quick_replies": ["Explore Rooms", "Deluxe Rates", "How to Book"],
                "action": "navigate:rooms"
            }

        # ----------------------------------------------------
        # 5. ROOM PRICING & TARIFFS
        # ----------------------------------------------------
        if any(w in clean_text for w in ["price", "prices", "cost", "costs", "rate", "rates", "pricing", "tariff", "how much", "charge"]):
            rates_text = ", ".join([f"{cat} ({p}/night)" for cat, p in rooms_info["rates"].items()])
            return {
                "reply": f"Current nightly rates: {rates_text}. All total prices are calculated automatically by the backend as: Number of Nights × Room Price per Night, with zero hidden booking charges.",
                "intent": "room_prices",
                "quick_replies": ["Explore Rooms", "How to Book", "Cancellation Policy"],
                "action": "navigate:rooms"
            }

        # ----------------------------------------------------
        # 6. ROOM CATEGORIES & SUITES OVERVIEW
        # ----------------------------------------------------
        if any(p in clean_text for p in ["category", "categories", "types of room", "room type", "what rooms", "kinds of room"]):
            cat_list = ", ".join(rooms_info["categories"])
            return {
                "reply": f"StayEase features three curated categories: {cat_list}. Each tier is furnished with hypoallergenic bedding, en-suite bathroom, climate AC, and complimentary high-speed WiFi.",
                "intent": "room_categories",
                "quick_replies": ["Check Prices", "Suite Rates", "Book a Room"],
                "action": "navigate:rooms"
            }

        # ----------------------------------------------------
        # 7. ROOM CAPACITY / GUEST LIMITS
        # ----------------------------------------------------
        if any(w in clean_text for w in ["capacity", "guests", "how many people", "family", "max guests", "persons", "occupancy"]):
            return {
                "reply": "Our room capacities: Standard Rooms host up to 2 guests, Deluxe Rooms host up to 3 guests, and Executive Suites comfortably host up to 4 guests. You can filter rooms by capacity using our search bar.",
                "intent": "room_capacity",
                "quick_replies": ["Explore Rooms", "Check Prices", "How to Book"],
                "action": "navigate:rooms"
            }

        # ----------------------------------------------------
        # 8. LIVE ROOM AVAILABILITY
        # ----------------------------------------------------
        if any(w in clean_text for w in ["available", "availability", "vacant", "free room", "any room available", "rooms left"]):
            return {
                "reply": f"There are currently {rooms_info['available_count']} rooms active in our inventory. To view live availability for your exact stay dates, use the date picker in the floating Search Bar at the top of the page.",
                "intent": "room_availability",
                "quick_replies": ["Explore Rooms", "Check Prices", "How to Book"],
                "action": "navigate:rooms"
            }

        # ----------------------------------------------------
        # 9. HOW TO BOOK A ROOM (GUIDANCE)
        # ----------------------------------------------------
        if any(p in clean_text for p in ["how to book", "how do i book", "how can i book", "booking guide", "make reservation", "make a reservation", "reserve a room", "book a room", "steps to book"]):
            return {
                "reply": "Booking is quick and simple: 1. Enter your stay dates and guests in the top Search bar. 2. Browse available suites and click 'Book Now'. 3. Sign in (or register for free). 4. Review the booking confirmation breakdown and click 'Confirm Reservation'!",
                "intent": "booking_guide",
                "quick_replies": ["Explore Rooms", "How to Register", "Payment Methods"],
                "action": "navigate:rooms"
            }

        # ----------------------------------------------------
        # 10. HOW TO SEARCH ROOMS
        # ----------------------------------------------------
        if any(p in clean_text for p in ["how to search", "how do i search", "filter room", "search by date", "search room", "search for room", "search for rooms", "find room", "find a room", "search"]):
            return {
                "reply": "In the floating Search Bar, select your Check-in and Check-out dates, desired guest capacity, and room category. Click 'Check Availability' — the backend will immediately filter out any already-reserved rooms.",
                "intent": "search_guide",
                "quick_replies": ["Explore Rooms", "Check Prices", "How to Book"],
                "action": "navigate:rooms"
            }

        # ----------------------------------------------------
        # 11. REGISTRATION & ACCOUNT CREATION
        # ----------------------------------------------------
        if any(p in clean_text for p in ["how to register", "how do i register", "create account", "create an account", "sign up", "signing up", "new account", "registration", "make account", "register"]):
            return {
                "reply": "To create an account, click 'Book a Room' or 'Register' in the top navigation bar. Enter your full name, email, phone, and a secure password (minimum 8 characters). Password security is guarded with Argon2 encryption.",
                "intent": "registration_guide",
                "quick_replies": ["How to Login", "How to Book", "Booking Help"],
                "action": "open:auth"
            }

        # ----------------------------------------------------
        # 12. LOGIN & SIGN IN
        # ----------------------------------------------------
        if any(p in clean_text for p in ["how to login", "how do i login", "how to sign in", "how do i sign in", "log in", "sign in", "login"]):
            return {
                "reply": "Click 'Sign In' in the top navigation bar. Enter your email address and password. Once authenticated, your personalized customer profile dropdown and booking history become accessible.",
                "intent": "login_guide",
                "quick_replies": ["How to Register", "My Bookings Help", "Explore Rooms"],
                "action": "open:auth"
            }

        # ----------------------------------------------------
        # 13. VIEW MY BOOKINGS
        # ----------------------------------------------------
        if any(p in clean_text for p in ["my booking", "my bookings", "view booking", "view my booking", "see my booking", "see my bookings", "booking history", "my reservation", "where are my booking", "where can i see"]):
            return {
                "reply": "You can view all your reservations by clicking 'My Bookings' in the top navigation bar or from your customer profile dropdown. You can filter by Upcoming, Completed, and Cancelled stays.",
                "intent": "my_bookings_guide",
                "quick_replies": ["How to Cancel", "Print Invoice", "Explore Rooms"],
                "action": "navigate:my-bookings"
            }

        # ----------------------------------------------------
        # 14. CANCELLATION POLICY
        # ----------------------------------------------------
        if any(p in clean_text for p in ["cancellation policy", "refund policy", "can i cancel", "free cancellation", "penalty", "cancellation rule"]):
            return {
                "reply": f"Our cancellation policy: {hotel['cancellation_policy']} Cancelled dates are immediately returned to inventory, and no penalties apply when cancelled within the eligible window.",
                "intent": "cancellation_policy",
                "quick_replies": ["How to Cancel", "My Bookings", "Contact Concierge"],
                "action": "none"
            }

        # ----------------------------------------------------
        # 15. HOW TO CANCEL BOOKING
        # ----------------------------------------------------
        if any(p in clean_text for p in ["how to cancel", "how do i cancel", "cancel booking", "cancel my reservation", "cancel room", "cancelling"]):
            return {
                "reply": "To cancel a booking: 1. Sign in to your account. 2. Click 'My Bookings' in the navigation bar. 3. Locate the reservation and click 'Cancel Booking'. 4. Confirm the prompt. The room will be immediately released.",
                "intent": "cancel_guide",
                "quick_replies": ["Cancellation Policy", "My Bookings", "Contact Support"],
                "action": "navigate:my-bookings"
            }

        # ----------------------------------------------------
        # 16. PAYMENT METHODS & CASH AT HOTEL
        # ----------------------------------------------------
        if any(w in clean_text for w in ["payment", "pay", "credit card", "upi", "cash", "how to pay", "payment method", "pay at hotel"]):
            return {
                "reply": "StayEase supports two payment options: 1. 'Demo Online Payment' (instant simulated card or UPI checkout for project demonstration). 2. 'Cash at hotel' (settle your bill in person at the front desk upon arrival).",
                "intent": "payment_methods",
                "quick_replies": ["How to Book", "Print Invoice", "Cancellation Policy"],
                "action": "none"
            }

        # ----------------------------------------------------
        # 17. INVOICE, BILLS & RECEIPTS
        # ----------------------------------------------------
        if any(w in clean_text for w in ["invoice", "bill", "receipt", "billing", "tax invoice", "print invoice", "download invoice"]):
            return {
                "reply": "Official invoices with unique invoice numbers (e.g. INV-2026-XXXXX) and transaction references are generated for every confirmed reservation. You can view, print, or save them as PDF anytime from 'My Bookings'.",
                "intent": "invoice_billing",
                "quick_replies": ["My Bookings", "How to Book", "Payment Methods"],
                "action": "navigate:my-bookings"
            }

        # ----------------------------------------------------
        # 18. AMENITIES, FACILITIES & SPA
        # ----------------------------------------------------
        if any(w in clean_text for w in ["amenities", "facilities", "wifi", "pool", "swimming", "breakfast", "food", "dining", "restaurant", "spa", "gym", "parking"]):
            return {
                "reply": f"{hotel['hotel_name']} features a skyline heated infinity pool, fine-dining restaurant with artisanal breakfasts, restorative massage spa, 24/7 concierge, private parking, and high-speed WiFi throughout.",
                "intent": "facilities_amenities",
                "quick_replies": ["Explore Rooms", "Check Prices", "Contact Concierge"],
                "action": "navigate:about"
            }

        # ----------------------------------------------------
        # 19. HOTEL INFO & LOCATION
        # ----------------------------------------------------
        if any(p in clean_text for p in ["about hotel", "hotel info", "where is hotel", "location", "address", "tell me about hotel", "who are you", "what is stayease"]):
            return {
                "reply": f"{hotel['hotel_name']} is situated at {hotel['hotel_address']}. We are a premier hospitality residence offering curated luxury suites, 24/7 royal concierge service, and verified live digital reservations.",
                "intent": "hotel_info",
                "quick_replies": ["Explore Rooms", "Check-in Times", "Contact Concierge"],
                "action": "navigate:about"
            }

        # ----------------------------------------------------
        # 20. CONTACT & SUPPORT
        # ----------------------------------------------------
        if any(w in clean_text for w in ["contact", "support", "phone", "email", "front desk", "reception", "call", "help desk", "number"]):
            return {
                "reply": f"Our 24/7 concierge desk is here to assist: Phone: {hotel['contact_phone']} | Email: {hotel['contact_email']} | Property Address: {hotel['hotel_address']}. You can also submit an inquiry directly through our Contact section.",
                "intent": "contact_support",
                "quick_replies": ["Contact Concierge", "Check-in Times", "Explore Rooms"],
                "action": "navigate:contact"
            }

        # ----------------------------------------------------
        # 21. FALLBACK RESPONSE
        # ----------------------------------------------------
        return {
            "reply": f"I am the StayEase Assistant, programmed to guide you through hotel accommodations, rates, and bookings. I didn't quite understand that. Would you like assistance with room rates, available suites, booking instructions, or hotel policies?",
            "intent": "fallback",
            "quick_replies": ["Explore Rooms", "Check Prices", "How to Book", "Cancellation Policy", "Contact Support"],
            "action": "none"
        }
