"""
StayEase Security, Authorization & IDOR Automated Tests
"""

import unittest
from datetime import date, timedelta
from fastapi import HTTPException
from tests.base import BaseTestCase
from database.models import Customer
import main


class TestSecurity(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.admin = self.create_customer(name="Security Admin", email="sec_admin@example.com", role="admin")
        self.alice = self.create_customer(name="Alice Sec", email="alice_sec@example.com", role="customer")
        self.bob = self.create_customer(name="Bob Sec", email="bob_sec@example.com", role="customer")
        self.room = self.create_room(room_number="R801", price=2500.0)
        self.alice_booking = self.create_booking(self.alice, self.room)

    def test_passwords_are_argon2_hashed(self):
        cust = self.db.query(Customer).filter(Customer.email == "alice_sec@example.com").first()
        self.assertTrue(cust.password.startswith("$argon2"))
        self.assertNotIn("Password123!", cust.password)

    def test_customer_cannot_access_admin_dashboard(self):
        with self.assertRaises(HTTPException) as ctx:
            main.admin_dashboard(admin=main.require_admin(self.alice), db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_customer_cannot_access_admin_staff(self):
        with self.assertRaises(HTTPException) as ctx:
            main.admin_get_staff(admin=main.require_admin(self.alice), db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_customer_cannot_access_admin_analytics(self):
        with self.assertRaises(HTTPException) as ctx:
            main.admin_get_analytics(admin=main.require_admin(self.alice), db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_customer_cannot_access_admin_settings(self):
        with self.assertRaises(HTTPException) as ctx:
            main.admin_get_settings(admin=main.require_admin(self.alice), db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_idor_bob_cannot_view_alice_booking(self):
        with self.assertRaises(HTTPException) as ctx:
            main.get_booking_details(self.alice_booking.id, customer=self.bob, db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("not authorized", ctx.exception.detail.lower())

    def test_idor_bob_cannot_access_alice_invoice(self):
        with self.assertRaises(HTTPException) as ctx:
            main.get_booking_invoice(self.alice_booking.id, customer=self.bob, db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("not authorized", ctx.exception.detail.lower())

    def test_idor_bob_cannot_cancel_alice_booking(self):
        with self.assertRaises(HTTPException) as ctx:
            main.cancel_booking(self.alice_booking.id, customer=self.bob, db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("only cancel your own", ctx.exception.detail.lower())

    def test_admin_can_view_any_booking(self):
        res = main.get_booking_details(self.alice_booking.id, customer=self.admin, db=self.db)
        self.assertEqual(res["id"], self.alice_booking.id)

    def test_admin_can_view_any_invoice(self):
        res = main.get_booking_invoice(self.alice_booking.id, customer=self.admin, db=self.db)
        self.assertIn("INV-2026-", res["invoice_number"])

    def test_sql_injection_payload_in_queries(self):
        # SQL injection strings must be safely handled by ORM parameterized queries
        sqli_payload = "' OR '1'='1"
        rooms = main.get_rooms(room_type=sqli_payload, db=self.db)
        self.assertEqual(len(rooms), 0)

        # SQL injection in room search keyword
        rooms2 = main.get_rooms(room_type="'; DROP TABLE rooms; --", db=self.db)
        self.assertEqual(len(rooms2), 0)


if __name__ == "__main__":
    unittest.main()
