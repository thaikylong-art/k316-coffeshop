"""Kiểm tra site/: số món so với CSV, số món từng danh mục, ảnh tồn tại,
và (nếu có Edge/Chrome) kiểm tra DOM thực tế sau khi JS chạy + chụp ảnh màn hình điện thoại.
Chạy:  python tools/check_site.py
"""
import csv
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
ok = True


def check(cond, msg):
    global ok
    print(("  OK   " if cond else "  LỖI  ") + msg)
    ok = ok and cond


def load_data():
    txt = (SITE / "data.js").read_text(encoding="utf-8")
    return json.loads(re.search(r"window\.MENU_DATA = (.*);\s*$", txt, re.S).group(1))


def find_browser():
    cands = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for c in cands:
        if Path(c).is_file():
            return c
    return shutil.which("msedge") or shutil.which("chrome") or shutil.which("google-chrome")


def main():
    with open(ROOT / "data/product.csv", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    csv_counts = Counter(int(r["category_id"]) for r in rows)
    D = load_data()

    print("1) data.js so với CSV")
    check(len(D["products"]) == len(rows), f"Tổng món: data.js={len(D['products'])}, CSV={len(rows)}")
    for c in D["categories"]:
        check(c["count"] == csv_counts[c["id"]], f"{c['name']}: {c['count']} (CSV {csv_counts[c['id']]})")
    check(all("<" not in p["description"] and "&nbsp;" not in p["description"] for p in D["products"]), "Mô tả không còn thẻ HTML")
    check(all(p["description"] for p in D["products"]), "Không món nào mô tả rỗng")

    print("2) Ảnh")
    missing = [p["image"] for p in D["products"] if not (SITE / p["image"]).is_file()]
    check(not missing, f"Mọi ảnh tồn tại trong site/ ({len(D['products']) - len(missing)}/{len(D['products'])})" + (f" thiếu: {missing}" if missing else ""))

    print("3) DOM thực tế (trình duyệt headless)")
    br = find_browser()
    if not br:
        print("  BỎ QUA: không tìm thấy Edge/Chrome")
        return 0 if ok else 1
    url = (SITE / "index.html").as_uri()
    dom = subprocess.run([br, "--headless=new", "--disable-gpu", "--allow-file-access-from-files",
                          "--virtual-time-budget=5000", "--dump-dom", url],
                         capture_output=True, text=True, encoding="utf-8", timeout=60).stdout
    grid = dom.split('id="grid"', 1)[1].split('id="empty"', 1)[0] if 'id="grid"' in dom else ""
    n_grid = grid.count('class="card"')
    check(n_grid == len(rows), f"Lưới hiển thị {n_grid} món khi không lọc (CSV {len(rows)})")
    for c in D["categories"]:
        m = re.search(r'data-cat="%d"[^>]*>[^<]*<span class="tab-count">\((\d+)\)' % c["id"], dom)
        check(bool(m) and int(m.group(1)) == csv_counts[c["id"]], f"Tab {c['name']} hiển thị ({m.group(1) if m else '?'})")
    m = re.search(r'data-cat="all"[^>]*>[^<]*<span class="tab-count">\((\d+)\)', dom)
    check(bool(m) and int(m.group(1)) == len(rows), f"Tab Tất cả hiển thị ({m.group(1) if m else '?'})")
    check(dom.count("card card-featured") == 6, "Gợi ý hôm nay có 6 món")
    check("img-fallback" not in dom, "Không ảnh nào rơi vào khối dự phòng (ảnh lỗi)")

    shots = ROOT / "tools" / "screenshots"
    shots.mkdir(exist_ok=True)
    # Edge headless không thu cửa sổ nhỏ hơn ~500px → đặt trang trong iframe 390px để thử đúng bề rộng điện thoại.
    harness = shots / "_mobile_harness.html"
    harness.write_text(
        '<!doctype html><body style="margin:0;background:#888">'
        f'<iframe id="f" src="{url}" style="width:390px;height:844px;border:0;display:block"></iframe>'
        '<script>setTimeout(function(){var w=document.getElementById("f").contentWindow;'
        'document.body.setAttribute("data-probe",w.innerWidth+"|"+w.document.documentElement.scrollWidth)},1500)</script></body>',
        encoding="utf-8")
    base = [br, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
            "--virtual-time-budget=6000"]
    probe = subprocess.run(base + ["--window-size=500,844", "--dump-dom", harness.as_uri()],
                           capture_output=True, text=True, encoding="utf-8", timeout=60).stdout
    m = re.search(r'data-probe="(\d+)\|(\d+)"', probe)
    check(bool(m) and m.group(1) == "390" and int(m.group(2)) <= 390,
          f"Bề rộng điện thoại 390px không tràn ngang (viewport|scrollWidth = {m.group(1) + '|' + m.group(2) if m else '?'})")
    for name, size, target in [("mobile_390", "500,844", harness.as_uri()), ("desktop_1280", "1280,900", url)]:
        out = shots / f"{name}.png"
        subprocess.run(base + [f"--window-size={size}", f"--screenshot={out}", target], capture_output=True, timeout=60)
        print(f"  Ảnh chụp: {out.relative_to(ROOT)} ({'có' if out.is_file() else 'không tạo được'})")
    return 0 if ok else 1


if __name__ == "__main__":
    r = main()
    print("KẾT QUẢ:", "ĐẠT" if r == 0 else "CÓ LỖI")
    sys.exit(r)
