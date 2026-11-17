"""Píxel de Meta (Facebook): configuración y envío de eventos por la API de conversiones (servidor).
El navegador manda InitiateCheckout y Purchase con el píxel; el servidor manda el mismo Purchase por la API
de conversiones con el mismo event_id, y Meta los cuenta una sola vez. El token nunca sale del servidor."""
import hashlib
import logging
import re
import threading
import time

import httpx

import almacen
import config

log = logging.getLogger("cod")
VERSION_GRAPH = "v21.0"
MONEDAS = ("VES", "USD", "COP", "EUR")


def _limpiar_ids(texto) -> list[str]:
    ids = re.findall(r"\d{10,20}", " ".join(texto) if isinstance(texto, list) else str(texto or ""))
    return list(dict.fromkeys(ids))[:5]


def configuracion() -> dict:
    """Configuración del píxel con valores por defecto."""
    p = (almacen.leer_integraciones() or {}).get("pixel") or {}
    return {
        "activo": bool(p.get("activo")) and bool(_limpiar_ids(p.get("ids"))),
        "ids": _limpiar_ids(p.get("ids")),
        "token": p.get("token") or "",
        "codigo_prueba": p.get("codigo_prueba") or "",
        "moneda": p.get("moneda") if p.get("moneda") in MONEDAS else "VES",
        "iniciar_compra": p.get("iniciar_compra", True) is not False,
    }


def para_navegador() -> dict:
    """Lo que el formulario necesita saber (sin el token)."""
    c = configuracion()
    if not c["activo"]:
        return {"activo": False}
    return {"activo": True, "ids": c["ids"], "moneda": c["moneda"], "iniciar_compra": c["iniciar_compra"]}


def para_panel() -> dict:
    """Lo que ve el menú: el token solo con sus últimas 4 letras."""
    c = configuracion()
    p = (almacen.leer_integraciones(forzar=True) or {}).get("pixel") or {}
    return {"activo": bool(p.get("activo")), "ids": "\n".join(_limpiar_ids(p.get("ids"))), "moneda": c["moneda"],
            "iniciar_compra": c["iniciar_compra"], "codigo_prueba": c["codigo_prueba"],
            "token_guardado": ("•••• " + c["token"][-4:]) if c["token"] else ""}


def guardar(cuerpo: dict) -> tuple[dict, list[str]]:
    errores = []
    ids = _limpiar_ids(cuerpo.get("ids"))
    if cuerpo.get("activo") and not ids:
        errores.append("Escribe el ID del píxel (solo números, de 10 a 20 dígitos)")
    moneda = cuerpo.get("moneda") if cuerpo.get("moneda") in MONEDAS else "VES"
    datos = dict(almacen.leer_integraciones(forzar=True) or {})
    anterior = datos.get("pixel") or {}
    token = anterior.get("token", "")
    if cuerpo.get("borrar_token"):
        token = ""
    elif str(cuerpo.get("token") or "").strip():
        token = str(cuerpo["token"]).strip()
        if not re.fullmatch(r"[A-Za-z0-9_\-|]{20,400}", token):
            errores.append("El token de la API de conversiones no parece válido")
    if errores:
        return {}, errores
    datos["pixel"] = {"activo": bool(cuerpo.get("activo")), "ids": ids, "token": token, "moneda": moneda,
                      "codigo_prueba": re.sub(r"[^A-Za-z0-9]", "", str(cuerpo.get("codigo_prueba") or ""))[:20],
                      "iniciar_compra": bool(cuerpo.get("iniciar_compra", True))}
    almacen.guardar_integraciones(datos)
    return para_panel(), []


def _h(valor: str) -> str:
    return hashlib.sha256(valor.strip().lower().encode()).hexdigest()


def evento_compra(numero: str, datos: dict, producto: dict, oferta: dict, navegador: dict, ip: str, prueba: bool = False) -> dict:
    """Arma el evento Purchase para la API de conversiones (datos personales cifrados con SHA-256, como pide Meta)."""
    c = configuracion()
    telefono = re.sub(r"\D", "", datos.get("telefono") or "")
    usuario = {"ph": [_h(telefono)], "fn": [_h(datos.get("nombre", ""))], "ln": [_h(datos.get("apellido", ""))],
               "ct": [_h(re.sub(r"\s", "", datos.get("ciudad", "")))], "country": [_h("ve")],
               "external_id": [_h(telefono)], "client_ip_address": ip or None,
               "client_user_agent": navegador.get("agente") or None,
               "fbp": navegador.get("fbp") or None, "fbc": navegador.get("fbc") or None}
    return {
        "event_name": "Purchase", "event_time": int(time.time()), "event_id": "rcod-" + numero.lstrip("#"),
        "action_source": "website", "event_source_url": navegador.get("url") or None,
        "user_data": {k: v for k, v in usuario.items() if v},
        "custom_data": {"currency": c["moneda"], "value": float(oferta["precio"]), "order_id": numero,
                        "content_type": "product", "content_ids": [str(producto.get("producto_id") or "")],
                        "content_name": producto.get("titulo"), "num_items": oferta["cantidad"],
                        "contents": [{"id": str(producto.get("producto_id") or ""), "quantity": oferta["cantidad"]}]},
    }


def enviar(eventos: list[dict], codigo_prueba: str = "", cliente=None) -> tuple[bool, str]:
    """Manda eventos a cada píxel configurado. Devuelve (todo bien, explicación)."""
    c = configuracion()
    if not (c["activo"] and c["token"]):
        return False, "Falta activar el píxel o el token de la API de conversiones"
    propio = cliente is None
    cliente = cliente or httpx.Client(timeout=20)
    try:
        for pid in c["ids"]:
            cuerpo = {"data": eventos, "access_token": c["token"]}
            if codigo_prueba or c["codigo_prueba"]:
                cuerpo["test_event_code"] = codigo_prueba or c["codigo_prueba"]
            r = cliente.post(f"https://graph.facebook.com/{VERSION_GRAPH}/{pid}/events", json=cuerpo)
            if r.status_code != 200:
                try:
                    msg = r.json().get("error", {}).get("message", "")
                except ValueError:
                    msg = ""
                return False, f"Meta rechazó el evento del píxel {pid}: {msg or r.status_code}"
        return True, "Meta recibió el evento"
    except httpx.HTTPError as e:
        return False, f"No se pudo conectar con Meta ({type(e).__name__})"
    finally:
        if propio:
            cliente.close()


def compra_en_segundo_plano(numero, datos, producto, oferta, navegador, ip):
    def tarea():
        ok, msg = enviar([evento_compra(numero, datos, producto, oferta, navegador, ip)])
        (log.info if ok else log.warning)("Meta (API de conversiones) pedido %s: %s", numero, msg)
    if configuracion()["token"]:
        threading.Thread(target=tarea, daemon=True).start()
