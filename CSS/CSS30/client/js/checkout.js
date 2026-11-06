function renderCheckout() {
  const cart = JSON.parse(localStorage.getItem('aurelian-cart') || '[]');
  const summary = document.querySelector('#checkoutSummary');
  const totalNode = document.querySelector('#checkoutTotal');
  const form = document.querySelector('#checkoutForm');

  if (!summary) return;
  if (!cart.length) {
    summary.innerHTML = '<div class="empty-state">Your cart is empty. Add products before checkout.</div>';
    return;
  }

  const productMap = productData.reduce((map, product) => {
    map[Number(product.id)] = product;
    return map;
  }, {});

  let subtotal = 0;
  summary.innerHTML = cart.map((entry) => {
    const product = productMap[Number(entry.id)];
    const quantity = Number(entry.quantity) || 1;
    const amount = product.price * quantity;
    subtotal += amount;
    return `
      <div class="summary-item" style="display:flex;justify-content:space-between;gap:14px;padding:12px 0;border-bottom:1px solid var(--line)">
        <div><strong>${product.name}</strong><div style="color:var(--muted);font-size:0.8rem">Qty: ${quantity}</div></div>
        <span>${formatPrice(amount)}</span>
      </div>
    `;
  }).join('');

  const delivery = subtotal > 2000 ? 0 : 199;
  const total = subtotal + delivery;
  if (totalNode) totalNode.textContent = formatPrice(total);

  form?.addEventListener('submit', (event) => {
    event.preventDefault();
    const order = {
      id: `ORD-${Date.now()}`,
      total: total,
      status: 'Paid',
      date: new Date().toISOString(),
    };
    localStorage.setItem('aurelian-last-order', JSON.stringify(order));
    localStorage.setItem('aurelian-cart', '[]');
    showToast('Order placed successfully');
    setTimeout(() => window.location.href = 'orders.html', 800);
  });
}

renderCheckout();
