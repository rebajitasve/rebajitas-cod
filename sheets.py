"""Envía cada pedido nuevo a la hoja de Google Sheets (a través del código de integraciones/google_sheets.gs)."""
import logging
import threading
from datetime import datetime, timedelta, timezone

import httpx

import config

log = logging.getLogger("cod")

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]
HORA_VENEZUELA = timezone(timedelta(hours=-4))


def activo() -> bool:
    return bool(config.SHEETS_URL and config.SHEETS_CLAVE)


def nombre_hoja(ahora: datetime) -> str:
    """Pestaña del mes, ej. "Tealca Noviembre COD" (el patrón se cambia con SHEETS_HOJA)."""
    return config.SHEETS_HOJA.replace("{mes}", MESES[ahora.month - 1])


def armar_fila(datos: dict, producto: str, oferta: dict, utm: dict, ahora: datetime) -> dict:
    """Mismas columnas que llenaba Releasit."""
    utm = utm or {}
    return {
        "fecha": f"{ahora:%Y-%m-%d} {ahora.hour}:{ahora:%M:%S}",
        "nombre": f"{datos['nombre']} {datos['apellido']}",
        "telefono": datos["telefono"],
        "estado": datos["estado"].upper(),
        "oficina": f"DOMICILIO: {datos['direccion']}" if datos.get("domicilio") else datos["oficina"],
        "producto": producto,
        "cantidad": oferta["cantidad"],
        "valor": float(oferta["precio"]),
        "utm_source": str(utm.get("utm_source") or "")[:150],
        "utm_campaign": str(utm.get("utm_campaign") or "")[:150],
        "utm_medium": str(utm.get("utm_medium") or "")[:150],
        "utm_content": str(utm.get("utm_content") or "")[:150],
    }


def enviar(numero: str, datos: dict, producto: str, oferta: dict, utm: dict, cliente=None) -> bool:
    """Escribe la fila. Reintenta 3 veces. Nunca lanza error: el pedido ya está creado en Shopify."""
    ahora = datetime.now(HORA_VENEZUELA)
    cuerpo = {"clave": config.SHEETS_CLAVE, "hoja": nombre_hoja(ahora),
              "fila": armar_fila(datos, producto, oferta, utm, ahora)}
    propio = cliente is None
    cliente = cliente or httpx.Client(timeout=30, follow_redirects=True)
    try:
        for intento in range(3):
            try:
                r = cliente.post(config.SHEETS_URL, json=cuerpo)
                respuesta = r.json() if r.status_code == 200 else {}
                if respuesta.get("ok"):
                    if respuesta.get("aviso"):
                        log.warning("Sheets: pedido %s guardado en '%s' (%s)", numero, respuesta.get("hoja"), respuesta["aviso"])
                    else:
                        log.info("Sheets: pedido %s agregado a '%s'", numero, respuesta.get("hoja"))
                    return True
                log.warning("Sheets: intento %s del pedido %s falló (%s %s)", intento + 1, numero, r.status_code,
                            respuesta.get("error", "respuesta inesperada"))
            except (httpx.HTTPError, ValueError) as e:
                log.warning("Sheets: intento %s del pedido %s falló (%s)", intento + 1, numero, e)
        log.error("Sheets: el pedido %s NO se pudo agregar a la hoja; hay que anotarlo a mano", numero)
        return False
    finally:
        if propio:
            cliente.close()


def enviar_en_segundo_plano(*args):
    """Para no hacer esperar al cliente mientras se escribe en la hoja."""
    threading.Thread(target=enviar, args=args, daemon=True).start()
