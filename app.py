import functools
import os
import random
import sqlite3
from datetime import datetime
from pathlib import Path
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db, init_db

ROOT = Path(__file__).resolve().parent

# Khởi tạo Flask Application
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "coffeeshop_vibe_key_2026_secret_secure")

# Khởi tạo CSDL SQLite nếu chưa có
init_db()

# Thông tin cửa hàng chuẩn theo thong_tin_cua_hang.md
STORE_INFO = {
    "name": "CoffeeShop",
    "slogan": "Cà phê phin – chậm lại một chút",
    "hotline": "1900 0001",
    "email": "order@coffeeshop.example",
    "address": "227 Nguyễn Văn Cừ, Phường Chợ Quán, TP.HCM",
    "hours": "7h00–22h00, Thứ Hai – Chủ nhật",
    "copyright": "Ảnh sản phẩm thuộc bản quyền chủ sở hữu – trang dùng cho mục đích học tập, không phát hành.",
}

FEATURED_IDS = [1, 7, 14, 24, 29, 39]


# Decorator kiểm tra đăng nhập
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Vui lòng đăng nhập để sử dụng tính năng này.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(**kwargs)

    return wrapped_view


# Context processor inject dữ liệu dùng chung vào mọi template
@app.context_processor
def inject_global_data():
    user = None
    if "user_id" in session:
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        conn.close()

    cart = session.get("cart", {})
    cart_count = sum(cart.values())

    return {
        "store": STORE_INFO,
        "current_user": user,
        "cart_count": cart_count,
    }


# Template filter định dạng giá tiền
@app.template_filter("format_price")
def format_price_filter(val):
    if val is None:
        return "Liên hệ"
    try:
        val = int(val)
        return f"{val:,}".replace(",", ".") + " đ"
    except (ValueError, TypeError):
        return f"{val} đ"


# Phục vụ ảnh món ăn trực tiếp từ thư mục images/products
@app.route("/images/products/<path:filename>")
def serve_product_images(filename):
    return send_from_directory(ROOT / "images" / "products", filename)


# Phục vụ FontAwesome trực tiếp từ site/vendor
@app.route("/vendor/<path:filename>")
def serve_vendor(filename):
    return send_from_directory(ROOT / "site" / "vendor", filename)


# Helper helper format thông tin trạng thái đơn hàng
def format_order_status(status):
    classes = {
        "Chờ xác nhận": ("pending", '<i class="fa-solid fa-clock"></i>', 1),
        "Đang pha chế": ("brewing", '<i class="fa-solid fa-blender"></i>', 2),
        "Đang giao hàng": ("shipping", '<i class="fa-solid fa-motorcycle"></i>', 3),
        "Hoàn thành": ("completed", '<i class="fa-solid fa-circle-check"></i>', 4),
        "Đã hủy": ("cancelled", '<i class="fa-solid fa-ban"></i>', 0),
    }
    return classes.get(status, ("secondary", '<i class="fa-solid fa-info"></i>', 0))


# ==========================================
# 1. TRANG CHỦ & THỰC ĐƠN
# ==========================================
@app.route("/")
def index():
    conn = get_db()
    # Danh mục và số lượng món
    categories = conn.execute(
        """
        SELECT c.*, COUNT(p.id) as count
        FROM categories c
        LEFT JOIN products p ON c.id = p.category_id
        GROUP BY c.id
        ORDER BY c.id ASC
        """
    ).fetchall()

    # Toàn bộ món ăn
    products = conn.execute(
        """
        SELECT p.*, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        ORDER BY p.id ASC
        """
    ).fetchall()

    # Món gợi ý hôm nay (ids: 1, 7, 14, 24, 29, 39)
    placeholders = ",".join("?" for _ in FEATURED_IDS)
    featured = conn.execute(
        f"""
        SELECT p.*, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.id IN ({placeholders})
        ORDER BY CASE p.id
            WHEN 1 THEN 1
            WHEN 7 THEN 2
            WHEN 14 THEN 3
            WHEN 24 THEN 4
            WHEN 29 THEN 5
            WHEN 39 THEN 6
        END
        """,
        FEATURED_IDS,
    ).fetchall()

    conn.close()
    return render_template(
        "index.html",
        categories=categories,
        products=products,
        featured_products=featured,
    )


# ==========================================
# 2. ĐĂNG KÝ THÀNH VIÊN
# ==========================================
@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("profile"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []
        if not username or len(username) < 3:
            errors.append("Tên đăng nhập phải từ 3 ký tự trở lên.")
        if not full_name:
            errors.append("Vui lòng nhập họ và tên.")
        if not email or "@" not in email:
            errors.append("Địa chỉ email không hợp lệ.")
        if len(password) < 6:
            errors.append("Mật khẩu phải có tối thiểu 6 ký tự.")
        if password != confirm_password:
            errors.append("Mật khẩu xác nhận không trùng khớp.")

        conn = get_db()
        # Kiểm tra trùng username
        existing_user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing_user:
            errors.append(f"Tên đăng nhập '{username}' đã được sử dụng. Vui lòng chọn tên khác.")

        # Kiểm tra trùng email
        existing_email = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing_email:
            errors.append(f"Email '{email}' đã được đăng ký trên hệ thống.")

        if errors:
            for err in errors:
                flash(err, "danger")
            conn.close()
            return render_template("register.html", form_data=request.form)

        # Lưu người dùng mới vào SQLite
        hashed = generate_password_hash(password)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (username, email, password_hash, full_name, phone, address, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (username, email, hashed, full_name, phone, address, now),
        )
        new_id = cur.lastrowid
        conn.commit()
        conn.close()

        # Tự động đăng nhập
        session["user_id"] = new_id
        flash(f"Đăng ký thành công! Chào mừng {full_name} gia nhập CoffeeShop.", "success")
        return redirect(url_for("index"))

    return render_template("register.html", form_data=None)


# ==========================================
# 3. ĐĂNG NHẬP / ĐĂNG XUẤT
# ==========================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("profile"))

    next_url = request.args.get("next") or request.form.get("next") or ""

    if request.method == "POST":
        login_input = request.form.get("username_or_email", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (login_input, login_input.lower()),
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash(f"Đăng nhập thành công! Chào mừng {user['full_name']} trở lại.", "success")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("index"))
        else:
            flash("Tên đăng nhập / Email hoặc mật khẩu không chính xác.", "danger")
            return render_template("login.html", username=login_input, next_url=next_url)

    return render_template("login.html", next_url=next_url)


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Bạn đã đăng xuất tài khoản an toàn.", "info")
    return redirect(url_for("index"))


# ==========================================
# 4. QUẢN LÝ THÔNG TIN CÁ NHÂN (PROFILE)
# ==========================================
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = session["user_id"]
    conn = get_db()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        if not full_name:
            flash("Họ và tên không được để trống.", "danger")
        else:
            conn.execute(
                """
                UPDATE users
                SET full_name = ?, phone = ?, address = ?
                WHERE id = ?
                """,
                (full_name, phone, address, user_id),
            )
            conn.commit()
            flash("Cập nhật thông tin cá nhân thành công!", "success")

    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    total_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id = ?", (user_id,)).fetchone()[0]
    completed_orders = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'Hoàn thành'", (user_id,)
    ).fetchone()[0]
    conn.close()

    stats = {
        "total_orders": total_orders,
        "completed_orders": completed_orders,
    }

    return render_template("profile.html", user=user, stats=stats)


@app.route("/change-password", methods=["POST"])
@login_required
def change_password():
    user_id = session["user_id"]
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_new_password = request.form.get("confirm_new_password", "")

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if not check_password_hash(user["password_hash"], current_password):
        flash("Mật khẩu hiện tại không chính xác.", "danger")
    elif len(new_password) < 6:
        flash("Mật khẩu mới phải có ít nhất 6 ký tự.", "danger")
    elif new_password != confirm_new_password:
        flash("Xác nhận mật khẩu mới không trùng khớp.", "danger")
    else:
        new_hashed = generate_password_hash(new_password)
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hashed, user_id))
        conn.commit()
        flash("Đổi mật khẩu thành công! Hãy ghi nhớ mật khẩu mới của bạn.", "success")

    conn.close()
    return redirect(url_for("profile"))


# ==========================================
# 5. XEM THÔNG TIN ĐƠN HÀNG (ORDERS)
# ==========================================
@app.route("/orders")
@login_required
def orders():
    user_id = session["user_id"]
    status_filter = request.args.get("status", "").strip()

    conn = get_db()

    # Thống kê số lượng đơn theo trạng thái
    status_counts = {
        "total": conn.execute("SELECT COUNT(*) FROM orders WHERE user_id = ?", (user_id,)).fetchone()[0],
        "pending": conn.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'Chờ xác nhận'", (user_id,)
        ).fetchone()[0],
        "brewing": conn.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'Đang pha chế'", (user_id,)
        ).fetchone()[0],
        "shipping": conn.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'Đang giao hàng'", (user_id,)
        ).fetchone()[0],
        "completed": conn.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'Hoàn thành'", (user_id,)
        ).fetchone()[0],
        "cancelled": conn.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'Đã hủy'", (user_id,)
        ).fetchone()[0],
    }

    if status_filter:
        query = "SELECT * FROM orders WHERE user_id = ? AND status = ? ORDER BY id DESC"
        params = (user_id, status_filter)
    else:
        query = "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC"
        params = (user_id,)

    raw_orders = conn.execute(query, params).fetchall()

    orders_list = []
    for o in raw_orders:
        items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (o["id"],)).fetchall()
        s_class, s_icon, s_step = format_order_status(o["status"])
        orders_list.append({
            "id": o["id"],
            "order_code": o["order_code"],
            "recipient_name": o["recipient_name"],
            "recipient_phone": o["recipient_phone"],
            "recipient_address": o["recipient_address"],
            "notes": o["notes"],
            "total_amount": o["total_amount"],
            "status": o["status"],
            "status_class": s_class,
            "status_icon": s_icon,
            "timeline_step": s_step,
            "created_at": o["created_at"],
            "order_items": items,
        })

    conn.close()

    return render_template(
        "orders.html",
        orders=orders_list,
        current_status=status_filter,
        status_counts=status_counts,
    )


@app.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    user_id = session["user_id"]
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, user_id)).fetchone()

    if not order:
        conn.close()
        flash("Không tìm thấy đơn hàng yêu cầu.", "danger")
        return redirect(url_for("orders"))

    items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    conn.close()

    s_class, s_icon, s_step = format_order_status(order["status"])
    order_data = {
        "id": order["id"],
        "order_code": order["order_code"],
        "recipient_name": order["recipient_name"],
        "recipient_phone": order["recipient_phone"],
        "recipient_address": order["recipient_address"],
        "notes": order["notes"],
        "total_amount": order["total_amount"],
        "status": order["status"],
        "status_class": s_class,
        "status_icon": s_icon,
        "timeline_step": s_step,
        "created_at": order["created_at"],
        "order_items": items,
    }

    return render_template("order_detail.html", order=order_data)


@app.route("/orders/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    user_id = session["user_id"]
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, user_id)).fetchone()

    if not order:
        conn.close()
        flash("Đơn hàng không tồn tại.", "danger")
        return redirect(url_for("orders"))

    if order["status"] != "Chờ xác nhận":
        conn.close()
        flash("Chỉ có thể hủy đơn hàng khi đơn ở trạng thái 'Chờ xác nhận'.", "warning")
        return redirect(url_for("order_detail", order_id=order_id))

    conn.execute("UPDATE orders SET status = 'Đã hủy' WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()

    flash(f"Đã hủy đơn hàng #{order['order_code']} thành công.", "info")
    return redirect(url_for("order_detail", order_id=order_id))


# ==========================================
# 6. GIỎ HÀNG & ĐẶT HÀNG TRỰC TUYẾN (CART & CHECKOUT)
# ==========================================
@app.route("/cart")
def view_cart():
    cart = session.get("cart", {})
    conn = get_db()

    cart_items = []
    total_amount = 0
    total_quantity = 0

    for pid_str, qty in cart.items():
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        p = conn.execute(
            """
            SELECT p.*, c.name as category_name
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.id = ?
            """,
            (pid,),
        ).fetchone()
        if p:
            subtotal = p["price"] * qty
            total_amount += subtotal
            total_quantity += qty
            cart_items.append({
                "product": p,
                "quantity": qty,
                "subtotal": subtotal,
            })

    conn.close()
    return render_template(
        "cart.html",
        cart_items=cart_items,
        total_amount=total_amount,
        total_quantity=total_quantity,
    )


@app.route("/cart/add", methods=["POST"])
def add_to_cart():
    if request.is_json:
        data = request.get_json() or {}
        pid = str(data.get("product_id"))
        qty = int(data.get("quantity", 1))
    else:
        pid = str(request.form.get("product_id"))
        qty = int(request.form.get("quantity", 1))

    if qty < 1:
        qty = 1

    cart = session.get("cart", {})
    cart[pid] = cart.get(pid, 0) + qty
    session["cart"] = cart
    session.modified = True

    total_count = sum(cart.values())

    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "cart_count": total_count})

    flash("Đã thêm món vào giỏ hàng!", "success")
    return redirect(url_for("view_cart"))


@app.route("/cart/update", methods=["POST"])
def update_cart():
    pid = str(request.form.get("product_id"))
    action = request.form.get("action", "")

    cart = session.get("cart", {})
    if pid in cart:
        if action == "increase":
            cart[pid] += 1
        elif action == "decrease":
            if cart[pid] > 1:
                cart[pid] -= 1
            else:
                cart.pop(pid, None)
        elif action == "remove":
            cart.pop(pid, None)

    session["cart"] = cart
    session.modified = True
    return redirect(url_for("view_cart"))


@app.route("/cart/clear", methods=["POST"])
def clear_cart():
    session["cart"] = {}
    session.modified = True
    flash("Đã xóa tất cả món trong giỏ hàng.", "info")
    return redirect(url_for("view_cart"))


@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    cart = session.get("cart", {})
    if not cart:
        flash("Giỏ hàng của bạn đang trống.", "warning")
        return redirect(url_for("view_cart"))

    user_id = session["user_id"]
    recipient_name = request.form.get("recipient_name", "").strip()
    recipient_phone = request.form.get("recipient_phone", "").strip()
    recipient_address = request.form.get("recipient_address", "").strip()
    notes = request.form.get("notes", "").strip()

    if not recipient_name or not recipient_phone or not recipient_address:
        flash("Vui lòng điền đầy đủ Họ tên, Số điện thoại và Địa chỉ nhận hàng.", "danger")
        return redirect(url_for("view_cart"))

    conn = get_db()
    cur = conn.cursor()

    # Tính tổng tiền và lấy thông tin chi tiết từng món
    order_items_data = []
    total_amount = 0

    for pid_str, qty in cart.items():
        pid = int(pid_str)
        p = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
        if p:
            subtotal = p["price"] * qty
            total_amount += subtotal
            order_items_data.append((p["id"], p["name"], p["image"], p["price"], qty, subtotal))

    if not order_items_data:
        conn.close()
        flash("Có lỗi khi kiểm tra các món trong giỏ hàng.", "danger")
        return redirect(url_for("view_cart"))

    # Sinh mã đơn hàng dạng CF-YYYYMMDD-XXXX
    date_str = datetime.now().strftime("%Y%m%d")
    rand_seq = random.randint(100, 999)
    order_code = f"CF-{date_str}-{rand_seq}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Lưu vào bảng orders
    cur.execute(
        """
        INSERT INTO orders (order_code, user_id, recipient_name, recipient_phone, recipient_address, notes, total_amount, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order_code,
            user_id,
            recipient_name,
            recipient_phone,
            recipient_address,
            notes,
            total_amount,
            "Chờ xác nhận",
            now_str,
        ),
    )
    order_id = cur.lastrowid

    # Lưu vào bảng order_items
    for it in order_items_data:
        cur.execute(
            """
            INSERT INTO order_items (order_id, product_id, product_name, product_image, price, quantity, subtotal)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (order_id, it[0], it[1], it[2], it[3], it[4], it[5]),
        )

    conn.commit()
    conn.close()

    # Xóa giỏ hàng sau khi đặt thành công
    session["cart"] = {}
    session.modified = True

    flash(f"🎉 Đặt hàng thành công! Đơn hàng #{order_code} đã được tạo và chuyển đến quầy pha chế.", "success")
    return redirect(url_for("order_detail", order_id=order_id))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("==================================================")
    print("  CoffeeShop Web Động (Python + SQLite)")
    print(f"  Đang chạy tại: http://127.0.0.1:{port}")
    print("  Tài khoản dùng thử: khachhang / 123456")
    print("==================================================")
    app.run(host="0.0.0.0", port=port, debug=True)
