# GESAC — Sistema de Gestión Administrativa Condominal

Sistema web para la administración integral de condominios, plazas comerciales, unidades habitacionales y propiedades en renta: cobranza, facturación fiscal (CFDI), gastos, presupuestos y reportes financieros en tiempo real.

**Demo / sitio en producción:** https://paginaweb-ro9v.onrender.com/gestor_condominal
**Sitio comercial:** https://www.gesacadmin.com

## Apps móviles

| Plataforma | Estado | Enlace |
|---|---|---|
| iOS | Publicada | [App Store — Gesac Condominos](https://apps.apple.com/us/app/gesac-condominos/id6756532273) |
| Android | En pruebas cerradas | [Google Play — MantPro](https://play.google.com/store/apps/details?id=com.jmeb.mantpro) |

## Tabla de contenidos

- [Características principales](#características-principales)
- [Módulos del sistema](#módulos-del-sistema)
- [Stack tecnológico](#stack-tecnológico)
- [Arquitectura](#arquitectura)
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
11. **Configuración** — carga inicial de clientes, locales, contratos, saldos, cuentas bancarias
12. **Ayuda** — manuales y soporte

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Django 5.2, Django REST Framework |
| Base de datos | PostgreSQL (`psycopg2`, `dj-database-url`) |
| Autenticación API | `djangorestframework-simplejwt` |
| Frontend | Templates Django + Bootstrap 5 (`crispy-bootstrap5`) |
| Reportes PDF | WeasyPrint |
| Reportes Excel | OpenPyXL |
| Facturación fiscal | Facturama (CFDI 4.0) |
| Pagos | Stripe |
| Email | SendGrid |
| Almacenamiento | AWS S3 (`django-storages`, `boto3`) |
| Monitoreo de errores | Sentry |
| Servidor WSGI | Gunicorn |
| Hosting | Render |

## Arquitectura

```
sistemaWEB/
├── core/                 # Settings, urls raíz, configuración del proyecto
├── adminpanel/           # Panel de administración
├── clientes/             # Altas y gestión de clientes
├── locales/               # Locales comerciales
├── areas/                # Áreas comunes
├── facturacion/          # Facturación masiva y CFDI
├── gastos/               # Gastos, proveedores, empleados
├── caja_chica/           # Control de caja chica
├── presupuestos/         # Matriz de presupuestos
├── informes_financieros/ # Dashboards y reportes
├── conciliaciones/       # Conciliaciones bancarias
├── proveedores/          # Catálogo de proveedores
├── empleados/            # Catálogo de empleados
├── empresas/             # Multiempresa
├── anuncios/              # Avisos del condominio
├── publicidad/           # Publicidad institucional (app)
├── principal/            # Home / dashboard principal
├── static/               # CSS, JS, imágenes
├── templates/            # Plantillas HTML compartidas
├── manage.py
├── requirements.txt
└── Procfile
```

## Licencia

Ver [LICENSE.TXT](./LICENSE.TXT).

## Contacto y soporte

Para soporte o información comercial, visitar [gesacadmin.com](https://www.gesacadmin.com).
