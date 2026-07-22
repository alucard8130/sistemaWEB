"""Handler para crear solicitud de gasto desde comprobante"""
from typing import Dict, List, Any, Optional
from .base_handler import BaseHandler
from gastos.models import Gasto, TipoGasto
from proveedores.models import Proveedor
from datetime import date
from django.db.models import Q


class SolicitudGastoHandler(BaseHandler):
    intencion_principal = 'crear_solicitud_gasto'
    intencion_aliases = [
        'solicitud_gasto', 'nueva_solicitud_gasto', 'registrar_gasto',
        'crear_gasto', 'nuevo_gasto', 'registrar_solicitud_gasto',
        'subir_factura', 'subir_comprobante'
    ]
    descripcion = "Crear solicitud de gasto"
    emoji = "🧾"

    def obtener_campos(self) -> List[Dict]:
        proveedores = Proveedor.objects.filter(
            empresa=self.empresa
        ).values_list('id', 'nombre')
        prov_opciones = [(str(p[0]), p[1]) for p in proveedores]

        tipos = TipoGasto.objects.filter(empresa=self.empresa).exclude(
            nombre__icontains='caja chica'
        ).select_related('subgrupo').values_list('id', 'nombre', 'subgrupo__nombre')
        tipos_opciones = [(str(t[0]), f"{t[2]} — {t[1]}" if t[2] else t[1]) for t in tipos]

        campos = []

        # Solo pedir proveedor si no se encontró automáticamente por RFC
        proveedor_auto = self._buscar_proveedor_automatico(self.datos)
        if proveedor_auto:
            self.datos['proveedor_id'] = proveedor_auto
        else:
            campos.append({
                'nombre': 'proveedor_id',
                'label': '¿A qué proveedor corresponde este gasto? (No encontré el proveedor en el catálogo por RFC)',
                'tipo': 'select',
                'requerido': True,
                'opciones': prov_opciones
            })

        # Solo pedir cuenta de gasto si no se encontró automáticamente por descripción
        descripcion = self.datos.get('descripcion', '')
        tipo_gasto_auto = self._buscar_tipo_gasto_automatico(descripcion)
        if tipo_gasto_auto:
            self.datos['tipo_gasto_id'] = tipo_gasto_auto
        else:
            campos.append({
                'nombre': 'tipo_gasto_id',
                'label': '¿Cuál es la cuenta de gasto?',
                'tipo': 'select',
                'requerido': True,
                'opciones': tipos_opciones
            })

        campos += [
            {
                'nombre': 'fecha',
                'label': '¿Cuál es la fecha del comprobante? (YYYY-MM-DD)',
                'tipo': 'text',
                'requerido': True,
            },
            {
                'nombre': 'monto',
                'label': '¿Cuál es el importe total con IVA?',
                'tipo': 'number',
                'requerido': True,
            },
            {
                'nombre': 'descripcion',
                'label': '¿Cuál es la descripción del gasto?',
                'tipo': 'text',
                'requerido': True,
            },
            {
                'nombre': 'retencion_iva',
                'label': '¿Tiene retención de IVA? (opcional)',
                'tipo': 'number',
                'requerido': False,
            },
            {
                'nombre': 'retencion_isr',
                'label': '¿Tiene retención de ISR? (opcional)',
                'tipo': 'number',
                'requerido': False,
            },
        ]

        return campos
    

    def _buscar_proveedor_automatico(self, datos: Dict) -> Optional[str]:
        """Busca el proveedor por RFC o nombre del comprobante"""
        rfc = datos.get('rfc_proveedor')
        nombre = datos.get('proveedor_nombre_comprobante')

        if rfc:
            prov = Proveedor.objects.filter(
                empresa=self.empresa, rfc__iexact=rfc
            ).first()
            if prov:
                return str(prov.id)

        if nombre:
            prov = Proveedor.objects.filter(
                empresa=self.empresa, nombre__icontains=nombre[:10]
            ).first()
            if prov:
                return str(prov.id)

        return None
    
    def validar(self) -> bool:
        self.limpiar_errores()
        if not self.datos.get('proveedor_id'):
            self.agregar_error('proveedor_id', 'El proveedor es requerido')
            return False
        if not self.datos.get('tipo_gasto_id'):
            self.agregar_error('tipo_gasto_id', 'La cuenta de gasto es requerida')
            return False
        if not self.datos.get('fecha'):
            self.agregar_error('fecha', 'La fecha es requerida')
            return False
        if not self.datos.get('monto'):
            self.agregar_error('monto', 'El monto es requerido')
            return False
        if not self.datos.get('descripcion'):
            self.agregar_error('descripcion', 'La descripción es requerida')
            return False

        # Validar año
        try:
            fecha = date.fromisoformat(self.datos['fecha'])
            if fecha.year < date.today().year:
                self.agregar_error('fecha', f'No se permiten fechas del año {fecha.year}')
                return False
            if fecha > date.today():
                self.agregar_error('fecha', 'No se permiten fechas futuras')
                return False
        except Exception:
            self.agregar_error('fecha', 'Formato de fecha inválido, usa YYYY-MM-DD')
            return False

        return True

    def procesar(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        self.establecer_datos(datos)
       

        if not self.datos.get('tipo_gasto_id'):
            tipo_id = self._buscar_tipo_gasto_automatico(self.datos.get('descripcion', ''))
            if tipo_id:
                self.datos['tipo_gasto_id'] = tipo_id

        # Asignar proveedor automático por RFC si no está seleccionado
        if not self.datos.get('proveedor_id'):
            proveedor_id = self._buscar_proveedor_automatico(self.datos)
            if proveedor_id:
                self.datos['proveedor_id'] = proveedor_id

        # Validar duplicado por folio de comprobante
        folio = self.datos.get('folio_comprobante') or self.datos.get('folio')
        proveedor_id = self.datos.get('proveedor_id')

        if folio and proveedor_id:
            duplicado = Gasto.objects.filter(
                empresa=self.empresa,
                folio_comprobante=folio,
                proveedor_id=proveedor_id
            ).first()
            if duplicado:
                return {
                    'exito': False,
                    'mensaje': f"⚠️ Ya existe una solicitud de gasto con el folio {folio} para este proveedor — ID: {duplicado.id}, fecha: {duplicado.fecha}. No se creó una nueva.",
                    'errores': {'folio_comprobante': 'Folio duplicado para este proveedor'}
                }
        
        if not self.validar():
            return {
                'exito': False,
                'errores': self.errores,
                'mensaje': '❌ Hay errores en los datos: ' + str(self.errores)
            }
        try:
            proveedor = Proveedor.objects.get(id=self.datos['proveedor_id'])
            tipo_gasto = TipoGasto.objects.get(id=self.datos['tipo_gasto_id'])
            fecha = date.fromisoformat(self.datos['fecha'])

            gasto = Gasto.objects.create(
                empresa=self.empresa,
                proveedor=proveedor,
                tipo_gasto=tipo_gasto,
                fecha=fecha,
                monto=float(self.datos['monto']),
                descripcion=self.datos.get('descripcion', ''),
                retencion_iva=float(self.datos.get('retencion_iva') or 0),
                retencion_isr=float(self.datos.get('retencion_isr') or 0),
                folio_comprobante=folio,
                estatus='pendiente',
                observaciones='Creado por Sherlock'
            )
            return {
                'exito': True,
                'mensaje': f"✅ Solicitud de gasto creada correctamente por ${float(self.datos['monto']):,.2f} — Proveedor: {proveedor.nombre}",
                'objeto_id': gasto.id,
            }
        except Exception as e:
            return {
                'exito': False,
                'mensaje': f"❌ Error al crear la solicitud: {str(e)}",
                'errores': {'general': str(e)}
            }
        
    def _buscar_tipo_gasto_automatico(self, descripcion: str) -> Optional[str]:
        """Busca la cuenta de gasto más probable según la descripción del comprobante"""
        if not descripcion:
            return None
        
        # Buscar por coincidencia en nombre del tipo de gasto o subgrupo
        palabras = [p.strip().lower() for p in descripcion.split() if len(p) > 3]
        print(f"[DEBUG] Palabras a buscar: {palabras}")

        print(f"[DEBUG] self.empresa: {self.empresa} id:{self.empresa.id if self.empresa else None}")
        for palabra in palabras:
            qs = TipoGasto.objects.filter(
                empresa=self.empresa
            ).exclude(
                nombre__icontains='caja chica'
            ).filter(
                Q(nombre__icontains=palabra) |
                Q(subgrupo__nombre__icontains=palabra)
            )
            print(f"[DEBUG] Palabra: {palabra!r} → count: {qs.count()} → first: {qs.first()}")
            if qs.exists():
                tipo = qs.first()
                print(f"[DEBUG] Encontrado: id={tipo.id} nombre={tipo.nombre}")
                return str(tipo.id)
        
        return None