"""Conexión con Shopify: leer el producto y crear el pedido. Solo usa lo necesario para estas dos cosas."""
import logging
import time
from decimal import Decimal

import httpx

import config

log = logging.getLogger("cod")


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


PRODUCTO_PRUEBA = {"titulo": "AO Black Maca", "producto_id": "prueba", "direccion": "ao-black-maca-potencia-brutal", "variante": "", "precio": Decimal("32450.00"),
                   "disponible": True, "moneda": "VES"}


def hay_llaves() -> bool:
    return bool(config.SHOPIFY_TIENDA and (config.SHOPIFY_TOKEN or (config.SHOPIFY_CLIENT_ID and config.SHOPIFY_CLIENT_SECRET)))


def permisos(cliente=None) -> set[str]:
    """Permisos que la tienda le dio a la app (ej. write_orders, read_customers)."""
    datos = _consulta("{ currentAppInstallation { accessScopes { handle } } }", {}, cliente)
    return {a["handle"] for a in datos["currentAppInstallation"]["accessScopes"]}


def listar_productos(cliente=None) -> list[dict]:
    """Productos de la tienda para el menú de Ofertas: número, nombre, dirección, precio, estado y fotos."""
    productos, despues = [], None
    for _ in range(10):  # hasta 1.000 productos
        datos = _consulta("""
            query($after: String) {
              products(first: 100, after: $after, sortKey: TITLE) {
                pageInfo { hasNextPage endCursor }
                nodes {
                  id title handle status
                  featuredMedia { preview { image { url } } }
                  media(first: 12) { nodes { preview { image { url } } } }
                  variants(first: 1) { nodes { id price } }
                }
              }
            }""", {"after": despues}, cliente)["products"]
        for p in datos["nodes"]:
            fotos = [m["preview"]["image"]["url"] for m in p["media"]["nodes"]
                     if m.get("preview") and m["preview"].get("image")]
            variante = (p["variants"]["nodes"] or [{}])[0]
            productos.append({
                "id": p["id"].rsplit("/", 1)[-1], "titulo": p["title"], "direccion": p["handle"], "estado": p["status"],
                "precio": str(variante.get("price", "0")), "variante": (variante.get("id") or "").rsplit("/", 1)[-1],
                "foto": ((p.get("featuredMedia") or {}).get("preview") or {}).get("image", {}).get("url", ""),
                "fotos": fotos,
            })
        if not datos["pageInfo"]["hasNextPage"]:
            break
        despues = datos["pageInfo"]["endCursor"]
    return productos


# Datos propios de la app (ej. las ofertas), guardados en Shopify como "metacampo" de la instalación de la app.
# No necesitan permisos extra y no se ven en la tienda.
ESPACIO_APP = "rebajitas"


def leer_dato_app(clave: str, cliente=None) -> str | None:
    datos = _consulta("""
        query($k: String!) { currentAppInstallation { metafield(namespace: "%s", key: $k) { value } } }""" % ESPACIO_APP,
        {"k": clave}, cliente)
    campo = datos["currentAppInstallation"]["metafield"]
    return campo["value"] if campo else None


def guardar_dato_app(clave: str, valor_json: str, cliente=None) -> None:
    dueno = _consulta("{ currentAppInstallation { id } }", {}, cliente)["currentAppInstallation"]["id"]
    datos = _consulta("""
        mutation($m: [MetafieldsSetInput!]!) { metafieldsSet(metafields: $m) { userErrors { field message } } }""",
        {"m": [{"ownerId": dueno, "namespace": ESPACIO_APP, "key": clave, "type": "json", "value": valor_json}]}, cliente)
    errores = datos["metafieldsSet"]["userErrors"]
    if errores:
        raise ErrorShopify("Shopify no guardó los datos: " + "; ".join(e["message"] for e in errores))


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
          productVariant(id: $id) { title price availableForSale product { id title handle } }
          shop { currencyCode }
        }""", {"id": f"gid://shopify/ProductVariant/{variante_id}"}, cliente)
    v = datos.get("productVariant")
    if not v:
        raise ErrorShopify("Ese producto no existe en la tienda")
    return {
        "titulo": v["product"]["title"],
        "producto_id": v["product"]["id"].rsplit("/", 1)[-1],
        "direccion": v["product"].get("handle", ""),
        "variante": "" if v["title"] == "Default Title" else v["title"],
        "precio": Decimal(str(v["price"])),
        "disponible": v["availableForSale"],
        "moneda": datos["shop"]["currencyCode"],
    }


def buscar_o_crear_cliente(nombre: str, apellido: str, telefono: str, cliente=None) -> str | None:
    """Devuelve el ID del cliente en Shopify con ese teléfono (lo crea si no existe), para enlazarlo al pedido.
    Necesita los permisos read_customers y write_customers. Si algo falla, devuelve None y el pedido
    se crea igual, sin cliente (nunca se pierde una venta por esto)."""
    if config.MODO_PRUEBA:
        return None
    try:
        encontrado = _consulta("""
            query($q: String!) { customers(first: 1, query: $q) { nodes { id } } }""",
            {"q": f"phone:{telefono}"}, cliente)["customers"]["nodes"]
        if encontrado:
            return encontrado[0]["id"]
        creado = _consulta("""
            mutation($input: CustomerInput!) {
              customerCreate(input: $input) { customer { id } userErrors { field message } }
            }""", {"input": {"firstName": nombre, "lastName": apellido, "phone": telefono}}, cliente)["customerCreate"]
        if creado["customer"]:
            return creado["customer"]["id"]
        log.warning("Cliente no creado (%s): %s", telefono[-4:], "; ".join(e["message"] for e in creado["userErrors"]))
    except (ErrorShopify, KeyError, TypeError) as e:
        log.warning("No se pudo buscar/crear el cliente; el pedido sale sin cliente: %s", e)
    return None


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
