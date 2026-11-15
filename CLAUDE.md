# Instrucciones permanentes · Formulario Rebajitas COD

## Quién soy
- Soy Mike, dueño de Rebajitas Venezuela. **No sé programar**: explícame todo en lenguaje sencillo, sin tecnicismos, y dime exactamente qué probar y cómo.

## Qué es esto
- Una app privada para mi tienda Shopify que reemplaza a Releasit COD: botón "Pagar al recibir" en la página del producto, formulario propio y pedido creado directamente en Shopify.
- Los pedidos deben seguir llegando igual que hoy a Shopify, Pancake (confirmación por WhatsApp), mi hoja de Google Sheets y Dropanas.

## Reglas que nunca se rompen
- **Nunca subir a GitHub (push) sin que yo lo apruebe por escrito.** Lo que llega a GitHub lo publica Render y lo ven mis clientes.
- Nunca mostrar, copiar ni pedir lo que hay en `.env` (llaves de Shopify y Meta). Nunca subir `.env`.
- El precio de cada pedido lo decide el servidor (`reglas.py` + Shopify), nunca lo que mande el navegador.
- Las pruebas se hacen en mi computador con `MODO_PRUEBA=1` (no crea pedidos reales) antes de tocar la tienda.

## Cómo trabajamos
- Antes de cada cambio, guarda una versión en Git (commit local) con una descripción en español.
- Un cambio a la vez. Al terminar cada paso, explícame qué hiciste y qué debo probar, y espera mi "sigue".
- Las reglas de negocio (ofertas, validaciones, estados, oficinas) viven en `reglas.py`. No las dupliques en otros archivos.
- Al terminar un tema, actualiza `especificación.md` y `LEEME.md`.

## Dónde está todo
- Qué debe hacer la app y en qué etapa vamos: `especificación.md`
- Cómo se usa, se prueba y se publica: `LEEME.md`
