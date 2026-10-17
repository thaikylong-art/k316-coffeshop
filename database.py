import csv
import html
import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "coffeeshop.db"
DATA_DIR = ROOT / "data"

EMPTY_DESC = "Mô tả đang được cập nhật."


def nfc(s):
    return unicodedata.normalize("NFC", s or "").strip()


def strip_html(s):
    s = re.sub(r"<br\s*/?>|</p>", " ", s or "", flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def title_case(s):
    return nfc((s or "").lower().title())


def parse_date(s):
    if not s:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Tạo bảng
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        created_at TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY,
        category_id INTEGER NOT NULL REFERENCES categories(id),
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        image TEXT,
        description TEXT,
        published_date TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_code TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL REFERENCES users(id),
        recipient_name TEXT NOT NULL,
        recipient_phone TEXT NOT NULL,
        recipient_address TEXT NOT NULL,
        notes TEXT,
        total_amount INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'Chờ xác nhận',
        created_at TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL REFERENCES products(id),
        product_name TEXT NOT NULL,
        product_image TEXT,
        price INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        subtotal INTEGER NOT NULL
    );
    """)

    # Khởi tạo categories nếu chưa có
    cur.execute("SELECT COUNT(*) as cnt FROM categories")
    if cur.fetchone()["cnt"] == 0:
        cat_file = DATA_DIR / "category.csv"
        if cat_file.exists():
            with open(cat_file, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    cur.execute(
                        "INSERT INTO categories (id, name, description) VALUES (?, ?, ?)",
                        (
                            int(r["id"]),
                            nfc(r["name"]),
                            strip_html(nfc(r.get("description", ""))),
                        ),
                    )

    # Khởi tạo products nếu chưa có
    cur.execute("SELECT COUNT(*) as cnt FROM products")
    if cur.fetchone()["cnt"] == 0:
        prod_file = DATA_DIR / "product.csv"
        if prod_file.exists():
            with open(prod_file, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    pid = int(r["id"])
                    cid = int(r["category_id"])
                    try:
                        price = int(float(r["price"]))
                    except (ValueError, TypeError):
                        price = 0
                    img = nfc(r.get("image", "")).replace("\\", "/")
                    desc = strip_html(nfc(r.get("description", ""))) or EMPTY_DESC
                    dt = parse_date(r.get("published_date", ""))
                    cur.execute(
                        """
                        INSERT INTO products (id, category_id, name, price, image, description, published_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (pid, cid, title_case(r["name"]), price, img, desc, dt),
                    )

    # Tạo tài khoản demo mặc định nếu chưa có
    cur.execute("SELECT * FROM users WHERE username = ?", ("khachhang",))
    demo_user = cur.fetchone()
    if not demo_user:
        hashed = generate_password_hash("123456")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """
            INSERT INTO users (username, email, password_hash, full_name, phone, address, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "khachhang",
                "khachhang@coffeeshop.vn",
                hashed,
                "Nguyễn Văn An",
                "0901234567",
                "227 Nguyễn Văn Cừ, Phường Chợ Quán, Quận 5, TP.HCM",
                now,
            ),
        )
        user_id = cur.lastrowid
    else:
        user_id = demo_user["id"]

    # Tạo đơn hàng mẫu cho tài khoản demo nếu chưa có đơn nào
    cur.execute("SELECT COUNT(*) as cnt FROM orders WHERE user_id = ?", (user_id,))
    if cur.fetchone()["cnt"] == 0:
        sample_orders = [
            {
                "code": "CF-20261015-001",
                "status": "Hoàn thành",
                "notes": "Giao tận tay, xin thêm đá riêng",
                "date": "2026-10-15 08:30:00",
                "items": [
                    (1, "Phin Đen Đá", "images/products/Phin_Den_Da.jpg", 29000, 2),
                    (29, "Bánh Mousse Đào", "images/products/MOUSSEDAO.png", 35000, 1),
                ],
            },
            {
                "code": "CF-20261016-002",
                "status": "Đang pha chế",
                "notes": "Trà sen ít ngọt 50% đường",
                "date": "2026-10-16 14:15:00",
                "items": [
                    (24, "Trà Sen Vàng Củ Năng", "images/products/HLC_New_logo_5.1_Products__TRA_SEN_VANG_CU_NANG.jpg", 45000, 2),
                    (14, "Freeze Trà Xanh", "images/products/HLC_New_logo_5.1_Products__FREEZE_TRA_XANH.jpg", 55000, 1),
                ],
            },
            {
                "code": "CF-20261017-003",
                "status": "Chờ xác nhận",
                "notes": "Mang lên lầu 3 giúp mình",
                "date": "2026-10-17 11:20:00",
                "items": [
                    (7, "Bạc Xỉu", "images/products/Bac_Xiu.jpg", 29000, 1),
                    (39, "Bánh Phô Mai Cà Phê", "images/products/PHOMAICAPHE.jpg", 35000, 1),
                ],
            },
        ]

        for s in sample_orders:
            total = sum(it[3] * it[4] for it in s["items"])
            cur.execute(
                """
                INSERT INTO orders (order_code, user_id, recipient_name, recipient_phone, recipient_address, notes, total_amount, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    s["code"],
                    user_id,
                    "Nguyễn Văn An",
                    "0901234567",
                    "227 Nguyễn Văn Cừ, Phường Chợ Quán, Quận 5, TP.HCM",
                    s["notes"],
                    total,
                    s["status"],
                    s["date"],
                ),
            )
            oid = cur.lastrowid
            for it in s["items"]:
                pid, pname, pimg, price, qty = it
                cur.execute(
                    """
                    INSERT INTO order_items (order_id, product_id, product_name, product_image, price, quantity, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (oid, pid, pname, pimg, price, qty, price * qty),
                )

    conn.commit()
    conn.close()
    print("Khởi tạo SQLite database thành công!")


if __name__ == "__main__":
    init_db()
