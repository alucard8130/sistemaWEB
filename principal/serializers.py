from rest_framework import serializers
from facturacion.models import Factura

# class FacturaSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Factura
#         fields = ['id', 'folio', 'tipo_cuota', 'local','area_comun', 'estatus', 'monto', 'saldo_pendiente', 'fecha_vencimiento']

class FacturaSerializer(serializers.ModelSerializer):
    local = serializers.SerializerMethodField()
    area_comun = serializers.SerializerMethodField()

    class Meta:
        model = Factura
        fields = ['id', 'folio', 'tipo_cuota', 'local', 'area_comun', 'estatus', 'monto', 'saldo_pendiente', 'fecha_vencimiento']

    def get_local(self, obj):
        # Si local es un objeto, retorna su campo clave, por ejemplo 'clave' o 'nombre'
        return str(obj.local) if obj.local else ''

    def get_area_comun(self, obj):
        return str(obj.area_comun) if obj.area_comun else ''        