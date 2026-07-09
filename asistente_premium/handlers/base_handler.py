"""Clase base para todos los handlers del asistente"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any


class BaseHandler(ABC):
    """
    Clase base para handlers de intenciones.
    Cada handler es responsable de una categoría de tareas.
    """
    
    # Metadatos del handler
    intencion_principal = None  # Ej: 'crear_cliente'
    intencion_aliases = []       # Ej: ['alta_cliente', 'nuevo_cliente']
    descripcion = ""
    emoji = "❓"
    
    # Campos requeridos y opcionales
    campos_requeridos = []
    campos_opcionales = []
    
    def __init__(self, usuario, empresa=None):
        self.usuario = usuario
        self.empresa = empresa
        self.datos = {}
        self.errores = {}
    
    @abstractmethod
    def procesar(self, datos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa los datos y realiza la acción.
        
        Args:
            datos: Diccionario con los datos recopilados
            
        Returns:
            Diccionario con resultado de la ejecución
        """
        pass
    
    @abstractmethod
    def obtener_campos(self) -> List[Dict]:
        """Retorna la lista de campos que necesita este handler"""
        pass
    
    @abstractmethod
    def validar(self) -> bool:
        """Valida que los datos sean correctos"""
        pass
    
    def obtener_mensaje_bienvenida(self) -> str:
        """Mensaje inicial cuando se selecciona este handler"""
        return f"{self.emoji} {self.descripcion}"
    
    def obtener_mensaje_proximo_campo(self, campo: Dict) -> str:
        """Genera mensaje para solicitar un campo"""
        return f"{self.emoji} {campo['label']}:"
    
    def establecer_datos(self, datos: Dict[str, Any]):
        """Establece los datos para procesar"""
        self.datos.update(datos)
    
    def agregar_error(self, campo: str, error: str):
        """Agrega un error de validación"""
        self.errores[campo] = error
    
    def limpiar_errores(self):
        """Limpia los errores"""
        self.errores = {}