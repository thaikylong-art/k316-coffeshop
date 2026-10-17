(function () {
  "use strict";

  // Tiện ích bỏ dấu tiếng Việt để tìm kiếm thông minh
  function fold(s) {
    return (s || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();
  }

  // Định dạng tiền tệ VND
  function formatPrice(n) {
    if (n == null) return "Liên hệ";
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ".") + " đ";
  }

  // Toast notification
  function showToast(message, type) {
    type = type || "success";
    var container = document.getElementById("toast-container");
    if (!container) return;

    var toast = document.createElement("div");
    toast.className = "toast toast-" + type;
    var iconClass = type === "success" ? "fa-circle-check text-success" : "fa-circle-exclamation text-danger";
    toast.innerHTML = '<i class="fa-solid ' + iconClass + '"></i><span>' + message + "</span>";

    container.appendChild(toast);
    setTimeout(function () {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(20px)";
      toast.style.transition = "all 0.3s";
      setTimeout(function () {
        if (toast.parentElement) toast.remove();
      }, 300);
    }, 3000);
  }
  window.showToast = showToast;

  // Thêm vào giỏ hàng AJAX
  window.addToCart = function (productId, productName, price, qty) {
    qty = qty || 1;
    fetch("/cart/add", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({
        product_id: productId,
        quantity: qty,
      }),
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        if (data.success) {
          var badge = document.getElementById("cart-badge");
          if (badge) {
            badge.textContent = data.cart_count;
            badge.style.transform = "scale(1.35)";
            setTimeout(function () {
              badge.style.transform = "scale(1)";
            }, 250);
          }
          showToast("Đã thêm " + (qty > 1 ? qty + " " : "") + productName + " vào giỏ!", "success");
          closeModal();
        } else {
          showToast(data.message || "Không thể thêm vào giỏ hàng.", "error");
        }
      })
      .catch(function (err) {
        console.error("Cart error:", err);
        // Fallback gửi form thông thường nếu fetch lỗi
        var form = document.createElement("form");
        form.method = "POST";
        form.action = "/cart/add";
        var inp1 = document.createElement("input");
        inp1.type = "hidden";
        inp1.name = "product_id";
        inp1.value = productId;
        var inp2 = document.createElement("input");
        inp2.type = "hidden";
        inp2.name = "quantity";
        inp2.value = qty;
        form.appendChild(inp1);
        form.appendChild(inp2);
        document.body.appendChild(form);
        form.submit();
      });
  };

  // User Dropdown menu
  var userBtn = document.getElementById("user-btn");
  var userDropdown = document.getElementById("user-dropdown");
  if (userBtn && userDropdown) {
    userBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      var expanded = userBtn.getAttribute("aria-expanded") === "true";
      userBtn.setAttribute("aria-expanded", !expanded);
      userDropdown.classList.toggle("show");
    });
    document.addEventListener("click", function (e) {
      if (!userDropdown.contains(e.target) && !userBtn.contains(e.target)) {
        userDropdown.classList.remove("show");
        userBtn.setAttribute("aria-expanded", "false");
      }
    });
  }

  // Trang chủ: Lọc món & Tìm kiếm
  var tabsContainer = document.getElementById("tabs");
  var searchInput = document.getElementById("search-input");
  var searchClear = document.getElementById("search-clear");
  var sortSelect = document.getElementById("sort-select");
  var grid = document.getElementById("product-grid");
  var resultCount = document.getElementById("result-count");
  var emptyState = document.getElementById("empty-state");
  var resetBtn = document.getElementById("btn-reset-filter");

  var currentCat = "all";
  var currentQuery = "";
  var currentSort = "default";

  function applyFilters() {
    if (!grid) return;
    var cards = Array.from(grid.querySelectorAll(".product-card"));
    var count = 0;

    cards.forEach(function (card) {
      var cat = card.dataset.cat;
      var name = card.dataset.name || "";
      var desc = card.dataset.desc || "";

      var matchCat = currentCat === "all" || cat === currentCat;
      var matchQuery = true;
      if (currentQuery) {
        var foldedName = fold(name);
        var foldedDesc = fold(desc);
        matchQuery = foldedName.indexOf(currentQuery) !== -1 || foldedDesc.indexOf(currentQuery) !== -1;
      }

      if (matchCat && matchQuery) {
        card.style.display = "";
        count++;
      } else {
        card.style.display = "none";
      }
    });

    // Sắp xếp các card còn hiển thị
    if (currentSort !== "default") {
      var sortedCards = cards.filter(function (c) {
        return c.style.display !== "none";
      });
      sortedCards.sort(function (a, b) {
        var priceA = parseInt(a.dataset.price, 10) || 0;
        var priceB = parseInt(b.dataset.price, 10) || 0;
        var nameA = (a.dataset.name || "").toLowerCase();
        var nameB = (b.dataset.name || "").toLowerCase();

        if (currentSort === "price-asc") return priceA - priceB;
        if (currentSort === "price-desc") return priceB - priceA;
        if (currentSort === "name-asc") return nameA.localeCompare(nameB, "vi");
        return 0;
      });
      sortedCards.forEach(function (c) {
        grid.appendChild(c);
      });
    }

    if (resultCount) {
      resultCount.textContent = "Hiển thị " + count + " món";
    }
    if (emptyState) {
      emptyState.hidden = count > 0;
    }

    // Hiển thị mô tả danh mục
    var allCatDescs = document.querySelectorAll(".cat-desc-panel");
    allCatDescs.forEach(function (p) {
      p.hidden = true;
    });
    if (currentCat !== "all") {
      var activeDesc = document.getElementById("cat-desc-" + currentCat);
      if (activeDesc) activeDesc.hidden = false;
    }
  }

  if (tabsContainer) {
    tabsContainer.addEventListener("click", function (e) {
      var btn = e.target.closest(".tab");
      if (!btn) return;
      tabsContainer.querySelectorAll(".tab").forEach(function (t) {
        t.classList.remove("active");
        t.setAttribute("aria-selected", "false");
      });
      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
      currentCat = btn.dataset.cat;
      applyFilters();
    });
  }

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      currentQuery = fold(this.value);
      if (searchClear) searchClear.hidden = !this.value;
      applyFilters();
    });
  }
  if (searchClear) {
    searchClear.addEventListener("click", function () {
      if (searchInput) {
        searchInput.value = "";
        currentQuery = "";
        this.hidden = true;
        applyFilters();
        searchInput.focus();
      }
    });
  }

  if (sortSelect) {
    sortSelect.addEventListener("change", function () {
      currentSort = this.value;
      applyFilters();
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      currentCat = "all";
      currentQuery = "";
      if (searchInput) searchInput.value = "";
      if (searchClear) searchClear.hidden = true;
      if (tabsContainer) {
        tabsContainer.querySelectorAll(".tab").forEach(function (t) {
          t.classList.remove("active");
          if (t.dataset.cat === "all") t.classList.add("active");
        });
      }
      applyFilters();
    });
  }

  // Modal Chi Tiết Món
  var modal = document.getElementById("product-modal");
  var modalMedia = document.getElementById("modal-media");
  var modalCat = document.getElementById("modal-cat");
  var modalTitle = document.getElementById("modal-title");
  var modalPrice = document.getElementById("modal-price");
  var modalDesc = document.getElementById("modal-desc");
  var modalQty = document.getElementById("modal-qty");
  var qtyMinus = document.getElementById("qty-minus");
  var qtyPlus = document.getElementById("qty-plus");
  var modalBtnAdd = document.getElementById("modal-btn-add");

  var activeProduct = null;

  function openModal(data) {
    if (!modal) return;
    activeProduct = data;
    modalTitle.textContent = data.name;
    modalPrice.textContent = formatPrice(data.price);
    modalDesc.textContent = data.desc || "Mô tả đang được cập nhật.";
    modalCat.textContent = data.catName || "CoffeeShop";
    if (modalQty) modalQty.value = "1";

    if (modalMedia) {
      modalMedia.innerHTML = "";
      var img = document.createElement("img");
      img.src = data.image;
      img.alt = data.name;
      img.onerror = function () {
        modalMedia.innerHTML = '<div class="img-fallback"><span>' + data.name + "</span></div>";
      };
      modalMedia.appendChild(img);
    }

    modal.hidden = false;
    document.body.classList.add("no-scroll");
  }

  function closeModal() {
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove("no-scroll");
    activeProduct = null;
  }
  window.closeModal = closeModal;

  if (modal) {
    modal.addEventListener("click", function (e) {
      if (e.target.hasAttribute("data-close") || e.target.closest("[data-close]")) {
        closeModal();
      }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !modal.hidden) closeModal();
    });

    if (qtyMinus && qtyPlus && modalQty) {
      qtyMinus.addEventListener("click", function () {
        var v = parseInt(modalQty.value, 10) || 1;
        if (v > 1) modalQty.value = v - 1;
      });
      qtyPlus.addEventListener("click", function () {
        var v = parseInt(modalQty.value, 10) || 1;
        if (v < 99) modalQty.value = v + 1;
      });
    }

    if (modalBtnAdd) {
      modalBtnAdd.addEventListener("click", function () {
        if (!activeProduct) return;
        var qty = parseInt(modalQty.value, 10) || 1;
        window.addToCart(activeProduct.id, activeProduct.name, activeProduct.price, qty);
      });
    }
  }

  // Click card để mở modal
  document.addEventListener("click", function (e) {
    var card = e.target.closest(".product-card, .card-featured");
    if (!card) return;
    if (e.target.closest(".btn-add-cart") || e.target.closest("a") || e.target.closest("button")) {
      return;
    }
    var catSpan = card.querySelector(".card-cat");
    openModal({
      id: parseInt(card.dataset.id, 10),
      name: card.dataset.name,
      price: parseInt(card.dataset.price, 10),
      image: card.dataset.image,
      desc: card.dataset.desc,
      catName: catSpan ? catSpan.textContent : "",
    });
  });

  // Hỗ trợ bấm phím Enter/Space khi focus vào card
  document.addEventListener("keydown", function (e) {
    if (e.key === "Enter" || e.key === " ") {
      var card = e.target.closest(".product-card, .card-featured");
      if (card && document.activeElement === card) {
        e.preventDefault();
        var catSpan = card.querySelector(".card-cat");
        openModal({
          id: parseInt(card.dataset.id, 10),
          name: card.dataset.name,
          price: parseInt(card.dataset.price, 10),
          image: card.dataset.image,
          desc: card.dataset.desc,
          catName: catSpan ? catSpan.textContent : "",
        });
      }
    }
  });
})();
