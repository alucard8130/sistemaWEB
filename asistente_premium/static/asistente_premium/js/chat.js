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
        agregarMensajeUsuario(mensaje);
        mostrarLoading();

        // Si hay datos del comprobante y se está confirmando la solicitud
        const body = {
            mensaje: mensaje,
            intencion: intencion,
            conversacion_id: currentConversationId,
            empresa_id: config.empresaId
        };

        if (window._datosComprobante && ['crear_solicitud_gasto', 'crear_cliente', 'actualizar_cliente_constancia'].includes(intencion)) {
            body.datos_comprobante = window._datosComprobante;
            window._datosComprobante = null;
        }

        const respuesta = await fetch(config.apiUrl, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': config.csrfToken
            },
            body: JSON.stringify(body)
        });

        if (!respuesta.ok) {
            throw new Error('Error en la respuesta del servidor');
        }

        const datos = await respuesta.json();

        if (datos.conversacion_id) {
            currentConversationId = datos.conversacion_id;
        }

        procesarRespuestaAsistente(datos);
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
    console.log('[DEBUG] Respuesta del backend:', JSON.stringify(datos));
    const mensaje = datos.mensaje || '';
    const opciones = datos.opciones || [];
    const estado = datos.estado;

    const campoInfo = estado === 'solicitando_datos' ? {
        tipo: datos.campo_tipo,
        opciones: datos.campo_opciones,
        requerido: datos.campo_requerido
    } : null;

    agregarMensajeAsistente(mensaje, opciones, campoInfo);

    // Solo mostrar modal de éxito si no hay opciones de seguimiento
    if (estado === 'completada' && datos.exito !== false && opciones.length === 0) {
        mostrarExito(mensaje);
    }

    if (estado === 'solicitando_datos') {
        habilitarInputChat();
        mostrarBotonCancelar();
    } else {
        ocultarBotonCancelar();
    }

    // Resetear conversación solo si no hay opciones de seguimiento
    if (estado === 'completada' || estado === 'error') {
        if (opciones.length === 0) {
            currentConversationId = null;
        }
        // Si hay opciones, mantener currentConversationId para que
        // el siguiente mensaje llegue con contexto
    }

    if (estado === 'error') {
        if (datos.requiere_upgrade) {
            mostrarBotonActualizarMembresia(datos.requiere_upgrade);
        }
        if (!datos.bloqueo_total) {
            mostrarMenuPrincipal(
                datos.requiere_upgrade ? '¿Quieres intentar algo más?' : '¿Quieres intentarlo de nuevo?'
            );
        }
    }

    if (estado === 'solicitando_intención') {
        currentConversationId = null;
    }
}

/**
 * Muestra un botón para actualizar el plan
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
 * Inicia checkout de Stripe
 */
async function iniciarCheckoutStripe(nivelRequerido) {
    const url = nivelRequerido === 'premium' ? config.urlCrearSesionPagoPremium : config.urlCrearSesionPagoPlus;
    const nuevaPestana = window.open('', '_blank');

    try {
        mostrarLoading();

        const respuesta = await fetch(url);
        const data = await respuesta.json();

        if (!respuesta.ok || !data.id) {
            throw new Error(data.detail || data.status || 'No se pudo crear la sesion de pago.');
        }

        if (data.url) {
            if (nuevaPestana) {
                nuevaPestana.location.href = data.url;
            } else {
                window.open(data.url, '_blank', 'noopener,noreferrer');
            }
        } else {
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
 * Cancela la conversación en curso
 */
async function cancelarConversacion() {
    if (!currentConversationId) {
        reiniciarChat();
        mostrarMenuPrincipal('❌ Solicitud cancelada. ¿En qué más puedo ayudarte?');
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
 * Reinicia el estado del chat
 */
function reiniciarChat() {
    currentConversationId = null;
    ocultarBotonCancelar();
    const input = document.getElementById('messageInput');
    input.disabled = false;
    input.value = '';
    input.focus();
}

function mostrarBotonCancelar() {
    const btn = document.getElementById('cancelBtn');
    if (btn) btn.style.display = 'inline-flex';
}

function ocultarBotonCancelar() {
    const btn = document.getElementById('cancelBtn');
    if (btn) btn.style.display = 'none';
}

/**
 * Agrega mensaje del usuario
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
 * Agrega mensaje del asistente
 */
function agregarMensajeAsistente(texto, opciones = [], campoInfo = null) {
    console.log('[DEBUG] agregarMensajeAsistente - opciones:', opciones.length, 'campoInfo:', JSON.stringify(campoInfo));
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = 'message message-asistente';

    let html = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">   
            <p>${escapeHtml(texto)}</p>
    `;

    if (opciones.length > 0) {
        html += '<div class="message-options">';
        opciones.forEach(opcion => {
            // NUEVO: si la opción es de cancelar, usa la función real de
            // cancelar en vez de mandar "cancelar" como mensaje de texto
            // (evita caer en el menú genérico de "no entiendo").
            if (opcion.accion === 'cancelar') {
                html += `
                    <button class="option-btn" onclick="cancelarConversacion()">
                        ${escapeHtml(opcion.texto)}
                    </button>
                `;
                return;
            }

            const valor = typeof opcion.valor === 'string' ? opcion.valor : opcion.texto;
            const intencionArg = opcion.intencion ? `'${escapeHtml(opcion.intencion)}'` : 'null';

            if (opcion.intencion) {
                html += `
                    <button class="option-btn" onclick="enviarMensajeConSeguimiento('${escapeHtml(valor)}', ${intencionArg})">
                        ${escapeHtml(opcion.texto)}
                    </button>
                `;
            } else {
                html += `
                    <button class="option-btn" onclick="enviarMensaje('${escapeHtml(valor)}', ${intencionArg})">
                        ${escapeHtml(opcion.texto)}
                    </button>
                `;
            }
        });
        html += '</div>';
    } else if (campoInfo && ((campoInfo.tipo === 'select' && campoInfo.opciones) || campoInfo.requerido === false)) {
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

function enviarMensajeConSeguimiento(mensaje, intencion) {
    // Resetear conversación actual para crear una nueva con la intención de seguimiento
    console.log('[DEBUG] enviarMensajeConSeguimiento:', mensaje, intencion);
    currentConversationId = null;
    enviarMensaje(mensaje, intencion);
}

/**
 * Agrega mensaje de error
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

function mostrarLoading() {
    const modal = document.getElementById('loadingModal');
    const overlay = document.getElementById('modalOverlay');
    modal.classList.add('visible');
    overlay.classList.add('visible');
}

function cerrarLoading() {
    const modal = document.getElementById('loadingModal');
    const overlay = document.getElementById('modalOverlay');
    modal.classList.remove('visible');
    overlay.classList.remove('visible');
}

function mostrarExito(mensaje) {
    const modal = document.getElementById('successModal');
    const overlay = document.getElementById('modalOverlay');
    const successMessage = document.getElementById('successMessage');
    successMessage.textContent = mensaje;
    modal.classList.add('visible');
    overlay.classList.add('visible');
}

function cerrarModal() {
    document.getElementById('successModal').classList.remove('visible');
    document.getElementById('modalOverlay').classList.remove('visible');
    mostrarMenuPrincipal();
}

const MENU_OPCIONES = [
    { requerido: 'plus', emoji: '\ud83d\udc65', texto: 'Alta Cliente', mensaje: 'Quiero dar de alta un cliente' },
    { requerido: 'plus', emoji: '\ud83c\udfe2', texto: 'Alta Proveedor', mensaje: 'Quiero dar de alta un proveedor' },
    { requerido: 'plus', emoji: '\ud83d\udc68\u200d\ud83d\udcbc', texto: 'Alta Empleado', mensaje: 'Quiero dar de alta un empleado' },
    { requerido: 'plus', emoji: '\ud83d\udcb5', texto: 'Alta Cuenta Bancaria', mensaje: 'Quiero dar de alta una cuenta bancaria' },
    { requerido: 'plus', emoji: '\ud83d\udcb3', texto: 'Alta Cuenta de Gastos', mensaje: 'Quiero dar de alta una cuenta de gastos' },
    { requerido: 'premium', emoji: '\ud83d\udd0d', texto: 'Buscar Factura Cuotas y asignar cobro', mensaje: 'Quiero buscar una factura' },
    { requerido: 'plus', emoji: '\ud83e\uddfe', texto: 'Solicitud de gasto ', mensaje: 'Quiero registrar una solicitud de gasto' },
    { requerido: 'premium', emoji: '\ud83d\udcce', texto: 'Subir comprobante y generar solicitud de gasto', mensaje: 'subir_comprobante' },
    { requerido: 'premium', emoji: '📄', texto: 'Subir Constancia Fiscal (Cliente)', mensaje: 'subir_constancia_fiscal' },
];

const NIVEL_ORDEN_JS = { demo: 0, plus: 1, premium: 2 };

function opcionesDisponiblesMenu() {
    const nivelActual = NIVEL_ORDEN_JS[config.nivelEmpresa] ?? 0;
    return MENU_OPCIONES.filter(op => NIVEL_ORDEN_JS[op.requerido] <= nivelActual);
}

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

    const botonesHtml = disponibles.map(op => {
        // El botón de subir comprobante activa el input de archivo
        if (op.mensaje === 'subir_comprobante' || op.mensaje === 'subir_constancia_fiscal') {
            const inputId = op.mensaje === 'subir_comprobante' ? 'comprobanteInput' : 'constanciaInput';
            return `
                <button class="quick-action-btn" onclick="document.getElementById('${inputId}').click()">
                    <span class="emoji">${op.emoji}</span>
                    <span>${escapeHtml(op.texto)}</span>
                </button>
            `;
        }
        return `
            <button class="quick-action-btn" onclick="enviarMensaje('${escapeHtml(op.mensaje)}')">
                <span class="emoji">${op.emoji}</span>
                <span>${escapeHtml(op.texto)}</span>
            </button>
        `;
    }).join('');

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

function minimizarChat() {
    const container = document.querySelector('.chat-container');
    container.style.display = 'none';
}

function scrollAlFinal() {
    const container = document.getElementById('chatMessages');
    setTimeout(() => {
        container.scrollTop = container.scrollHeight;
    }, 100);
}

function habilitarInputChat() {
    const input = document.getElementById('messageInput');
    input.disabled = false;
    input.focus();
}

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

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    console.log('Chat asistente cargado ✓');

    document.getElementById('messageInput').addEventListener('keypress', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            enviarFormulario(event);
        }
    });

    scrollAlFinal();
    ocultarBotonCancelar();
    mostrarMenuPrincipal('\ud83d\udc4b \u00a1Hola! Soy Sherlock, tu asistente virtual. \u00bfEn qu\u00e9 puedo ayudarte hoy?');

    // Subida de comprobante
    const comprobanteInput = document.getElementById('comprobanteInput');
    if (comprobanteInput) {
        comprobanteInput.addEventListener('change', async function(e) {
            const archivo = e.target.files[0];
            if (!archivo) return;

            agregarMensajeUsuario(`📎 Analizando comprobante: ${archivo.name}...`);
            mostrarLoading();

            const formData = new FormData();
            formData.append('comprobante', archivo);

            try {
                const resp = await fetch('/asistente/api/conversaciones/procesar_comprobante/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': config.csrfToken },
                    body: formData
                });
                const data = await resp.json();
                cerrarLoading();

                if (data.exito && data.datos) {
                    const d = data.datos;
                    agregarMensajeAsistente(
                        `✅ Comprobante analizado:\n\n` +
                        `🏢 Proveedor: ${d.proveedor_nombre || 'No detectado'}\n` +
                        `📅 Fecha: ${d.fecha || 'No detectada'}\n` +
                        `💰 Total: $${d.monto_total || 0}\n` +
                        `📝 Concepto: ${d.descripcion || 'No detectado'}\n\n` +
                        `¿Quieres que cree la solicitud de gasto con estos datos?`,
                        [
                            { texto: '✅ Sí, crear solicitud', valor: 'Quiero registrar una solicitud de gasto', intencion: 'crear_solicitud_gasto' },
                            { texto: '❌ No, cancelar', accion: 'cancelar' }
                        ]
                    );
                    window._datosComprobante = d;
                } else {
                    agregarMensajeError(`❌ No pude leer el comprobante: ${data.error || 'Error desconocido'}`);
                }
            } catch (err) {
                cerrarLoading();
                agregarMensajeError('❌ Error al procesar el archivo.');
            }

            e.target.value = '';
        });
        // Subida de constancia fiscal
    const constanciaInput = document.getElementById('constanciaInput');
    if (constanciaInput) {
        constanciaInput.addEventListener('change', async function(e) {
            const archivo = e.target.files[0];
            if (!archivo) return;

            agregarMensajeUsuario(`📎 Analizando constancia fiscal: ${archivo.name}...`);
            mostrarLoading();

            const formData = new FormData();
            formData.append('constancia', archivo);

            try {
                const resp = await fetch('/asistente/api/conversaciones/procesar_constancia_fiscal/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': config.csrfToken },
                    body: formData
                });
                const data = await resp.json();
                cerrarLoading();

                if (!data.exito) {
                    agregarMensajeError(`❌ No pude leer la constancia: ${data.error || 'Error desconocido'}`);
                    e.target.value = '';
                    return;
                }

                const d = data.datos;

                if (data.modo === 'actualizar') {
                    const campos = data.campos_a_actualizar || {};
                    const camposTexto = Object.keys(campos).length > 0
                        ? Object.entries(campos).map(
                            ([k, v]) => `• ${k}: ${v.anterior} → ${v.nuevo}`
                          ).join('\n')
                        : '(no hay cambios, los datos ya coinciden)';

                    agregarMensajeAsistente(
                        `✅ Ya existe un cliente con RFC ${d.rfc}: ${data.cliente_nombre}\n\n` +
                        `Esto se actualizaría:\n${camposTexto}\n\n` +
                        `¿Actualizo el cliente con estos datos?`,
                        [
                            { texto: '✅ Sí, actualizar', valor: 'Actualizar cliente con constancia', intencion: 'actualizar_cliente_constancia' },
                            { texto: '❌ No, cancelar', accion: 'cancelar' }
                        ]
                    );
                    window._datosComprobante = { cliente_id: data.cliente_id, ...d };

                } else {
                    agregarMensajeAsistente(
                        `✅ Constancia analizada — no existe un cliente con este RFC, se creará uno nuevo:\n\n` +
                        `🏢 Nombre: ${d.nombre || 'No detectado'}\n` +
                        `🆔 RFC: ${d.rfc}\n` +
                        `📋 Régimen fiscal: ${d.regimen_fiscal || 'No detectado'}\n` +
                        `📮 C.P.: ${d.codigo_postal || 'No detectado'}\n\n` +
                        `¿Quieres que cree el cliente con estos datos?`,
                        [
                            { texto: '✅ Sí, crear cliente', valor: 'Quiero dar de alta un cliente', intencion: 'crear_cliente' },
                            { texto: '❌ No, cancelar', accion: 'cancelar' }
                        ]
                    );
                    window._datosComprobante = d;
                }

            } catch (err) {
                cerrarLoading();
                agregarMensajeError('❌ Error al procesar el archivo.');
            }

            e.target.value = '';
        });
    }
        
    }
});