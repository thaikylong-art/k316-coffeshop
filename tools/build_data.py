"""Đọc data/*.csv (chỉ đọc, không sửa) → làm sạch theo chính sách hiển thị → ghi site/data.js.

Đồng thời chép ảnh images/products/ → site/images/products/ để thư mục site/ chạy độc lập.
Chạy:  python tools/build_data.py
"""
import csv
import html
import json
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = ROOT / "site"
IMG_SRC = ROOT / "images" / "products"
IMG_DST = SITE / "images" / "products"

# Theo thong_tin_cua_hang.md
FEATURED_IDS = [1, 7, 14, 24, 29, 39]
EMPTY_DESC = "Mô tả đang được cập nhật."
STORE = {
    "name": "CoffeeShop",
    "slogan": "Cà phê phin – chậm lại một chút",
    "hotline": "1900 0001",
    "email": "order@coffeeshop.example",
    "address": "227 Nguyễn Văn Cừ, Phường Chợ Quán, TP.HCM",
    "hours": "7h00–22h00, Thứ Hai – Chủ nhật",
    "copyright": "Ảnh sản phẩm thuộc bản quyền chủ sở hữu – trang dùng cho mục đích học tập, không phát hành.",
}


def nfc(s):
    return unicodedata.normalize("NFC", s or "").strip()


def strip_html(s):
    """Bỏ thẻ HTML, giải mã thực thể (&nbsp; ...), gộp khoảng trắng."""
    s = re.sub(r"<br\s*/?>|</p>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def title_case(s):
    """'PHIN ĐEN ĐÁ' → 'Phin Đen Đá'; 'SÔ-CÔ-LA' → 'Sô-Cô-La'."""
    return nfc(s.lower().title())


def parse_date(s):
    """Chấp nhận cả 'YYYY-MM-DD HH:MM:SS' và có phần micro giây."""
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    return None


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    warnings = []
    cat_rows = read_csv(DATA / "category.csv")
    prod_rows = read_csv(DATA / "product.csv")

    categories = []
    for r in sorted(cat_rows, key=lambda r: int(r["id"])):
        categories.append({
            "id": int(r["id"]),
            "name": nfc(r["name"]),
            "description": strip_html(nfc(r["description"])),  # trống → "" → giao diện bỏ qua
        })
    cat_ids = {c["id"] for c in categories}

    products = []
    for r in prod_rows:
        pid = int(r["id"])
        cid = int(r["category_id"])
        if cid not in cat_ids:
            warnings.append(f"Món id {pid}: category_id {cid} không tồn tại")
        try:
            price = int(float(r["price"]))
        except ValueError:
            price = None
            warnings.append(f"Món id {pid}: giá không hợp lệ '{r['price']}'")
        image = nfc(r["image"]).replace("\\", "/")
        if image and not (ROOT / image).is_file():
            warnings.append(f"Món id {pid}: thiếu ảnh {image}")
        desc = strip_html(nfc(r["description"])) or EMPTY_DESC
        date = parse_date(r["published_date"])
        if date is None:
            warnings.append(f"Món id {pid}: ngày không đọc được '{r['published_date']}'")
        products.append({
            "id": pid,
            "name": title_case(r["name"]),
            "price": price,
            "image": image,  # đường dẫn tương đối so với site/index.html
            "description": desc,
            "categoryId": cid,
            "publishedDate": date,
        })
    products.sort(key=lambda p: p["id"])

    for c in categories:
        c["count"] = sum(1 for p in products if p["categoryId"] == c["id"])

    ids = {p["id"] for p in products}
    for fid in FEATURED_IDS:
        if fid not in ids:
            warnings.append(f"Gợi ý hôm nay: không có món id {fid}")

    # Chép ảnh
    IMG_DST.mkdir(parents=True, exist_ok=True)
    copied = 0
    for f in IMG_SRC.iterdir():
        if f.is_file():
            shutil.copy2(f, IMG_DST / f.name)
            copied += 1

    data = {
        "store": STORE,
        "featuredIds": FEATURED_IDS,
        "categories": categories,
        "products": products,
        "generatedFrom": {"productRows": len(prod_rows), "categoryRows": len(cat_rows)},
    }
    out = SITE / "data.js"
    out.write_text(
        "// Tệp sinh tự động bởi tools/build_data.py – không sửa tay.\n"
        "window.MENU_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n",
        encoding="utf-8",
    )

    print(f"Đã ghi {out.relative_to(ROOT)}: {len(products)} món, {len(categories)} danh mục; chép {copied} ảnh.")
    for c in categories:
        print(f"  - {c['name']}: {c['count']} món")
    for w in warnings:
        print("CẢNH BÁO:", w)
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
