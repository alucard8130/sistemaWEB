"""Handler para tareas relacionadas con cuentas bancarias"""
import re
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Any, Optional
from .base_handler import BaseHandler
from empresas.models import CuentaBancaria


class CuentaBancariaHandler(BaseHandler):
    """Handler para dar de alta una cuenta bancaria"""

    intencion_principal = 'cuenta_bancaria'
    intencion_aliases = [
        'alta_cuenta_bancaria', 'nueva_cuenta_bancaria', 'agregar_cuenta_bancaria','agrega_cuenta_bancaria',
        'registrar_cuenta_bancaria','registra_cuenta_bancaria',
        'crear_cuenta_bancaria', 'crea_cuenta_bancaria',
        'dar_de_alta_cuenta_bancaria', 'da_de_alta_cuenta_bancaria',
        
    ]
    descripcion = "Dar de alta una cuenta bancaria"
    emoji = "🏦"

    campos_requeridos = ['banco', 'numero_cuenta']
    campos_opcionales = ['clabe', 'tipo_cuenta', 'moneda', 'saldo_inicial']

    def obtener_campos(self) -> List[Dict]:
        return [
            {
                'nombre': 'banco',
                'label': '¿Cuál es el banco?',
                'tipo': 'select',
                'requerido': True,
                'opciones': CuentaBancaria.BANCOS_CHOICES,
            },
            {
                'nombre': 'numero_cuenta',
                'label': '¿Cuál es el número de cuenta?',
                'tipo': 'text',
                'requerido': True,
            },
            {
                'nombre': 'clabe',
                'label': '¿Cuál es la CLABE interbancaria? (opcional, 18 dígitos)',
                'tipo': 'text',
                'requerido': False,
            },
            {
                'nombre': 'tipo_cuenta',
                'label': '¿Qué tipo de cuenta es?',
                'tipo': 'select',
                'requerido': False,
                'opciones': CuentaBancaria.TIPO_CUENTA,
            },
            {
                'nombre': 'moneda',
                'label': '¿En qué moneda está la cuenta?',
                'tipo': 'select',
                'requerido': False,
                'opciones': CuentaBancaria.TIPO_MONEDA,
            },
            {
                'nombre': 'saldo_inicial',
                'label': '¿Cuál es el saldo inicial? (opcional, si no sabes escribe "omitir" y se deja en $0.00)',
                'tipo': 'text',
                'requerido': False,
            },
        ]

    def validar(self) -> bool:
        self.limpiar_errores()

        # Banco: requerido, debe ser una de las opciones válidas (ya viene
        # normalizado por _normalizar_valor_select en services.py, pero se
        # revalida aquí por seguridad ante llamadas directas al handler)
        if not self.datos.get('banco'):
            self.agregar_error('banco', 'El banco es requerido')
            return False

        # Número de cuenta: requerido
        if not self.datos.get('numero_cuenta'):
            self.agregar_error('numero_cuenta', 'El número de cuenta es requerido')
            return False

        # Evitar duplicados: mismo número de cuenta ya registrado para esta empresa
        if CuentaBancaria.objects.filter(empresa=self.empresa, numero_cuenta=self.datos['numero_cuenta']).exists():
            self.agregar_error('numero_cuenta', 'Ya existe una cuenta registrada con este número')
            return False

        # CLABE: opcional, pero si viene debe tener formato y dígito verificador válidos
        if self.datos.get('clabe'):
            if not self._validar_clabe(self.datos['clabe']):
                self.agregar_error('clabe', 'CLABE inválida (deben ser 18 dígitos con dígito verificador correcto)')
                return False

            if CuentaBancaria.objects.filter(empresa=self.empresa, clabe=self.datos['clabe']).exists():
                self.agregar_error('clabe', 'Ya existe una cuenta registrada con esta CLABE')
                return False

        # Saldo inicial: opcional, pero si viene debe ser un número válido
        if self.datos.get('saldo_inicial'):
            monto = self._parsear_decimal(self.datos['saldo_inicial'])
            if monto is None:
                self.agregar_error('saldo_inicial', 'El saldo inicial debe ser un número válido, ej. 1000.50')
                return False
            self.datos['saldo_inicial'] = monto

        return True

    def _normalizar_datos(self):
        """Limpia espacios en número de cuenta y CLABE."""
        if self.datos.get('numero_cuenta'):
            self.datos['numero_cuenta'] = re.sub(r'\s+', '', self.datos['numero_cuenta'].strip())

        if self.datos.get('clabe'):
            self.datos['clabe'] = re.sub(r'\s+', '', self.datos['clabe'].strip())

    def procesar(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        self.establecer_datos(datos)
        self._normalizar_datos()

        if not self.validar():
            return {
                'exito': False,
                'errores': self.errores,
                'mensaje': '❌ Hay errores en los datos ingresados'
            }

        # saldo_inicial: el modelo tiene default=0.00 y no acepta vacío, así
        # que si se omitió ('' en datos_recopilados) se usa 0.00 explícito.
        saldo_inicial = self.datos.get('saldo_inicial')
        if not isinstance(saldo_inicial, Decimal):
            saldo_inicial = Decimal('0.00')

        try:
            cuenta = CuentaBancaria.objects.create(
                empresa=self.empresa,
                banco=self.datos.get('banco'),
                numero_cuenta=self.datos.get('numero_cuenta'),
                clabe=self.datos.get('clabe') or None,
                tipo_cuenta=self.datos.get('tipo_cuenta') or None,
                moneda=self.datos.get('moneda') or None,
                saldo_inicial=saldo_inicial,
                saldo_final=None,
                activa=True,
            )

            banco_display = dict(CuentaBancaria.BANCOS_CHOICES).get(cuenta.banco, cuenta.banco)

            return {
                'exito': True,
                'mensaje': f"✅ ¡Cuenta bancaria de {banco_display} (•••{cuenta.numero_cuenta[-4:]}) creada exitosamente!",
                'objeto_id': cuenta.id,
                'objeto_nombre': f"{banco_display} - {cuenta.numero_cuenta}",
            }

        except Exception as e:
            return {
                'exito': False,
                'mensaje': f"❌ Error al crear la cuenta bancaria: {str(e)}",
                'errores': {'general': str(e)}
            }

    @staticmethod
    def _validar_clabe(clabe: str) -> bool:
        """
        Valida una CLABE interbancaria mexicana: 18 dígitos donde el último
        es un dígito verificador calculado con la suma ponderada estándar
        (pesos 3,7,1 repetidos sobre los primeros 17 dígitos).
        """
        if not re.match(r'^\d{18}$', clabe):
            return False

        pesos = [3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7]
        digitos = [int(d) for d in clabe[:17]]
        suma = sum((d * p) % 10 for d, p in zip(digitos, pesos)) % 10
        digito_verificador = (10 - suma) % 10

        return digito_verificador == int(clabe[17])

    @staticmethod
    def _parsear_decimal(valor: str) -> Optional[Decimal]:
        """Acepta números con o sin comas de miles (ej. '1,000.50' o '1000.50')."""
        limpio = valor.strip().replace(',', '').replace('$', '')
        try:
            return Decimal(limpio)
        except (InvalidOperation, ValueError):
            return None