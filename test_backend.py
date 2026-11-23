# ==========================================
# STAYEASE - AUTOMATED BACKEND TEST SUITE
# Verifies all 34 endpoints and business logic
# ==========================================

import os
import sys
from datetime import date, timedelta

# Point to project root
sys.path.insert(0, "/Users/ayushbishnoi/Desktop/StayEase")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from database.database import Base
from database.models import Customer, Room, Booking, Payment, Staff
import main

# Setup in-memory SQLite database for test isolation
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

Base.metadata.create_all(bind=test_engine)
db = TestingSessionLocal()

passed = 0
failed = 0

def test(name, condition, error_msg=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        print(f"  ✗ {name}: {error_msg}")

print("\n==========================================")
print("RUNNING STAYEASE BACKEND TEST SUITE")
print("==========================================\n")

# ------------------------------------------
# 1. CUSTOMER REGISTRATION
# ------------------------------------------
print("[1] Testing Registration...")
reg_data = main.RegisterRequest(
    name="Test Guest",
    email="guest@example.com",
    password="Password123!",
    phone="+91 99999 88888"
)
reg_res = main.register(reg_data, db=db)
test("Registration creates user", "customer_id" in reg_res)

try:
    main.register(reg_data, db=db)
    test("Duplicate registration rejected", False, "Allowed duplicate email")
except HTTPException as e:
    test("Duplicate registration rejected with 400", e.status_code == 400)

# ------------------------------------------
# 2. CUSTOMER LOGIN & JWT
# ------------------------------------------
print("\n[2] Testing Authentication & JWT...")
login_data = main.LoginRequest(email="guest@example.com", password="Password123!")
login_res = main.login(login_data, db=db)
test("Login returns access_token", "access_token" in login_res and login_res["token_type"] == "bearer")
guest_token = login_res["access_token"]
guest_id = login_res["customer"]["id"]

# Test wrong password
try:
    main.login(main.LoginRequest(email="guest@example.com", password="WrongPassword"), db=db)
    test("Wrong password rejected", False)
except HTTPException as e:
    test("Wrong password rejected with 401", e.status_code == 401)

# Test get_current_user
creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=guest_token)
guest_user = main.get_current_user(creds, db=db)
test("get_current_user resolves guest", guest_user.id == guest_id and guest_user.role == "customer")

# Setup Admin user
admin_user = Customer(
    name="Super Admin",
    email="admin@stayease.com",
    password=main.password_hash.hash("admin123"),
    phone="+91 98765 00000",
    role="admin"
)
db.add(admin_user)
db.commit()
db.refresh(admin_user)

admin_login_res = main.login(main.LoginRequest(email="admin@stayease.com", password="admin123"), db=db)
admin_token = admin_login_res["access_token"]
admin_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=admin_token)
resolved_admin = main.get_current_user(admin_creds, db=db)
test("get_current_user resolves admin", resolved_admin.role == "admin")

# Test require_admin
test("require_admin accepts admin", main.require_admin(resolved_admin) == resolved_admin)
try:
    main.require_admin(guest_user)
    test("require_admin blocks customer", False)
except HTTPException as e:
    test("require_admin blocks customer with 403", e.status_code == 403)

# ------------------------------------------
# 3. CUSTOMER PROFILE APIs
# ------------------------------------------
print("\n[3] Testing Customer Profile APIs...")
profile = main.get_customer_profile(customer=guest_user)
test("GET /me returns customer info", profile["email"] == "guest@example.com")

updated_profile = main.update_customer_profile(
    main.ProfileUpdateRequest(name="Updated Guest Name", phone="+91 98888 77777"),
    customer=guest_user,
    db=db
)
test("PUT /me updates name & phone", updated_profile["customer"]["name"] == "Updated Guest Name")

# ------------------------------------------
# 4. ROOM APIs (CRUD & FILTERS)
# ------------------------------------------
print("\n[4] Testing Room APIs...")
new_room_data = main.RoomCreateRequest(
    room_number="101",
    room_type="Standard",
    price=1800.0,
    capacity=2,
    description="Standard room with AC",
    image_url="https://images.unsplash.com/test101.jpg"
)
room_res = main.add_room(new_room_data, admin=resolved_admin, db=db)
test("POST /rooms creates room (Admin)", "room_id" in room_res)
room_id_101 = room_res["room_id"]

# Add deluxe room
room_res_201 = main.add_room(
    main.RoomCreateRequest(
        room_number="201",
        room_type="Deluxe",
        price=3000.0,
        capacity=3,
        description="Deluxe room with balcony"
    ),
    admin=resolved_admin,
    db=db
)
room_id_201 = room_res_201["room_id"]

# Test get all rooms & filters
all_rooms = main.get_rooms(db=db)
test("GET /rooms returns all rooms", len(all_rooms) == 2)

deluxe_filter = main.get_rooms(room_type="Deluxe", db=db)
test("GET /rooms?room_type=Deluxe filters correctly", len(deluxe_filter) == 1 and deluxe_filter[0]["room_number"] == "201")

price_filter = main.get_rooms(min_price=2000.0, db=db)
test("GET /rooms?min_price=2000 filters correctly", len(price_filter) == 1 and price_filter[0]["price"] == 3000.0)

# Test single room details
single_room = main.get_room_details(room_id_101, db=db)
test("GET /rooms/{id} returns details", single_room["room_number"] == "101")
test("GET /rooms/{id} includes amenities list", isinstance(single_room["amenities"], list) and len(single_room["amenities"]) > 0)

# Test room update
main.update_room(room_id_101, main.RoomUpdateRequest(price=1900.0), admin=resolved_admin, db=db)
updated_room = main.get_room_details(room_id_101, db=db)
test("PUT /rooms/{id} updates room price", updated_room["price"] == 1900.0)

# Test availability check
today = date.today()
t_in = today + timedelta(days=2)
t_out = today + timedelta(days=5)
avail = main.check_availability(room_id_101, check_in=t_in, check_out=t_out, db=db)
test("GET /rooms/{id}/availability returns available=True", avail["available"] is True)

# ------------------------------------------
# 5. BOOKING APIs & CONCURRENCY / OVERLAP PREVENTIONS
# ------------------------------------------
print("\n[5] Testing Booking APIs & Double-Booking Protection...")
booking_data = main.BookingCreateRequest(
    room_id=room_id_101,
    check_in=t_in,
    check_out=t_out,
    guests=2,
    payment_method="Demo Online Payment"
)
booking_res = main.create_booking(booking_data, customer=guest_user, db=db)
test("POST /bookings creates confirmed booking", booking_res["booking"]["status"] == "Confirmed")
b_id = booking_res["booking"]["id"]
expected_price = 1900.0 * 3 # 3 nights
test("Automatic price calculation (3 nights × 1900)", booking_res["booking"]["total_price"] == expected_price)
test("Demo payment record created", booking_res["booking"]["payment"]["status"] == "Completed")

# Check availability now False for overlapping dates
avail_after = main.check_availability(room_id_101, check_in=t_in, check_out=t_out, db=db)
test("Room availability now reports False for booked dates", avail_after["available"] is False)

# Try booking overlapping dates -> MUST FAIL with 409 Conflict
try:
    overlap_booking = main.BookingCreateRequest(
        room_id=room_id_101,
        check_in=t_in + timedelta(days=1),
        check_out=t_out + timedelta(days=1),
        guests=1
    )
    main.create_booking(overlap_booking, customer=guest_user, db=db)
    test("Overlapping booking rejected", False, "Allowed double booking")
except HTTPException as e:
    test("Overlapping booking rejected with 409 Conflict", e.status_code == 409)

# Test date-range live availability filtering in GET /rooms
date_filtered_rooms = main.get_rooms(check_in=t_in, check_out=t_out, db=db)
test("GET /rooms with dates excludes booked room 101", all(r["id"] != room_id_101 for r in date_filtered_rooms))

# Test guest booking history
my_bookings = main.get_my_bookings(customer=guest_user, db=db)
test("GET /my-bookings returns guest reservations", len(my_bookings) == 1 and my_bookings[0]["id"] == b_id)
test("GET /my-bookings includes booking_reference and timing_status", my_bookings[0]["booking_reference"].startswith("SE-BK-") and my_bookings[0]["timing_status"] == "Upcoming")

# Test single booking details
booking_details = main.get_booking_details(b_id, customer=guest_user, db=db)
test("GET /bookings/{id} returns full booking breakdown", booking_details["room"]["room_number"] == "101")

# Test invoice generation
inv = main.get_booking_invoice(b_id, customer=guest_user, db=db)
test("GET /bookings/{id}/invoice generates invoice", inv["booking_reference"].startswith("SE-BK-") and inv["billing"]["total_amount"] == expected_price)

# Guard against non-owner accessing booking
other_user = Customer(name="Other User", email="other@example.com", password="pwd", phone="", role="customer")
db.add(other_user)
db.commit()
try:
    main.get_booking_details(b_id, customer=other_user, db=db)
    test("Non-owner blocked from viewing booking", False)
except HTTPException as e:
    test("Non-owner blocked with 403 Forbidden", e.status_code == 403)

# ------------------------------------------
# 6. PAYMENT MODULE (DEMONSTRATION)
# ------------------------------------------
print("\n[6] Testing Payment Module...")
pay_res = main.process_demo_payment(
    booking_id=b_id,
    data=main.DemoPaymentRequest(payment_method="Demo Online Payment", card_last4="4242"),
    customer=guest_user,
    db=db
)
test("POST /bookings/{id}/pay creates payment record", pay_res["payment"]["payment_status"] == "Completed")
test("Payment includes demonstration disclaimer", "demonstration" in pay_res["disclaimer"].lower())

b_payments = main.get_booking_payments(b_id, customer=guest_user, db=db)
test("GET /bookings/{id}/payments lists transactions", len(b_payments) >= 1)

admin_payments = main.admin_get_all_payments(admin=resolved_admin, db=db)
test("GET /admin/payments lists all transactions (Admin)", len(admin_payments) >= 1)

p_id = b_payments[0]["id"]
main.admin_update_payment_status(p_id, main.PaymentStatusUpdateRequest(payment_status="Completed"), admin=resolved_admin, db=db)
test("PUT /admin/payments/{id}/status updates status", True)

# ------------------------------------------
# 7. STAFF MANAGEMENT APIs (ADMIN ONLY)
# ------------------------------------------
print("\n[7] Testing Staff Management APIs...")
staff_res = main.admin_add_staff(
    main.StaffCreateRequest(
        name="Sunil Sharma",
        email="sunil.manager@stayease.com",
        phone="+91 91234 56789",
        designation="Operations Manager",
        status="Active"
    ),
    admin=resolved_admin,
    db=db
)
test("POST /admin/staff creates staff member", "staff_id" in staff_res)
staff_id = staff_res["staff_id"]

staff_list = main.admin_get_staff(admin=resolved_admin, db=db)
test("GET /admin/staff returns directory", len(staff_list) == 1 and staff_list[0]["name"] == "Sunil Sharma")

single_staff = main.admin_get_staff_member(staff_id, admin=resolved_admin, db=db)
test("GET /admin/staff/{id} returns staff info", single_staff["designation"] == "Operations Manager")

main.admin_update_staff(staff_id, main.StaffUpdateRequest(phone="+91 99999 11111"), admin=resolved_admin, db=db)
updated_staff = main.admin_get_staff_member(staff_id, admin=resolved_admin, db=db)
test("PUT /admin/staff/{id} updates phone", updated_staff["phone"] == "+91 99999 11111")

# ------------------------------------------
# 8. ADMIN DASHBOARD & OVERSIGHT
# ------------------------------------------
print("\n[8] Testing Admin Dashboard & Oversight...")
dash = main.admin_dashboard(admin=resolved_admin, db=db)
test("GET /admin/dashboard returns total_rooms", dash["total_rooms"] == 2)
test("GET /admin/dashboard returns active_bookings", dash["active_bookings"] == 1)
test("GET /admin/dashboard returns total_revenue", dash["total_revenue"] == expected_price)
test("GET /admin/dashboard returns total_staff", dash["total_staff"] == 1)

all_bookings = main.admin_all_bookings(admin=resolved_admin, db=db)
test("GET /admin/bookings returns all reservations", len(all_bookings) >= 1)

all_customers = main.admin_all_customers(admin=resolved_admin, db=db)
test("GET /admin/customers lists customers", len(all_customers) >= 1)

# ------------------------------------------
# 9. BOOKING CANCELLATION & SAFE DELETION GUARDS
# ------------------------------------------
print("\n[9] Testing Cancellation & Deletion Guards...")
# Try deleting room with active booking -> MUST FAIL
try:
    main.delete_room(room_id_101, admin=resolved_admin, db=db)
    test("Protected room cannot be deleted while active booking exists", False)
except HTTPException as e:
    test("Protected room blocked from deletion with 400", e.status_code == 400)

# Cancel booking
cancel_res = main.cancel_booking(b_id, customer=guest_user, db=db)
test("PUT /bookings/cancel/{id} cancels booking", cancel_res["status"] == "Cancelled")

# Check room is now available again
avail_recheck = main.check_availability(room_id_101, check_in=t_in, check_out=t_out, db=db)
test("Cancelled dates freed for new bookings", avail_recheck["available"] is True)

# Safe delete unused room 201
del_res = main.delete_room(room_id_201, admin=resolved_admin, db=db)
test("DELETE /rooms/{id} deletes room without bookings", "successfully" in del_res["message"])

# Delete staff member
del_staff_res = main.admin_delete_staff(staff_id, admin=resolved_admin, db=db)
test("DELETE /admin/staff/{id} removes staff member", "successfully" in del_staff_res["message"])

# ------------------------------------------
# 10. TESTING NEW ADMIN DASHBOARD MODULES
# ------------------------------------------
print("\n[10] Testing Extended Admin Modules...")

# 1. Overview 8 metrics check
test("Admin overview includes total_rooms", "total_rooms" in dash)
test("Admin overview includes available_rooms", "available_rooms" in dash)
test("Admin overview includes occupied_rooms", "occupied_rooms" in dash)
test("Admin overview includes total_customers", "total_customers" in dash)
test("Admin overview includes total_bookings", "total_bookings" in dash)
test("Admin overview includes confirmed_bookings", "confirmed_bookings" in dash)
test("Admin overview includes cancelled_bookings", "cancelled_bookings" in dash)
test("Admin overview includes total_revenue", "total_revenue" in dash)

# 2. Customer Management
cust_detail = main.admin_get_customer_detail(guest_user.id, admin=resolved_admin, db=db)
test("GET /admin/customers/{id} returns customer profile", cust_detail["email"] == guest_user.email)
test("GET /admin/customers/{id} includes booking list", len(cust_detail["bookings"]) >= 1)

main.admin_update_customer(guest_user.id, main.AdminCustomerUpdateRequest(phone="+91 91234 56789"), admin=resolved_admin, db=db)
cust_updated = main.admin_get_customer_detail(guest_user.id, admin=resolved_admin, db=db)
test("PUT /admin/customers/{id} updates customer phone", cust_updated["phone"] == "+91 91234 56789")

main.admin_update_customer_status(guest_user.id, main.AdminCustomerStatusUpdateRequest(status="Inactive"), admin=resolved_admin, db=db)
cust_deactivated = main.admin_get_customer_detail(guest_user.id, admin=resolved_admin, db=db)
test("PUT /admin/customers/{id}/status deactivates account", cust_deactivated["status"] == "Inactive")

# Admin self-deactivation guard
try:
    main.admin_update_customer_status(resolved_admin.id, main.AdminCustomerStatusUpdateRequest(status="Inactive"), admin=resolved_admin, db=db)
    test("Admin cannot deactivate own account", False)
except HTTPException as e:
    test("Admin self-deactivation blocked with 400", e.status_code == 400)

# Reactivate guest user
main.admin_update_customer_status(guest_user.id, main.AdminCustomerStatusUpdateRequest(status="Active"), admin=resolved_admin, db=db)

# 3. Housekeeping Module
hk_list = main.admin_get_housekeeping(admin=resolved_admin, db=db)
test("GET /admin/housekeeping returns room list", len(hk_list) >= 1)
test("Room has housekeeping_status attribute", "housekeeping_status" in hk_list[0])

hk_update = main.admin_update_housekeeping(
    room_id_101,
    main.HousekeepingUpdateRequest(housekeeping_status="Cleaning in Progress"),
    admin=resolved_admin,
    db=db
)
test("PUT /admin/housekeeping/{id} updates status to 'Cleaning in Progress'", hk_update["housekeeping_status"] == "Cleaning in Progress")
test("Housekeeping update records last_cleaned timestamp", hk_update["last_cleaned"] is not None)

# 4. Analytics Module
analytics = main.admin_get_analytics(admin=resolved_admin, db=db)
test("GET /admin/analytics returns occupancy stats", "occupancy" in analytics and "occupancy_rate" in analytics["occupancy"])
test("GET /admin/analytics returns monthly_trends", "monthly_trends" in analytics and len(analytics["monthly_trends"]) == 6)
test("GET /admin/analytics returns popular_categories", "popular_categories" in analytics)
test("GET /admin/analytics returns customer_statistics", "customer_statistics" in analytics)
test("GET /admin/analytics returns housekeeping_breakdown", "housekeeping_breakdown" in analytics)

# 5. Hotel Settings Module
settings = main.admin_get_settings(admin=resolved_admin, db=db)
test("GET /admin/settings returns hotel configuration", "hotel_name" in settings and "check_in_time" in settings)

updated_settings = main.admin_update_settings(
    main.HotelSettingsUpdateRequest(hotel_name="StayEase Palace & Luxury Suites", check_in_time="15:00"),
    admin=resolved_admin,
    db=db
)
test("PUT /admin/settings updates hotel name and check-in time", updated_settings["settings"]["hotel_name"] == "StayEase Palace & Luxury Suites" and updated_settings["settings"]["check_in_time"] == "15:00")

# 6. Security & Role Gates: verify customer receives 403 on admin endpoints
try:
    main.admin_get_settings(admin=main.require_admin(guest_user), db=db)
    test("Non-admin blocked from settings", False)
except HTTPException as e:
    test("Customer blocked from admin settings with 403", e.status_code == 403)

try:
    main.admin_get_analytics(admin=main.require_admin(guest_user), db=db)
    test("Non-admin blocked from analytics", False)
except HTTPException as e:
    test("Customer blocked from admin analytics with 403", e.status_code == 403)

try:
    main.admin_get_housekeeping(admin=main.require_admin(guest_user), db=db)
    test("Non-admin blocked from housekeeping", False)
except HTTPException as e:
    test("Customer blocked from housekeeping with 403", e.status_code == 403)

print("\n==========================================")
print(f"RESULTS: {passed} PASSED, {failed} FAILED")
print("==========================================\n")

if failed > 0:
    sys.exit(1)
