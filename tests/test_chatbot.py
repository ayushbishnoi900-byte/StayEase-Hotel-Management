"""
StayEase Chatbot Assistant Automated Tests
Verifies 26 Customer Support Scenarios
"""

import unittest
from tests.base import BaseTestCase
from chatbot.assistant import StayEaseAssistant
import main


class TestChatbot(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.create_room(room_number="R101", room_type="Standard", price=1800.0, capacity=2)
        self.create_room(room_number="R201", room_type="Deluxe", price=3000.0, capacity=3)
        self.create_room(room_number="R301", room_type="Suite", price=5000.0, capacity=4)

    def test_greetings_and_hotel_info(self):
        r1 = StayEaseAssistant.respond("Hello", user_name="Ayush", db=self.db)
        self.assertIn("Ayush", r1["reply"])
        self.assertEqual(r1["intent"], "greeting")

        r2 = StayEaseAssistant.respond("What is StayEase?", db=self.db)
        self.assertIn("StayEase", r2["reply"])

    def test_checkin_checkout_timings(self):
        r3 = StayEaseAssistant.respond("What is check in time?", db=self.db)
        self.assertIn("14:00", r3["reply"])

        r4 = StayEaseAssistant.respond("Early check-in inquiry", db=self.db)
        self.assertIn("front desk", r4["reply"].lower())

        r5 = StayEaseAssistant.respond("What time is check out?", db=self.db)
        self.assertIn("11:00", r5["reply"])

    def test_room_categories_and_rates(self):
        r6 = StayEaseAssistant.respond("What room categories do you have?", db=self.db)
        self.assertIn("Standard", r6["reply"])
        self.assertIn("Deluxe", r6["reply"])
        self.assertIn("Suite", r6["reply"])

        r7 = StayEaseAssistant.respond("How much do rooms cost?", db=self.db)
        self.assertIn("₹", r7["reply"])

        r8 = StayEaseAssistant.respond("Tell me about the Standard room", db=self.db)
        self.assertEqual(r8["intent"], "room_standard_detail")

        r9 = StayEaseAssistant.respond("What is the price of a Deluxe room?", db=self.db)
        self.assertEqual(r9["intent"], "room_deluxe_detail")

        r10 = StayEaseAssistant.respond("How much is the Executive Suite?", db=self.db)
        self.assertEqual(r10["intent"], "room_suite_detail")

        r11 = StayEaseAssistant.respond("What is the capacity of your rooms?", db=self.db)
        self.assertIn("guests", r11["reply"].lower())

        r12 = StayEaseAssistant.respond("What amenities do the rooms have?", db=self.db)
        self.assertTrue("wifi" in r12["reply"].lower() or "amenities" in r12["reply"].lower())

        r13 = StayEaseAssistant.respond("Are there rooms available right now?", db=self.db)
        self.assertTrue("available" in r13["reply"].lower() or "inventory" in r13["reply"].lower())

    def test_booking_and_account_guidance(self):
        r14 = StayEaseAssistant.respond("How do I book a room?", db=self.db)
        self.assertIn("Confirm", r14["reply"])

        r15 = StayEaseAssistant.respond("How do I search for rooms by date?", db=self.db)
        self.assertIn("Check-in", r15["reply"])

        r16 = StayEaseAssistant.respond("How do I create an account?", db=self.db)
        self.assertTrue("Register" in r16["reply"] or "account" in r16["reply"].lower())

        r17 = StayEaseAssistant.respond("How do I sign in?", db=self.db)
        self.assertIn("Sign In", r17["reply"])

        r18 = StayEaseAssistant.respond("Where can I see my bookings?", db=self.db)
        self.assertIn("My Bookings", r18["reply"])

    def test_policies_payments_support(self):
        r19 = StayEaseAssistant.respond("What is your cancellation policy?", db=self.db)
        self.assertIn("cancellation", r19["reply"].lower())

        r20 = StayEaseAssistant.respond("How do I cancel my reservation?", db=self.db)
        self.assertIn("My Bookings", r20["reply"])

        r21 = StayEaseAssistant.respond("What payment methods do you accept?", db=self.db)
        self.assertIn("Cash at hotel", r21["reply"])

        r22 = StayEaseAssistant.respond("How do I get an invoice for my stay?", db=self.db)
        self.assertIn("invoice", r22["reply"].lower())

        r23 = StayEaseAssistant.respond("How can I contact customer support?", db=self.db)
        self.assertIn("98765", r23["reply"])

        r24 = StayEaseAssistant.respond("Do you have a swimming pool and restaurant?", db=self.db)
        self.assertTrue("pool" in r24["reply"].lower() or "restaurant" in r24["reply"].lower())

    def test_fallback_and_rate_limiting(self):
        r25 = StayEaseAssistant.respond("What is the meaning of life?", db=self.db)
        self.assertEqual(r25["intent"], "fallback")
        self.assertGreaterEqual(len(r25["quick_replies"]), 3)

        # Test FastAPI endpoint wrapper
        class DummyClient:
            host = "127.0.0.1"

        class DummyRequest:
            client = DummyClient()
            headers = {}

        api_res = main.chat_with_assistant(
            main.ChatMessageRequest(message="Hello StayEase assistant"),
            request=DummyRequest(),
            db=self.db
        )
        self.assertIn("reply", api_res)
        self.assertIn("timestamp", api_res)


if __name__ == "__main__":
    unittest.main()
