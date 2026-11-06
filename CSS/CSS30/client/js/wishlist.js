function renderWishlistCards() {
  const container = document.querySelector('#wishlistItems');
  if (!container) return;

  const wishlist = JSON.parse(localStorage.getItem('aurelian-wishlist') || '[]');
  if (!wishlist.length) {
    container.innerHTML = '<div class="empty-state">Your wishlist is empty. Save products for later.</div>';
    return;
  }

  container.innerHTML = productData.filter((product) => wishlist.includes(String(product.id))).map((product) => `
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
  `).join('');

  document.querySelectorAll('[data-wishlist-id]').forEach((button) => {
    button.addEventListener('click', () => {
      const itemId = String(button.dataset.wishlistId);
      const updated = JSON.parse(localStorage.getItem('aurelian-wishlist') || '[]').filter((id) => String(id) !== itemId);
      localStorage.setItem('aurelian-wishlist', JSON.stringify(updated));
      renderWishlistCards();
      document.dispatchEvent(new Event('storage'));
    });
  });

  bindQuickActions();
}

renderWishlistCards();
