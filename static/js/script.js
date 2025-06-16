// Primero, verificar si el modo oscuro estaba activado
document.addEventListener('DOMContentLoaded', () => {
    const isDark = localStorage.getItem('dark-mode') === 'true';
    if (isDark) {
        document.body.classList.add('dark-mode');
    }

    // Botón para cambiar el modo oscuro
    const toggleBtn = document.getElementById('toggleDark');
    const ball = toggleBtn.querySelector('.toggle-ball');

    // Actualizar icono según estado
    ball.innerHTML = isDark
        ?'<i class="bi bi-brightness-high-fill"></i>'
        :'<i class="bi bi-moon-fill"></i>';
    
    if (isDark) {
        toggleBtn.classList.add('active');
    }

    toggleBtn.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('dark-mode', isDark);
        
    // Actualizar icono según estado
    ball.innerHTML = isDark
            ?'<i class="bi bi-brightness-high-fill"></i>'
            :'<i class="bi bi-moon-fill"></i>';

    // Aplicar o quitar estado "active" en el interruptor
    if (isDark) {
        toggleBtn.classList.add('active');
    } else {
        toggleBtn.classList.remove('active');
    }
    });
});


