"""Conexión con Shopify: leer el producto y crear el pedido. Solo usa lo necesario para estas dos cosas."""
import time
from decimal import Decimal

import httpx

import config


class ErrorShopify(Exception):
    pass


_token = {"valor": None, "vence": 0.0}


def _obtener_token(cliente: httpx.Client) -> str:
    """Usa el token fijo si existe; si no, pide uno temporal con el ID y secreto de la app (dura ~24 h)."""
    if config.SHOPIFY_TOKEN:
        return config.SHOPIFY_TOKEN
    if _token["valor"] and time.time() < _token["vence"]:
        return _token["valor"]
    if not (config.SHOPIFY_CLIENT_ID and config.SHOPIFY_CLIENT_SECRET):
        raise ErrorShopify("Faltan las llaves de Shopify en la configuración")
    r = cliente.post(f"https://{config.SHOPIFY_TIENDA}/admin/oauth/access_token", data={
        "grant_type": "client_credentials",
        "client_id": config.SHOPIFY_CLIENT_ID,
        "client_secret": config.SHOPIFY_CLIENT_SECRET,
    })
    if r.status_code != 200:
        raise ErrorShopify(f"Shopify no entregó el permiso de acceso (código {r.status_code})")
    datos = r.json()
    _token["valor"] = datos["access_token"]
    _token["vence"] = time.time() + int(datos.get("expires_in", 3600)) - 300
    return _token["valor"]


def _consulta(consulta: str, variables: dict, cliente: httpx.Client | None = None) -> dict:
    propio = cliente is None
    cliente = cliente or httpx.Client(timeout=20)
    try:
        token = _obtener_token(cliente)
        r = cliente.post(
            f"https://{config.SHOPIFY_TIENDA}/admin/api/{config.SHOPIFY_VERSION_API}/graphql.json",
            json={"query": consulta, "variables": variables},
            headers={"X-Shopify-Access-Token": token},
        )
        if r.status_code != 200:
            raise ErrorShopify(f"Shopify respondió con código {r.status_code}")
        respuesta = r.json()
        if respuesta.get("errors"):
            raise ErrorShopify(f"Shopify rechazó la consulta: {respuesta['errors']}")
        return respuesta["data"]
    except httpx.HTTPError as e:
        raise ErrorShopify(f"No se pudo hablar con Shopify: {e}") from e
    finally:
        if propio:
            cliente.close()


PRODUCTO_PRUEBA = {"titulo": "AO Black Maca", "direccion": "ao-black-maca-potencia-brutal", "variante": "", "precio": Decimal("32450.00"),
                   "disponible": True, "moneda": "VES"}


def hay_llaves() -> bool:
    return bool(config.SHOPIFY_TIENDA and (config.SHOPIFY_TOKEN or (config.SHOPIFY_CLIENT_ID and config.SHOPIFY_CLIENT_SECRET)))


def probar_conexion(cliente=None) -> str:
    """Lee solo el nombre de la tienda, para confirmar que las llaves funcionan."""
    return _consulta("{ shop { name } }", {}, cliente)["shop"]["name"]


def leer_variante(variante_id: str, cliente=None) -> dict:
    """Nombre, precio y disponibilidad de una variante, más la moneda de la tienda.
    En modo prueba se lee el producto real si hay llaves (leer no cambia nada en la tienda);
    sin llaves, o en la página de prueba, se usa un producto de ejemplo."""
    if config.MODO_PRUEBA and (not str(variante_id).isdigit() or not hay_llaves()):
        return dict(PRODUCTO_PRUEBA)
    datos = _consulta("""
        query($id: ID!) {
          productVariant(id: $id) { title price availableForSale product { title handle } }
          shop { currencyCode }
        }""", {"id": f"gid://shopify/ProductVariant/{variante_id}"}, cliente)
    v = datos.get("productVariant")
    if not v:
        raise ErrorShopify("Ese producto no existe en la tienda")
    return {
        "titulo": v["product"]["title"],
        "direccion": v["product"].get("handle", ""),
        "variante": "" if v["title"] == "Default Title" else v["title"],
        "precio": Decimal(str(v["price"])),
        "disponible": v["availableForSale"],
        "moneda": datos["shop"]["currencyCode"],
    }


def crear_pedido(pedido: dict, cliente=None) -> dict:
    """Crea el pedido en Shopify. Devuelve su número (ej. #1234)."""
    if config.MODO_PRUEBA:
        return {"numero": f"#PRUEBA-{int(time.time()) % 100000}", "id": None}
    datos = _consulta("""
        mutation($order: OrderCreateOrderInput!, $options: OrderCreateOptionsInput) {
          orderCreate(order: $order, options: $options) {
            order { id name }
            userErrors { field message }
          }
        }""", {"order": pedido, "options": {
            "inventoryBehaviour": "DECREMENT_OBEYING_POLICY",
            "sendReceipt": False,
            "sendFulfillmentReceipt": False,
        }}, cliente)
    resultado = datos["orderCreate"]
    if resultado["userErrors"]:
        raise ErrorShopify("Shopify no aceptó el pedido: " + "; ".join(e["message"] for e in resultado["userErrors"]))
    return {"numero": resultado["order"]["name"], "id": resultado["order"]["id"]}
