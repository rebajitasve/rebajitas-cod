"""Reglas de negocio del formulario. Todo lo que decide precios, validaciones y cómo se arma el pedido vive aquí."""
import json
import re
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

# Celulares venezolanos: Movilnet (416, 426), Movistar (414, 424), Digitel (412, 422).
PREFIJOS_CELULAR = ("412", "414", "416", "422", "424", "426")

# Ofertas por cantidad (etapa 2). Clave: ID de la variante en Shopify.
# Cada oferta: cantidad y precio TOTAL. Si una variante no está aquí, se vende 1 unidad al precio de Shopify.
OFERTAS: dict[str, list[dict]] = {}

# WhatsApp donde el cliente confirma su pedido al terminar (solo dígitos, con código de país).
WHATSAPP_CONFIRMACION = "584122254027"

ETIQUETAS_PEDIDO = ["COD", "Formulario Rebajitas"]
ORIGEN = "Formulario Rebajitas COD"


def ofertas_de(variante_id: str, precio_shopify: Decimal) -> list[dict]:
    """Lista de ofertas que se muestran para una variante. Precios en Decimal, siempre del servidor."""
    if variante_id in OFERTAS:
        return [{"cantidad": o["cantidad"], "precio": Decimal(str(o["precio"])),
                 "antes": precio_shopify * o["cantidad"], "etiqueta": o.get("etiqueta")}
                for o in OFERTAS[variante_id]]
    return [{"cantidad": 1, "precio": precio_shopify, "antes": precio_shopify, "etiqueta": None}]


def precio_unitario(oferta: dict) -> Decimal:
    return (oferta["precio"] / oferta["cantidad"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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


def armar_pedido(datos: dict, variante_id: str, oferta: dict, moneda: str, ip: str) -> dict:
    """Arma el pedido tal como se envía a Shopify (orderCreate)."""
    direccion = {
        "firstName": datos["nombre"],
        "lastName": datos["apellido"],
        "address1": f"Oficina TEALCA: {datos['oficina']}",
        "city": datos["ciudad"],
        "province": datos["estado"],
        "countryCode": "VE",
        "phone": datos["telefono"],
    }
    return {
        "currency": moneda,
        "financialStatus": "PENDING",
        "phone": datos["telefono"],
        "lineItems": [{
            "variantId": f"gid://shopify/ProductVariant/{variante_id}",
            "quantity": oferta["cantidad"],
            "priceSet": {"shopMoney": {"amount": str(precio_unitario(oferta)), "currencyCode": moneda}},
        }],
        "shippingAddress": direccion,
        "billingAddress": direccion,
        "tags": ETIQUETAS_PEDIDO,
        "note": f"Pago al recibir. Retiro en oficina TEALCA: {datos['oficina']} ({datos['ciudad']}, {datos['estado']}).",
        "customAttributes": [
            {"key": "Origen", "value": ORIGEN},
            {"key": "Estado", "value": datos["estado"]},
            {"key": "Ciudad", "value": datos["ciudad"]},
            {"key": "Oficina TEALCA", "value": datos["oficina"]},
            {"key": "IP del cliente", "value": ip or "desconocida"},
        ],
    }
