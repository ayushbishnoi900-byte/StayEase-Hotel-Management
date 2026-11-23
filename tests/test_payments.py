"""
StayEase Payments Module Automated Tests
"""

import unittest
from fastapi import HTTPException
from tests.base import BaseTestCase
import main


class TestPayments(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.admin = self.create_customer(name="Admin Pay", email="admin_pay@example.com", role="admin")
        self.guest = self.create_customer(name="Guest Pay", email="guest_pay@example.com", role="customer")
        self.other = self.create_customer(name="Other Pay", email="other_pay@example.com", role="customer")
        self.room = self.create_room(room_number="R701", price=3000.0)
        self.booking = self.create_booking(self.guest, self.room)

    def test_payment_history_accessible_by_owner(self):
        res = main.get_booking_payments(self.booking.id, customer=self.guest, db=self.db)
        self.assertGreaterEqual(len(res), 1)
        self.assertEqual(res[0]["payment_status"], "Completed")

    def test_payment_history_forbidden_for_other_customer(self):
        with self.assertRaises(HTTPException) as ctx:
            main.get_booking_payments(self.booking.id, customer=self.other, db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_additional_demo_payment_process(self):
        req = main.DemoPaymentRequest(payment_method="Demo Online Payment")
        res = main.process_demo_payment(self.booking.id, req, customer=self.guest, db=self.db)
        self.assertEqual(res["payment"]["payment_status"], "Completed")
        self.assertIn("DEMO-", res["payment"]["transaction_ref"])

    def test_other_customer_cannot_pay_for_booking(self):
        req = main.DemoPaymentRequest(payment_method="Demo Online Payment")
        with self.assertRaises(HTTPException) as ctx:
            main.process_demo_payment(self.booking.id, req, customer=self.other, db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_admin_view_and_update_payment_status(self):
        all_payments = main.admin_get_all_payments(admin=self.admin, db=self.db)
        self.assertGreaterEqual(len(all_payments), 1)

        pay_id = all_payments[0]["id"]
        status_req = main.PaymentStatusUpdateRequest(payment_status="Refunded")
        updated = main.admin_update_payment_status(pay_id, status_req, admin=self.admin, db=self.db)
        self.assertEqual(updated["payment_status"], "Refunded")


if __name__ == "__main__":
    unittest.main()
