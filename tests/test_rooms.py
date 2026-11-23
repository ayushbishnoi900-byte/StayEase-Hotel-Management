"""
StayEase Rooms Management Automated Tests
"""

import unittest
from datetime import date, timedelta
from fastapi import HTTPException
from tests.base import BaseTestCase
import main


class TestRooms(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.admin = self.create_customer(name="Admin User", email="admin_rooms@example.com", role="admin")
        self.guest = self.create_customer(name="Guest User", email="guest_rooms@example.com", role="customer")

    def test_admin_create_room(self):
        req = main.RoomCreateRequest(
            room_number="R201",
            room_type="Deluxe",
            price=3200.0,
            capacity=3,
            status="Available",
            description="Spacious Deluxe room.",
            image_url="https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800"
        )
        res = main.add_room(req, admin=self.admin, db=self.db)
        self.assertIn("room_id", res)
        self.assertEqual(res["message"], "Room added successfully.")

    def test_customer_cannot_create_room(self):
        req = main.RoomCreateRequest(
            room_number="R999",
            room_type="Suite",
            price=5000.0,
            capacity=4,
            status="Available"
        )
        with self.assertRaises(HTTPException) as ctx:
            main.add_room(req, admin=main.require_admin(self.guest), db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_duplicate_room_number_rejected(self):
        req = main.RoomCreateRequest(
            room_number="R202",
            room_type="Standard",
            price=1800.0,
            capacity=2,
            status="Available"
        )
        main.add_room(req, admin=self.admin, db=self.db)
        with self.assertRaises(HTTPException) as ctx:
            main.add_room(req, admin=self.admin, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("already exists", ctx.exception.detail.lower())

    def test_list_and_filter_rooms(self):
        self.create_room(room_number="R301", room_type="Standard", price=1500.0, capacity=2)
        self.create_room(room_number="R302", room_type="Deluxe", price=3000.0, capacity=3)
        self.create_room(room_number="R303", room_type="Suite", price=5500.0, capacity=4)

        # Filter by room_type
        deluxe_rooms = main.get_rooms(room_type="Deluxe", db=self.db)
        self.assertTrue(all(r["room_type"] == "Deluxe" for r in deluxe_rooms))

        # Filter by min_price
        expensive_rooms = main.get_rooms(min_price=4000.0, db=self.db)
        self.assertTrue(all(r["price"] >= 4000.0 for r in expensive_rooms))

        # Filter by capacity
        family_rooms = main.get_rooms(capacity=4, db=self.db)
        self.assertTrue(all(r["capacity"] >= 4 for r in family_rooms))

    def test_update_room(self):
        room = self.create_room(room_number="R401", price=2000.0)
        update_req = main.RoomUpdateRequest(price=2200.0, status="Available")
        updated = main.update_room(room.id, update_req, admin=self.admin, db=self.db)
        self.assertEqual(updated["room"]["price"], 2200.0)

    def test_delete_room_with_active_bookings_blocked(self):
        room = self.create_room(room_number="R501", price=2500.0)
        self.create_booking(self.guest, room)
        with self.assertRaises(HTTPException) as ctx:
            main.delete_room(room.id, admin=self.admin, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("active booking", ctx.exception.detail.lower())

    def test_delete_room_without_bookings_success(self):
        room = self.create_room(room_number="R502", price=2500.0)
        res = main.delete_room(room.id, admin=self.admin, db=self.db)
        self.assertIn("deleted successfully", res["message"].lower())


if __name__ == "__main__":
    unittest.main()
