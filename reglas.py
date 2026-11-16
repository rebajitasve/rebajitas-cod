"""Reglas de negocio del formulario. Todo lo que decide precios, validaciones y cómo se arma el pedido vive aquí."""
import json
import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ESTADOS = [
    "Amazonas", "Anzoátegui", "Apure", "Aragua", "Barinas", "Bolívar", "Carabobo", "Cojedes",
    "Delta Amacuro", "Distrito Capital", "Falcón", "Guárico", "La Guaira", "Lara", "Mérida",
    "Miranda", "Monagas", "Nueva Esparta", "Portuguesa", "Sucre", "Táchira", "Trujillo",
    "Yaracuy", "Zulia",
]

# Oficinas TEALCA por estado, desde oficinas_tealca.json (lista de Mike, nov. 2026).
# Si un estado no tiene oficinas en la lista, el cliente escribe la oficina a mano.
with open(Path(__file__).parent / "oficinas_tealca.json", encoding="utf-8") as _f:
    OFICINAS_TEALCA: dict[str, list[str]] = json.load(_f)

# Ciudades por estado, desde ciudades_ve.json (ver su campo "fuente"). El cliente elige de la lista
# o marca "Otra ciudad" y la escribe, así que el servidor acepta cualquier ciudad escrita.
with open(Path(__file__).parent / "ciudades_ve.json", encoding="utf-8") as _f:
    CIUDADES: dict[str, list[str]] = json.load(_f)["ciudades"]

# Código de cada estado en Shopify (ISO 3166-2:VE). Releasit lo usa así: "LECHERÍA - B" = Anzoátegui.
CODIGO_ESTADO = {
    "Distrito Capital": "A", "Anzoátegui": "B", "Apure": "C", "Aragua": "D", "Barinas": "E", "Bolívar": "F",
    "Carabobo": "G", "Cojedes": "H", "Falcón": "I", "Guárico": "J", "Lara": "K", "Mérida": "L", "Miranda": "M",
    "Monagas": "N", "Nueva Esparta": "O", "Portuguesa": "P", "Sucre": "R", "Táchira": "S", "Trujillo": "T",
    "Yaracuy": "U", "Zulia": "V", "La Guaira": "X", "Delta Amacuro": "Y", "Amazonas": "Z",
}

# Forma de pago que muestra Shopify en el pedido (igual que Releasit).
PASARELA_COD = "Cash on Delivery (COD)"

# Celulares venezolanos: Movilnet (416, 426), Movistar (414, 424), Digitel (412, 422).
PREFIJOS_CELULAR = ("412", "414", "416", "422", "424", "426")

# Ofertas por cantidad. Clave: dirección del producto (lo que va después de /products/ en la tienda),
# o nombre del producto en Shopify (sin importar mayúsculas/acentos), o ID de la variante.
# Cada oferta: cantidad y precio TOTAL. El precio de lista por unidad es el de la oferta de 1 unidad.
# Si un producto no está aquí, se vende 1 unidad al precio que tenga en Shopify.
OFERTAS: dict[str, list[dict]] = {
    "ao-black-maca-potencia-brutal": [
        {"cantidad": 1, "precio": 37500},
        {"cantidad": 2, "precio": 57500, "etiqueta": "Más vendido"},
        {"cantidad": 3, "precio": 65500, "etiqueta": "Mejor precio"},
    ],
}

# WhatsApp que abre el botón final (el mismo desde donde Pancake escribe). Solo dígitos, con código de país.
WHATSAPP_CONFIRMACION = "584122254027"

ETIQUETAS_PEDIDO = ["COD", "Formulario Rebajitas"]
ORIGEN = "Formulario Rebajitas COD"


def _clave(texto: str) -> str:
    return unicodedata.normalize("NFD", texto or "").encode("ascii", "ignore").decode().upper().strip()


def ofertas_de(variante_id: str, titulo: str, precio_shopify: Decimal, direccion: str = "") -> list[dict]:
    """Ofertas que se muestran para un producto. Precios en Decimal, siempre del servidor.
    'lista' = precio por unidad sin descuento; 'antes' = lista × cantidad (el precio tachado)."""
    por_clave = {_clave(k): v for k, v in OFERTAS.items()}
    config = OFERTAS.get(str(variante_id)) or por_clave.get(_clave(direccion)) or por_clave.get(_clave(titulo))
    if not config:
        return [{"cantidad": 1, "precio": precio_shopify, "lista": precio_shopify, "antes": precio_shopify, "etiqueta": None}]
    base = next((o for o in config if o["cantidad"] == 1), config[0])
    lista = (Decimal(str(base["precio"])) / base["cantidad"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return [{"cantidad": o["cantidad"], "precio": Decimal(str(o["precio"])), "lista": lista,
             "antes": lista * o["cantidad"], "etiqueta": o.get("etiqueta")} for o in config]


def normalizar_telefono(texto: str) -> str | None:
    """Convierte '0412-123.45.67', '+58 412 1234567', etc. en '+584121234567'. None si no es celular venezolano."""
    digitos = re.sub(r"\D", "", texto or "")
    if digitos.startswith("58") and len(digitos) == 12:
        digitos = digitos[2:]
    if digitos.startswith("0") and len(digitos) == 11:
        digitos = digitos[1:]
    if len(digitos) == 10 and digitos[:3] in PREFIJOS_CELULAR:
        return "+58" + digitos
    return None


def limpiar(texto, largo=80) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()[:largo]


def validar_datos(datos: dict) -> tuple[dict, dict]:
    """Revisa lo que escribió el cliente. Devuelve (datos limpios, errores por campo)."""
    limpio = {
        "nombre": limpiar(datos.get("nombre"), 60),
        "apellido": limpiar(datos.get("apellido"), 60),
        "telefono": normalizar_telefono(datos.get("telefono", "")),
        "estado": limpiar(datos.get("estado"), 40),
        "ciudad": limpiar(datos.get("ciudad"), 60),
        "oficina": limpiar(datos.get("oficina"), 120),
    }
    errores = {}
    for campo, mensaje in [("nombre", "Escribe tu nombre"), ("apellido", "Escribe tu apellido"),
                           ("ciudad", "Escribe tu ciudad"), ("oficina", "Elige la oficina donde vas a retirar")]:
        if not limpio[campo]:
            errores[campo] = mensaje
    if not limpio["telefono"]:
        errores["telefono"] = "Revisa el número: debe ser un celular venezolano, ej. 412 123 4567"
    if limpio["estado"] not in ESTADOS:
        errores["estado"] = "Selecciona tu estado"
    elif limpio["oficina"] and OFICINAS_TEALCA.get(limpio["estado"]) and limpio["oficina"] not in OFICINAS_TEALCA[limpio["estado"]]:
        errores["oficina"] = "Elige una oficina de la lista"
    return limpio, errores


UTM_CAMPOS = [("utm_term", "UTM term"), ("utm_content", "UTM content"), ("utm_campaign", "UTM campaign"),
              ("utm_medium", "UTM medium"), ("utm_source", "UTM source")]


def armar_pedido(datos: dict, variante_id: str, oferta: dict, moneda: str, ip: str, utm: dict | None = None) -> dict:
    """Arma el pedido tal como se envía a Shopify (orderCreate).
    Copia el formato de los pedidos de Releasit, para que Pancake, Sheets y Dropanas los lean igual:
    dirección = la ciudad que eligió el cliente, ciudad = la oficina TEALCA, estado con su código de Shopify,
    pago pendiente por "Cash on Delivery (COD)", envío "Gratis" y cliente creado o enlazado por su teléfono."""
    dinero = lambda valor: {"shopMoney": {"amount": f"{valor:.2f}", "currencyCode": moneda}}
    direccion = {
        "firstName": datos["nombre"],
        "lastName": datos["apellido"],
        "address1": datos["ciudad"],
        "city": datos["oficina"],
        "provinceCode": CODIGO_ESTADO[datos["estado"]],
        "countryCode": "VE",
        "phone": datos["telefono"],
    }
    utm = utm or {}
    atributos = [{"key": nombre, "value": limpiar(utm.get(campo), 150)} for campo, nombre in UTM_CAMPOS if limpiar(utm.get(campo))]
    atributos += [
        {"key": "Country code", "value": "VE"},
        {"key": "Nombre", "value": datos["nombre"]},
        {"key": "Apellido", "value": datos["apellido"]},
        {"key": "Teléfono", "value": datos["telefono"].removeprefix("+58")},
        {"key": "Estado", "value": datos["estado"].upper()},
        {"key": "Ciudad", "value": datos["ciudad"]},
        {"key": "Oficina de TEALCA", "value": datos["oficina"]},
        {"key": "IP address", "value": ip or "desconocida"},
    ]
    pedido = {
        "currency": moneda,
        "financialStatus": "PENDING",
        "phone": datos["telefono"],
        "lineItems": [{
            "variantId": f"gid://shopify/ProductVariant/{variante_id}",
            "quantity": oferta["cantidad"],
            "priceSet": dinero(oferta["lista"]),
        }],
        "shippingAddress": direccion,
        "billingAddress": direccion,
        "shippingLines": [{"title": "Gratis", "priceSet": dinero(0)}],
        "transactions": [{"kind": "SALE", "status": "PENDING", "gateway": PASARELA_COD, "amountSet": dinero(oferta["precio"])}],
        "customer": {"toUpsert": {"firstName": datos["nombre"], "lastName": datos["apellido"], "phone": datos["telefono"]}},
        "tags": ETIQUETAS_PEDIDO,
        "customAttributes": atributos,
    }
    descuento = oferta["antes"] - oferta["precio"]
    if descuento > 0:
        pedido["discountCode"] = {"itemFixedDiscountCode": {
            "code": f"OFERTA {oferta['cantidad']} UNIDADES", "amountSet": dinero(descuento)}}
    return pedido
