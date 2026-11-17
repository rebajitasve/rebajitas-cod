"""Dónde se guardan las ofertas que se crean en el menú de la app.
- En la tienda (Render): dentro de Shopify, como dato propio de la app (no cuesta nada ni necesita base de datos).
- En el computador, sin llaves de Shopify: en el archivo datos_locales/ofertas.json (para probar).
Se guarda una copia en memoria para no preguntarle a Shopify en cada visita."""
import json
import logging
import threading
import time

import config
import reglas
import shopify

log = logging.getLogger("cod")
ARCHIVO_LOCAL = config.CARPETA / "datos_locales" / "ofertas.json"
CLAVE = "ofertas"
SEGUNDOS_MEMORIA = 60

_candado = threading.Lock()
_memoria = {"datos": None, "hora": 0.0}


def _usa_shopify() -> bool:
    return shopify.hay_llaves()


def _iniciales() -> dict:
    return {"version": 1, "productos": json.loads(json.dumps(reglas.OFERTAS_INICIALES))}


def leer(forzar: bool = False) -> dict:
    with _candado:
        if not forzar and _memoria["datos"] is not None and time.time() - _memoria["hora"] < SEGUNDOS_MEMORIA:
            return _memoria["datos"]
    try:
        if _usa_shopify():
            texto = shopify.leer_dato_app(CLAVE)
        else:
            texto = ARCHIVO_LOCAL.read_text(encoding="utf-8") if ARCHIVO_LOCAL.exists() else None
        datos = json.loads(texto) if texto else _iniciales()
    except (shopify.ErrorShopify, ValueError, OSError) as e:
        log.warning("No se pudieron leer las ofertas guardadas (%s); se usan las últimas conocidas", e)
        with _candado:
            return _memoria["datos"] or _iniciales()
    with _candado:
        _memoria.update(datos=datos, hora=time.time())
    return datos


def guardar_producto(producto_id: str, direccion: str, cfg: dict) -> dict:
    """Guarda la configuración de un producto (ya revisada con reglas.normalizar_config_producto)."""
    datos = json.loads(json.dumps(leer(forzar=True)))
    productos = datos.setdefault("productos", {})
    productos.pop(direccion, None)  # si había una configuración antigua por dirección, pasa a usar el número
    productos[str(producto_id)] = cfg
    texto = json.dumps(datos, ensure_ascii=False)
    if _usa_shopify():
        shopify.guardar_dato_app(CLAVE, texto)
    else:
        ARCHIVO_LOCAL.parent.mkdir(exist_ok=True)
        ARCHIVO_LOCAL.write_text(texto, encoding="utf-8")
    with _candado:
        _memoria.update(datos=datos, hora=time.time())
    return datos
