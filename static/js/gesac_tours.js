// ============================================================
// Libreria de tours guiados de GESAC.
//
// Para agregar un tour nuevo: solo agrega una llave mas aqui abajo
// (con su lista de pasos), y una entrada en TOUR_CHOICES del modelo
// NotificacionSistema -- NO hace falta tocar navbar.html para nada.
// ============================================================

window.GESAC_TOURS = {
    navbar: [
        { id: 'tour-inicio', title: '¡Bienvenido al tour por el nuevo y mejorado MENU!', description:' BOTON INICIO: Este botón siempre te regresa a tu pantalla de inicio, con el resumen de tu condominio.' },
        { id: 'tour-catalogos', title: 'Catálogos', description: 'MENU CATALOGOS: Aquí administras tus clientes, proveedores, y el catálogo contable.' },
        { id: 'tour-tesoreria', title: 'Tesorería', description: 'MENU TESORERIA: Tus cuentas bancarias y tu caja chica, en un solo lugar.' },
        { id: 'tour-propiedades', title: 'Propiedades', description: 'MENU PROPIEDADES: El listado de locales o unidades de tu condominio, con sus cuotas.' },
        { id: 'tour-areas', title: 'Áreas / Amenidades', description: 'MENU AREAS / AMENIDADES: Administra tus áreas comunes o amenidades, según el tipo de tu condominio.' },
        { id: 'tour-facturacion', title: 'Facturación', description: 'MENU FACTURACION: Aquí generas la facturación mensual de cuotas, y consultas o cobras las facturas ya emitidas.' },
        { id: 'tour-ingresos', title: 'Ingresos y Cartera', description: 'MENU INGRESOS Y CARTERA: Consulta tus depósitos, y da seguimiento a la cartera vencida de tus clientes.' },
        { id: 'tour-gastos', title: 'Gastos', description: 'MENU GASTOS: Registra y da seguimiento a las solicitudes de gasto de tu condominio. realiza pagos y controla el presupuesto de gastos.' },
        { id: 'tour-nomina', title: 'Nómina', description: 'MENU NOMINA: Dispersión de nómina e incidencias de tus empleados.' },
        { id: 'tour-presupuestos', title: 'Presupuestos y Reportes', description: 'MENU PRESUPUESTOS Y REPORTES: Tus matrices de presupuesto, y los comparativos contra lo real.' },
        { id: 'tour-comunicacion', title: 'Comunicación', description: 'MENU COMUNICACION: Asuntos generales y avisos para tus condóminos.' },
        { id: 'tour-cuenta', title: 'Mi cuenta', description: 'MENU MI CUENTA: Renueva tu membresía, o invita a un colaborador a tu equipo.' },
        { id: 'tour-campanita', title: 'Notificaciones', description: 'CAMPANITA NOTIFICACIONES: Aquí verás avisos importantes -- membresía por vencer, recordatorios, y novedades del sistema.' },
        { id: 'tour-ayuda', title: '¿Necesitas ayuda?', description: 'BOTON AYUDA: Descarga el manual completo, o consulta tutoriales en video, cuando lo necesites.' },
    ],

    facturacion: [
        { id: 'tour-fact-kpi', title: 'Adeudo acumulado', description: 'Aquí ves el resumen de cuánto adeudo hay este mes, comparado contra el mes anterior y el mismo mes del año pasado.' },
        { id: 'tour-fact-filtros', title: 'Filtra por propiedad', description: 'Selecciona una propiedad o área común para ver su estado de cuenta -- también puedes buscar por folio o cliente.' },
        { id: 'tour-fact-recordatorio', title: 'Recordatorio de adeudos', description: 'Con una propiedad seleccionada, puedes enviarle un correo automático recordándole su adeudo pendiente.' },
        { id: 'tour-fact-exportar', title: 'Descargar Adeudos', description: 'Exporta a Excel el estado de cuenta de la propiedad que tengas filtrada.' },
        { id: 'tour-fact-tabla', title: 'Detalle de facturas', description: 'Aquí ves cada factura con su saldo, estatus, y las acciones disponibles -- registrar pago, editar, timbrar, o generar una nueva.' },
    ],
    // ============================================================
// Agrega estas 3 entradas dentro de tu objeto window.GESAC_TOURS
// existente, junto a navbar y facturacion.
// ============================================================

lista_areas: [
    { id: 'tour-la-kpis', title: 'Indicadores generales', description: 'Aquí ves de un vistazo cuántas áreas tienes, sus cuotas, y qué tan ocupada está tu propiedad.' },
    { id: 'form-filtros', title: 'Buscar un área', description: 'Busca por número de área o por nombre del cliente que la ocupa.' },
    { id: 'tour-la-nueva', title: 'Registrar un área nueva', description: 'Solo se piden los datos físicos del área (número, tipo, superficie) -- nace disponible, sin arrendatario. El contrato se asigna después, desde su Historial.' },
    { id: 'tour-la-th-estado', title: 'Estado del área', description: 'Solo tiene 2 valores: Disponible (sin arrendatario) u Ocupado (con un contrato activo). Los detalles del contrato -- renta, fechas, estatus exacto -- viven en el Historial de Contratos.' },
    { id: 'tour-la-th-opciones', title: 'Opciones por área', description: 'Cada botón tiene un color distinto: azul es el Historial de Contratos, verde es Facturas y cobranza, verde-azulado es Editar, rojo es Inactivar, y dorado es el QR de instrucciones de pago.' },
],

historial_contratos: [
    { id: 'tour-hc-header', title: 'Historial de esta área', description: 'Aquí ves TODOS los contratos que ha tenido esta área específica, del más reciente al más antiguo.' },
    { id: 'tour-hc-renovar', title: 'Renovar o crear contrato', description: 'Si el área ya tiene un contrato activo, este botón te lleva a un borrador de renovación con todo precargado. Si está disponible, te deja capturar un contrato nuevo desde cero.' },
    { id: 'tour-hc-badge', title: 'Estatus del contrato', description: 'Vigente (todo en orden), Vencido -- Mes a mes (nadie lo renovó, pero se sigue facturando y extendiendo solo), Renovado, o Terminado.' },
    { id: 'tour-hc-tarjeta', title: 'Detalle del contrato', description: 'Cliente, giro, tipo de renta, fechas, días de gracia, plazo, incremento pactado, y periodicidad de facturación -- todo en un solo lugar.' },
    { id: 'tour-hc-acciones', title: 'Acciones del contrato activo', description: 'Generar el documento PDF (solo plan Premium), Capturar Ventas (si es renta variable o mixta), o Terminar el contrato sin renovar.' },
],

expediente_contratos: [
    { id: 'tour-ex-header', title: 'Expediente de Contratos', description: 'A diferencia del Historial (que es por área), aquí ves TODOS los contratos de TODAS tus áreas en una sola tabla.' },
    { id: 'tour-ex-toolbar', title: 'Buscar y filtrar', description: 'Busca por área o cliente, y filtra por estatus -- por ejemplo, para ver de un vistazo cuántos contratos están "Mes a mes" en toda tu propiedad.' },
    { id: 'tour-ex-primera-fila', title: 'Número de área', description: 'Da clic aquí para ir directo a Lista de Áreas, ya filtrada a esta área específica.' },
    { id: 'tour-ex-th-estatus', title: 'Estatus del contrato', description: 'Mismo criterio que en el Historial -- Vigente, Mes a mes, Renovado, o Terminado.' },
    { id: 'tour-ex-th-acciones', title: 'Acciones rápidas', description: 'El botón "Historial" siempre está disponible. Si el contrato está activo, también verás las opciones de renovación (simple, con % pactado, o con INPC) y "Liberar".' },
],
    // gastos: [ ... ] -- se agrega cuando construyamos ese tour
    // cartera: [ ... ] -- se agrega cuando construyamos ese tour
};

function getCsrfTokenGesac() {
    var input = document.querySelector('input[name=csrfmiddlewaretoken]');
    return input ? input.value : '';
}

window.iniciarTour = function (nombreTour) {
    var pasosDefinidos = window.GESAC_TOURS[nombreTour];
    if (!pasosDefinidos) {
        console.warn('Tour "' + nombreTour + '" no está definido.');
        return;
    }

    var modalRecordatorio = document.getElementById('modalRecordatorio');
    if (modalRecordatorio) {
        modalRecordatorio.style.display = 'none';
    }

    function marcarTourVisto() {
        if (nombreTour === 'navbar' && window.GESAC_URLS && window.GESAC_URLS.marcarTourVisto) {
            fetch(window.GESAC_URLS.marcarTourVisto, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrfTokenGesac() },
            });
        }
        if (modalRecordatorio) {
            modalRecordatorio.style.display = 'flex';
        }
    }

    var steps = pasosDefinidos
        .filter(function (p) { return document.getElementById(p.id) !== null; })
        .map(function (p) {
            return { element: '#' + p.id, popover: { title: p.title, description: p.description } };
        });

    if (steps.length === 0) {
        // NUEVO -- ninguno de los elementos de este tour existe en la
        // pantalla actual. Si hay una URL mapeada para este tour, te
        // manda ahí, y guarda la intención de lanzarlo en cuanto
        // cargue esa pantalla (ver el DOMContentLoaded del navbar).
        if (window.GESAC_TOUR_URLS && window.GESAC_TOUR_URLS[nombreTour]) {
            sessionStorage.setItem('gesac_tour_pendiente', nombreTour);
            window.location.href = window.GESAC_TOUR_URLS[nombreTour];
        }
        return;
    }

    var driverObj = window.driver.js.driver({
        showProgress: true,
        nextBtnText: 'Siguiente',
        prevBtnText: 'Atrás',
        doneBtnText: 'Terminar',
        progressText: '{{current}} de {{total}}',
        onDestroyed: marcarTourVisto,
        steps: steps,
    });

    driverObj.drive();
};