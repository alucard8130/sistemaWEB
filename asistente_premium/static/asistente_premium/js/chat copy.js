// Estado global
let currentConversationId = null;
let isWaitingForResponse = false;

/**
 * Envía el formulario del chat
 */
function enviarFormulario(event) {
    event.preventDefault();

    const input = document.getElementById('messageInput');
    const mensaje = input.value.trim();

    if (!mensaje) return;

    enviarMensaje(mensaje);
    input.value = '';
    input.focus();
}

/**
 * Envía un mensaje al asistente
 */
async function enviarMensaje(mensaje, intencion = null) {
    if (isWaitingForResponse) return;

    try {
        isWaitingForResponse = true;

        // Mostrar mensaje del usuario
        agregarMensajeUsuario(mensaje);

        // Mostrar loading
        mostrarLoading();

        // Enviar al servidor
        const respuesta = await fetch(config.apiUrl, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': config.csrfToken
            },
            body: JSON.stringify({
                mensaje: mensaje,
                intencion: intencion,
                conversacion_id: currentConversationId,
                empresa_id: config.empresaId
            })
        });

        if (!respuesta.ok) {
            throw new Error('Error en la respuesta del servidor');
        }

        const datos = await respuesta.json();

        // Actualizar ID de conversación
        if (datos.conversacion_id) {
            currentConversationId = datos.conversacion_id;
        }

        // Procesar respuesta
        procesarRespuestaAsistente(datos);

        // Auto-scroll
        scrollAlFinal();

    } catch (error) {
        console.error('Error:', error);
        agregarMensajeError('Hubo un error al procesar tu solicitud. Intenta nuevamente.');
    } finally {
        isWaitingForResponse = false;
        cerrarLoading();
    }
}

/**
 * Procesa la respuesta del asistente
 */
function procesarRespuestaAsistente(datos) {
    const mensaje = datos.mensaje || '';
    const opciones = datos.opciones || [];
    const estado = datos.estado;

    // Metadata del campo actual (solo aplica cuando se están pidiendo datos):
    // - campo_tipo === 'select' + campo_opciones -> botones de selección
    // - campo_requerido === false -> botón para saltar el campo
    const campoInfo = estado === 'solicitando_datos' ? {
        tipo: datos.campo_tipo,
        opciones: datos.campo_opciones,
        requerido: datos.campo_requerido
    } : null;

    // Agregar mensaje del asistente
    agregarMensajeAsistente(mensaje, opciones, campoInfo);

    // Si esta completo, mostrar modal de exito -- excepto cuando la
    // respuesta trae botones de accion (ej. "Asignar pago" al buscar una
    // factura pendiente), porque el modal los taparia y el usuario tendria
    // que cerrarlo antes de poder darles clic.
    if (estado === 'completada' && datos.exito !== false && opciones.length === 0) {
        mostrarExito(mensaje);
    }

    // Si hay campos requeridos, ajustar UI y mostrar boton de cancelar
    if (estado === 'solicitando_datos') {
        habilitarInputChat();
        mostrarBotonCancelar();
    } else {
        ocultarBotonCancelar();
    }

    // La conversacion termino (con exito, o fallo y el backend la marco como
    // cancelada) -> el siguiente mensaje del usuario debe iniciar una nueva
    if (estado === 'completada' || estado === 'error') {
        currentConversationId = null;
    }

    // Si hubo un error de validacion (ej. RFC invalido), se vuelve a mostrar
    // el menu principal para que el usuario pueda reintentar u optar por
    // otra tarea -- EXCEPTO cuando es un bloqueo total por plan (empresa
    // demo): ahi no tiene sentido ofrecer el menu porque no puede hacer
    // nada de todos modos, solo se le ofrece el boton de actualizar plan.
    if (estado === 'error') {
        if (datos.requiere_upgrade) {
            mostrarBotonActualizarMembresia(datos.requiere_upgrade);
        }
        if (!datos.bloqueo_total) {
            mostrarMenuPrincipal(
                datos.requiere_upgrade ? '\u00bfQuieres intentar algo m\u00e1s?' : '\u00bfQuieres intentarlo de nuevo?'
            );
        }
    }

    // Si no se reconocio la intencion ("no entiendo bien"), NO se debe
    // arrastrar este conversacion_id al siguiente mensaje: si se arrastra,
    // el backend jamas vuelve a intentar reconocer la intencion (ni por
    // texto libre ni por el boton de opcion) y el chat se queda atorado
    // repitiendo "no entiendo" para siempre. Al resetear, cada intento
    // (escrito o por boton) arranca una conversacion nueva y limpia.
    if (estado === 'solicitando_intenci\u00f3n') {
        currentConversationId = null;
    }
}

/**
 * Muestra un boton para actualizar el plan (ej. cuando Sherlock no puede
 * ayudar porque la funcion requiere un nivel de membresia superior). Al
 * hacer clic dispara el mismo flujo de checkout de Stripe que ya usas en
 * pantalla_inicio.html (crear sesion -> redirectToCheckout), en vez de
 * mandar a un link externo.
 */
function mostrarBotonActualizarMembresia(nivelRequerido) {
    const container = document.getElementById('chatMessages');
    const nivelTexto = nivelRequerido === 'premium' ? 'Premium' : 'Plus';

    const div = document.createElement('div');
    div.className = 'message message-asistente';
    div.innerHTML = `
        <div class="message-avatar">\ud83d\udd0d</div>
        <div class="message-content">
            <div class="message-options">
                <button type="button" class="option-btn option-btn-upgrade" onclick="iniciarCheckoutStripe('${nivelRequerido}')">
                    \ud83d\udcb3 Actualizar a ${nivelTexto}
                </button>
            </div>
        </div>
    `;

    container.appendChild(div);
    scrollAlFinal();
}

/**
 * Crea la sesion de checkout de Stripe para el nivel indicado ('plus' o
 * 'premium') y redirige al usuario a la pagina de pago hospedada por Stripe.
 * Mismo mecanismo que 'stripe-checkout-demo-btn' / 'stripe-checkout-premium-btn'
 * en pantalla_inicio.html, solo que disparado desde un boton dentro del chat.
 */
async function iniciarCheckoutStripe(nivelRequerido) {
    const url = nivelRequerido === 'premium' ? config.urlCrearSesionPagoPremium : config.urlCrearSesionPagoPlus;

    // Se abre la pestana en blanco de forma SINCRONA con el clic (antes del
    // fetch), porque los navegadores bloquean window.open() si no ocurre
    // como reaccion directa e inmediata a una interaccion del usuario.
    const nuevaPestana = window.open('', '_blank');

    try {
        mostrarLoading();

        const respuesta = await fetch(url);
        const data = await respuesta.json();

        if (!respuesta.ok || !data.id) {
            throw new Error(data.detail || data.status || 'No se pudo crear la sesion de pago.');
        }

        if (data.url) {
            // Forma recomendada: la sesion de Stripe ya trae su propia URL
            // de checkout, se navega ahi la pestana nueva.
            if (nuevaPestana) {
                nuevaPestana.location.href = data.url;
            } else {
                // El navegador bloqueo el popup: se abre igual, aunque el
                // usuario tendria que permitir popups para verla.
                window.open(data.url, '_blank', 'noopener,noreferrer');
            }
        } else {
            // Fallback si el backend solo regresa el id de sesion sin 'url':
            // redirectToCheckout navega la pestana ACTUAL (no puede abrir
            // una nueva), asi que se cierra la pestana en blanco y se usa
            // el comportamiento anterior en la misma ventana.
            if (nuevaPestana) nuevaPestana.close();
            const stripe = Stripe(config.stripePublicKey);
            await stripe.redirectToCheckout({ sessionId: data.id });
        }

    } catch (error) {
        if (nuevaPestana) nuevaPestana.close();
        console.error('Error:', error);
        agregarMensajeError('No se pudo iniciar el pago: ' + error.message);
    } finally {
        cerrarLoading();
    }
}

/**
 * Cancela la conversacion en curso llamando al endpoint 'cancelar' del backend
 */
async function cancelarConversacion() {
    if (!currentConversationId) {
        reiniciarChat();
        return;
    }
    if (isWaitingForResponse) return;

    try {
        isWaitingForResponse = true;
        mostrarLoading();

        const url = config.cancelarUrlTemplate.replace('/0/', `/${currentConversationId}/`);
        const respuesta = await fetch(url, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': config.csrfToken
            }
        });

        if (!respuesta.ok) {
            throw new Error('No se pudo cancelar la conversacion');
        }

        reiniciarChat();
        mostrarMenuPrincipal('\u274c Solicitud cancelada. \u00bfEn que mas puedo ayudarte?');

    } catch (error) {
        console.error('Error:', error);
        agregarMensajeError('No se pudo cancelar. Intenta nuevamente.');
    } finally {
        isWaitingForResponse = false;
        cerrarLoading();
    }
}

/**
 * Reinicia el estado del chat en el navegador tras cancelar/terminar
 */
function reiniciarChat() {
    currentConversationId = null;
    ocultarBotonCancelar();
    const input = document.getElementById('messageInput');
    input.disabled = false;
    input.value = '';
    input.focus();
}

/**
 * Muestra el boton de cancelar (mientras hay una conversacion en curso)
 */
function mostrarBotonCancelar() {
    const btn = document.getElementById('cancelBtn');
    if (btn) btn.style.display = 'inline-flex';
}

/**
 * Oculta el boton de cancelar
 */
function ocultarBotonCancelar() {
    const btn = document.getElementById('cancelBtn');
    if (btn) btn.style.display = 'none';
}

/**
 * Agrega un mensaje del usuario
 */
function agregarMensajeUsuario(texto) {
    const container = document.getElementById('chatMessages');

    const div = document.createElement('div');
    div.className = 'message message-usuario';
    div.innerHTML = `
        <div class="message-avatar">👤</div>
        <div class="message-content">
            <p>${escapeHtml(texto)}</p>
        </div>
    `;

    container.appendChild(div);
    scrollAlFinal();
}

/**
 * Agrega un mensaje del asistente
 *
 * @param {string} texto - Contenido del mensaje
 * @param {Array} opciones - Opciones de selección de intención (ej. "no entendí, ¿qué quieres hacer?")
 * @param {Object|null} campoInfo - Metadata del campo actual que se está pidiendo:
 *        { tipo, opciones: [{valor, label}], requerido }
 */
function agregarMensajeAsistente(texto, opciones = [], campoInfo = null) {
    const container = document.getElementById('chatMessages');

    const div = document.createElement('div');
    div.className = 'message message-asistente';

    let html = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <p>${escapeHtml(texto)}</p>
    `;

    if (opciones.length > 0) {
        // Botones de selección de intención (flujo "no entendí")
        html += '<div class="message-options">';
        opciones.forEach(opcion => {
            const valor = typeof opcion.valor === 'string' ? opcion.valor : opcion.texto;
            const intencionArg = opcion.intencion ? `'${escapeHtml(opcion.intencion)}'` : 'null';
            html += `
                <button class="option-btn" onclick="enviarMensaje('${escapeHtml(valor)}', ${intencionArg})">
                    ${escapeHtml(opcion.texto)}
                </button>
            `;
        });
        html += '</div>';
    } else if (campoInfo && ((campoInfo.tipo === 'select' && campoInfo.opciones) || campoInfo.requerido === false)) {
        // Botones del campo actual: opciones de selección + botón de saltar
        html += '<div class="message-options campo-options">';

        if (campoInfo.tipo === 'select' && campoInfo.opciones) {
            campoInfo.opciones.forEach(op => {
                html += `
                    <button class="option-btn" onclick="enviarMensaje('${escapeHtml(String(op.valor))}')">
                        ${escapeHtml(op.label)}
                    </button>
                `;
            });
        }

        if (campoInfo.requerido === false) {
            html += `
                <button class="option-btn option-btn-skip" onclick="enviarMensaje('omitir')">
                    ⏭️ Saltar este dato
                </button>
            `;
        }

        html += '</div>';
    }

    html += '</div>';

    div.innerHTML = html;
    container.appendChild(div);
    scrollAlFinal();
}

/**
 * Agrega un mensaje de error
 */
function agregarMensajeError(texto) {
    const container = document.getElementById('chatMessages');

    const div = document.createElement('div');
    div.className = 'message message-asistente message-error';
    div.innerHTML = `
        <div class="message-avatar">⚠️</div>
        <div class="message-content">
            <p>${escapeHtml(texto)}</p>
        </div>
    `;

    container.appendChild(div);
    scrollAlFinal();
}

/**
 * Muestra el modal de carga
 */
function mostrarLoading() {
    const modal = document.getElementById('loadingModal');
    const overlay = document.getElementById('modalOverlay');

    modal.classList.add('visible');
    overlay.classList.add('visible');
}

/**
 * Cierra el modal de carga
 */
function cerrarLoading() {
    const modal = document.getElementById('loadingModal');
    const overlay = document.getElementById('modalOverlay');

    modal.classList.remove('visible');
    overlay.classList.remove('visible');
}

/**
 * Muestra modal de éxito
 */
function mostrarExito(mensaje) {
    const modal = document.getElementById('successModal');
    const overlay = document.getElementById('modalOverlay');
    const successMessage = document.getElementById('successMessage');

    successMessage.textContent = mensaje;

    modal.classList.add('visible');
    overlay.classList.add('visible');
}

/**
 * Cierra modal. Tras completar una tarea con exito, vuelve a mostrar el
 * menu principal en el chat para que el usuario pueda iniciar otra tarea
 * sin recargar la pagina.
 */
function cerrarModal() {
    document.getElementById('successModal').classList.remove('visible');
    document.getElementById('modalOverlay').classList.remove('visible');

    mostrarMenuPrincipal();
}

/**
 * Agrega al chat el mensaje de bienvenida con las opciones rapidas
 * (el mismo menu que se ve al abrir el chat por primera vez).
 */
// Catalogo de opciones del menu principal, con el nivel minimo de plan
// requerido para cada una. Es la UNICA fuente de verdad para el frontend:
// se usa en la bienvenida inicial, al cancelar, y en "no entiendo bien"
// (aunque para "no entiendo bien" el backend ya manda sus propias opciones
// filtradas -- ver mas abajo).
const MENU_OPCIONES = [
    { requerido: 'plus', emoji: '\ud83d\udc65', texto: 'Alta Cliente', mensaje: 'Quiero dar de alta un cliente' },
    { requerido: 'plus', emoji: '\ud83c\udfe2', texto: 'Alta Proveedor', mensaje: 'Quiero dar de alta un proveedor' },
    { requerido: 'plus', emoji: '\ud83d\udc68\u200d\ud83d\udcbc', texto: 'Alta Empleado', mensaje: 'Quiero dar de alta un empleado' },
    { requerido: 'plus', emoji: '\ud83d\udcb5', texto: 'Alta Cuenta Bancaria', mensaje: 'Quiero dar de alta una cuenta bancaria' },
    { requerido: 'plus', emoji: '\ud83d\udcb3', texto: 'Alta Cuenta de Gastos', mensaje: 'Quiero dar de alta una cuenta de gastos' },
    { requerido: 'premium', emoji: '\ud83d\udd0d', texto: 'Buscar Factura', mensaje: 'Quiero buscar una factura' },
    { requerido: 'premium', emoji: '\ud83d\udcb0', texto: 'Registrar Cobro', mensaje: 'Quiero registrar un cobro' },
    { requerido: 'premium', emoji: '\ud83d\udcb8', texto: 'Crear solicitud de gasto', mensaje: 'Quiero registrar una solicitud de gasto' },
];

const NIVEL_ORDEN_JS = { demo: 0, plus: 1, premium: 2 };

/**
 * Filtra MENU_OPCIONES segun config.nivelEmpresa (viene del backend via
 * ChatView -> nivel_empresa -> config.nivelEmpresa en chat.html).
 */
function opcionesDisponiblesMenu() {
    const nivelActual = NIVEL_ORDEN_JS[config.nivelEmpresa] ?? 0;
    return MENU_OPCIONES.filter(op => NIVEL_ORDEN_JS[op.requerido] <= nivelActual);
}

/**
 * Agrega al chat el mensaje de bienvenida/menu con las opciones filtradas
 * segun el plan de la empresa (config.nivelEmpresa). Se usa tanto para la
 * bienvenida inicial como al cancelar o al "no reconocer" mas intentos.
 * Si la empresa es demo (sin acceso a nada), en vez de un menu vacio se
 * muestra el aviso de actualizar plan.
 */
function mostrarMenuPrincipal(mensaje = '\u00bfEn que mas puedo ayudarte?') {
    const disponibles = opcionesDisponiblesMenu();

    if (disponibles.length === 0) {
        agregarMensajeAsistente(
            '\ud83d\udd12 Sherlock no est\u00e1 disponible en tu plan actual (Demo). Necesitas al menos el plan Plus para usarme.'
        );
        mostrarBotonActualizarMembresia('plus');
        return;
    }

    const container = document.getElementById('chatMessages');

    const botonesHtml = disponibles.map(op => `
        <button class="quick-action-btn" onclick="enviarMensaje('${escapeHtml(op.mensaje)}')">
            <span class="emoji">${op.emoji}</span>
            <span>${escapeHtml(op.texto)}</span>
        </button>
    `).join('');

    const div = document.createElement('div');
    div.className = 'message message-asistente welcome-message';
    div.innerHTML = `
        <div class="message-avatar">\ud83e\udd16</div>
        <div class="message-content">
            <p>${escapeHtml(mensaje)}</p>
            <div class="quick-actions">
                ${botonesHtml}
            </div>
        </div>
    `;

    container.appendChild(div);
    scrollAlFinal();
}

/**
 * Minimiza el chat
 */
function minimizarChat() {
    const container = document.querySelector('.chat-container');
    container.style.display = 'none';
}

/**
 * Scroll automático al final
 */
function scrollAlFinal() {
    const container = document.getElementById('chatMessages');
    setTimeout(() => {
        container.scrollTop = container.scrollHeight;
    }, 100);
}

/**
 * Habilita el input del chat
 */
function habilitarInputChat() {
    const input = document.getElementById('messageInput');
    input.disabled = false;
    input.focus();
}

/**
 * Escapa HTML para evitar XSS
 */
function escapeHtml(texto) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(texto).replace(/[&<>"']/g, m => map[m]);
}

// Inicialización cuando carga la página
document.addEventListener('DOMContentLoaded', function() {
    console.log('Chat asistente cargado ✓');

    // Permitir Enter para enviar
    document.getElementById('messageInput').addEventListener('keypress', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            enviarFormulario(event);
        }
    });

    // Auto-scroll inicial
    scrollAlFinal();

    // El boton de cancelar solo se muestra mientras hay una conversacion en curso
    ocultarBotonCancelar();

    // Bienvenida inicial: usa la misma funcion filtrada por plan que se usa
    // en cancelar/reintentar, para que el HTML no tenga botones duplicados
    // ni desalineados del nivel de membresia real.
    mostrarMenuPrincipal('\ud83d\udc4b \u00a1Hola! Soy Sherlock, tu asistente virtual. En que puedo ayudarte hoy?');
});

// Subida de comprobante
document.getElementById('comprobanteInput').addEventListener('change', async function(e) {
    const archivo = e.target.files[0];
    if (!archivo) return;

    // Mostrar mensaje en el chat
    agregarMensaje('usuario', `📎 Subiendo comprobante: ${archivo.name}...`);
    mostrarModal('loadingModal');

    const formData = new FormData();
    formData.append('comprobante', archivo);

    try {
        const resp = await fetch('/api/conversaciones/procesar_comprobante/', {
            method: 'POST',
            headers: { 'X-CSRFToken': config.csrfToken },
            body: formData
        });
        const data = await resp.json();
        ocultarModal('loadingModal');

        if (data.exito && data.datos) {
            const d = data.datos;
            // Mostrar resumen extraído
            agregarMensaje('asistente', 
                `✅ Comprobante analizado:\n\n` +
                `🏢 **Proveedor:** ${d.proveedor_nombre || 'No detectado'}\n` +
                `📅 **Fecha:** ${d.fecha || 'No detectada'}\n` +
                `💰 **Total:** $${d.monto_total || 0}\n` +
                `📝 **Concepto:** ${d.descripcion || 'No detectado'}\n\n` +
                `¿Quieres que cree la solicitud de gasto con estos datos?`
            );
            // Guardar datos extraídos para usarlos en el handler
            window._datosComprobante = d;
            // Mostrar botones de confirmación
            mostrarOpciones([
                { texto: '✅ Sí, crear solicitud', valor: 'confirmar_comprobante', intencion: 'crear_solicitud_gasto' },
                { texto: '❌ No, cancelar', valor: 'cancelar' }
            ]);
        } else {
            agregarMensaje('asistente', `❌ No pude leer el comprobante: ${data.error || 'Error desconocido'}`);
        }
    } catch (err) {
        ocultarModal('loadingModal');
        agregarMensaje('asistente', '❌ Error al procesar el archivo.');
    }

    // Limpiar input
    e.target.value = '';
});

// En la función que maneja el envío de mensaje, detectar si hay datos del comprobante
if (window._datosComprobante && intencion === 'crear_solicitud_gasto') {
    const d = window._datosComprobante;
    // Precargar fecha y monto en el mensaje para que el handler los extraiga
    mensaje = `crear solicitud de gasto fecha:${d.fecha} monto:${d.monto_total} descripcion:${d.descripcion} retencion_iva:${d.retencion_iva || 0} retencion_isr:${d.retencion_isr || 0}`;
    window._datosComprobante = null;
}