# Especificación · Formulario Rebajitas COD

## Objetivo
Reemplazar Releasit COD en la tienda Shopify de Rebajitas con una app propia: botón "Pagar al recibir" en la página del producto, formulario más moderno y pedido creado directamente en Shopify. Los pedidos deben seguir llegando igual a Pancake (confirmación por WhatsApp), Google Sheets y Dropanas.

## Cómo funciona
1. En la página del producto, un bloque "Liquid personalizado" carga `formulario.js` desde el servidor (Render).
2. El botón muestra el precio que da el servidor (leído de Shopify). Si el servidor no responde, el botón no aparece y la tienda sigue normal.
3. El cliente llena: nombre, apellido, WhatsApp (+58), estado, ciudad, oficina TEALCA.
4. El servidor valida todo otra vez, decide el precio (nunca confía en el navegador) y crea el pedido en Shopify.

## Cómo queda el pedido en Shopify
- Producto y cantidad de la oferta elegida, con el precio del servidor. Estado de pago: **pendiente**.
- Dirección de envío y facturación: nombre, apellido, `Oficina TEALCA: <oficina>`, ciudad, estado, país Venezuela, teléfono `+58…`.
- Teléfono del pedido: `+58…` (lo usa Pancake para escribir por WhatsApp).
- Etiquetas: `COD`, `Formulario Rebajitas`.
- Nota: "Pago al recibir. Retiro en oficina TEALCA: …".
- Datos adicionales: Origen, Estado, Ciudad, Oficina TEALCA, IP del cliente.
- No se envía correo de confirmación de Shopify al cliente; se descuenta el inventario.
- **Pendiente:** comparar con un pedido real de Releasit para que Pancake, Sheets y Dropanas lo lean igual.

## Protecciones
- Teléfono: solo celulares venezolanos (412, 414, 416, 422, 424, 426), con o sin 0 o +58.
- Pedido repetido: si el mismo teléfono pide el mismo producto en menos de 3 minutos, no se crea otro (se devuelve el mismo número).
- Máximo 5 pedidos cada 10 minutos desde la misma conexión.
- Producto agotado: no se crea el pedido.
- Estas protecciones viven en la memoria del servidor: se reinician si Render reinicia.

## Etapas
| Etapa | Qué | Estado |
|---|---|---|
| 1 | Formulario + pedido en Shopify | Hecho en código; falta probar con la tienda real |
| 2 | Ofertas por cantidad (bundles) | Pendiente (el formulario ya las muestra si se configuran en `reglas.py`) |
| 3 | Bloqueo de teléfonos e IP | Pendiente (necesita base de datos) |
| 4 | Píxel de Meta (navegador + servidor) | Pendiente |
| 5 | Google Sheets directo | Solo si hace falta (hoy lo llena Releasit) |

## Datos pendientes de Mike
- Lista real de oficinas TEALCA por estado (mientras tanto el cliente la escribe a mano).
- Precios reales de 2 y 3 unidades de AO Black Maca.
- Captura de un pedido de Releasit en Shopify (para copiar el formato).
