"""
StayEase Admin Management, Staff, Housekeeping & Analytics Automated Tests
"""

import unittest
from fastapi import HTTPException
from tests.base import BaseTestCase
from database.models import Staff, Room
import main


class TestAdmin(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.admin = self.create_customer(name="Master Admin", email="master_admin@example.com", role="admin")
        self.guest = self.create_customer(name="Test Guest", email="admin_test_guest@example.com", role="customer")
        self.room = self.create_room(room_number="R901", price=2800.0)
        self.booking = self.create_booking(self.guest, self.room)

    def test_admin_dashboard_metrics(self):
        dash = main.admin_dashboard(admin=self.admin, db=self.db)
        self.assertGreaterEqual(dash["total_rooms"], 1)
        self.assertGreaterEqual(dash["total_customers"], 1)
        self.assertGreaterEqual(dash["total_bookings"], 1)
        self.assertGreaterEqual(dash["total_revenue"], 2800.0)

    def test_admin_customer_management(self):
        customers = main.admin_all_customers(admin=self.admin, db=self.db)
        self.assertGreaterEqual(len(customers), 2)

        # View customer profile with bookings
        cust_profile = main.admin_get_customer_detail(self.guest.id, admin=self.admin, db=self.db)
        self.assertEqual(cust_profile["email"], self.guest.email)
        self.assertGreaterEqual(len(cust_profile["bookings"]), 1)

        # Update customer phone
        update_req = main.AdminCustomerUpdateRequest(phone="+91 91111 22222")
        updated = main.admin_update_customer(self.guest.id, update_req, admin=self.admin, db=self.db)
        self.assertEqual(updated["customer"]["phone"], "+91 91111 22222")

        # Deactivate customer
        status_req = main.AdminCustomerStatusUpdateRequest(status="Inactive")
        deact = main.admin_update_customer_status(self.guest.id, status_req, admin=self.admin, db=self.db)
        self.assertEqual(deact["status"], "Inactive")

        # Admin self-deactivation blocked
        with self.assertRaises(HTTPException) as ctx:
            main.admin_update_customer_status(self.admin.id, status_req, admin=self.admin, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_staff_crud(self):
        # Create staff
        req = main.StaffCreateRequest(
            name="Vikram Singh",
            email="vikram@stayease.com",
            phone="+91 98765 77777",
            designation="Concierge Lead",
            status="Active"
        )
        created = main.admin_add_staff(req, admin=self.admin, db=self.db)
        self.assertIn("staff_id", created)
        staff_id = created["staff_id"]

        # Read directory
        staff_list = main.admin_get_staff(admin=self.admin, db=self.db)
        self.assertTrue(any(s["id"] == staff_id for s in staff_list))

        # Update staff
        update_req = main.StaffUpdateRequest(phone="+91 98765 88888")
        updated = main.admin_update_staff(staff_id, update_req, admin=self.admin, db=self.db)
        self.assertEqual(updated["staff"]["phone"], "+91 98765 88888")

        # Delete staff
        deleted = main.admin_delete_staff(staff_id, admin=self.admin, db=self.db)
        self.assertIn("successfully", deleted["message"].lower())

    def test_housekeeping_management(self):
        rooms = main.admin_get_housekeeping(admin=self.admin, db=self.db)
        self.assertGreaterEqual(len(rooms), 1)

        hk_req = main.HousekeepingUpdateRequest(housekeeping_status="Cleaning in Progress")
        res = main.admin_update_housekeeping(self.room.id, hk_req, admin=self.admin, db=self.db)
        self.assertEqual(res["housekeeping_status"], "Cleaning in Progress")
        self.assertIsNotNone(res["last_cleaned"])

    def test_admin_analytics_and_settings(self):
        analytics = main.admin_get_analytics(admin=self.admin, db=self.db)
        self.assertIn("occupancy", analytics)
        self.assertIn("monthly_trends", analytics)
        self.assertIn("popular_categories", analytics)

        settings = main.admin_get_settings(admin=self.admin, db=self.db)
        self.assertIn("hotel_name", settings)

        update_settings_req = main.HotelSettingsUpdateRequest(
            hotel_name="StayEase Palace & Resort"
        )
        updated_settings = main.admin_update_settings(update_settings_req, admin=self.admin, db=self.db)
        self.assertEqual(updated_settings["settings"]["hotel_name"], "StayEase Palace & Resort")


if __name__ == "__main__":
    unittest.main()
