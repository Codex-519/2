const cartStorageKey = 'aurelian-cart';
const wishlistStorageKey = 'aurelian-wishlist';

function getCartItems() {
  return JSON.parse(localStorage.getItem(cartStorageKey) || '[]');
}

function setCartItems(items) {
  localStorage.setItem(cartStorageKey, JSON.stringify(items));
}

function getWishlistItems() {
  return JSON.parse(localStorage.getItem(wishlistStorageKey) || '[]');
}

function renderCartPage() {
  const cart = getCartItems();
  const cartList = document.querySelector('#cartItems');
  const subtotalNode = document.querySelector('#cartSubtotal');
  const totalNode = document.querySelector('#cartTotal');
  const countNode = document.querySelector('[data-cart-count]');

  if (!cartList) return;

  if (!cart.length) {
    cartList.innerHTML = '<div class="empty-state">Your cart is empty. Start shopping to add essentials to your bag.</div>';
    if (subtotalNode) subtotalNode.textContent = '₹0';
    if (totalNode) totalNode.textContent = '₹0';
    if (countNode) countNode.textContent = '0';
    return;
  }

  const productMap = productData.reduce((map, product) => {
    map[Number(product.id)] = product;
    return map;
  }, {});

  let subtotal = 0;
  cartList.innerHTML = cart.map((entry) => {
    const product = productMap[Number(entry.id)];
    if (!product) return '';
    const quantity = Number(entry.quantity) || 1;
    const itemTotal = product.price * quantity;
    subtotal += itemTotal;

    return `
      <div class="cart-item" data-cart-product="${product.id}">
        <img src="${product.image}" alt="${product.name}">
        <div>
          <h3>${product.name}</h3>
          <div class="muted">${product.category}</div>
          <div class="cart-controls">
            <div class="cart-qty">
              <button type="button" data-cart-adjust="minus" data-cart-id="${product.id}">−</button>
              <input type="number" value="${quantity}" min="1" readonly>
              <button type="button" data-cart-adjust="plus" data-cart-id="${product.id}">+</button>
            </div>
            <button class="ghost-btn" data-cart-remove="${product.id}">Remove</button>
          </div>
        </div>
        <div class="cart-price">${formatPrice(itemTotal)}</div>
      </div>
    `;
  }).join('');

  const delivery = subtotal > 2000 ? 0 : 199;
  const total = subtotal + delivery;
  if (subtotalNode) subtotalNode.textContent = formatPrice(subtotal);
  if (totalNode) totalNode.textContent = formatPrice(total);
  if (countNode) countNode.textContent = cart.reduce((sum, item) => sum + Number(item.quantity), 0);

  document.querySelectorAll('[data-cart-adjust]').forEach((button) => {
    button.addEventListener('click', () => {
      const productId = Number(button.dataset.cartId);
      const nextCart = getCartItems();
      const item = nextCart.find((entry) => Number(entry.id) === productId);
      if (!item) return;

      if (button.dataset.cartAdjust === 'plus') item.quantity += 1;
      else item.quantity = Math.max(1, item.quantity - 1);

      setCartItems(nextCart);
      renderCartPage();
    });
  });

  document.querySelectorAll('[data-cart-remove]').forEach((button) => {
    button.addEventListener('click', () => {
      const productId = Number(button.dataset.cartRemove);
      const updated = getCartItems().filter((item) => Number(item.id) !== productId);
      setCartItems(updated);
      renderCartPage();
    });
  });
}

function renderWishlistPage() {
  const wishlist = getWishlistItems();
  const list = document.querySelector('#wishlistItems');
  if (!list) return;

  if (!wishlist.length) {
    list.innerHTML = '<div class="empty-state">No items saved yet. Pick your favorites and revisit them anytime.</div>';
    return;
  }

  const productMap = productData.reduce((map, product) => {
    map[Number(product.id)] = product;
    return map;
  }, {});

  list.innerHTML = wishlist.map((id) => {
    const product = productMap[Number(id)];
    if (!product) return '';
    return `
      <article class="product-card">
        <div class="product-media">
          <img src="${product.image}" alt="${product.name}">
        </div>
        <div class="product-content">
          <a href="product.html?id=${product.id}" class="product-name">${product.name}</a>
          <div class="product-price">
            <strong>${formatPrice(product.price)}</strong>
            <small>${formatPrice(product.comparePrice)}</small>
          </div>
          <div class="product-actions">
            <button class="primary-btn" data-action="add-to-cart" data-product-id="${product.id}">Add to cart</button>
            <button class="ghost-btn" data-wishlist-id="${product.id}">Remove</button>
          </div>
        </div>
      </article>
    `;
  }).join('');

  document.querySelectorAll('[data-wishlist-id]').forEach((button) => {
    button.addEventListener('click', () => {
      const productId = String(button.dataset.wishlistId);
      const next = getWishlistItems().filter((id) => String(id) !== productId);
      localStorage.setItem(wishlistStorageKey, JSON.stringify(next));
      renderWishlistPage();
      document.dispatchEvent(new Event('storage'));
    });
  });

  bindQuickActions();
}

if (document.querySelector('#cartItems')) renderCartPage();
if (document.querySelector('#wishlistItems')) renderWishlistPage();
