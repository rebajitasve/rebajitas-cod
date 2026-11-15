# Especificación · Formulario Rebajitas COD

## Objetivo
Reemplazar Releasit COD en la tienda Shopify de Rebajitas con una app propia: botón "Pagar al recibir" en la página del producto, formulario más moderno y pedido creado directamente en Shopify. Los pedidos deben seguir llegando igual a Pancake (confirmación por WhatsApp), Google Sheets y Dropanas.

## Cómo funciona
1. En la página del producto, un bloque "Liquid personalizado" carga `formulario.js` desde el servidor (Render).
2. El botón muestra el precio que da el servidor (leído de Shopify). Si el servidor no responde, el botón no aparece y la tienda sigue normal.
3. El cliente llena: nombre, apellido, WhatsApp (+58), estado, ciudad, oficina TEALCA.
4. El servidor valida todo otra vez, decide el precio (nunca confía en el navegador) y crea el pedido en Shopify.
5. Pantalla final: resumen del pedido y botón verde **"Ir a WhatsApp a confirmar mi pedido"**, que abre el chat con +58 412 225 4027 (sin mensaje escrito: Pancake envía la confirmación automática y el cliente solo la responde). El número se cambia en `reglas.py` (`WHATSAPP_CONFIRMACION`).

## Ofertas (bundles)
- Se configuran en `reglas.py` (`OFERTAS`) por nombre del producto en Shopify.
- AO Black Maca: 1 unidad Bs.S. 37.500 · 2 unidades Bs.S. 57.500 ("Más vendido", viene marcada) · 3 unidades Bs.S. 65.500 ("Mejor precio").
- Precio tachado = precio de 1 unidad × cantidad.
- En Shopify el pedido va con el precio de 1 unidad por cada unidad y un descuento `OFERTA N UNIDADES` por la diferencia (ej. 3 × 37.500 − 47.000 = 65.500).
- **Verificar en la primera prueba real** que el total del pedido en Shopify quede exacto.

## Oficinas TEALCA
- 131 oficinas en `oficinas_tealca.json`, tomadas del Excel de Mike (nov. 2026). La lista de oficinas aparece al elegir el estado; solo se aceptan oficinas de la lista.
- Amazonas no tiene oficinas en la lista: ahí el cliente escribe la oficina a mano.
- Revisar: en Carabobo aparece "CAUCAGUA–HIGUEROTE–BARLOVENTO–TACARIGUA", que parece de Miranda.

## Cómo queda el pedido en Shopify
- Producto y cantidad de la oferta elegida, con el precio del servidor. Estado de pago: **pendiente**.
- Dirección de envío y facturación: nombre, apellido, `Oficina TEALCA: <oficina>`, ciudad, estado, país Venezuela, teléfono `+58…`.
- Teléfono del pedido: `+58…` (lo usa Pancake para escribir por WhatsApp).
- Etiquetas: `COD`, `Formulario Rebajitas`.
- Nota: "Pago al recibir. Retiro en oficina TEALCA: …".
- Datos adicionales, con los mismos nombres que Releasit: UTM term, UTM content, UTM campaign, UTM medium, UTM source (si el cliente llegó por un anuncio), Country code, Nombre, Apellido, Teléfono (10 dígitos, sin +58), Estado (en mayúsculas), Ciudad, Oficina de TEALCA, IP address.
- Las UTM se guardan cuando el cliente llega a la tienda, aunque luego navegue a otras páginas.
- Canal: aparecerá el nombre de nuestra app en Shopify (antes decía "Releasit COD Form").
- No se envía correo de confirmación de Shopify al cliente; se descuenta el inventario.

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
| 2 | Ofertas por cantidad (bundles) | Hecho en código; falta probar con la tienda real |
| 3 | Bloqueo de teléfonos e IP | Pendiente (necesita base de datos) |
| 4 | Píxel de Meta (navegador + servidor) | Pendiente |
| 5 | Google Sheets directo | Solo si hace falta (hoy lo llena Releasit) |

## Datos pendientes de Mike
- ¿El precio de AO Black Maca en Shopify (Bs.S. 32.450) debe pasar a 37.500? El formulario usa 37.500 de todas formas.
