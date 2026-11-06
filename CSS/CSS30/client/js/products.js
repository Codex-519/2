const productData = [
  { id: 1, slug: 'aura-x1-headphones', name: 'Aura X1 Wireless Headphones', category: 'Electronics', price: 2499, comparePrice: 3999, rating: 4.9, reviews: 324, badge: 'Best Seller', image: 'https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=900&q=80', images: ['https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1518444065439-e933c06ce9cd?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1583394838336-acd977736f90?auto=format&fit=crop&w=900&q=80'], description: 'Luxury wireless audio designed for deep focus, commuting, and everyday comfort.', specs: ['40h battery life', 'Active noise cancellation', 'Fast charging support'], stock: 18 },
  { id: 2, slug: 'verdant-strap-watch', name: 'Verdant Strap Smart Watch', category: 'Accessories', price: 1899, comparePrice: 2599, rating: 4.7, reviews: 186, badge: 'New', image: 'https://images.unsplash.com/photo-1523170335258-f5ed11844a49?auto=format&fit=crop&w=900&q=80', images: ['https://images.unsplash.com/photo-1523170335258-f5ed11844a49?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1508057198894-247b23fe5ade?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1516574187841-cb9cc2ca948b?auto=format&fit=crop&w=900&q=80'], description: 'Track workouts, manage wellness, and stay connected in a sleek minimal form.', specs: ['AMOLED display', '5 ATM water resistant', 'Heart-rate and sleep tracking'], stock: 24 },
  { id: 3, slug: 'luna-studio-lamp', name: 'Luna Studio Table Lamp', category: 'Home & Living', price: 1299, comparePrice: 1999, rating: 4.8, reviews: 214, badge: 'Featured', image: 'https://images.unsplash.com/photo-1517705008128-361805f42e86?auto=format&fit=crop&w=900&q=80', images: ['https://images.unsplash.com/photo-1517705008128-361805f42e86?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1494438639946-1ebd1d20bf85?auto=format&fit=crop&w=900&q=80'], description: 'Soft ambient lighting with a premium matte finish for bedrooms and work spaces.', specs: ['USB-C powered', 'Warm dimmable glow', 'Compact footprint'], stock: 16 },
  { id: 4, slug: 'atlas-travel-bag', name: 'Atlas Travel Pro Backpack', category: 'Fashion', price: 2199, comparePrice: 3299, rating: 4.6, reviews: 119, badge: 'Hot', image: 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=900&q=80', images: ['https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1566150905458-1bf1fc113f0d?auto=format&fit=crop&w=900&q=80'], description: 'Weather-ready carry-all designed for urban travel, daily commutes, and weekend adventures.', specs: ['Laptop sleeve', 'Quick-access organizer', 'Water-resistant fabric'], stock: 12 },
  { id: 5, slug: 'solstice-skin-kit', name: 'Solstice Glow Skin Kit', category: 'Beauty', price: 899, comparePrice: 1499, rating: 4.9, reviews: 411, badge: 'Top Rated', image: 'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=900&q=80', images: ['https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1556228578-8c89e6adf883?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1571781926291-c477ebfd024b?auto=format&fit=crop&w=900&q=80'], description: 'A curated skincare routine for hydration, brightness, and a healthy daily glow.', specs: ['3-step ritual', 'Vitamin C blend', 'Dermatologist approved'], stock: 30 },
  { id: 6, slug: 'nova-fit-core', name: 'NovaFit Core Trainer', category: 'Sports', price: 2799, comparePrice: 4299, rating: 4.5, reviews: 92, badge: 'Limited', image: 'https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=900&q=80', images: ['https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=900&q=80'], description: 'Targeted home fitness gear that supports strength, mobility, and low-impact routines.', specs: ['Multi-angle design', 'Premium anti-slip base', 'Compact for small spaces'], stock: 8 },
  { id: 7, slug: 'oro-blend-mug', name: 'Oro Blend Ceramic Mug', category: 'Home & Living', price: 699, comparePrice: 999, rating: 4.7, reviews: 95, badge: 'Giftable', image: 'https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=900&q=80', images: ['https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=900&q=80'], description: 'An elevated everyday mug made for slow mornings and premium coffee rituals.', specs: ['Food-safe glaze', 'Hand-finished ceramic', 'Dishwasher safe'], stock: 42 },
  { id: 8, slug: 'mira-compact-speaker', name: 'Mira Compact Speaker', category: 'Electronics', price: 1699, comparePrice: 2499, rating: 4.8, reviews: 274, badge: 'Trending', image: 'https://images.unsplash.com/photo-1511379938547-c1f69419868d?auto=format&fit=crop&w=900&q=80', images: ['https://images.unsplash.com/photo-1511379938547-c1f69419868d?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1545454675-3531b543be5d?auto=format&fit=crop&w=900&q=80','https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80'], description: 'Pocket-sized powerhouse audio for home, desk, and travel setups.', specs: ['360° sound', 'Bluetooth 5.3', '12-hour battery'], stock: 20 },
];

function formatPrice(value) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);
}

function getDiscountPercent(price, comparePrice) {
  if (!comparePrice || comparePrice <= price) return 0;
  return Math.round(((comparePrice - price) / comparePrice) * 100);
}

function createProductCard(product) {
  const discount = getDiscountPercent(product.price, product.comparePrice);
  return `
    <article class="product-card" data-product-id="${product.id}">
      <div class="product-media">
        <img src="${product.image}" alt="${product.name}">
        <span class="product-badge">${product.badge}</span>
        <button class="product-wishlist" data-wishlist-id="${product.id}" aria-label="Add to wishlist">♥</button>
      </div>
      <div class="product-content">
        <div class="product-meta">
          <span>${product.category}</span>
          <span class="rating">★ ${product.rating}</span>
        </div>
        <a href="product.html?id=${product.id}" class="product-name">${product.name}</a>
        <div class="product-price">
          <strong>${formatPrice(product.price)}</strong>
          <small>${formatPrice(product.comparePrice)}</small>
          <span class="product-discount">${discount}% off</span>
        </div>
        <div class="product-actions">
          <button class="primary-btn" data-action="add-to-cart" data-product-id="${product.id}">Add to cart</button>
          <a class="ghost-btn" href="product.html?id=${product.id}">Quick view</a>
        </div>
      </div>
    </article>
  `;
}

function renderProducts(targetSelector, filteredProducts) {
  const target = document.querySelector(targetSelector);
  if (!target) return;

  if (!filteredProducts.length) {
    target.innerHTML = '<div class="empty-state">No products match your filters. Try adjusting the range or category.</div>';
    return;
  }

  target.innerHTML = filteredProducts.map(createProductCard).join('');
}

function applyProductFilters() {
  const category = document.querySelector('#categoryFilter')?.value || 'all';
  const maxPrice = Number(document.querySelector('#priceRange')?.value || 5000);
  const rating = Number(document.querySelector('#ratingFilter')?.value || 0);
  const sortValue = document.querySelector('#sortSelect')?.value || 'featured';
  const search = (document.querySelector('#shopSearch')?.value || '').trim().toLowerCase();

  const filtered = productData.filter((product) => {
    if (category !== 'all' && product.category.toLowerCase() !== category.toLowerCase()) return false;
    if (product.price > maxPrice) return false;
    if (rating > 0 && product.rating < rating) return false;
    if (search && !product.name.toLowerCase().includes(search) && !product.category.toLowerCase().includes(search)) return false;
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (sortValue === 'price-low') return a.price - b.price;
    if (sortValue === 'price-high') return b.price - a.price;
    if (sortValue === 'rating') return b.rating - a.rating;
    if (sortValue === 'newest') return b.id - a.id;
    return b.reviews - a.reviews;
  });

  renderProducts('#productGrid', sorted);
  initWishlistButtons();
  bindQuickActions();
}

function initWishlistButtons() {
  const wishlist = JSON.parse(localStorage.getItem('aurelian-wishlist') || '[]');
  document.querySelectorAll('[data-wishlist-id]').forEach((button) => {
    const id = String(button.dataset.wishlistId);
    button.classList.toggle('active', wishlist.includes(id));
    button.textContent = wishlist.includes(id) ? '♥' : '♡';
  });
}

function renderHomepageProducts() {
  const grouped = document.querySelector('[data-home-products]');
  if (!grouped) return;
  grouped.innerHTML = productData.slice(0, 4).map(createProductCard).join('');
  initWishlistButtons();
  bindQuickActions();
}

function renderFeaturedProduct() {
  const container = document.querySelector('[data-product-detail]');
  if (!container) return;

  const params = new URLSearchParams(window.location.search);
  const productId = Number(params.get('id') || 1);
  const product = productData.find((item) => item.id === productId) || productData[0];

  const related = productData.filter((item) => item.id !== product.id).slice(0, 3);
  const discount = getDiscountPercent(product.price, product.comparePrice);

  const mainImage = product.images?.[0] || product.image;
  const thumbs = (product.images || [product.image]).slice(0, 3).map((image, index) => `
    <button class="thumb ${index === 0 ? 'active' : ''}" data-thumb="${image}"><img src="${image}" alt="${product.name} view ${index + 1}"></button>
  `).join('');

  container.innerHTML = `
    <div class="product-layout">
      <div class="gallery">
        <div class="thumb-list">${thumbs}</div>
        <div class="main-image"><img src="${mainImage}" alt="${product.name}"></div>
      </div>
      <div class="product-summary">
        <div class="meta-row">
          <span class="rating">★ ${product.rating}</span>
          <span>(${product.reviews} reviews)</span>
          <span>${product.category}</span>
        </div>
        <h1>${product.name}</h1>
        <div class="price-row">
          <strong>${formatPrice(product.price)}</strong>
          <small>${formatPrice(product.comparePrice)}</small>
          <span class="product-discount">${discount}% off</span>
        </div>
        <div class="stock-status">${product.stock > 0 ? 'In stock' : 'Out of stock'}</div>
        <div class="purchase-actions">
          <div class="quantity-box">
            <button type="button" data-qty-adjust="minus">−</button>
            <input type="number" value="1" min="1" max="10" aria-label="Quantity" readonly>
            <button type="button" data-qty-adjust="plus">+</button>
          </div>
          <button class="primary-btn" data-product-id="${product.id}" data-action="add-to-cart">Add to cart</button>
          <button class="ghost-btn" data-wishlist-id="${product.id}">Wishlist</button>
        </div>
        <div class="product-details">
          <div class="info-block">
            <h3>Product description</h3>
            <p>${product.description}</p>
          </div>
          <div class="info-block">
            <h3>Specifications</h3>
            <ul>${(product.specs || []).map((spec) => `<li>${spec}</li>`).join('')}</ul>
          </div>
        </div>
      </div>
    </div>
    <div class="product-desc-grid">
      <div class="tab-panel">
        <h3>Delivery information</h3>
        <p>Free delivery on orders over ₹2,000. Most orders arrive within 3-5 business days across India.</p>
      </div>
      <div class="tab-panel">
        <h3>Return policy</h3>
        <p>Easy 7-day returns for eligible items with original packaging. Warranty support available on premium electronics.</p>
      </div>
    </div>
    <div class="section">
      <div class="section-header">
        <div>
          <h2>Related products</h2>
          <p>Customers also bought</p>
        </div>
      </div>
      <div class="product-grid">
        ${related.map(createProductCard).join('')}
      </div>
    </div>
  `;

  document.querySelectorAll('[data-thumb]').forEach((thumb) => {
    thumb.addEventListener('click', () => {
      const src = thumb.dataset.thumb;
      const main = document.querySelector('.main-image img');
      if (main) main.src = src;
      document.querySelectorAll('[data-thumb]').forEach((el) => el.classList.toggle('active', el === thumb));
    });
  });

  const qtyInput = document.querySelector('.quantity-box input');
  const qtyButtons = document.querySelectorAll('[data-qty-adjust]');
  if (qtyInput && qtyButtons.length) {
    qtyButtons.forEach((button) => {
      button.addEventListener('click', () => {
        const current = Number(qtyInput.value || 1);
        const next = button.dataset.qtyAdjust === 'plus' ? current + 1 : Math.max(1, current - 1);
        qtyInput.value = next;
      });
    });
  }

  initWishlistButtons();
  bindQuickActions();
}

function renderShopPage() {
  const grid = document.querySelector('#productGrid');
  if (!grid) return;
  renderProducts('#productGrid', productData);
  const category = document.querySelector('#categoryFilter');
  if (category) {
    category.addEventListener('change', applyProductFilters);
  }
  const priceRange = document.querySelector('#priceRange');
  if (priceRange) {
    const label = document.querySelector('#priceValue');
    priceRange.addEventListener('input', () => {
      if (label) label.textContent = `Up to ${formatPrice(Number(priceRange.value))}`;
      applyProductFilters();
    });
    label.textContent = `Up to ${formatPrice(Number(priceRange.value))}`;
  }
  const ratingFilter = document.querySelector('#ratingFilter');
  if (ratingFilter) ratingFilter.addEventListener('change', applyProductFilters);
  const sortSelect = document.querySelector('#sortSelect');
  if (sortSelect) sortSelect.addEventListener('change', applyProductFilters);
  const searchInput = document.querySelector('#shopSearch');
  if (searchInput) searchInput.addEventListener('input', applyProductFilters);

  initWishlistButtons();
  bindQuickActions();
}

if (document.querySelector('#productGrid')) renderShopPage();
if (document.querySelector('[data-product-detail]')) renderFeaturedProduct();
if (document.querySelector('[data-home-products]')) renderHomepageProducts();
if (document.querySelector('[data-wishlist-id]')) initWishlistButtons();
