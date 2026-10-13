/**
 * main.js – Global JavaScript for Foody Hunters
 * Handles: Cart, Search, Toasts, Modals, Navbar, Form helpers
 */

/* ── CSRF / API helpers ──────────────────────────────────────────── */
const API = {
  async post(url, data) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  },
  async get(url) {
    const res = await fetch(url);
    return res.json();
  }
};

/* ── TOAST NOTIFICATIONS ─────────────────────────────────────────── */
const Toast = {
  container: null,
  init() {
    this.container = document.querySelector('.toast-container') || (() => {
      const el = document.createElement('div');
      el.className = 'toast-container';
      document.body.appendChild(el);
      return el;
    })();
  },
  show(message, type = 'info', duration = 3500) {
    if (!this.container) this.init();
    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${icons[type] || ''}</span><span>${message}</span>`;
    this.container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = '.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },
  success(msg) { this.show(msg, 'success'); },
  error(msg)   { this.show(msg, 'error'); },
  info(msg)    { this.show(msg, 'info'); },
};

/* ── CART MANAGEMENT ─────────────────────────────────────────────── */
const Cart = {
  cartCountEl: null,

  init() {
    this.cartCountEl = document.querySelector('.cart-badge');
    document.querySelectorAll('.add-to-cart').forEach(btn => {
      btn.addEventListener('click', (e) => this.addItem(e));
    });
  },

  async addItem(e) {
    const btn    = e.currentTarget;
    const foodId = btn.dataset.foodId;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px"></span>';

    try {
      const data = await API.post('/api/cart/add', { food_id: foodId, quantity: 1 });
      if (data.success) {
        // Replace button with qty control
        const wrap = btn.closest('.food-footer, .menu-item-actions');
        if (wrap) {
          btn.replaceWith(this._qtyCtrl(foodId, 1, data));
        }
        this._updateCount(data.cart_count);
        Toast.success(data.message || 'Added to cart!');
      } else if (data.conflict) {
        this._showClearCartModal(foodId);
      } else {
        Toast.error(data.message || 'Could not add item.');
        btn.disabled = false;
        btn.textContent = 'ADD';
      }
    } catch (err) {
      Toast.error('Network error. Please try again.');
      btn.disabled = false;
      btn.textContent = 'ADD';
    }
  },

  _qtyCtrl(foodId, qty, data) {
    const div = document.createElement('div');
    div.className = 'qty-ctrl';
    div.innerHTML = `
      <button class="qty-btn" onclick="Cart.change(this, '${foodId}', -1)">−</button>
      <span class="qty-num">${qty}</span>
      <button class="qty-btn" onclick="Cart.change(this, '${foodId}', 1)">+</button>`;
    return div;
  },

  async change(btn, foodId, delta) {
    const ctrl  = btn.closest('.qty-ctrl');
    const numEl = ctrl.querySelector('.qty-num');
    let qty = parseInt(numEl.textContent) + delta;

    if (qty <= 0) {
      const itemId = ctrl.dataset.itemId;
      await API.post('/api/cart/remove', { item_id: itemId });
      // Replace with ADD button
      const addBtn = document.createElement('button');
      addBtn.className = 'add-btn add-to-cart';
      addBtn.dataset.foodId = foodId;
      addBtn.textContent = 'ADD';
      addBtn.addEventListener('click', (e) => this.addItem(e));
      ctrl.replaceWith(addBtn);
      this._refreshCount();
      return;
    }

    numEl.textContent = qty;
    const itemId = ctrl.dataset.itemId;
    await API.post('/api/cart/update', { item_id: itemId, quantity: qty });
    this._refreshCount();
  },

  async _refreshCount() {
    const data = await API.get('/api/cart/data');
    if (data.success) {
      const total = data.items.reduce((s, i) => s + i.quantity, 0);
      this._updateCount(total);
    }
  },

  _updateCount(count) {
    if (this.cartCountEl) {
      this.cartCountEl.textContent = count;
      this.cartCountEl.style.display = count > 0 ? 'flex' : 'none';
    }
  },

  _showClearCartModal(newFoodId) {
    const modal = document.getElementById('clearCartModal');
    if (modal) {
      modal.classList.add('show');
      document.getElementById('clearCartConfirm').onclick = async () => {
        await API.post('/api/cart/clear', {});
        modal.classList.remove('show');
        // retry add
        await API.post('/api/cart/add', { food_id: newFoodId, quantity: 1 });
        Toast.success('Cart cleared and item added!');
        this._refreshCount();
      };
    }
  }
};

/* ── COUPON ──────────────────────────────────────────────────────── */
const Coupon = {
  applied: false,
  discount: 0,
  couponId: null,

  async apply() {
    const input    = document.getElementById('couponInput');
    const subtotal = parseFloat(document.getElementById('subtotalVal')?.dataset.value || 0);
    const code     = input?.value.trim().toUpperCase();
    if (!code) { Toast.error('Enter a coupon code.'); return; }

    const data = await API.post('/api/coupon/apply', { code, subtotal });
    if (data.success) {
      this.applied  = true;
      this.discount = data.discount;
      this.couponId = data.coupon_id;
      document.getElementById('couponId').value = data.coupon_id;
      document.getElementById('discountRow').style.display = 'flex';
      document.getElementById('discountVal').textContent = `−₹${data.discount.toFixed(2)}`;
      document.getElementById('couponApplied').style.display = 'flex';
      document.getElementById('couponApplied').querySelector('.coupon-code-text').textContent = code;
      document.getElementById('discountHidden').value = data.discount;
      this._recalcTotal();
      Toast.success(data.message);
    } else {
      Toast.error(data.message);
    }
  },

  remove() {
    this.applied = false; this.discount = 0; this.couponId = null;
    document.getElementById('discountRow').style.display = 'none';
    document.getElementById('couponApplied').style.display = 'none';
    document.getElementById('couponInput').value = '';
    document.getElementById('discountHidden').value = 0;
    document.getElementById('couponId').value = '';
    this._recalcTotal();
  },

  _recalcTotal() {
    const subtotal     = parseFloat(document.getElementById('subtotalVal')?.dataset.value || 0);
    const deliveryFee  = parseFloat(document.getElementById('deliveryFeeVal')?.dataset.value || 40);
    const taxRate      = 0.05;
    const taxable      = subtotal - this.discount;
    const tax          = taxable * taxRate;
    const grand        = taxable + deliveryFee + tax;

    document.getElementById('taxVal')  && (document.getElementById('taxVal').textContent = `₹${tax.toFixed(2)}`);
    document.getElementById('grandVal')&& (document.getElementById('grandVal').textContent = `₹${grand.toFixed(2)}`);
    document.getElementById('amountHidden') && (document.getElementById('amountHidden').value = grand.toFixed(2));
  }
};

/* ── CART PAGE – Inline quantity update ──────────────────────────── */
function cartUpdateQty(itemId, delta) {
  const qtyEl = document.getElementById(`qty-${itemId}`);
  const priceEl = document.getElementById(`price-${itemId}`);
  const totalEl = document.getElementById(`total-${itemId}`);
  let qty = parseInt(qtyEl.textContent) + delta;

  if (qty < 1) qty = 1;
  qtyEl.textContent = qty;

  const unitPrice = parseFloat(priceEl?.dataset.price || 0);
  if (totalEl) totalEl.textContent = `₹${(unitPrice * qty).toFixed(2)}`;

  API.post('/api/cart/update', { item_id: itemId, quantity: qty }).then(() => {
    recalcCartTotals();
  });
}

function cartRemoveItem(itemId) {
  API.post('/api/cart/remove', { item_id: itemId }).then(data => {
    if (data.success) {
      const row = document.getElementById(`cart-row-${itemId}`);
      if (row) {
        row.style.opacity = '0'; row.style.height = '0'; row.style.overflow = 'hidden';
        row.style.transition = '.3s'; setTimeout(() => { row.remove(); recalcCartTotals(); }, 300);
      }
      Toast.success('Item removed from cart.');
    }
  });
}

function recalcCartTotals() {
  let subtotal = 0;
  document.querySelectorAll('.cart-item').forEach(row => {
    const totalEl = row.querySelector('[id^="total-"]');
    if (totalEl) subtotal += parseFloat(totalEl.textContent.replace('₹',''));
  });
  const deliveryFee  = parseFloat(document.getElementById('deliveryFeeVal')?.dataset.value || 40);
  const discount     = parseFloat(document.getElementById('discountHidden')?.value || 0);
  const taxable      = subtotal - discount;
  const tax          = taxable * 0.05;
  const grand        = taxable + deliveryFee + tax;

  document.getElementById('subtotalDisplay') && (document.getElementById('subtotalDisplay').textContent = `₹${subtotal.toFixed(2)}`);
  document.getElementById('taxDisplay')      && (document.getElementById('taxDisplay').textContent = `₹${tax.toFixed(2)}`);
  document.getElementById('grandDisplay')    && (document.getElementById('grandDisplay').textContent = `₹${grand.toFixed(2)}`);
  document.getElementById('subtotalVal')     && (document.getElementById('subtotalVal').dataset.value = subtotal.toFixed(2));
}

/* ── LIVE SEARCH ─────────────────────────────────────────────────── */
const LiveSearch = {
  timeout: null,
  init(inputId, dropdownId) {
    const input    = document.getElementById(inputId);
    const dropdown = document.getElementById(dropdownId);
    if (!input || !dropdown) return;

    input.addEventListener('input', () => {
      clearTimeout(this.timeout);
      const q = input.value.trim();
      if (q.length < 2) { dropdown.style.display = 'none'; return; }
      this.timeout = setTimeout(() => this._fetch(q, dropdown), 300);
    });

    document.addEventListener('click', (e) => {
      if (!input.contains(e.target)) dropdown.style.display = 'none';
    });
  },

  async _fetch(q, dropdown) {
    const results = await API.get(`/api/search/live?q=${encodeURIComponent(q)}`);
    if (!results.length) { dropdown.style.display = 'none'; return; }
    dropdown.innerHTML = results.map(r => `
      <div class="suggestion-item" onclick="location.href='${
        r.type === 'restaurant' ? `/restaurant/${r.id}` : `/restaurant/${r.restaurant_id}`
      }'">
        <i class="fas ${r.type === 'restaurant' ? 'fa-store' : 'fa-utensils'} suggestion-icon"></i>
        <span>${r.name}</span>
        ${r.cuisine ? `<small style="color:var(--text-muted);margin-left:auto">${r.cuisine}</small>` : ''}
      </div>`).join('');
    dropdown.style.display = 'block';
  }
};

/* ── NAVBAR ──────────────────────────────────────────────────────── */
function initNavbar() {
  const hamburger = document.querySelector('.hamburger');
  const nav       = document.querySelector('.navbar-nav');
  if (hamburger && nav) {
    hamburger.addEventListener('click', () => nav.classList.toggle('open'));
  }

  // Sticky shadow on scroll
  const navbar = document.querySelector('.navbar');
  window.addEventListener('scroll', () => {
    navbar?.classList.toggle('scrolled', window.scrollY > 20);
  });
}

/* ── FLASH MESSAGE AUTO-DISMISS ──────────────────────────────────── */
function initFlashMessages() {
  document.querySelectorAll('.flash-msg').forEach(msg => {
    setTimeout(() => {
      msg.style.opacity = '0';
      msg.style.transform = 'translateX(60px)';
      msg.style.transition = '.35s ease';
      setTimeout(() => msg.remove(), 350);
    }, 4000);
    msg.querySelector('.close-btn')?.addEventListener('click', () => msg.remove());
  });
}

/* ── PAYMENT OPTIONS ─────────────────────────────────────────────── */
function initPaymentOptions() {
  document.querySelectorAll('.payment-option').forEach(opt => {
    opt.addEventListener('click', () => {
      document.querySelectorAll('.payment-option').forEach(o => o.classList.remove('selected'));
      opt.classList.add('selected');
      const radio = opt.querySelector('input[type="radio"]');
      if (radio) radio.checked = true;
      const method = radio?.value;
      // Show/hide payment detail sections
      document.querySelectorAll('[data-payment-section]').forEach(s => s.style.display = 'none');
      const section = document.querySelector(`[data-payment-section="${method}"]`);
      if (section) section.style.display = 'block';
    });
  });
}

/* ── RATING STARS ────────────────────────────────────────────────── */
function initStarRating() {
  const container = document.querySelector('.star-rating');
  if (!container) return;
  const stars = container.querySelectorAll('.star');
  const input = document.getElementById('ratingInput');
  stars.forEach((star, i) => {
    star.addEventListener('click', () => {
      stars.forEach((s, j) => s.classList.toggle('active', j <= i));
      if (input) input.value = i + 1;
    });
    star.addEventListener('mouseover', () => {
      stars.forEach((s, j) => s.classList.toggle('hovered', j <= i));
    });
    star.addEventListener('mouseout', () => {
      stars.forEach(s => s.classList.remove('hovered'));
    });
  });
}

/* ── ORDER STATUS POLL ───────────────────────────────────────────── */
function initOrderStatusPoll(orderId) {
  if (!orderId) return;
  setInterval(async () => {
    const data = await API.get(`/api/order/status/${orderId}`);
    if (data && data.status) {
      const statusEl = document.querySelector('.current-order-status');
      if (statusEl && statusEl.dataset.status !== data.status) {
        statusEl.dataset.status = data.status;
        location.reload(); // Simple refresh for demo
      }
    }
  }, 15000); // Poll every 15 seconds
}

/* ── PASSWORD TOGGLE ─────────────────────────────────────────────── */
function togglePassword(inputId, iconId) {
  const input = document.getElementById(inputId);
  const icon  = document.getElementById(iconId);
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    if (icon) icon.className = 'fas fa-eye-slash';
  } else {
    input.type = 'password';
    if (icon) icon.className = 'fas fa-eye';
  }
}

/* ── FORM VALIDATION ─────────────────────────────────────────────── */
function validateRegistrationForm(e) {
  const name    = document.getElementById('name')?.value.trim();
  const email   = document.getElementById('email')?.value.trim();
  const phone   = document.getElementById('phone')?.value.trim();
  const pw      = document.getElementById('password')?.value;
  const confirm = document.getElementById('confirm_password')?.value;

  let valid = true;
  const errors = [];

  if (!name)               { errors.push('Full name is required.'); valid = false; }
  if (!/^[\w.-]+@[\w.-]+\.\w{2,}$/.test(email)) { errors.push('Enter a valid email.'); valid = false; }
  if (!/^[6-9]\d{9}$/.test(phone)) { errors.push('Enter valid 10-digit mobile number.'); valid = false; }
  if (pw.length < 6)       { errors.push('Password min 6 characters.'); valid = false; }
  if (pw !== confirm)      { errors.push('Passwords do not match.'); valid = false; }

  if (!valid) {
    e.preventDefault();
    errors.forEach(err => Toast.error(err));
  }
}

/* ── CARD NUMBER FORMAT ──────────────────────────────────────────── */
function formatCardNumber(input) {
  let val = input.value.replace(/\D/g,'').substring(0, 16);
  input.value = val.replace(/(\d{4})/g, '$1 ').trim();
}

function formatExpiry(input) {
  let val = input.value.replace(/\D/g,'').substring(0, 4);
  if (val.length > 2) val = val.substring(0,2) + '/' + val.substring(2);
  input.value = val;
}

/* ── SIDEBAR TOGGLE (dashboard) ──────────────────────────────────── */
function toggleSidebar() {
  document.querySelector('.sidebar')?.classList.toggle('open');
}

/* ── CONFIRM DELETE ──────────────────────────────────────────────── */
function confirmDelete(message, form) {
  if (confirm(message || 'Are you sure? This action cannot be undone.')) {
    if (typeof form === 'string') {
      document.getElementById(form)?.submit();
    } else if (form instanceof HTMLFormElement) {
      form.submit();
    }
  }
}

/* ── INIT ────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  Toast.init();
  Cart.init();
  initNavbar();
  initFlashMessages();
  initPaymentOptions();
  initStarRating();
  LiveSearch.init('navSearchInput', 'navSearchDropdown');
  LiveSearch.init('heroSearchInput', 'heroSearchDropdown');

  // Registration form validation
  const regForm = document.getElementById('registrationForm');
  if (regForm) regForm.addEventListener('submit', validateRegistrationForm);
});
