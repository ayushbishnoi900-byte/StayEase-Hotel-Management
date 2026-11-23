"""
StayEase Authentication & User Profile Automated Tests
"""

import unittest
from fastapi import HTTPException
from tests.base import BaseTestCase
import main


class TestAuth(BaseTestCase):

    def test_registration_success(self):
        req = main.RegisterRequest(
            name="Alice Walker",
            email="alice@example.com",
            password="SecurePassword123!",
            phone="+91 98765 11111"
        )
        res = main.register(req, db=self.db)
        self.assertIn("customer_id", res)
        self.assertEqual(res["message"], "Account created successfully. Please login.")

    def test_duplicate_registration_prevented(self):
        req = main.RegisterRequest(
            name="Duplicate User",
            email="duplicate@example.com",
            password="Password123!",
            phone="+91 98765 22222"
        )
        main.register(req, db=self.db)
        with self.assertRaises(HTTPException) as ctx:
            main.register(req, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("already registered", ctx.exception.detail.lower())

    def test_login_success(self):
        self.create_customer(name="Bob Smith", email="bob@example.com", password="SecretPassword99!")
        req = main.LoginRequest(email="bob@example.com", password="SecretPassword99!")
        res = main.login(req, db=self.db)
        self.assertIn("access_token", res)
        self.assertEqual(res["token_type"], "bearer")
        self.assertEqual(res["customer"]["email"], "bob@example.com")

    def test_login_invalid_password(self):
        self.create_customer(email="charlie@example.com", password="CorrectPassword123!")
        req = main.LoginRequest(email="charlie@example.com", password="WrongPassword!")
        with self.assertRaises(HTTPException) as ctx:
            main.login(req, db=self.db)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("invalid", ctx.exception.detail.lower())

    def test_login_nonexistent_email(self):
        req = main.LoginRequest(email="nobody@example.com", password="Password123!")
        with self.assertRaises(HTTPException) as ctx:
            main.login(req, db=self.db)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_jwt_token_resolution(self):
        self.create_customer(email="token_user@example.com", password="Password123!")
        login_res = main.login(main.LoginRequest(email="token_user@example.com", password="Password123!"), db=self.db)
        token = login_res["access_token"]

        class MockCreds:
            credentials = token

        user = main.get_current_user(MockCreds(), db=self.db)
        self.assertEqual(user.email, "token_user@example.com")

    def test_profile_read_and_update(self):
        cust = self.create_customer(name="Initial Name", email="profile@example.com", phone="+91 99999 11111")
        prof = main.get_customer_profile(customer=cust)
        self.assertEqual(prof["name"], "Initial Name")

        update_req = main.ProfileUpdateRequest(name="Updated Name", phone="+91 88888 22222")
        updated = main.update_customer_profile(update_req, customer=cust, db=self.db)
        self.assertEqual(updated["customer"]["name"], "Updated Name")
        self.assertEqual(updated["customer"]["phone"], "+91 88888 22222")


if __name__ == "__main__":
    unittest.main()
