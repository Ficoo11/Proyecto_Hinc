from django.contrib import admin
from .models import CustomUser, Producto, Categoria, Carrito, ItemCarrito, StockTalla, Pedido, DetallePedido

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'estado', 'created_at']
    list_filter = ['role', 'estado', 'created_at']
    search_fields = ['username', 'email', 'first_name', 'last_name']

@admin.register(StockTalla)
class StockTallaAdmin(admin.ModelAdmin):
    list_display = ['producto', 'talla', 'stock', 'stock_inicial']
    list_filter = ['producto', 'talla']
    search_fields = ['producto__nombre']

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['numero_pedido', 'usuario', 'total', 'estado', 'metodo_pago', 'creado_en']
    list_filter = ['estado', 'metodo_pago', 'creado_en']
    search_fields = ['numero_pedido', 'usuario__username', 'nombre_completo']

@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ['pedido', 'producto', 'talla', 'cantidad', 'precio']
    list_filter = ['pedido', 'producto']
    search_fields = ['pedido__numero_pedido', 'producto__nombre']

admin.site.register(Producto)
admin.site.register(Categoria)
admin.site.register(Carrito)
admin.site.register(ItemCarrito)