"""Revisa que quien usa el menú de la app sea alguien con sesión abierta en el panel de Shopify de la tienda.
Shopify entrega un "token de sesión" (JWT firmado con el secreto de la app); aquí se comprueba la firma,
la fecha, que sea para esta app y para esta tienda."""
import base64
import hashlib
import hmac
import json
import time

import config


class SesionInvalida(Exception):
    pass


def _b64(parte: str) -> bytes:
    return base64.urlsafe_b64decode(parte + "=" * (-len(parte) % 4))


def verificar(token: str, ahora: float | None = None) -> dict:
    if not token or token.count(".") != 2:
        raise SesionInvalida("Falta la sesión de Shopify")
    if not (config.SHOPIFY_CLIENT_SECRET and config.SHOPIFY_CLIENT_ID):
        raise SesionInvalida("Faltan las llaves de la app en Render")
    cabeza, cuerpo, firma = token.split(".")
    try:
        if json.loads(_b64(cabeza)).get("alg") != "HS256":
            raise SesionInvalida("Sesión con firma desconocida")
        esperada = hmac.new(config.SHOPIFY_CLIENT_SECRET.encode(), f"{cabeza}.{cuerpo}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(esperada, _b64(firma)):
            raise SesionInvalida("La firma de la sesión no es válida")
        datos = json.loads(_b64(cuerpo))
    except (ValueError, TypeError) as e:
        raise SesionInvalida("Sesión mal formada") from e
    ahora = time.time() if ahora is None else ahora
    if datos.get("exp", 0) < ahora - 5 or datos.get("nbf", 0) > ahora + 5:
        raise SesionInvalida("La sesión venció: recarga la página")
    if datos.get("aud") != config.SHOPIFY_CLIENT_ID:
        raise SesionInvalida("La sesión es de otra app")
    tienda = str(datos.get("dest", "")).removeprefix("https://").rstrip("/")
    if tienda != config.SHOPIFY_TIENDA:
        raise SesionInvalida("La sesión es de otra tienda")
    return datos
