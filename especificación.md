# Especificación · Formulario Rebajitas COD

## Objetivo
Reemplazar Releasit COD en la tienda Shopify de Rebajitas con una app propia: botón "Pagar al recibir" en la página del producto, formulario más moderno y pedido creado directamente en Shopify. Los pedidos deben seguir llegando igual a Pancake (confirmación por WhatsApp), Google Sheets y Dropanas.

## En qué productos aparece
- **Todos los productos**: el código `integraciones/tema-todos-los-productos.liquid` se pega una vez en `layout/theme.liquid` (antes de `</body>`). El botón se coloca solo debajo del formulario de compra del producto (se ignora el formulario de cuotas); si la plantilla no tiene botón de compra (ej. Oxi-Break Uñas), va debajo del precio, o del título.
- Si una plantilla tiene el bloque pegado a mano (como la maca), se usa ese y el automático se descarta.
- Productos con variantes: el formulario usa la variante elegida en la página (se recarga precio y ofertas al cambiarla).
- Productos sin ofertas en `reglas.py`: 1 unidad al precio de Shopify, sin sección de ofertas.
- Se ocultan "Add to cart", la cantidad y "Comprar ya" del tema (`OCULTAR_CARRITO_TEMA` en `reglas.py`), **solo cuando nuestro botón cargó bien**; si el servidor falla, la tienda muestra su botón normal.

## Cómo funciona
1. En la página del producto, un bloque "Liquid personalizado" carga `formulario.js` desde el servidor (Render).
2. El botón muestra el precio que da el servidor (leído de Shopify). Si el servidor no responde, el botón no aparece y la tienda sigue normal.
3. El cliente llena: nombre, apellido, WhatsApp (+58), estado, ciudad, oficina TEALCA.
4. El servidor valida todo otra vez, decide el precio (nunca confía en el navegador) y crea el pedido en Shopify.
5. Pantalla final: resumen del pedido y botón verde **"Ir a WhatsApp a confirmar mi pedido"**, que abre el chat con +58 412 225 4027 (sin mensaje escrito: Pancake envía la confirmación automática y el cliente solo la responde). El número se cambia en `reglas.py` (`WHATSAPP_CONFIRMACION`).

## Ofertas (bundles)
- Se configuran en `reglas.py` (`OFERTAS`) por dirección del producto (`ao-black-maca-potencia-brutal`), nombre o ID de variante.
- AO Black Maca: 1 unidad Bs.S. 37.500 · 2 unidades Bs.S. 57.500 ("Más vendido", viene marcada) · 3 unidades Bs.S. 65.500 ("Mejor precio").
- Precio tachado = precio de 1 unidad × cantidad.
- En Shopify el pedido va con el precio de 1 unidad por cada unidad y un descuento `OFERTA N UNIDADES` por la diferencia (ej. 3 × 37.500 − 47.000 = 65.500).
- **Verificar en la primera prueba real** que el total del pedido en Shopify quede exacto.

## Cédula y entrega a domicilio
- Campo obligatorio **Cédula de quien retira** (o "de quien recibe" en domicilio), debajo de la oficina: letra V/E + 5 a 9 números. Se guarda como `V-12345678`.
- En Shopify: línea 2 de la dirección `C.I. V-12345678` y dato adicional "Cédula".
- **Entrega a domicilio** (`ENTREGA_DOMICILIO` en `reglas.py`, hoy: Distrito Capital → Caracas, y **todo Miranda**; mismo costo que el retiro en oficina): al elegir esa ciudad desaparece la oficina y aparece "Dirección de entrega" (mínimo 10 letras). Textos: "Entrega a domicilio · Pagas al recibir".
- Pedido a domicilio en Shopify: dirección = la del cliente, ciudad = Caracas, estado A, envío "Entrega a domicilio" (0), etiqueta `DOMICILIO`, datos adicionales "Oficina de TEALCA" = ENTREGA A DOMICILIO, "Dirección", "Tipo de entrega".
- En Google Sheets, columna Oficina = `DOMICILIO: <dirección>`. La cédula va en la **columna P**.

## Integración con DroPanas (flujo: Rebajitas Form → Shopify → Pancake → DroPanas)
- **Catálogo único**: `oficinas_tealca.csv` (oficial de DroPanas, 134 oficinas, 23 estados, 70 ciudades). Estados, ciudades y oficinas del formulario salen solo de aquí. Ya no se usa la lista general de ciudades ni "Otra ciudad".
- **Cascada**: Estado → Ciudad → Oficina. Se muestra el "Nombre para el cliente", la dirección y el horario de la oficina elegida.
- **La oficina viaja por su número** (Oficina DroPanas ID) y el servidor saca de esa fila el estado y la ciudad. Nunca se busca por nombre.
- **Entrega a domicilio**: Distrito Capital → Caracas, y todas las ciudades de Miranda del catálogo (Carrizal, Charallave, Guarenas, Guatire, Higuerote, Los Teques, San Antonio de Los Altos). Pide dirección (obligatoria, cualquier texto, máx. 250) y punto de referencia (opcional, máx. 300).
- **Solo Tealca y domicilio**: no se ofrece Zoom ni MRW (son prepago).
- **Validaciones DroPanas**: nombre y apellido separados, máx. 50 c/u; teléfono venezolano móvil (412, 414, 416, 422, 424, 426) o fijo (2xx), se guarda con 11 dígitos empezando por 0 (ej. 04141234567); acepta 4141234567, 04141234567 o +58 414-1234567; cédula tipo V, E, P o J con 7 a 9 dígitos (ej. V-20216018).
- **Información adicional del pedido** (Retiro en oficina): Country code, Nombre, Apellido, Teléfono (11 dígitos), Cédula, Estado, Ciudad, Tipo de entrega = "Retiro en oficina TEALCA", Dirección (= dirección de la oficina), Oficina de TEALCA (nombre), **Oficina DroPanas ID**, **Estado DroPanas ID**, **Ciudad DroPanas ID**, IP address, y las UTM si hay.
- **Domicilio**: igual pero Tipo de entrega = "Entrega a domicilio", Dirección, Punto de referencia (si lo hay), Estado/Ciudad DroPanas ID; sin Oficina DroPanas ID.
- Referencia para el puente (no lo hace el formulario): Tealca → tipo_entrega "oficina", shipping_type_id 3, tipo_pago "con_recaudo", oficina_id = Oficina DroPanas ID, direccion.state_id = Estado DroPanas ID, direccion.city_id = Ciudad DroPanas ID.
- **Dirección del cliente** (decisión de Mike, 17-nov): en retiro en oficina = la dirección de la oficina Tealca; en domicilio = la que escribe el cliente (cualquier texto, obligatoria, máx. 250). Va en el dato adicional "Dirección" y en la línea 1 de la dirección de Shopify.
- Decisiones confirmadas: Caracas solo domicilio; Miranda a domicilio solo en las 7 ciudades del catálogo; Amazonas no aparece (sin oficinas).
- Dirección de envío en Shopify: línea 1 = la dirección del cliente (ver arriba), línea 2 = "C.I. V-…", ciudad = la ciudad, estado con su código de Shopify. Etiqueta `TEALCA` o `DOMICILIO`.

## Cómo queda el pedido en Shopify (igual que los de Releasit)
- Producto y cantidad de la oferta elegida: cada unidad al precio de lista (37.500) y, si aplica, descuento `OFERTA N UNIDADES` por la diferencia.
- Pago: **pendiente**, forma de pago "Cash on Delivery (COD)" por el total de la oferta.
- Envío: línea "Gratis" (0).
- Dirección de envío y facturación, igual que Releasit:
  - Nombre y apellido del cliente.
  - Dirección (línea 1): la **ciudad** que eligió o escribió el cliente.
  - Ciudad: la **oficina TEALCA** (ej. LECHERÍA).
  - Estado: código de Shopify (A = Distrito Capital, B = Anzoátegui, G = Carabobo, …; lista en `reglas.py`).
  - País Venezuela y teléfono `+58…`.
- Cliente: se busca en Shopify por teléfono y, si no existe, se crea (nombre, apellido, teléfono); luego se enlaza al pedido. Necesita los permisos `read_customers` y `write_customers` en la app. Si falla (por ejemplo sin esos permisos), el pedido se crea igual sin cliente. (El enlace directo por teléfono no se puede: Shopify exige correo, error del 16-nov-2026.)
- Cada producto va marcado como **requiere envío** (sin esto Shopify mostraba "No se requiere envío", pedido #3805).
- Sin nota.
- Etiquetas: `COD`, `Formulario Rebajitas` (la etiqueta `releasit_cod_form` no la usa nadie, confirmado por Mike).
- Datos adicionales, con los mismos nombres que Releasit: UTM term, UTM content, UTM campaign, UTM medium, UTM source (si el cliente llegó por un anuncio), Country code, Nombre, Apellido, Teléfono (10 dígitos, sin +58), Estado (en mayúsculas), Ciudad, Oficina de TEALCA, IP address.
- Las UTM se guardan cuando el cliente llega a la tienda, aunque luego navegue a otras páginas.
- Canal: "Rebajitas COD" (antes "Releasit COD Form").
- No se envía correo de confirmación de Shopify al cliente; se descuenta el inventario.
- **Verificar con el primer pedido real**: que Shopify acepte la forma de pago, el cliente y el código de estado, y que el total quede exacto.

## Modo prueba y pantalla de estado
- `MODO_PRUEBA=1`: el formulario lee el producto y precio **reales** de Shopify (si hay llaves) pero **no crea pedidos**; devuelve números `#PRUEBA-…`. La página `/prueba` usa un producto de ejemplo.
- La dirección principal del servidor (`/`, la que abre Shopify al tocar la app en el panel) muestra si la conexión con Shopify funciona y si está en modo prueba o real.

## Tienda
- Shopify: `ifgcu1-dg.myshopify.com` · Pública: `rebajitasve.com`
- App en el Dev Dashboard: "Rebajitas COD", permisos `write_orders, read_products, read_customers, write_customers`, instalada en la tienda (nov. 2026). Llaves por client credentials (token de 24 h que el servidor renueva solo).

## Diagnóstico
- Si el botón no aparece, abrir la página del producto con `?rcod=1` al final (o en vista previa del tema): arriba sale una franja oscura con cada paso (✔/✖) y el motivo. Los clientes no la ven.
- Si no sale ni la franja, el bloque no está en la plantilla que usa ese producto.
- El tema de la tienda esconde cajas "vacías" (`div:empty`); por eso el bloque se fuerza a `display:block`.
- El bloque debe estar pegado **una sola vez** por página (debajo del precio).

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
| 5 | Google Sheets directo | Hecho (falta conectar la hoja) |

## Google Sheets
- Hoja "Rebajitas", pestaña del mes con nombre exacto **"Tealca COD Noviembre"** (una pestaña nueva cada mes).
- Funciona con un código de Apps Script pegado en la hoja (`integraciones/google_sheets.gs`) que recibe cada pedido real y agrega la fila. La pestaña se elige por mes (`SHEETS_HOJA` = "Tealca COD {mes}"); si no existe, va a "Pedidos sin pestaña". Se envía en segundo plano (el cliente no espera) con 3 reintentos; si falla, queda en el registro de Render para anotarlo a mano.
- La pantalla de la app (`/`) verifica la hoja sin escribir nada y dice en palabras simples qué falla (acceso, clave, pestaña del mes inexistente, código desactualizado).
- Columnas: A Fecha, B Nombre y Apellido, C Teléfono, D Estado, E Oficina, F Producto, G Cantidad, H Valor a Pagar; P Cédula; T utm_source, U utm_campaign, V utm_medium, W utm_content. Las demás las llena el equipo.

## Datos pendientes de Mike
- ¿El precio de AO Black Maca en Shopify (Bs.S. 32.450) debe pasar a 37.500? El formulario usa 37.500 de todas formas.
