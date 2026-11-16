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
    """Pestaña del mes, ej. "Tealca COD Noviembre" (el patrón se cambia con SHEETS_HOJA)."""
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
        "cedula": datos.get("cedula") or "",
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


def verificar(cliente=None) -> tuple[bool, str]:
    """Revisa la conexión con la hoja SIN escribir nada. Devuelve (todo bien, explicación en palabras simples)."""
    if not activo():
        return False, "sin configurar (faltan SHEETS_URL o SHEETS_CLAVE en Render)"
    hoja = nombre_hoja(datetime.now(HORA_VENEZUELA))
    propio = cliente is None
    cliente = cliente or httpx.Client(timeout=30, follow_redirects=True)
    try:
        r = cliente.post(config.SHEETS_URL, json={"clave": config.SHEETS_CLAVE, "hoja": hoja, "prueba": True})
        texto = r.text[:3000]
    except httpx.HTTPError as e:
        return False, f"Google no respondió ({type(e).__name__}). Revisa que SHEETS_URL sea la dirección que termina en /exec"
    finally:
        if propio:
            cliente.close()
    try:
        j = r.json()
    except ValueError:
        if "accounts.google.com" in texto or "ServiceLogin" in texto or "Iniciar sesión" in texto or "Sign in" in texto:
            return False, ("Google pide iniciar sesión: en Apps Script → Implementar → Gestionar implementaciones, "
                           "'Quién tiene acceso' debe ser 'Cualquier persona'")
        import html
        import re
        titulo = re.search(r"<title>(.*?)</title>", texto, re.S | re.I)
        mensaje = re.search(r"(?:TypeError|ReferenceError|Exception)[^<]{0,160}", texto)
        detalle = html.unescape((mensaje.group(0) if mensaje else titulo.group(1) if titulo else "").strip())[:160]
        return False, ("SHEETS_URL no llega al código de la hoja: copia la URL de la implementación ACTIVA "
                       "(Implementar → Gestionar implementaciones) y pégala en Render"
                       + (f" (Google responde: «{detalle}», código {r.status_code})" if detalle else f" (código {r.status_code})"))
    if j.get("ok") and j.get("existe", True):
        return True, f"conectado (pestaña de este mes: «{hoja}»)"
    if j.get("ok"):
        return False, f"conectado, pero NO existe la pestaña «{hoja}» (los pedidos irían a 'Pedidos sin pestaña')"
    if j.get("error") == "clave incorrecta":
        return False, "la clave no coincide: SHEETS_CLAVE en Render debe ser igual a CLAVE en el código de la hoja"
    return False, f"la hoja respondió con error: {j.get('error', 'desconocido')}"


def enviar_en_segundo_plano(*args):
    """Para no hacer esperar al cliente mientras se escribe en la hoja."""
    threading.Thread(target=enviar, args=args, daemon=True).start()
