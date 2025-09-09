// static/js/carrito.js
document.addEventListener('DOMContentLoaded', function () {
    // Inicializa el carrito
    fetchCarrito();

    // Configurar controles de cantidad
    setupCantidadControls();

    // Manejar clic en botones de quitar producto
    document.addEventListener('click', function (e) {
        if (e.target.classList.contains('btn-quitar-producto')) {
            const btn = e.target;
            const productoId = btn.getAttribute('data-producto-id');
            quitarProducto(productoId);
        }
    });
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
            const input = this.parentElement.querySelector('.cantidad-input');
            const cantidad = parseInt(input.value) || 1;
            agregarAlCarrito(productoId, cantidad);
        });
    });
}

// Función para agregar producto al carrito
function agregarAlCarrito(productoId, cantidad) {
    fetch(URL_AGREGAR_CARRITO, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ producto_id: productoId, cantidad: cantidad })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            fetchCarrito();
            abrirCarrito();
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
            <div class="flex justify-between items-center mb-4 p-2 border-b" data-producto-id="${item.id_producto}">
                <div class="flex items-center">
                    ${item.imagen ? `<img src="${item.imagen}" alt="${item.nombre}" class="w-12 h-12 object-cover rounded mr-3">` : ''}
                    <div>
                        <p class="font-medium text-sm">${item.nombre}</p>
                        <p class="text-gray-600 text-xs">Cantidad: ${item.cantidad}</p>
                        <p class="text-orange-500 font-semibold text-sm">$${item.precio} c/u</p>
                    </div>
                </div>
                <div class="text-right">
                    <p class="text-sm font-semibold">$${totalItem.toFixed(2)}</p>
                    <button class="btn-quitar-producto text-red-500 hover:text-red-700 text-xs mt-1" 
                            data-producto-id="${item.id_producto}">
                        <i class="fas fa-trash"></i> Quitar
                    </button>
                </div>
            </div>
        `;
    });

    contenido.innerHTML = html;
    subtotalSpan.textContent = `$${subtotal.toFixed(2)}`;
    contador.textContent = totalItems;
}

// Quitar producto del carrito
function quitarProducto(productoId) {
    fetch(URL_QUITAR_DEL_CARRITO, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ producto_id: productoId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            fetchCarrito();
            mostrarMensaje('Producto eliminado', 'success');
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
    console.log(`${tipo}: ${mensaje}`);
    // Aquí puedes agregar notificaciones bonitas si quieres
    alert(mensaje); // Temporalmente usando alert
}