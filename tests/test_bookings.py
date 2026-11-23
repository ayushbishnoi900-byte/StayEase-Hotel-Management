"""
StayEase Booking Workflows & Overlapping Dates Automated Tests
"""

import unittest
from datetime import date, timedelta
from fastapi import HTTPException
from tests.base import BaseTestCase
import main


class TestBookings(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.guest = self.create_customer(name="Booking Guest", email="booking_guest@example.com")
        self.other_guest = self.create_customer(name="Other Guest", email="other_guest@example.com")
        self.room = self.create_room(room_number="R601", price=2000.0, capacity=2)
        self.today = date.today()

    def test_valid_booking_creation(self):
        req = main.BookingCreateRequest(
            room_id=self.room.id,
            check_in=self.today + timedelta(days=1),
            check_out=self.today + timedelta(days=4),
            guests=2,
            payment_method="Demo Online Payment"
        )
        res = main.create_booking(req, customer=self.guest, db=self.db)
        self.assertEqual(res["message"], "Booking confirmed successfully.")
        b = res["booking"]
        self.assertEqual(b["nights"], 3)
        self.assertEqual(b["total_price"], 6000.0)
        self.assertEqual(b["status"], "Confirmed")

    def test_past_check_in_date_rejected(self):
        req = main.BookingCreateRequest(
            room_id=self.room.id,
            check_in=self.today - timedelta(days=1),
            check_out=self.today + timedelta(days=2),
            guests=1
        )
        with self.assertRaises(HTTPException) as ctx:
            main.create_booking(req, customer=self.guest, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("past", ctx.exception.detail.lower())

    def test_checkout_before_or_same_as_checkin_rejected(self):
        # Same day check-in and check-out
        req_same = main.BookingCreateRequest(
            room_id=self.room.id,
            check_in=self.today + timedelta(days=3),
            check_out=self.today + timedelta(days=3),
            guests=1
        )
        with self.assertRaises(HTTPException) as ctx:
            main.create_booking(req_same, customer=self.guest, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("after check-in", ctx.exception.detail.lower())

        # Checkout before checkin
        req_before = main.BookingCreateRequest(
            room_id=self.room.id,
            check_in=self.today + timedelta(days=5),
            check_out=self.today + timedelta(days=3),
            guests=1
        )
        with self.assertRaises(HTTPException) as ctx:
            main.create_booking(req_before, customer=self.guest, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_guests_exceeding_capacity_rejected(self):
        req = main.BookingCreateRequest(
            room_id=self.room.id,
            check_in=self.today + timedelta(days=1),
            check_out=self.today + timedelta(days=3),
            guests=10  # capacity is 2
        )
        with self.assertRaises(HTTPException) as ctx:
            main.create_booking(req, customer=self.guest, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("maximum of 2 guest", ctx.exception.detail.lower())

    def test_overlapping_reservations_rejected(self):
        # Initial booking: Day 10 to Day 15
        d10 = self.today + timedelta(days=10)
        d15 = self.today + timedelta(days=15)
        self.create_booking(self.guest, self.room, check_in=d10, check_out=d15)

        # 1. Exact overlap: Day 10 to Day 15
        req_exact = main.BookingCreateRequest(
            room_id=self.room.id, check_in=d10, check_out=d15, guests=1
        )
        with self.assertRaises(HTTPException) as ctx:
            main.create_booking(req_exact, customer=self.other_guest, db=self.db)
        self.assertEqual(ctx.exception.status_code, 409)

        # 2. Inside overlap: Day 11 to Day 14
        req_inside = main.BookingCreateRequest(
            room_id=self.room.id,
            check_in=self.today + timedelta(days=11),
            check_out=self.today + timedelta(days=14),
            guests=1
        )
        with self.assertRaises(HTTPException) as ctx:
            main.create_booking(req_inside, customer=self.other_guest, db=self.db)
        self.assertEqual(ctx.exception.status_code, 409)

        # 3. Enclosing overlap: Day 8 to Day 17
        req_enclosing = main.BookingCreateRequest(
            room_id=self.room.id,
            check_in=self.today + timedelta(days=8),
            check_out=self.today + timedelta(days=17),
            guests=1
        )
        with self.assertRaises(HTTPException) as ctx:
            main.create_booking(req_enclosing, customer=self.other_guest, db=self.db)
        self.assertEqual(ctx.exception.status_code, 409)

        # 4. Start overlap: Day 8 to Day 12
        req_start = main.BookingCreateRequest(
            room_id=self.room.id,
            check_in=self.today + timedelta(days=8),
            check_out=self.today + timedelta(days=12),
            guests=1
        )
        with self.assertRaises(HTTPException) as ctx:
            main.create_booking(req_start, customer=self.other_guest, db=self.db)
        self.assertEqual(ctx.exception.status_code, 409)

        # 5. End overlap: Day 13 to Day 18
        req_end = main.BookingCreateRequest(
            room_id=self.room.id,
            check_in=self.today + timedelta(days=13),
            check_out=self.today + timedelta(days=18),
            guests=1
        )
        with self.assertRaises(HTTPException) as ctx:
            main.create_booking(req_end, customer=self.other_guest, db=self.db)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_same_day_checkout_and_checkin_allowed(self):
        # Booking A: Day 20 to Day 25
        d20 = self.today + timedelta(days=20)
        d25 = self.today + timedelta(days=25)
        self.create_booking(self.guest, self.room, check_in=d20, check_out=d25)

        # Booking B: Day 25 to Day 30 (Starts the moment Booking A checks out)
        d30 = self.today + timedelta(days=30)
        req_next = main.BookingCreateRequest(
            room_id=self.room.id, check_in=d25, check_out=d30, guests=1
        )
        res_next = main.create_booking(req_next, customer=self.other_guest, db=self.db)
        self.assertEqual(res_next["booking"]["status"], "Confirmed")

        # Booking C: Day 15 to Day 20 (Ends the moment Booking A checks in)
        d15 = self.today + timedelta(days=15)
        req_prev = main.BookingCreateRequest(
            room_id=self.room.id, check_in=d15, check_out=d20, guests=1
        )
        res_prev = main.create_booking(req_prev, customer=self.other_guest, db=self.db)
        self.assertEqual(res_prev["booking"]["status"], "Confirmed")

    def test_cancellation_and_rebooking(self):
        # Create booking for Day 35 to Day 40
        d35 = self.today + timedelta(days=35)
        d40 = self.today + timedelta(days=40)
        b = self.create_booking(self.guest, self.room, check_in=d35, check_out=d40)

        # Cancel the booking
        cancel_res = main.cancel_booking(b.id, customer=self.guest, db=self.db)
        self.assertEqual(cancel_res["status"], "Cancelled")

        # Rebooking the exact same dates now MUST succeed
        rebook_req = main.BookingCreateRequest(
            room_id=self.room.id, check_in=d35, check_out=d40, guests=2
        )
        rebook_res = main.create_booking(rebook_req, customer=self.other_guest, db=self.db)
        self.assertEqual(rebook_res["booking"]["status"], "Confirmed")


if __name__ == "__main__":
    unittest.main()
