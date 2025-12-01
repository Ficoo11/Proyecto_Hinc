// static/js/carrito.js
document.addEventListener('DOMContentLoaded', function () {
    // Inicializa el carrito
    fetchCarrito();

    // Configurar controles de cantidad
    setupCantidadControls();
});

// Configurar controles de cantidad
function setupCantidadControls() {
    document.querySelectorAll('.cantidad-mas').forEach(btn => {
        btn.addEventListener('click', function() {
            const input = this.parentElement.querySelector('.cantidad-input');
            let value = parseInt(input.value) || 1;
            const max = parseInt(input.max) || 10;
            input.value = Math.min(value + 1, max);
        });
    });

    document.querySelectorAll('.cantidad-menos').forEach(btn => {
        btn.addEventListener('click', function() {
            const input = this.parentElement.querySelector('.cantidad-input');
            let value = parseInt(input.value) || 1;
            input.value = Math.max(value - 1, 1);
        });
    });

    document.querySelectorAll('.agregar-carrito').forEach(btn => {
        btn.addEventListener('click', function() {
            const productoId = this.getAttribute('data-producto-id');
            const tallaSelect = document.querySelector(`select[data-producto-id="${productoId}"]`);
            const talla = tallaSelect ? tallaSelect.value : null;
            
            if (!talla) {
                mostrarMensaje('Por favor selecciona una talla', 'error');
                return;
            }
            
            const input = this.parentElement.querySelector('.cantidad-input');
            const cantidad = parseInt(input.value) || 1;
            agregarAlCarrito(productoId, cantidad, talla);
        });
    });
}

// Función para agregar producto al carrito - VERSIÓN CORREGIDA
function agregarAlCarrito(productoId, cantidad, talla) {
    fetch(URL_AGREGAR_CARRITO, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ 
            producto_id: productoId, 
            cantidad: cantidad,
            talla: talla
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            fetchCarrito();
            mostrarMensaje('Producto agregado al carrito', 'success');
        } else {
            mostrarMensaje(data.error || 'Error al agregar producto', 'error');
        }
    })
    .catch(err => {
        console.error('Error:', err);
        mostrarMensaje('Error de conexión', 'error');
    });
}

// Obtener y renderizar carrito
function fetchCarrito() {
    fetch(URL_OBTENER_CARRITO)
    .then(res => res.json())
    .then(data => {
        if (data.success && data.carrito) {
            actualizarCarritoUI(data.carrito);
        } else {
            actualizarCarritoUI([]);
        }
    })
    .catch(err => {
        console.error('Error fetching carrito:', err);
        actualizarCarritoUI([]);
    });
}

function actualizarCarritoUI(carritoData) {
    const contenido = document.getElementById("carritoContenido");
    const subtotalSpan = document.getElementById("subtotalCarrito");
    const contador = document.getElementById("cart-count");

    if (!contenido || !subtotalSpan || !contador) return;

    if (!carritoData || !carritoData.items || carritoData.items.length === 0) {
        contenido.innerHTML = "<p class='text-gray-500 py-4'>No tienes productos en tu carrito</p>";
        subtotalSpan.textContent = "$0";
        contador.textContent = "0";
        return;
    }

    let html = "";
    let subtotal = 0;
    let totalItems = 0;

    carritoData.items.forEach(item => {
        const totalItem = item.precio * item.cantidad;
        subtotal += totalItem;
        totalItems += item.cantidad;

        html += `
            <div class="flex justify-between items-center mb-4 p-2 border-b" data-producto-id="${item.id_producto}" data-talla="${item.talla}">
                <div class="flex items-center">
                    ${item.imagen ? `<img src="${item.imagen}" alt="${item.nombre}" class="w-12 h-12 object-cover rounded mr-3">` : ''}
                    <div>
                        <p class="font-medium text-sm">${item.nombre}</p>
                        <p class="text-gray-600 text-xs">Cantidad: ${item.cantidad}</p>
                        <p class="text-gray-600 text-xs">Talla: ${item.talla}</p>
                        <p class="text-orange-500 font-semibold text-sm">$${item.precio} c/u</p>
                    </div>
                </div>
                <div class="text-right">
                    <p class="text-sm font-semibold">$${totalItem.toFixed(2)}</p>
                    <button class="btn-quitar-producto text-red-500 hover:text-red-700 text-xs mt-1" 
                            data-producto-id="${item.id_producto}"
                            data-talla="${item.talla}">
                        <i class="fas fa-trash"></i> Quitar
                    </button>
                </div>
            </div>
        `;
    });

    contenido.innerHTML = html;
    subtotalSpan.textContent = `$${subtotal.toFixed(2)}`;
    contador.textContent = totalItems;
    
    // Agregar event listeners a los nuevos botones
    document.querySelectorAll('.btn-quitar-producto').forEach(btn => {
        btn.addEventListener('click', function() {
            const productoId = this.getAttribute('data-producto-id');
            const talla = this.getAttribute('data-talla');
            quitarProducto(productoId, talla);
        });
    });
}

// Quitar producto del carrito - VERSIÓN CORREGIDA
function quitarProducto(productoId, talla) {
    if (!confirm('¿Estás seguro de que quieres eliminar este producto del carrito?')) {
        return;
    }
    
    console.log('Eliminando producto:', { productoId, talla });
    
    fetch(URL_QUITAR_DEL_CARRITO, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ 
            producto_id: productoId,
            talla: talla
        })
    })
    .then(res => res.json())
    .then(data => {
        console.log('Respuesta de eliminación:', data);
        if (data.success) {
            fetchCarrito();
            mostrarMensaje('Producto eliminado del carrito', 'success');
        } else {
            mostrarMensaje(data.error || 'Error al eliminar', 'error');
        }
    })
    .catch(err => {
        console.error('Error:', err);
        mostrarMensaje('Error de conexión', 'error');
    });
}

// Obtener CSRF token
function getCSRFToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.startsWith(name + '=')) {
            return decodeURIComponent(cookie.substring(name.length + 1));
        }
    }
    return '';
}

// Mostrar mensajes
function mostrarMensaje(mensaje, tipo = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-md shadow-lg z-50 ${
        tipo === 'success' ? 'bg-green-500 text-white' : 
        tipo === 'error' ? 'bg-red-500 text-white' : 
        'bg-blue-500 text-white'
    }`;
    notification.textContent = mensaje;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}