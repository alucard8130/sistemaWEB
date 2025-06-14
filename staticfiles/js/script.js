const toggleBtn = document.getElementById('toggleDark');
                toggleBtn.addEventListener('click', () => {
                    document.body.classList.toggle('dark-mode');
                    const isDark = document.body.classList.contains('dark-mode');
                    toggleBtn.innerHTML = isDark
                        ? '<i class="bi bi-sun"></i> Modo claro'
                        : '<i class="bi bi-moon"></i> Modo oscuro';
                });
