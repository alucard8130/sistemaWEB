# GESAC — Sistema de Gestión Administrativa Condominal

Sistema web para la administración integral de condominios, plazas comerciales, unidades habitacionales y propiedades en renta: cobranza, facturación fiscal (CFDI), gastos, presupuestos y reportes financieros en tiempo real.

**Sitio comercial:** https://www.gesacadmin.com

## Apps móviles

| Plataforma | Estado | Enlace |
|---|---|---|
| iOS | Publicada | [App Store — Gesac Condominos](https://apps.apple.com/us/app/gesac-condominos/id6756532273) |
| Android | En pruebas cerradas | [Google Play — MantPro](https://play.google.com/store/apps/details?id=com.jmeb.mantpro) |

## Tabla de contenidos

- [Características principales](#características-principales)
- [Módulos del sistema](#módulos-del-sistema)
- [Asistente Sherlock](#asistente-sherlock)
- [Control de asistencia](#control-de-asistencia)
- [Portal de acceso a condóminos](#portal-de-acceso-a-condóminos)
- [Stack tecnológico](#stack-tecnológico)
- [Arquitectura](#arquitectura)
- [Portal de acceso externo](#portal-de-acceso-externo)
- [Licencia](#licencia)

## Características principales

- Gestión de cartera de cobranza para locales comerciales, áreas comunes, casas, departamentos y bodegas
- Facturación masiva mensual con generación automática de cuotas
- Timbrado fiscal CFDI 4.0 (México) vía Facturama
- Cobro en línea con tarjeta a través de Stripe
- Generación de reportes en PDF (WeasyPrint) y Excel (OpenPyXL)
- Dashboards financieros: ingresos vs. gastos, estado de resultados, presupuesto vs. real
- Multiempresa / multicondominio desde un solo panel de administrador
- Apps móviles nativas para administradores y condóminos
- Sistema de tickets de soporte y avisos del condominio
- Espacio de publicidad institucional como fuente de ingreso adicional
- **Asistente conversacional "Sherlock"** con IA para altas rápidas y consultas, con acceso escalonado por membresía (Plus / Premium)
- **Control de asistencia con geolocalización**, checador digital vía link único por empleado (sin necesidad de app), detección automática de retardos y faltas
- **Portal de acceso a condóminos**, con login propio, para consultar estado de cuenta, pagar facturas en línea y timbrar
- **Portal de acceso externo** para empresas administradoras y comités (con suscripción mensual vía Stripe)
- **Módulo de estacionamiento** con cortes Z automáticos y facturación
- **Cobros por estado de cuenta bancario** con extracción de abonos via IA (Anthropic Claude)
- **Wizard de configuración** guiado al crear una nueva empresa
- Diseño responsive para dispositivos móviles en portal y login

## Módulos del sistema

1. **Propiedades** — locales comerciales: cobranza, facturación, notas de crédito
2. **Áreas comunes** — cobranza, contratos de uso, facturación
3. **Facturación** — alta de clientes, generación masiva de cuotas
4. **Actualización de cuotas** — locales y áreas comunes
5. **Gastos** — registro mensual, proveedores, empleados
6. **Caja chica** — vales y gastos menores
7. **Otros ingresos** — ingresos distintos a cuotas
8. **Cartera de cobranza** — adeudos en gráficos por tipo de cartera
9. **Presupuestos** — matriz de ingresos y gastos presupuestados
10. **Estadísticas y gráficos** — dashboards de adeudos, ingresos, gastos y comparativas
11. **Estacionamiento** — cortes Z semanales/quincenales/mensuales con operador externo, generación automática de factura y cobro
12. **Cobros por estado de cuenta** — carga de PDF bancario, extracción de abonos con IA (Claude API), matching con clientes y asignación a facturas
13. **Configuración** — wizard de alta de empresa (datos generales + cuenta bancaria), carga inicial de clientes, locales, contratos, saldos
14. **Asistente Sherlock** — asistente conversacional con IA para altas rápidas (clientes, proveedores, empleados, cuentas bancarias, cuentas de gastos) y búsqueda/cobro de facturas, con control de acceso por nivel de membresía
15. **Control de asistencia** — checador digital vía GPS con link único por empleado, detección automática de retardos y faltas, reporte con exportación a Excel para nómina
16. **Ayuda** — manuales y soporte

## Asistente Sherlock

Asistente conversacional con IA integrado en el sistema (widget flotante disponible en todas las pantallas), pensado para agilizar tareas repetitivas de captura sin salir del flujo de trabajo.

### Capacidades
- Alta de clientes, proveedores y empleados por conversación guiada (paso a paso, con validación y detección de duplicados)
- Alta de cuentas bancarias y cuentas de gastos
- Búsqueda del estatus de una factura por local, área común o cliente, con reporte de saldo pendiente
- Asignación de cobros a facturas encontradas, con actualización automática del estatus
- Normalización automática de datos (mayúsculas/minúsculas, formato de nombre, RFC, email)

### Control de acceso por membresía
- **Demo**: sin acceso al asistente — se le explica el requerimiento y se ofrece actualizar de plan
- **Plus**: alta de clientes, proveedores y empleados
- **Premium**: todas las funciones, incluyendo cuentas bancarias, cuentas de gastos, y búsqueda/cobro de facturas

El botón de actualización de plan, cuando aplica, dispara directamente el checkout de Stripe (sesión creada del lado del servidor, redirección a la página de pago de Stripe).

## Control de asistencia

Checador digital para empleados, con validación de ubicación por GPS, pensado para operar sin necesidad de instalar una app ni crear cuentas de usuario adicionales.

### Cómo funciona
- Cada empleado tiene un **link único y permanente** (identificado por token, sin login) que se comparte una sola vez, por ejemplo vía WhatsApp desde la lista de empleados
- Al abrir el link, el empleado ve un checador con reloj en vivo y un botón que cambia entre "Marcar entrada" / "Marcar salida" según el estado del día
- El navegador solicita la ubicación GPS al marcar; el sistema calcula la distancia contra la ubicación configurada de la empresa y marca si el registro quedó dentro o fuera del rango permitido
- **Detección automática de retardos**: si la entrada se marca después de la hora esperada más un margen de tolerancia configurable, se genera la incidencia automáticamente
- **Detección de faltas por periodo**: desde el reporte, se puede revisar un rango de fechas completo (ej. un mes, antes del cierre de nómina) y generar automáticamente las faltas de los días sin entrada registrada, respetando ausencias ya justificadas (permiso, vacaciones, incapacidad)

### Reporte de asistencia
- Vista de resumen por empleado (días asistidos, retardos, faltas, % de asistencia) con filtro por rango de fechas y departamento
- Detalle día por día por empleado, incluyendo validación de ubicación de cada checada
- Exportación a Excel, pensada para enviarse al proceso de nómina (GESAC no procesa nómina — el reporte es informativo)

## Portal de acceso a condóminos, inquilinos y propietarios

Portal independiente, con su propio sistema de login (modelo de acceso propio, sin usuario de Django — al estilo de `UsuarioAcceso` del portal externo, pero separado de él), pensado para que cada condómino consulte y gestione su cuenta sin necesidad de acceso al sistema operativo de GESAC.

### Características
- Consulta de estado de cuenta (cargos, pagos, saldo)
- Pago de facturas en línea
- Timbrado de comprobantes fiscales (CFDI)

## Portal de acceso empreesas de administracion y miembros de comites

Portal independiente en `/portal/` para empresas administradoras y comités de condominios que no son usuarios operativos del sistema.

### Características
- Registro propio sin crear usuario de Django — modelo `UsuarioAcceso` completamente independiente
- Autenticación por sesión propia (`ua_id` en sesión)
- Suscripción mensual vía Stripe (planes Básico $299, Profesional $499, Enterprise $999 + IVA)
- Upgrade de plan desde el dashboard con un clic
- Panel del superusuario para aprobar accesos y configurar permisos por empresa
- Reportes disponibles: Estado de Resultados, Cartera de Cobranza, Ingresos vs Gastos
- Recuperación de contraseña por email con token propio (sin auth_views de Django)
- Diseño responsive con sidebar colapsable en móvil
- Navbar independiente del sistema principal (sin acceso al sistema operativo)

### Planes

| Plan | Precio | Condominios |
|---|---|---|
| Básico | $299/mes + IVA | 1 condominio |
| Profesional | $499/mes + IVA | hasta 3 condominios |
| Enterprise | $999/mes + IVA | Ilimitados |


## Licencia

Ver [LICENSE.TXT](./LICENSE.TXT).

## Contacto y soporte

Para soporte o información comercial, visitar [gesacadmin.com](https://www.gesacadmin.com).
