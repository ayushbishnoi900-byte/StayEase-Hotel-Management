"""
StayEase Multi-Tenant SaaS Platform & RBAC Automated Test Suite.
Verifies complete tenant data isolation, role-based authorization,
and front-desk operational workflows.
"""

import unittest
from datetime import date, timedelta
from fastapi import HTTPException
from tests.base import BaseTestCase
from database.models import Hotel, User, Room, Guest, Reservation, Payment, Housekeeping, Maintenance
import saas_routes


class TestSaaSMultiTenancy(BaseTestCase):

    def test_owner_registration(self):
        """Verify Hotel Owner registration creates both Hotel tenant and Owner User."""
        req = saas_routes.OwnerRegisterRequest(
            full_name="Rajesh Sharma",
            email="rajesh@grandresort.com",
            phone="+91 98111 22233",
            password="OwnerPassword123!",
            confirm_password="OwnerPassword123!",
            hotel_name="Grand Heritage Resort",
            address="15 Beach Road, Calangute",
            city="Goa",
            state="Goa",
            country="India",
            contact_number="+91 832 2223344",
            hotel_email="info@grandresort.com",
            total_rooms=25,
            hotel_category="Resort"
        )
        res = saas_routes.register_hotel_owner(req, db=self.db)
        self.assertIn("access_token", res)
        self.assertEqual(res["user"]["role"], "owner")
        self.assertEqual(res["hotel"]["hotel_name"], "Grand Heritage Resort")

        # Verify DB records
        hotel = self.db.query(Hotel).filter(Hotel.hotel_name == "Grand Heritage Resort").first()
        self.assertIsNotNone(hotel)
        owner = self.db.query(User).filter(User.email == "rajesh@grandresort.com").first()
        self.assertIsNotNone(owner)
        self.assertEqual(hotel.owner_id, owner.id)
        self.assertEqual(owner.hotel_id, hotel.id)

    def test_multi_tenant_room_isolation(self):
        """Verify Hotel A cannot see, edit, or delete Hotel B's rooms."""
        # 1. Create Hotel A & Owner A
        hotel_a = Hotel(hotel_name="Hotel Alpha", hotel_category="Boutique")
        self.db.add(hotel_a)
        self.db.flush()
        owner_a = User(full_name="Owner A", email="owner_a@alpha.com", role="owner", hotel_id=hotel_a.id)
        self.db.add(owner_a)

        # 2. Create Hotel B & Owner B
        hotel_b = Hotel(hotel_name="Hotel Beta", hotel_category="Luxury")
        self.db.add(hotel_b)
        self.db.flush()
        owner_b = User(full_name="Owner B", email="owner_b@beta.com", role="owner", hotel_id=hotel_b.id)
        self.db.add(owner_b)

        # 3. Add rooms to both hotels
        room_a = Room(hotel_id=hotel_a.id, room_number="101-A", room_type="Standard", price=1500.0, capacity=2)
        room_b = Room(hotel_id=hotel_b.id, room_number="201-B", room_type="Deluxe", price=3500.0, capacity=3)
        self.db.add_all([room_a, room_b])
        self.db.commit()

        # 4. Owner A lists rooms -> sees only 101-A
        rooms_for_a = saas_routes.list_hotel_rooms(current_user=owner_a, db=self.db)
        room_numbers_a = [r["room_number"] for r in rooms_for_a]
        self.assertIn("101-A", room_numbers_a)
        self.assertNotIn("201-B", room_numbers_a)

        # 5. Owner B lists rooms -> sees only 201-B
        rooms_for_b = saas_routes.list_hotel_rooms(current_user=owner_b, db=self.db)
        room_numbers_b = [r["room_number"] for r in rooms_for_b]
        self.assertIn("201-B", room_numbers_b)
        self.assertNotIn("101-A", room_numbers_b)

        # 6. Owner A attempts to update Room B -> 404
        update_req = saas_routes.SaaSUpdateRoomRequest(price=5000.0)
        with self.assertRaises(HTTPException) as ctx:
            saas_routes.update_hotel_room(room_b.id, update_req, current_user=owner_a, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

        # 7. Owner A attempts to delete Room B -> 404
        with self.assertRaises(HTTPException) as ctx:
            saas_routes.delete_hotel_room(room_b.id, current_user=owner_a, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_staff_creation_and_rbac_authorization(self):
        """Verify role gating: receptionist cannot manage staff; housekeeping cannot view payments."""
        hotel = Hotel(hotel_name="Palace Hotel")
        self.db.add(hotel)
        self.db.flush()
        owner = User(full_name="Hotel Boss", email="boss@palace.com", role="owner", hotel_id=hotel.id)
        self.db.add(owner)
        self.db.commit()

        # 1. Owner creates Receptionist
        receptionist_req = saas_routes.StaffAccountCreateRequest(
            full_name="Pooja Sharma",
            email="pooja@palace.com",
            phone="+91 99999 11111",
            role="receptionist",
            designation="Senior Receptionist",
            department="Front Office",
            password="staffpassword1"
        )
        rec_res = saas_routes.create_staff_account(receptionist_req, current_user=owner, db=self.db)
        self.assertEqual(rec_res["staff"]["role"], "receptionist")

        # 2. Owner creates Housekeeping staff
        hk_req = saas_routes.StaffAccountCreateRequest(
            full_name="Ramesh Kumar",
            email="ramesh@palace.com",
            role="housekeeping",
            password="staffpassword2"
        )
        hk_res = saas_routes.create_staff_account(hk_req, current_user=owner, db=self.db)
        self.assertEqual(hk_res["staff"]["role"], "housekeeping")

        # Retrieve staff user instances
        receptionist = self.db.query(User).filter(User.email == "pooja@palace.com").first()
        housekeeping = self.db.query(User).filter(User.email == "ramesh@palace.com").first()

        # 3. Receptionist attempts to access staff management -> 403 Forbidden
        role_checker = saas_routes.require_roles("owner", "manager")
        with self.assertRaises(HTTPException) as ctx:
            role_checker(receptionist)
        self.assertEqual(ctx.exception.status_code, 403)

        # 4. Housekeeping attempts to access billing/payments -> 403 Forbidden
        billing_checker = saas_routes.require_roles("owner", "manager", "accountant", "receptionist")
        with self.assertRaises(HTTPException) as ctx:
            billing_checker(housekeeping)
        self.assertEqual(ctx.exception.status_code, 403)

        # 5. Housekeeping CAN access housekeeping board
        hk_checker = saas_routes.require_roles("owner", "manager", "housekeeping")
        verified_hk = hk_checker(housekeeping)
        self.assertEqual(verified_hk.id, housekeeping.id)

    def test_front_desk_walkin_reservation_lifecycle(self):
        """Test walk-in guest creation, room occupancy, check-out, and auto-housekeeping."""
        hotel = Hotel(hotel_name="Sunset Oasis")
        self.db.add(hotel)
        self.db.flush()

        owner = User(full_name="Sunset Owner", email="owner@sunset.com", role="owner", hotel_id=hotel.id)
        room = Room(hotel_id=hotel.id, room_number="305", room_type="Deluxe", price=2500.0, capacity=2)
        self.db.add_all([owner, room])
        self.db.commit()

        today = date.today()
        tomorrow = today + timedelta(days=1)

        # 1. Front Desk Walk-In Reservation
        res_req = saas_routes.FrontDeskReservationCreateRequest(
            guest_name="Karan Malhotra",
            guest_phone="+91 98888 77777",
            guest_email="karan@example.com",
            guest_id_proof_type="Passport",
            guest_id_proof_number="L12345678",
            room_id=room.id,
            check_in=today,
            check_out=tomorrow,
            number_of_guests=2,
            booking_source="Walk-in",
            payment_method="Cash",
            payment_status="Completed"
        )
        res_data = saas_routes.create_front_desk_reservation(res_req, current_user=owner, db=self.db)
        self.assertEqual(res_data["status"], "Checked In")

        # Verify Room is now Occupied
        self.db.refresh(room)
        self.assertEqual(room.operational_status, "Occupied")

        # Verify Guest record was created
        guest = self.db.query(Guest).filter(Guest.phone == "+91 98888 77777").first()
        self.assertIsNotNone(guest)
        self.assertEqual(guest.id_proof_number, "L12345678")

        # 2. Check Out -> Room becomes Available, Housekeeping becomes Dirty
        status_req = saas_routes.ReservationStatusUpdateRequest(status="Checked Out")
        saas_routes.update_reservation_status(res_data["reservation_id"], status_req, current_user=owner, db=self.db)

        self.db.refresh(room)
        self.assertEqual(room.operational_status, "Available")
        self.assertEqual(room.housekeeping_status, "Dirty")

        # Verify Housekeeping task was created
        hk_task = self.db.query(Housekeeping).filter(Housekeeping.room_id == room.id).first()
        self.assertIsNotNone(hk_task)
        self.assertEqual(hk_task.cleaning_status, "Dirty")

        # 3. Invoice Generation
        inv = saas_routes.get_reservation_invoice(res_data["reservation_id"], current_user=owner, db=self.db)
        self.assertEqual(inv["guest"]["name"], "Karan Malhotra")
        self.assertEqual(inv["financials"]["payment_status"], "Completed")


if __name__ == "__main__":
    unittest.main()
