// Primero, verificar si el modo oscuro estaba activado
document.addEventListener('DOMContentLoaded', () => {
    const isDark = localStorage.getItem('dark-mode') === 'true';
    if (isDark) {
        document.body.classList.add('dark-mode');
    }

    // Botón para cambiar el modo oscuro
    const toggleBtn = document.getElementById('toggleDark');
    toggleBtn.innerHTML = isDark
        ?'<i class="bi bi-sun"></i> Modo claro'
        :'<i class="bi bi-moon"></i> Modo oscuro';
        

    toggleBtn.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('dark-mode', isDark);
        toggleBtn.innerHTML = isDark
            ?'<i class="bi bi-sun"></i> Modo claro'
            :'<i class="bi bi-moon"></i> Modo oscuro';
    });
});


