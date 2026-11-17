"""Servidor del formulario: entrega el formulario a la tienda y crea los pedidos en Shopify."""
import logging
import re
from html import escape
import threading
import time
from decimal import Decimal

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

import almacen
import config
import meta
import reglas
import sesion
import sheets
import shopify

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("cod")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
# Direcciones de la tienda (config) + vistas previas de temas de Shopify (dirección temporal *.shopifypreview.com).
app.add_middleware(CORSMiddleware, allow_origins=config.TIENDA_ORIGENES,
                   allow_origin_regex=r"https://[a-z0-9-]+\.shopifypreview\.com",
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

ESTATICOS = config.CARPETA / "estaticos"

# Protecciones simples en memoria: pedidos repetidos y demasiados intentos desde la misma conexión.
_candado = threading.Lock()
_recientes: dict[tuple, tuple[float, dict]] = {}  # (teléfono, variante, entrega, cantidad, cédula) -> (hora, resumen del pedido)
_intentos: dict[str, list[float]] = {}            # IP -> horas de los últimos pedidos
MINUTOS_REPETIDO = 3
MAX_PEDIDOS_POR_IP = 5
MINUTOS_VENTANA_IP = 10


def ip_de(request: Request) -> str:
    reenviada = request.headers.get("x-forwarded-for", "")
    if reenviada:
        return reenviada.split(",")[0].strip()
    return request.client.host if request.client else ""


def _numero(valor: Decimal) -> float:
    return float(valor)


# ---------- Menú de la app dentro de Shopify ----------
# Las páginas del menú se abren dentro del panel de Shopify (App Bridge). Los datos se piden a /panel-api/*,
# que exige la sesión de Shopify (sesion.py). El ID de cliente de la app es público; el secreto nunca sale del servidor.

def cabecera_panel(titulo: str) -> str:
    return f"""<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="shopify-api-key" content="{escape(config.SHOPIFY_CLIENT_ID)}">
<script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
<title>{escape(titulo)} · Rebajitas Form</title>
<ui-nav-menu><a href="/" rel="home">Inicio</a><a href="/panel/ofertas">Ofertas</a><a href="/panel/integraciones">Integraciones</a></ui-nav-menu>"""


def respuesta_panel(html: str) -> HTMLResponse:
    # Solo el panel de Shopify de esta tienda puede mostrar estas páginas dentro de un marco.
    return HTMLResponse(html, headers={"Content-Security-Policy":
                                       f"frame-ancestors https://{config.SHOPIFY_TIENDA} https://admin.shopify.com;"})


def sesion_panel(request: Request) -> None:
    """Exige la sesión de Shopify. Solo en el computador (modo prueba y sin llaves) se deja pasar para probar."""
    if config.MODO_PRUEBA and not shopify.hay_llaves():
        return
    token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    sesion.verificar(token)


@app.exception_handler(sesion.SesionInvalida)
def _sesion_invalida(request: Request, e: sesion.SesionInvalida):
    return JSONResponse({"error": str(e)}, status_code=401)


@app.get("/panel/ofertas", response_class=HTMLResponse)
def panel_ofertas():
    html = (ESTATICOS / "panel" / "ofertas.html").read_text(encoding="utf-8")
    return respuesta_panel(html.replace("<!--CABECERA-->", cabecera_panel("Ofertas")))


@app.get("/panel/integraciones", response_class=HTMLResponse)
def panel_integraciones():
    html = (ESTATICOS / "panel" / "integraciones.html").read_text(encoding="utf-8")
    return respuesta_panel(html.replace("<!--CABECERA-->", cabecera_panel("Integraciones")))


@app.get("/panel-api/integraciones")
def panel_leer_integraciones(request: Request):
    sesion_panel(request)
    hoja_ok, hoja_txt = sheets.verificar()
    return {"pixel": meta.para_panel(), "monedas": meta.MONEDAS,
            "sheets": {"ok": hoja_ok, "texto": hoja_txt}}


@app.put("/panel-api/integraciones/pixel")
async def panel_guardar_pixel(request: Request):
    sesion_panel(request)
    try:
        pixel, errores = meta.guardar(await request.json())
    except shopify.ErrorShopify as e:
        log.error("No se guardó el píxel: %s", e)
        return JSONResponse({"error": "Shopify no guardó la configuración. Intenta de nuevo."}, status_code=502)
    if errores:
        return JSONResponse({"errores": errores}, status_code=422)
    log.info("Píxel de Meta guardado (activo=%s, %s píxel(es))", pixel["activo"], len(pixel["ids"].split()))
    return {"ok": True, "pixel": pixel}


@app.post("/panel-api/integraciones/pixel/prueba")
async def panel_probar_pixel(request: Request):
    """Manda un Purchase de prueba por la API de conversiones (aparece en Administrador de eventos → Probar eventos)."""
    sesion_panel(request)
    cuerpo = await request.json()
    codigo = re.sub(r"[^A-Za-z0-9]", "", str(cuerpo.get("codigo_prueba") or ""))[:20]
    if not codigo:
        return JSONResponse({"error": "Escribe el código de prueba que te da Meta en «Probar eventos»"}, status_code=422)
    evento = meta.evento_compra("PRUEBA-" + str(int(time.time())), {"telefono": "+584141234567", "nombre": "Prueba", "apellido": "Rebajitas",
                                "ciudad": "Caracas"}, {"producto_id": "prueba", "titulo": "Evento de prueba"},
                                {"precio": Decimal("1"), "cantidad": 1}, {"url": "https://" + config.SHOPIFY_TIENDA}, ip_de(request))
    ok, msg = meta.enviar([evento], codigo_prueba=codigo)
    return JSONResponse({"ok": ok, "mensaje": msg}, status_code=200 if ok else 502)


@app.get("/panel/panel.js")
def panel_js():
    return FileResponse(ESTATICOS / "panel" / "panel.js", media_type="application/javascript; charset=utf-8",
                        headers={"Cache-Control": "no-cache"})


PRODUCTOS_PRUEBA = [{"id": "prueba", "titulo": "AO Black Maca (ejemplo)", "direccion": "ao-black-maca-potencia-brutal",
                     "estado": "ACTIVE", "precio": "37500.00", "variante": "prueba", "foto": "", "fotos": []},
                    {"id": "prueba-2", "titulo": "Creatina (ejemplo)", "direccion": "creatina", "estado": "ACTIVE",
                     "precio": "29450.00", "variante": "prueba", "foto": "", "fotos": []}]


@app.get("/panel-api/productos")
def panel_productos(request: Request):
    sesion_panel(request)
    try:
        productos = shopify.listar_productos() if shopify.hay_llaves() else PRODUCTOS_PRUEBA
    except shopify.ErrorShopify as e:
        log.warning("No se pudieron listar los productos: %s", e)
        return JSONResponse({"error": "No pudimos leer los productos de Shopify"}, status_code=502)
    guardadas = almacen.leer(forzar=True)
    for p in productos:
        cfg = reglas.config_de_producto(guardadas, p["id"], p["direccion"])
        p["config"] = cfg or {"activo": False, "ofertas": []}
    return {"productos": productos, "moneda": "VED", "colores": reglas.COLORES_ETIQUETA,
            "maximo": reglas.MAX_OFERTAS, "max_cantidad": reglas.MAX_CANTIDAD}


@app.put("/panel-api/ofertas/{producto_id}")
async def panel_guardar_ofertas(producto_id: str, request: Request):
    sesion_panel(request)
    cuerpo = await request.json()
    cfg, errores = reglas.normalizar_config_producto(cuerpo.get("config") or {})
    if errores:
        return JSONResponse({"errores": errores}, status_code=422)
    try:
        almacen.guardar_producto(producto_id, str(cuerpo.get("direccion") or ""), cfg)
    except shopify.ErrorShopify as e:
        log.error("No se guardaron las ofertas de %s: %s", producto_id, e)
        return JSONResponse({"error": "Shopify no guardó las ofertas. Intenta de nuevo."}, status_code=502)
    log.info("Ofertas guardadas para el producto %s (%s ofertas, activo=%s)", producto_id, len(cfg["ofertas"]), cfg["activo"])
    return {"ok": True, "config": cfg}


@app.get("/", response_class=HTMLResponse)
def inicio():
    """Pantalla que se ve al abrir la app desde el panel de Shopify."""
    clientes = ""
    if not shopify.hay_llaves():
        conexion, ok = "Faltan las llaves de Shopify en Render", False
    else:
        try:
            conexion, ok = f"Conectada a la tienda «{shopify.probar_conexion()}»", True
            tiene = shopify.permisos()
            faltan = [p for p in ("write_orders", "read_products", "read_customers", "write_customers") if p not in tiene]
            clientes = ("✔ Permisos completos (pedidos, productos y clientes)" if not faltan else
                        "✖ Faltan permisos en la app: " + ", ".join(faltan) +
                        (" (sin esto los pedidos salen «Sin cliente»)" if any("customers" in p for p in faltan) else ""))
        except shopify.ErrorShopify as e:
            log.warning("Prueba de conexión fallida: %s", e)
            conexion, ok = "Las llaves no funcionan. Revisa el ID y el secreto del cliente en Render", False
    modo = "Modo prueba: el formulario NO crea pedidos reales" if config.MODO_PRUEBA else "Modo real: el formulario crea pedidos"
    hoja_ok, hoja_txt = sheets.verificar()
    hoja = ("✔ " if hoja_ok else "✖ ") + "Google Sheets: " + hoja_txt
    color = "#0d7a50" if ok else "#c2372f"
    return respuesta_panel(f"""<!doctype html><html lang="es"><head>{cabecera_panel("Inicio")}</head>
<body style="font-family:system-ui,sans-serif;background:#f4f7f5;color:#14181b;margin:0;padding:32px 16px">
<div style="max-width:520px;margin:auto;background:#fff;border-radius:16px;padding:24px;box-shadow:0 4px 20px rgba(0,0,0,.06)">
<h1 style="margin:0 0 16px;font-size:22px">Rebajitas Form</h1>
<p style="margin:8px 0;color:{color};font-weight:700">{"✔" if ok else "✖"} {escape(conexion)}</p>
<p style="margin:8px 0;font-weight:600">{modo}</p>
<p style="margin:8px 0">{escape(clientes)}</p>
<p style="margin:8px 0">{escape(hoja)}</p>
<p style="margin:16px 0 0;color:#5d6865;font-size:14px">Esta app maneja el botón "Pagar al recibir" de la tienda.
Las ofertas por producto se configuran en el menú <b>Ofertas</b>.</p>
</div></body></html>""")


@app.get("/salud")
def salud():
    return {"ok": True, "modo_prueba": config.MODO_PRUEBA}


@app.get("/formulario.js")
def formulario_js():
    return FileResponse(ESTATICOS / "formulario.js", media_type="application/javascript; charset=utf-8",
                        headers={"Cache-Control": "public, max-age=60"})


@app.get("/prueba", response_class=HTMLResponse)
def pagina_prueba():
    return (ESTATICOS / "prueba.html").read_text(encoding="utf-8")


@app.get("/api/producto/{variante}")
def producto(variante: str):
    if not variante.isdigit() and not config.MODO_PRUEBA:
        return JSONResponse({"error": "Producto no válido"}, status_code=400)
    try:
        v = shopify.leer_variante(variante)
    except shopify.ErrorShopify as e:
        log.warning("No se pudo leer la variante %s: %s", variante, e)
        return JSONResponse({"error": "No pudimos cargar el producto"}, status_code=502)
    ofertas = reglas.calcular_ofertas(
        reglas.config_de_producto(almacen.leer(), v.get("producto_id", ""), v.get("direccion", "")), v["precio"])
    return {
        "titulo": v["titulo"], "variante": v["variante"], "disponible": v["disponible"], "moneda": v["moneda"],
        "ofertas": [{"cantidad": o["cantidad"], "precio": _numero(o["precio"]), "antes": _numero(o["antes"]),
                     "etiqueta": o["etiqueta"], "color": o["color"], "titulo": o["titulo"], "subtitulo": o["subtitulo"],
                     "imagen": o["imagen"], "preseleccionada": o["preseleccionada"]} for o in ofertas],
        "estados": reglas.ESTADOS,
        # Oficinas para el formulario: número (DroPanas), estado, ciudad, nombre para el cliente, dirección y horario.
        "oficinas": [{"id": o["id"], "e": o["estado"], "c": o["ciudad"], "n": o["nombre"], "d": o["direccion"], "h": o["horario"]}
                     for o in reglas.OFICINAS],
        "tipos_cedula": reglas.TIPOS_CEDULA,
        "ciudades": reglas.CIUDADES,
        "domicilio": reglas.ENTREGA_DOMICILIO,
        "whatsapp": reglas.WHATSAPP_CONFIRMACION,
        "ocultar_carrito": reglas.OCULTAR_CARRITO_TEMA,
        "pixel": meta.para_navegador(),
        "producto_id": v.get("producto_id", ""),
        "modo_prueba": config.MODO_PRUEBA,
    }


@app.post("/api/pedido")
async def pedido(request: Request):
    try:
        cuerpo = await request.json()
        assert isinstance(cuerpo, dict)
    except Exception:
        return JSONResponse({"error": "Datos no válidos"}, status_code=400)

    variante = str(cuerpo.get("variante", ""))
    if not variante.isdigit() and not config.MODO_PRUEBA:
        return JSONResponse({"error": "Producto no válido"}, status_code=400)

    datos, errores = reglas.validar_datos(cuerpo)
    if errores:
        return JSONResponse({"errores": errores}, status_code=422)

    ip = ip_de(request)
    ahora = time.time()
    # Es "el mismo pedido" solo si TODO coincide; si el cliente cambió algo (oficina, cantidad…), es un pedido nuevo.
    entrega = datos["direccion"] if datos["domicilio"] else str((datos["oficina"] or {}).get("id"))
    clave = (datos["telefono"], variante, entrega, str(cuerpo.get("oferta", 0)), datos["cedula"])
    with _candado:
        previo = _recientes.get(clave)
        if previo and ahora - previo[0] < MINUTOS_REPETIDO * 60:
            return {"ok": True, "repetido": True, **previo[1]}
        horas = [h for h in _intentos.get(ip, []) if ahora - h < MINUTOS_VENTANA_IP * 60]
        if len(horas) >= MAX_PEDIDOS_POR_IP:
            return JSONResponse({"error": "Recibimos demasiados pedidos seguidos. Espera unos minutos o escríbenos por WhatsApp."},
                                status_code=429)

    try:
        v = shopify.leer_variante(variante)
        if not v["disponible"]:
            return JSONResponse({"error": "Este producto está agotado por ahora."}, status_code=409)
        ofertas = reglas.calcular_ofertas(
            reglas.config_de_producto(almacen.leer(), v.get("producto_id", ""), v.get("direccion", "")), v["precio"])
        try:
            oferta = ofertas[int(cuerpo.get("oferta", 0))]
        except (ValueError, IndexError, TypeError):
            oferta = ofertas[0]
        utm = cuerpo.get("utm") if isinstance(cuerpo.get("utm"), dict) else {}
        orden = reglas.armar_pedido(datos, variante, oferta, v["moneda"], ip, utm)
        cliente_id = shopify.buscar_o_crear_cliente(datos["nombre"], datos["apellido"], datos["telefono"])
        if cliente_id:
            orden["customer"] = {"toAssociate": {"id": cliente_id}}
        resultado = shopify.crear_pedido(orden)
    except shopify.ErrorShopify as e:
        log.error("Pedido NO creado (variante %s): %s", variante, e)
        return JSONResponse({"error": "No pudimos registrar tu pedido. Intenta de nuevo en un momento o escríbenos por WhatsApp."},
                            status_code=502)

    # Resumen de lo que SE GUARDÓ en Shopify: la pantalla de confirmación muestra esto, no lo que dice el formulario.
    resumen = {"numero": resultado["numero"], "total": _numero(oferta["precio"]), "moneda": v["moneda"],
               "producto": v["titulo"], "cantidad": oferta["cantidad"], "domicilio": datos["domicilio"],
               "entrega": datos["direccion"] if datos["domicilio"] else datos["oficina"]["nombre"],
               "cedula": datos["cedula"], "telefono": reglas.telefono_local(datos["telefono"])}
    with _candado:
        _recientes[clave] = (ahora, resumen)
        _intentos[ip] = horas + [ahora]
        for k in [k for k, (h, _r) in _recientes.items() if ahora - h > MINUTOS_REPETIDO * 60]:
            del _recientes[k]
    log.info("Pedido %s creado: %s x%s", resultado["numero"], v["titulo"], oferta["cantidad"])
    if not config.MODO_PRUEBA:
        nav = cuerpo.get("navegador") if isinstance(cuerpo.get("navegador"), dict) else {}
        nav = {k: str(nav.get(k) or "")[:500] for k in ("fbp", "fbc", "url")}
        nav["agente"] = request.headers.get("user-agent", "")[:500]
        meta.compra_en_segundo_plano(resultado["numero"], datos, v, oferta, nav, ip)
    if sheets.activo() and not config.MODO_PRUEBA:
        sheets.enviar_en_segundo_plano(resultado["numero"], datos, v["titulo"], oferta, utm)
    return {"ok": True, **resumen}


if __name__ == "__main__":
    import uvicorn
    print(f"Formulario encendido en http://{config.HOST}:{config.PUERTO}/prueba"
          f"  (modo prueba: {'SÍ, no crea pedidos reales' if config.MODO_PRUEBA else 'NO, crea pedidos reales'})")
    uvicorn.run(app, host=config.HOST, port=config.PUERTO)
