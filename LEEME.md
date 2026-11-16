# Formulario Rebajitas COD

App propia para la tienda Shopify: botón "Pagar al recibir" + formulario + pedido directo en Shopify. Reemplaza a Releasit.

## Archivos
- `app.py` — el servidor (entrega el formulario y crea los pedidos).
- `reglas.py` — reglas de negocio: estados, oficinas TEALCA, ofertas, validaciones, cómo se arma el pedido.
- `oficinas_tealca.json` — oficinas TEALCA por estado (para cambiarlas, editar este archivo).
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
