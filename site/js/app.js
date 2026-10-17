(function () {
  "use strict";
  var D = window.MENU_DATA;
  if (!D) { document.body.insertAdjacentHTML("afterbegin", "<p style='padding:1rem;color:#b00'>Thiếu site/data.js – hãy chạy: python tools/build_data.py</p>"); return; }

  var $ = function (id) { return document.getElementById(id); };
  var catById = {};
  D.categories.forEach(function (c) { catById[c.id] = c; });
  var byId = {};
  D.products.forEach(function (p) { byId[p.id] = p; });

  var state = { cat: "all", q: "", sort: "default" };

  // ---------- Tiện ích ----------
  function fold(s) {
    return (s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase().replace(/\s+/g, " ").trim();
  }
  function formatPrice(n) {
    if (n == null) return "Liên hệ";
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ".") + " đ";
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function orderHref(p) {
    return "mailto:" + D.store.email + "?subject=" + encodeURIComponent("Đặt món: " + p.name);
  }
  function fallback(name) {
    var f = el("div", "img-fallback");
    f.appendChild(el("span", null, name));
    return f;
  }
  // Ảnh theo cột image; lỗi → khối nâu kèm tên món
  function media(p, cls) {
    var wrap = el("div", cls);
    if (!p.image) { wrap.appendChild(fallback(p.name)); return wrap; }
    var img = new Image();
    img.alt = p.name;
    img.loading = "lazy";
    img.onerror = function () { wrap.replaceChild(fallback(p.name), img); wrap.classList.add("is-broken"); };
    img.src = p.image;
    wrap.appendChild(img);
    return wrap;
  }

  // ---------- Thẻ món ----------
  function card(p, extraCls) {
    var c = el("article", "card" + (extraCls ? " " + extraCls : ""));
    c.dataset.id = p.id;
    c.tabIndex = 0;
    c.setAttribute("role", "button");
    c.setAttribute("aria-label", "Xem chi tiết " + p.name);
    c.appendChild(media(p, "card-media"));
    var body = el("div", "card-body");
    body.appendChild(el("span", "card-cat", catById[p.categoryId] ? catById[p.categoryId].name : ""));
    body.appendChild(el("h3", "card-title", p.name));
    var foot = el("div", "card-foot");
    foot.appendChild(el("span", "price", formatPrice(p.price)));
    var a = el("a", "btn btn-order btn-sm", "Đặt món");
    a.href = orderHref(p);
    a.addEventListener("click", function (e) { e.stopPropagation(); });
    foot.appendChild(a);
    body.appendChild(foot);
    c.appendChild(body);
    c.addEventListener("click", function () { openModal(p); });
    c.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openModal(p); }
    });
    return c;
  }

  // ---------- Thông tin quán ----------
  function renderStore() {
    var s = D.store;
    $("store-name").textContent = s.name;
    $("store-slogan").textContent = s.slogan;
    $("store-hours").textContent = "Mở cửa " + s.hours;
    $("footer-name").textContent = s.name;
    $("footer-address").textContent = "Địa chỉ: " + s.address;
    $("footer-contact").innerHTML = "";
    $("footer-contact").append("Hotline: " + s.hotline + " · Email: ");
    var m = el("a", null, s.email); m.href = "mailto:" + s.email;
    $("footer-contact").appendChild(m);
    $("footer-hours").textContent = "Giờ mở cửa: " + s.hours;
    $("footer-copyright").textContent = s.copyright;
  }

  function renderFeatured() {
    var box = $("featured-list");
    D.featuredIds.forEach(function (id) {
      if (byId[id]) box.appendChild(card(byId[id], "card-featured"));
    });
  }

  function renderTabs() {
    var tabs = $("tabs");
    var list = [{ id: "all", name: "Tất cả", count: D.products.length }].concat(D.categories);
    list.forEach(function (c) {
      var b = el("button", "tab");
      b.type = "button";
      b.setAttribute("role", "tab");
      b.dataset.cat = c.id;
      b.appendChild(document.createTextNode(c.name + " "));
      b.appendChild(el("span", "tab-count", "(" + c.count + ")"));
      b.addEventListener("click", function () { state.cat = String(c.id); render(); });
      tabs.appendChild(b);
    });
  }

  function filtered() {
    var q = fold(state.q);
    var list = D.products.filter(function (p) {
      if (state.cat !== "all" && String(p.categoryId) !== state.cat) return false;
      if (q && fold(p.name).indexOf(q) === -1) return false;
      return true;
    });
    if (state.sort === "price-asc") list.sort(function (a, b) { return (a.price - b.price) || (a.id - b.id); });
    else if (state.sort === "price-desc") list.sort(function (a, b) { return (b.price - a.price) || (a.id - b.id); });
    else list.sort(function (a, b) { return a.id - b.id; });
    return list;
  }

  function render() {
    Array.prototype.forEach.call($("tabs").children, function (b) {
      var on = b.dataset.cat === state.cat;
      b.classList.toggle("active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    var cat = catById[state.cat];
    var desc = $("cat-desc");
    if (cat && cat.description) { desc.textContent = cat.description; desc.hidden = false; }
    else { desc.hidden = true; desc.textContent = ""; }

    var list = filtered();
    var grid = $("grid");
    grid.innerHTML = "";
    var frag = document.createDocumentFragment();
    list.forEach(function (p) { frag.appendChild(card(p)); });
    grid.appendChild(frag);
    $("result-count").textContent = "Đang hiển thị " + list.length + " món";
    $("empty").hidden = list.length > 0;
  }

  // ---------- Cửa sổ chi tiết ----------
  var lastFocus = null;
  function openModal(p) {
    lastFocus = document.activeElement;
    var m = $("modal-media");
    m.innerHTML = "";
    m.appendChild(media(p, "modal-img"));
    $("modal-cat").textContent = catById[p.categoryId] ? catById[p.categoryId].name : "";
    $("modal-title").textContent = p.name;
    $("modal-price").textContent = formatPrice(p.price);
    $("modal-desc").textContent = p.description;
    $("modal-order").href = orderHref(p);
    $("modal").hidden = false;
    document.body.classList.add("no-scroll");
    $("modal").querySelector(".modal-close").focus();
  }
  function closeModal() {
    $("modal").hidden = true;
    document.body.classList.remove("no-scroll");
    if (lastFocus) lastFocus.focus();
  }
  $("modal").addEventListener("click", function (e) {
    if (e.target.hasAttribute("data-close")) closeModal();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !$("modal").hidden) closeModal();
  });

  // ---------- Điều khiển ----------
  $("search").addEventListener("input", function (e) { state.q = e.target.value; render(); });
  $("sort").addEventListener("change", function (e) { state.sort = e.target.value; render(); });

  renderStore();
  renderFeatured();
  renderTabs();
  render();
})();
