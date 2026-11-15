"""Servidor del formulario: entrega el formulario a la tienda y crea los pedidos en Shopify."""
import logging
import threading
import time
from decimal import Decimal

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

import config
import reglas
import shopify

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("cod")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware, allow_origins=config.TIENDA_ORIGENES,
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

ESTATICOS = config.CARPETA / "estaticos"

# Protecciones simples en memoria: pedidos repetidos y demasiados intentos desde la misma conexión.
_candado = threading.Lock()
_recientes: dict[tuple, tuple[float, str]] = {}   # (teléfono, variante) -> (hora, número de pedido)
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


@app.get("/salud")
def salud():
    return {"ok": True, "modo_prueba": config.MODO_PRUEBA}


@app.get("/formulario.js")
def formulario_js():
    return FileResponse(ESTATICOS / "formulario.js", media_type="application/javascript",
                        headers={"Cache-Control": "public, max-age=300"})


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
    ofertas = reglas.ofertas_de(variante, v["precio"])
    return {
        "titulo": v["titulo"], "variante": v["variante"], "disponible": v["disponible"], "moneda": v["moneda"],
        "ofertas": [{"cantidad": o["cantidad"], "precio": _numero(o["precio"]), "antes": _numero(o["antes"]),
                     "etiqueta": o["etiqueta"]} for o in ofertas],
        "estados": reglas.ESTADOS,
        "oficinas": reglas.OFICINAS_TEALCA,
        "whatsapp": reglas.WHATSAPP_CONFIRMACION,
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
    clave = (datos["telefono"], variante)
    with _candado:
        previo = _recientes.get(clave)
        if previo and ahora - previo[0] < MINUTOS_REPETIDO * 60:
            return {"ok": True, "numero": previo[1], "repetido": True}
        horas = [h for h in _intentos.get(ip, []) if ahora - h < MINUTOS_VENTANA_IP * 60]
        if len(horas) >= MAX_PEDIDOS_POR_IP:
            return JSONResponse({"error": "Recibimos demasiados pedidos seguidos. Espera unos minutos o escríbenos por WhatsApp."},
                                status_code=429)

    try:
        v = shopify.leer_variante(variante)
        if not v["disponible"]:
            return JSONResponse({"error": "Este producto está agotado por ahora."}, status_code=409)
        ofertas = reglas.ofertas_de(variante, v["precio"])
        try:
            oferta = ofertas[int(cuerpo.get("oferta", 0))]
        except (ValueError, IndexError, TypeError):
            oferta = ofertas[0]
        resultado = shopify.crear_pedido(reglas.armar_pedido(datos, variante, oferta, v["moneda"], ip))
    except shopify.ErrorShopify as e:
        log.error("Pedido NO creado (variante %s): %s", variante, e)
        return JSONResponse({"error": "No pudimos registrar tu pedido. Intenta de nuevo en un momento o escríbenos por WhatsApp."},
                            status_code=502)

    with _candado:
        _recientes[clave] = (ahora, resultado["numero"])
        _intentos[ip] = horas + [ahora]
        for k in [k for k, (h, _) in _recientes.items() if ahora - h > MINUTOS_REPETIDO * 60]:
            del _recientes[k]
    log.info("Pedido %s creado: %s x%s", resultado["numero"], v["titulo"], oferta["cantidad"])
    return {"ok": True, "numero": resultado["numero"], "total": _numero(oferta["precio"]), "moneda": v["moneda"]}


if __name__ == "__main__":
    import uvicorn
    print(f"Formulario encendido en http://{config.HOST}:{config.PUERTO}/prueba"
          f"  (modo prueba: {'SÍ, no crea pedidos reales' if config.MODO_PRUEBA else 'NO, crea pedidos reales'})")
    uvicorn.run(app, host=config.HOST, port=config.PUERTO)
