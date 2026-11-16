# Formulario Rebajitas COD

App propia para la tienda Shopify: botón "Pagar al recibir" + formulario + pedido directo en Shopify. Reemplaza a Releasit.

## Archivos
- `app.py` — el servidor (entrega el formulario y crea los pedidos).
- `reglas.py` — reglas de negocio: estados, oficinas TEALCA, ofertas, validaciones, cómo se arma el pedido.
- `ciudades_ve.json` — ciudades de Venezuela por estado (para la lista de Ciudad). Para agregar una ciudad, editar este archivo.
- `oficinas_tealca.json` — oficinas TEALCA por estado (para cambiarlas, editar este archivo).
- `sheets.py` — envía cada pedido nuevo a Google Sheets.
- `integraciones/google_sheets.gs` — código que se pega en la hoja de Google (Apps Script).
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

## Instalar en la tienda (cuando esté en Render)
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
- `SHOPIFY_TOKEN` o bien `SHOPIFY_CLIENT_ID` + `SHOPIFY_CLIENT_SECRET` — llaves de la app en Shopify (permiso: crear pedidos y leer productos).
- `TIENDA_ORIGENES` — direcciones de la tienda autorizadas a enviar el formulario.

## Google Sheets
1. En la hoja "Rebajitas": **Extensiones → Apps Script**. Borrar lo que haya y pegar `integraciones/google_sheets.gs`, cambiando `PEGA_AQUI_LA_CLAVE` por una clave.
2. **Implementar → Nueva implementación → Tipo: Aplicación web**. Ejecutar como: **Yo**. Quién tiene acceso: **Cualquier persona**. Autorizar con la cuenta de Google.
3. Copiar la **URL de la aplicación web** (termina en `/exec`).
4. En Render → rebajitas-cod → Environment: `SHEETS_URL` = esa URL, `SHEETS_CLAVE` = la misma clave.
- La pestaña se elige sola por mes: "Tealca {mes} COD" (ej. "Tealca Diciembre COD"). **Hay que crear la pestaña del mes antes del día 1**; si no existe, los pedidos van a una pestaña "Pedidos sin pestaña".
- Solo escribe columnas A–H y T–W. En modo prueba no escribe nada.
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
- v0.10 — Google Sheets: cada pedido real se agrega a la pestaña del mes ("Tealca {mes} COD") con las columnas de Releasit.
- v0.11 — `MODO_PRUEBA` ya no tiene valor en `render.yaml`: se maneja solo desde la página de Render (antes cada subida lo devolvía a 1).
- v0.12 — Arreglo: Shopify rechazaba el pedido al enlazar el cliente sin correo; ya no se enlaza cliente.
- v0.13 — Campo Cédula (V/E) obligatorio y entrega a domicilio en Caracas (dirección en vez de oficina).
