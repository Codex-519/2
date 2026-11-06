const appState = {
  cart: JSON.parse(localStorage.getItem('aurelian-cart') || '[]'),
  wishlist: JSON.parse(localStorage.getItem('aurelian-wishlist') || '[]'),
};

const SELECTORS = {
  cartBadge: document.querySelector('[data-cart-count]'),
  wishlistBadge: document.querySelector('[data-wishlist-count]'),
};

function showToast(message) {
  let toast = document.querySelector('.toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.className = 'toast';
    document.body.appendChild(toast);
  }

  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove('show'), 2400);
}

function updateCounters() {
  const cartCount = appState.cart.reduce((sum, item) => sum + item.quantity, 0);
  const wishlistCount = appState.wishlist.length;

  if (SELECTORS.cartBadge) SELECTORS.cartBadge.textContent = cartCount;
  if (SELECTORS.wishlistBadge) SELECTORS.wishlistBadge.textContent = wishlistCount;
}

function addToCart(productId, quantity = 1) {
  const existing = appState.cart.find((item) => item.id === productId);
  if (existing) {
    existing.quantity += quantity;
  } else {
    appState.cart.push({ id: productId, quantity });
  }
  localStorage.setItem('aurelian-cart', JSON.stringify(appState.cart));
  updateCounters();
  showToast('Added to cart');
}

function toggleWishlist(productId) {
  const exists = appState.wishlist.includes(productId);
  if (exists) {
    appState.wishlist = appState.wishlist.filter((id) => id !== productId);
    showToast('Removed from wishlist');
  } else {
    appState.wishlist.push(productId);
    showToast('Saved to wishlist');
  }
  localStorage.setItem('aurelian-wishlist', JSON.stringify(appState.wishlist));
  updateCounters();
  document.querySelectorAll('[data-wishlist-id]').forEach((button) => {
    const active = String(button.dataset.wishlistId) === String(productId);
    button.classList.toggle('active', active && appState.wishlist.includes(productId));
  });
}

function bindQuickActions() {
  document.querySelectorAll('[data-action="add-to-cart"]').forEach((button) => {
    button.addEventListener('click', () => {
      const productId = Number(button.dataset.productId || button.closest('[data-product-id]')?.dataset.productId || 1);
      addToCart(productId, 1);
    });
  });

  document.querySelectorAll('[data-wishlist-id]').forEach((button) => {
    const productId = String(button.dataset.wishlistId);
    button.classList.toggle('active', appState.wishlist.includes(productId));
    button.addEventListener('click', () => toggleWishlist(productId));
  });
}

function initCountdown(targetId, deadline) {
  const node = document.querySelector(targetId);
  if (!node) return;

  const update = () => {
    const diff = deadline - new Date();
    if (diff <= 0) {
      node.innerHTML = '<div class="time-box"><strong>00</strong><span>hrs</span></div><div class="time-box"><strong>00</strong><span>min</span></div><div class="time-box"><strong>00</strong><span>sec</span></div>';
      return;
    }

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);

    node.innerHTML = `
      <div class="time-box"><strong>${String(hours).padStart(2, '0')}</strong><span>hrs</span></div>
      <div class="time-box"><strong>${String(minutes).padStart(2, '0')}</strong><span>min</span></div>
      <div class="time-box"><strong>${String(seconds).padStart(2, '0')}</strong><span>sec</span></div>
    `;
  };

  update();
  setInterval(update, 1000);
}

bindQuickActions();
updateCounters();

if (document.querySelector('[data-deal-timer]')) {
  initCountdown('[data-deal-timer]', Date.now() + 1000 * 60 * 60 * 48 + 1000 * 60 * 12);
}

window.addEventListener('storage', () => {
  appState.cart = JSON.parse(localStorage.getItem('aurelian-cart') || '[]');
  appState.wishlist = JSON.parse(localStorage.getItem('aurelian-wishlist') || '[]');
  updateCounters();
});
