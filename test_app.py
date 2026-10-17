import os
import unittest
from pathlib import Path
from app import app
from database import get_db, init_db

class CoffeeShopTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        init_db()

    def test_01_index_page(self):
        """Kiểm tra trang chủ hiển thị thành công"""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("CoffeeShop".encode("utf-8"), res.data)
        self.assertIn("Gợi ý hôm nay".encode("utf-8"), res.data)
        self.assertIn("Cà phê".encode("utf-8"), res.data)

    def test_02_login_demo_user(self):
        """Kiểm tra đăng nhập bằng tài khoản mẫu"""
        res = self.client.post("/login", data={
            "username_or_email": "khachhang",
            "password": "wrongpassword"
        }, follow_redirects=True)
        self.assertIn("không chính xác".encode("utf-8"), res.data)

        # Đăng nhập đúng
        res = self.client.post("/login", data={
            "username_or_email": "khachhang",
            "password": "123456"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Đăng nhập thành công".encode("utf-8"), res.data)
        self.assertIn("Nguyễn Văn An".encode("utf-8"), res.data)

    def test_03_register_new_user(self):
        """Kiểm tra đăng ký thành viên mới"""
        conn = get_db()
        conn.execute("DELETE FROM users WHERE username = 'testuser99'")
        conn.commit()
        conn.close()

        res = self.client.post("/register", data={
            "username": "testuser99",
            "full_name": "Trần Thị Thử Nghiệm",
            "email": "test99@example.com",
            "phone": "0988776655",
            "address": "123 Đường Số 1, Quận 1",
            "password": "secretpassword",
            "confirm_password": "secretpassword"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Đăng ký thành công".encode("utf-8"), res.data)

        # Kiểm tra CSDL SQLite có người dùng mới
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = 'testuser99'").fetchone()
        self.assertIsNotNone(user)
        self.assertEqual(user["full_name"], "Trần Thị Thử Nghiệm")
        conn.close()

    def test_04_profile_management(self):
        """Kiểm tra xem và cập nhật thông tin cá nhân"""
        # Đăng nhập
        self.client.post("/login", data={"username_or_email": "khachhang", "password": "123456"})
        
        # Xem profile
        res = self.client.get("/profile")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Quản lý thông tin cá nhân".encode("utf-8"), res.data)

        # Cập nhật thông tin
        res = self.client.post("/profile", data={
            "full_name": "Nguyễn Văn An (Đã Đổi)",
            "phone": "0909998877",
            "address": "456 Lê Lợi, Quận 1, TP.HCM"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Cập nhật thông tin cá nhân thành công".encode("utf-8"), res.data)

        # Khôi phục lại tên cũ
        self.client.post("/profile", data={
            "full_name": "Nguyễn Văn An",
            "phone": "0901234567",
            "address": "227 Nguyễn Văn Cừ, Phường Chợ Quán, Quận 5, TP.HCM"
        })

    def test_05_view_orders(self):
        """Kiểm tra xem thông tin đơn hàng"""
        # Đăng nhập
        self.client.post("/login", data={"username_or_email": "khachhang", "password": "123456"})

        # Danh sách đơn hàng
        res = self.client.get("/orders")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Đơn hàng của tôi".encode("utf-8"), res.data)
        self.assertIn("CF-20261015-001".encode("utf-8"), res.data)

        # Chi tiết đơn hàng
        conn = get_db()
        order = conn.execute("SELECT id FROM orders WHERE order_code = 'CF-20261015-001'").fetchone()
        conn.close()
        self.assertIsNotNone(order)

        res = self.client.get(f"/orders/{order['id']}")
        self.assertEqual(res.status_code, 200)
        self.assertIn("CF-20261015-001".encode("utf-8"), res.data)
        self.assertIn("Danh sách món đã đặt".encode("utf-8"), res.data)

    def test_06_cart_and_checkout(self):
        """Kiểm tra thêm món vào giỏ và đặt hàng thành công"""
        # Đăng nhập
        self.client.post("/login", data={"username_or_email": "khachhang", "password": "123456"})

        # Thêm món id 1 (Phin Đen Đá) vào giỏ
        res = self.client.post("/cart/add", json={"product_id": 1, "quantity": 2})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["cart_count"], 2)

        # Xem giỏ hàng
        res = self.client.get("/cart")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Phin Đen Đá".encode("utf-8"), res.data)

        # Đặt hàng (Checkout)
        res = self.client.post("/checkout", data={
            "recipient_name": "Nguyễn Văn An",
            "recipient_phone": "0901234567",
            "recipient_address": "227 Nguyễn Văn Cừ, Quận 5",
            "notes": "Cho nhiều sữa đặc"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Đặt hàng thành công".encode("utf-8"), res.data)

if __name__ == "__main__":
    unittest.main()
