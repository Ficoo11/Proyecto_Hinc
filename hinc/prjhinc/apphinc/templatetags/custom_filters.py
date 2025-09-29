from django import template

# Define un filtro personalizado para la aplicación Django 'apphinc', ubicado en el directorio templatetags. Este archivo crea una biblioteca de filtros para usar en templates, permitiendo personalizar la renderización de campos de formularios. El filtro add_class agrega una clase CSS específica a un campo de formulario, mejorando la estilización dinámica en los templates de la tienda en línea.
register = template.Library()

# Filtro que agrega una clase CSS al widget de un campo de formulario. Recibe el campo (field) y la clase CSS (css_class) como argumentos, y usa as_widget para renderizar el campo con el atributo class actualizado. Usado en templates para aplicar estilos personalizados a campos de formularios (como los de CustomUserCreationForm, LoginForm, ProductoForm, etc.) sin modificar el código de los formularios directamente.
@register.filter
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})