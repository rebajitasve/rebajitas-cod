# Formulario Rebajitas COD

App propia para la tienda Shopify: botón "Pagar al recibir" + formulario + pedido directo en Shopify. Reemplaza a Releasit.

## Archivos
- `app.py` — el servidor (entrega el formulario y crea los pedidos).
- `reglas.py` — reglas de negocio: estados, oficinas TEALCA, ofertas, validaciones, cómo se arma el pedido.
- `oficinas_tealca.csv` — catálogo oficial de oficinas TEALCA de DroPanas. De aquí salen los estados, ciudades y oficinas del formulario.
- `sheets.py` — envía cada pedido nuevo a Google Sheets.
- `integraciones/google_sheets.gs` — código que se pega en la hoja de Google (Apps Script).
- `meta.py` — píxel de Meta y API de conversiones.
- `almacen.py` — guarda las ofertas del menú (en Shopify, como dato propio de la app).
- `sesion.py` — revisa que el menú solo se use desde el panel de Shopify.
- `estaticos/panel/` — páginas del menú de la app (Ofertas).
- `shopify.py` — la conexión con Shopify (leer producto, crear pedido).
- `estaticos/formulario.js` — el botón y el formulario que ve el cliente.
- `estaticos/prueba.html` — página que imita la del producto, para probar.
- `pruebas/` — revisiones automáticas.

## Probar en tu computador (sin crear pedidos reales)
Solo la primera vez, en la carpeta del proyecto:
```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```
Luego, cada vez: doble clic en **Iniciar formulario.bat**. Se abre `http://127.0.0.1:8001/prueba`.
Con `MODO_PRUEBA=1` (como viene) el formulario funciona completo pero no toca tu tienda.

Revisiones automáticas: `.venv\Scripts\python -m pytest -q pruebas`

## Instalar en TODOS los productos (recomendado)
Tienda online → Temas → (tema publicado) ⋯ → **Editar código** → `layout/theme.liquid` → pegar el contenido de `integraciones/tema-todos-los-productos.liquid` justo antes de `</body>` → Guardar.

## Instalar en un solo producto (bloque manual)
En Shopify: Tienda online → Personalizar → plantilla de producto de AO Black Maca → Agregar bloque → **Liquid personalizado**, y pegar:
```
<div id="rebajitas-cod"
     data-variante="{{ product.selected_or_first_available_variant.id }}"
     data-imagen="{{ product.featured_image | image_url: width: 160 }}"></div>
<script src="https://rebajitas-cod.onrender.com/formulario.js" defer></script>
```

## Configuración (archivo `.env` o página de Render)
Ver `.env.example`. Nunca se sube a GitHub.
- `MODO_PRUEBA` — 1 no crea pedidos; 0 crea pedidos reales.
- `SHOPIFY_TIENDA` — nombre.myshopify.com
- `SHOPIFY_TOKEN` o bien `SHOPIFY_CLIENT_ID` + `SHOPIFY_CLIENT_SECRET` — llaves de la app en Shopify (permisos: write_orders, read_products, read_customers, write_customers).
- `TIENDA_ORIGENES` — direcciones de la tienda autorizadas a enviar el formulario.

## Actualizar las oficinas TEALCA (cuando Tealca abre o cierra oficinas)
El archivo `oficinas_tealca.csv` es el catálogo oficial de DroPanas (`GET /oficinas?carrier=tealca`).
1. Pídele al agente de DroPanas el archivo nuevo, con **las mismas columnas**:
   `Oficina DroPanas ID, Estado, Estado DroPanas ID, Ciudad, Ciudad DroPanas ID, Nombre en DroPanas, Nombre para el cliente, Código Tealca, Dirección, Horario, Teléfono, Latitud, Longitud, Campo en la orden`.
2. En GitHub, abre el repositorio `rebajitas-cod` → archivo `oficinas_tealca.csv` → botón de los tres puntos → **Upload / Replace file** (o arrastra el archivo nuevo con el mismo nombre) → **Commit changes**.
3. Render publica solo en 1–2 minutos. Revisa el formulario: los estados, ciudades y oficinas salen del archivo nuevo.
- Si el archivo nuevo trae horarios con "am" al cierre (ej. "8:00 am a 4:00 am"), corrígelos: ver especificación.md.
- No hay que tocar nada más. El formulario nunca busca oficinas por nombre: siempre por su número (Oficina DroPanas ID).

## Google Sheets
1. En la hoja "Rebajitas": **Extensiones → Apps Script**. Borrar lo que haya y pegar `integraciones/google_sheets.gs`, cambiando `PEGA_AQUI_LA_CLAVE` por una clave.
2. **Implementar → Nueva implementación → Tipo: Aplicación web**. Ejecutar como: **Yo**. Quién tiene acceso: **Cualquier persona**. Autorizar con la cuenta de Google.
3. Copiar la **URL de la aplicación web** (termina en `/exec`).
4. En Render → rebajitas-cod → Environment: `SHEETS_URL` = esa URL, `SHEETS_CLAVE` = la misma clave.
- La pestaña se elige sola por mes: "Tealca COD {mes}" (ej. "Tealca COD Diciembre"). **Hay que crear la pestaña del mes antes del día 1**; si no existe, los pedidos van a una pestaña "Pedidos sin pestaña".
- Solo escribe columnas A–H, P (cédula) y T–W. En modo prueba no escribe nada.
- La pantalla https://rebajitas-cod.onrender.com revisa la conexión con la hoja (sin escribir) y dice qué falla.
- Si se cambia el código de Apps Script: **Implementar → Gestionar implementaciones → editar → Nueva versión** (así la URL no cambia).

## Render
`render.yaml` crea el servicio `rebajitas-cod` (plan Starter, US$ 7/mes, siempre encendido para no hacer esperar al cliente).
Solo pide dos llaves: `SHOPIFY_CLIENT_ID` y `SHOPIFY_CLIENT_SECRET` (de dev.shopify.com → Rebajitas COD → Configuración).
Para pasar a pedidos reales: en Render → rebajitas-cod → Environment → `MODO_PRUEBA` = `0`.
Para revisar que todo está bien: abrir https://rebajitas-cod.onrender.com (dice si está conectada y en qué modo).

## Versiones
- v0.1 — Etapa 1: formulario nuevo y creación de pedidos en Shopify (probado en modo prueba).
- v0.2 — Oficinas TEALCA reales (131) y botón final "Ir a WhatsApp a confirmar mi pedido" (+58 412 225 4027).
- v0.3 — Ofertas de AO Black Maca (1/2/3 unidades), datos del pedido con los mismos nombres que Releasit, UTM de anuncios, botón de WhatsApp sin mensaje escrito.
- v0.4 — Modo prueba lee el producto real sin crear pedidos; pantalla de estado de la conexión; direcciones de la tienda ya configuradas en `render.yaml`.
- v0.5 — Se permite la vista previa de temas de Shopify (*.shopifypreview.com) y, solo en vista previa, el bloque explica por qué no aparece el botón.
- v0.6 — Ofertas atadas a la dirección del producto (`ao-black-maca-potencia-brutal`). Agregar `?rcod=1` a la dirección del producto muestra (solo a quien lo use) por qué no aparece el botón.
- v0.7 — Arreglo: el tema de la tienda (Dawn) escondía el botón por verse "vacío"; ahora se fuerza a mostrarse. Franja de diagnóstico paso a paso con `?rcod=1` (arriba, con ×) y aviso si el bloque está pegado dos veces.
- v0.8 — Ciudad como lista desplegable que depende del estado (497 ciudades), con opción "Otra ciudad (escribirla)".
- v0.9 — El pedido en Shopify queda con el formato de Releasit: dirección = ciudad, ciudad = oficina TEALCA, código de estado, pago COD pendiente, envío "Gratis", cliente enlazado, sin nota.
- v0.10 — Google Sheets: cada pedido real se agrega a la pestaña del mes ("Tealca COD {mes}") con las columnas de Releasit.
- v0.11 — `MODO_PRUEBA` ya no tiene valor en `render.yaml`: se maneja solo desde la página de Render (antes cada subida lo devolvía a 1).
- v0.12 — Arreglo: Shopify rechazaba el pedido al enlazar el cliente sin correo; ya no se enlaza cliente.
- v0.13 — Campo Cédula (V/E) obligatorio y entrega a domicilio en Caracas (dirección en vez de oficina).
- v0.14 — Todo Miranda con entrega a domicilio; cédula en la columna P de la hoja; verificación de Google Sheets en la pantalla de la app.
- v0.15 — Primer pedido real OK (#3805). Se enlaza/crea el cliente por teléfono y el pedido queda como "requiere envío".
- v0.16 — La pestaña del mes se llama "Tealca COD {mes}" (ej. "Tealca COD Noviembre"), nombre real confirmado por Mike. Verificación de la hoja con mensajes más claros.
- v0.17 — Migración a la tienda nueva de Shopify `ifgcu1-dg.myshopify.com` (la vieja era `e1bvrm-ze.myshopify.com`).
- v0.18 — Botón en todos los productos con un solo código en theme.liquid (se coloca solo bajo el botón de compra; sigue la variante elegida). La pantalla de la app muestra si faltan permisos (clientes).
- v0.19 — Se ocultan "Add to cart", cantidad y "Comprar ya" del tema cuando nuestro botón carga bien.
- v0.20 — Si la plantilla no tiene botón de compra, nuestro botón se pone debajo del precio (o del título). Verificado en vivo: Creatina, Shilajit y Maca.
- v0.21 — Integración DroPanas: estados, ciudades y oficinas desde el catálogo oficial (`oficinas_tealca.csv`, 134 oficinas), oficina por número, IDs de DroPanas ocultos en el pedido, teléfono 04/02 de 11 dígitos, cédula V/E/P/J de 7–9 dígitos, dirección ≤250, punto de referencia ≤300. UTM con "+" como Releasit.
- v0.22 — En retiro en oficina, la "Dirección" del cliente es la de la oficina Tealca; en domicilio cualquier texto es válido.
- v0.23 — Menú de la app dentro de Shopify: Inicio y **Ofertas** (bundles y descuentos por producto, con etiqueta, color, imagen, preseleccionada y vista previa). Se guardan en Shopify.
- v0.24 — Menú Integraciones: píxel de Meta (InitiateCheckout y Purchase en el navegador + Purchase por API de conversiones sin duplicar) y estado de Google Sheets.
- v0.25 — El botón final "Ir a WhatsApp a confirmar mi pedido" abre el número de Pancake: +58 424 687 5154.
- v0.26 — Nota del pedido con la línea DROPANAS para el puente POS Cake → DroPanas. La confirmación muestra el pedido guardado en Shopify (arreglo de #1001/#1002). Un pedido solo cuenta como repetido si todos sus datos coinciden.
- v0.27 — El número de pedido ya no se muestra en la confirmación ni llega al navegador (confidencial).
- v0.28 — Horarios corregidos en el catálogo: Maracaibo Norte, Merida Norte y El Cementerio ("am" → "pm" al cierre).
- v0.29 — Si el bloque pegado a mano está fuera de la información del producto (caso Pysta: quedaba al final de la página), el botón se mueve solo bajo el precio.
- v0.30 — Botón fijo abajo (sticky): aparece al bajar por la página cuando el botón de debajo del precio ya no se ve.
