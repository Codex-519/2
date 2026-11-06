const adminStats = document.querySelectorAll('[data-stat]');
adminStats.forEach((stat) => {
  stat.textContent = stat.dataset.stat;
});
