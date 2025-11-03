from django.contrib import admin
from .models import CustomUser, Producto, Categoria, Carrito, ItemCarrito, StockTalla

@admin.register(StockTalla)
class StockTallaAdmin(admin.ModelAdmin):
    list_display = ['producto', 'talla', 'stock']
    list_filter = ['producto', 'talla']
    search_fields = ['producto__nombre']

admin.site.register(CustomUser)
admin.site.register(Producto)
admin.site.register(Categoria)
admin.site.register(Carrito)
admin.site.register(ItemCarrito)