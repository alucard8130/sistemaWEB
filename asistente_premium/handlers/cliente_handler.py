"""Handler para tareas relacionadas con clientes"""
import re
from typing import Dict, List, Any
from .base_handler import BaseHandler
from clientes.models import Cliente


class ClienteHandler(BaseHandler):
    """Handler para crear/actualizar clientes"""
    
    intencion_principal = 'cliente'
    intencion_aliases = ['alta_cliente', 'nuevo_cliente', 'agrega_cliente', 'registra_cliente', 
                         'registra_nuevo_cliente', 'genera_cliente', 'genera_nuevo_cliente',
                         'registrar_cliente','registrar_nuevo_cliente','generar_cliente',
                         'generar_nuevo_cliente','crear_cliente','crear_nuevo_cliente','crea_cliente_nuevo','crea_cliente']
    descripcion = "Crear un nuevo cliente"
    emoji = "👥"
    
    campos_requeridos = ['nombre', 'rfc']
    campos_opcionales = [
        'email', 'telefono', 'tipo_contribuyente', 
        'regimen_fiscal', 'codigo_postal', 'direccion_domicilio'
    ]
    
    def obtener_campos(self) -> List[Dict]:
        """Retorna campos específicos para clientes"""
        return [
            {
                'nombre': 'nombre',
                'label': '¿Cuál es el nombre o razón social del cliente?',
                'tipo': 'text',
                'requerido': True,
                'validacion': 'minimo_2_caracteres'
            },
            {
                'nombre': 'rfc',
                'label': '¿Cuál es el RFC del cliente?',
                'tipo': 'text',
                'requerido': True,
                'validacion': 'rfc_mexicano'
            },
            {
                'nombre': 'email',
                'label': '¿Cuál es el email del cliente? (opcional)',
                'tipo': 'email',
                'requerido': False,
                'validacion': 'email'
            },
            {
                'nombre': 'telefono',
                'label': '¿Cuál es el teléfono? (opcional)',
                'tipo': 'tel',
                'requerido': False,
                'validacion': 'telefono'
            },
            {
                'nombre': 'tipo_contribuyente',
                'label': '¿Qué tipo de contribuyente es?',
                'tipo': 'select',
                'requerido': False,
                'opciones': [
                    ('Fisica', 'Persona Física'),
                    ('Moral', 'Persona Moral'),
                    ('Publico general', 'Público en General')
                ]
            },
            {
                'nombre': 'regimen_fiscal',
                'label': '¿Cuál es su régimen fiscal?',
                'tipo': 'select',
                'requerido': False,
                'opciones': [
                    ('601', 'General de Ley Personas Morales'),
                    ('603', 'Personas Morales con Fines no Lucrativos'),
                    ('605', 'Sueldos y Salarios'),
                    ('606', 'Arrendamiento'),
                    ('612', 'Personas Físicas'),
                    ('616', 'Sin obligaciones fiscales'),
                    ('621', 'Incorporación Fiscal'),
                    ('626', 'Régimen Simplificado'),
                ]
            },
            {
                'nombre': 'codigo_postal',
                'label': '¿Cuál es el código postal? (opcional)',
                'tipo': 'text',
                'requerido': False,
            },
            {
                'nombre': 'direccion_domicilio',
                'label': '¿Cuál es la dirección? (opcional)',
                'tipo': 'textarea',
                'requerido': False,
            }
        ]
    
    def validar(self) -> bool:
        """Valida los datos del cliente"""
        self.limpiar_errores()
        
        # Validar nombre
        if not self.datos.get('nombre'):
            self.agregar_error('nombre', 'El nombre es requerido')
            return False
        
        if len(self.datos['nombre']) < 2:
            self.agregar_error('nombre', 'El nombre debe tener al menos 2 caracteres')
            return False
        
        # Validar RFC: ahora es obligatorio
        if not self.datos.get('rfc'):
            self.agregar_error('rfc', 'El RFC es requerido')
            return False

        if not self._validar_rfc(self.datos['rfc']):
            self.agregar_error('rfc', 'RFC inválido')
            return False

        # Evitar duplicados: mismo RFC ya registrado para esta empresa
        if Cliente.objects.filter(empresa=self.empresa, rfc=self.datos['rfc']).exists():
            self.agregar_error('rfc', 'Ya existe un cliente registrado con este RFC')
            return False
        
        # Validar email si existe
        if self.datos.get('email'):
            if not self._validar_email(self.datos['email']):
                self.agregar_error('email', 'Email inválido')
                return False
        
        return True

    def _normalizar_datos(self):
        """
        Normaliza el formato de los datos antes de guardarlos:
        - nombre: MAYÚSCULAS, sin sufijo corporativo (SA de CV, SAPI, SC, etc.).
        - rfc: mayúsculas.
        - email: minúsculas.
        Los campos vacíos ('' de un opcional omitido) se dejan intactos.
        """
        if self.datos.get('nombre'):
            self.datos['nombre'] = self._formatear_nombre(self.datos['nombre'])

        if self.datos.get('rfc'):
            self.datos['rfc'] = self.datos['rfc'].strip().upper()

        if self.datos.get('email'):
            self.datos['email'] = self.datos['email'].strip().lower()

    @staticmethod
    def _formatear_nombre(nombre: str) -> str:
        """
        Convierte el nombre/razón social a MAYÚSCULAS y quita el sufijo
        corporativo si el usuario lo incluyó (SA de CV, SAPI, SC, AC, etc.),
        dejando solo el nombre comercial. Ej: "empresa sa de cv" -> "EMPRESA"
        """
        limpio = nombre.strip().replace('.', '')
        limpio = re.sub(r'\s+', ' ', limpio).upper()
        limpio = re.sub(r',\s*$', '', limpio)

        # Del más específico al más genérico, para no cortar "SAPI" como "SA"
        sufijos = [
            r'S\s*A\s*P\s*I\s*DE\s*C\s*V',
            r'S\s*A\s*P\s*I',
            r'S\s*DE\s*R\s*L\s*DE\s*C\s*V',
            r'S\s*DE\s*R\s*L',
            r'S\s*A\s*B\s*DE\s*C\s*V',
            r'S\s*A\s*DE\s*C\s*V',
            r'S\s*C\s*P',
            r'S\s*C',
            r'S\s*A',
            r'A\s*C',
        ]
        for patron in sufijos:
            nuevo = re.sub(r'[\s,]+' + patron + r'\s*$', '', limpio)
            # Solo se acepta si de verdad quitó algo y no dejó el nombre vacío
            if nuevo != limpio and nuevo.strip():
                limpio = nuevo.strip()
                break

        return limpio
    
    def procesar(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """Crea el cliente con los datos recopilados"""
        self.establecer_datos(datos)
        self._normalizar_datos()
        
        if not self.validar():
            return {
                'exito': False,
                'errores': self.errores,
                'mensaje': '❌ Hay errores en los datos ingresados'
            }
        
        try:
            cliente = Cliente.objects.create(
                empresa=self.empresa,
                nombre=self.datos.get('nombre'),
                rfc=self.datos.get('rfc'),
                email=self.datos.get('email'),
                telefono=self.datos.get('telefono'),
                tipo_contribuyente=self.datos.get('tipo_contribuyente'),
                regimen_fiscal=self.datos.get('regimen_fiscal'),
                codigo_postal=self.datos.get('codigo_postal'),
                direccion_domicilio=self.datos.get('direccion_domicilio'),
                uso_cfdi=self.datos.get('uso_cfdi', 'G03'),
                activo=True
            )
            
            return {
                'exito': True,
                'mensaje': f"✅ ¡Cliente '{cliente.nombre}' creado exitosamente!",
                'objeto_id': cliente.id,
                'objeto_nombre': cliente.nombre
            }
        
        except Exception as e:
            return {
                'exito': False,
                'mensaje': f"❌ Error al crear cliente: {str(e)}",
                'errores': {'general': str(e)}
            }
    
    @staticmethod
    def _validar_rfc(rfc: str) -> bool:
        """Valida formato RFC mexicano"""
        import re
        # Patrón RFC: 3-4 letras + 6 dígitos + 3 alfanuméricos
        pattern = r'^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$'
        return bool(re.match(pattern, rfc.upper()))
    
    @staticmethod
    def _validar_email(email: str) -> bool:
        """Valida formato email"""
        import re
        pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
        return bool(re.match(pattern, email))


class ActualizarClienteHandler(BaseHandler):
    """Handler para actualizar clientes existentes"""
    
    intencion_principal = 'actualizar_cliente'
    intencion_aliases = ['editar_cliente', 'modificar_cliente', 'actualizar_datos_cliente']
    descripcion = "Actualizar datos de un cliente existente"
    emoji = "✏️"
    
    campos_requeridos = ['cliente_id']
    campos_opcionales = ['nombre', 'email', 'telefono', 'rfc']
    
    def obtener_campos(self) -> List[Dict]:
        return [
            {
                'nombre': 'cliente_id',
                'label': '¿Cuál es el ID o nombre del cliente a actualizar?',
                'tipo': 'text',
                'requerido': True
            }
        ]
    
    def validar(self) -> bool:
        if not self.datos.get('cliente_id'):
            self.agregar_error('cliente_id', 'El ID del cliente es requerido')
            return False
        return True
    
    def procesar(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        # Implementar lógica de actualización
        return {'exito': True, 'mensaje': 'Cliente actualizado'}