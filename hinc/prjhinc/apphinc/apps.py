from django.apps import AppConfig

# Define la configuración de la aplicación Django 'apphinc', especificando el tipo de campo automático para los modelos y el nombre de la aplicación. La clase ApphincConfig hereda de AppConfig para configurar la aplicación que contiene los modelos, vistas, formularios y URLs de la tienda en línea, integrándola en el proyecto Django. El atributo default_auto_field establece BigAutoField como el tipo de clave primaria automática para los modelos, asegurando compatibilidad con bases de datos modernas, y el atributo name identifica la aplicación como 'apphinc' para su registro en settings.py.
class ApphincConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apphinc'