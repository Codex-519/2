function authInit() {
  const form = document.querySelector('#authForm');
  if (!form) return;

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    const currentPage = window.location.pathname.split('/').pop();

    if (currentPage === 'register.html') {
      if (!payload.name || !payload.email || !payload.password) {
        showToast('Please fill all fields.');
        return;
      }
      const user = {
        name: payload.name,
        email: payload.email,
        role: 'user',
      };
      localStorage.setItem('aurelian-user', JSON.stringify(user));
      localStorage.setItem('aurelian-token', 'demo-token');
      showToast('Registration successful');
      setTimeout(() => window.location.href = 'login.html', 800);
      return;
    }

    if (!payload.email || !payload.password) {
      showToast('Email and password are required.');
      return;
    }
    const savedUser = JSON.parse(localStorage.getItem('aurelian-user') || 'null');
    if (!savedUser || savedUser.email !== payload.email) {
      showToast('No matching user found. Please register first.');
      return;
    }

    localStorage.setItem('aurelian-token', 'demo-token');
    showToast('Login successful');
    setTimeout(() => window.location.href = 'profile.html', 800);
  });
}

authInit();
