from rest_framework import serializers
from facturacion.models import Factura


class FacturaSerializer(serializers.ModelSerializer):
    local = serializers.SerializerMethodField()
    area_comun = serializers.SerializerMethodField()
    locales_grupo = serializers.SerializerMethodField()  # NUEVO
    empresa = serializers.CharField(source='empresa.nombre', read_only=True)
    cliente = serializers.CharField(source='cliente.nombre', read_only=True)

    class Meta:
        model = Factura
        fields = ['empresa', 'id', 'folio', 'tipo_cuota', 'local', 'area_comun', 'locales_grupo', 'estatus', 'monto', 'saldo_pendiente', 'fecha_vencimiento', 'cliente']

    def get_local(self, obj):
        return str(obj.local) if obj.local else ''

    def get_area_comun(self, obj):
        return str(obj.area_comun) if obj.area_comun else ''

    def get_locales_grupo(self, obj):
        # NUEVO -- si es una factura consolidada de grupo, regresa la lista de números de local
        if obj.local_id is None and obj.locales_incluidos.exists():
            return [l.numero for l in obj.locales_incluidos.all()]
        return []