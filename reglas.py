"""Reglas de negocio del formulario. Todo lo que decide precios, validaciones y cómo se arma el pedido vive aquí."""
import csv
import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# ---- Oficinas TEALCA (catálogo oficial de DroPanas) ----
# Archivo único: oficinas_tealca.csv (exportado de DroPanas GET /oficinas?carrier=tealca).
# Para actualizarlo, se reemplaza ese archivo por uno nuevo con las MISMAS columnas (ver LEEME.md).
# Estados, ciudades y oficinas del formulario salen de aquí, y las oficinas se buscan SIEMPRE por su número.
ARCHIVO_OFICINAS = Path(__file__).parent / "oficinas_tealca.csv"


def _norm(texto: str) -> str:
    return unicodedata.normalize("NFD", texto or "").encode("ascii", "ignore").decode().lower().strip()


def cargar_oficinas(ruta: Path = ARCHIVO_OFICINAS) -> list[dict]:
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        filas = [r for r in csv.DictReader(f) if (r.get("Oficina DroPanas ID") or "").strip()]
    oficinas = []
    for r in filas:
        oficinas.append({
            "id": int(r["Oficina DroPanas ID"]),
            "estado": r["Estado"].strip(), "estado_id": int(r["Estado DroPanas ID"]),
            "ciudad": r["Ciudad"].strip(), "ciudad_id": int(r["Ciudad DroPanas ID"]),
            "nombre_dropanas": r["Nombre en DroPanas"].strip(),
            "nombre": r["Nombre para el cliente"].strip(),
            "codigo": r["Código Tealca"].strip(),
            "direccion": r["Dirección"].strip(),
            "horario": r["Horario"].strip(),
        })
    return oficinas


OFICINAS = cargar_oficinas()
OFICINA_POR_ID = {o["id"]: o for o in OFICINAS}
ESTADO_ID = {o["estado"]: o["estado_id"] for o in OFICINAS}
CIUDAD_ID = {(o["estado"], o["ciudad"]): o["ciudad_id"] for o in OFICINAS}
ESTADOS = sorted(ESTADO_ID, key=_norm)
CIUDADES = {e: sorted({o["ciudad"] for o in OFICINAS if o["estado"] == e}, key=_norm) for e in ESTADOS}

# Código de cada estado en Shopify (ISO 3166-2:VE). Releasit lo usa así: "LECHERÍA - B" = Anzoátegui.
CODIGO_ESTADO = {
    "Distrito Capital": "A", "Anzoátegui": "B", "Apure": "C", "Aragua": "D", "Barinas": "E", "Bolívar": "F",
    "Carabobo": "G", "Cojedes": "H", "Falcón": "I", "Guárico": "J", "Lara": "K", "Mérida": "L", "Miranda": "M",
    "Monagas": "N", "Nueva Esparta": "O", "Portuguesa": "P", "Sucre": "R", "Táchira": "S", "Trujillo": "T",
    "Yaracuy": "U", "Zulia": "V", "La Guaira": "X", "Delta Amacuro": "Y", "Amazonas": "Z",
}

# Ocultar el botón de compra normal del tema ("Add to cart", cantidad y "Comprar ya") cuando nuestro botón cargó bien.
OCULTAR_CARRITO_TEMA = True

# Forma de pago que muestra Shopify en el pedido (igual que Releasit).
PASARELA_COD = "Cash on Delivery (COD)"

# Entrega a domicilio (en vez de retiro en oficina TEALCA): estado -> lista de ciudades, o "*" = todo el estado.
ENTREGA_DOMICILIO = {"Distrito Capital": ["Caracas"], "Miranda": "*"}


def es_domicilio(estado: str, ciudad: str) -> bool:
    regla = ENTREGA_DOMICILIO.get(estado, [])
    return regla == "*" or ciudad in regla


def normalizar_cedula(texto: str) -> str | None:
    """Convierte 'v20.216.018', 'E-1234567', '20216018' (se asume V) en 'V-20216018'.
    Tipos que acepta DroPanas: V, E, P, J; número de 7 a 9 dígitos. None si no cumple."""
    t = re.sub(r"[\s.\-]", "", (texto or "").upper())
    letra = "V"
    if t[:1] in TIPOS_CEDULA:
        letra, t = t[0], t[1:]
    if re.fullmatch(r"\d{7,9}", t):
        return f"{letra}-{t}"
    return None


TIPOS_CEDULA = ("V", "E", "P", "J")


# Teléfonos venezolanos (regla DroPanas): móviles 04xx o fijos 02xx, 11 dígitos con el 0.
# Móviles: Movilnet (416, 426), Movistar (414, 424), Digitel (412, 422).
PREFIJOS_CELULAR = ("412", "414", "416", "422", "424", "426")

# Largos máximos que acepta DroPanas.
MAX_NOMBRE = 50
MAX_DIRECCION = 250
MAX_REFERENCIA = 300

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
    """Convierte '4141234567', '04141234567', '+58 414-1234567' en '+584141234567'.
    Acepta móviles (412, 414, 416, 422, 424, 426) y fijos (2xx). None si no es un número venezolano."""
    digitos = re.sub(r"\D", "", texto or "")
    if digitos.startswith("58") and len(digitos) == 12:
        digitos = digitos[2:]
    if digitos.startswith("0") and len(digitos) == 11:
        digitos = digitos[1:]
    if len(digitos) == 10 and (digitos[:3] in PREFIJOS_CELULAR or digitos[0] == "2"):
        return "+58" + digitos
    return None


def telefono_local(e164: str) -> str:
    """'+584141234567' → '04141234567' (11 dígitos, como lo pide DroPanas)."""
    return "0" + e164.removeprefix("+58")


def limpiar(texto, largo=80) -> str:
    return re.sub(r"\s+", " ", str(texto or "")).strip()[:largo]


def validar_datos(datos: dict) -> tuple[dict, dict]:
    """Revisa lo que escribió el cliente. Devuelve (datos limpios, errores por campo).
    Retiro en oficina: la oficina se busca por su número (Oficina DroPanas ID) y de ella salen estado y ciudad.
    Domicilio: estado y ciudad deben estar en el catálogo (para tener sus IDs de DroPanas)."""
    limpio = {
        "nombre": limpiar(datos.get("nombre"), MAX_NOMBRE),
        "apellido": limpiar(datos.get("apellido"), MAX_NOMBRE),
        "telefono": normalizar_telefono(datos.get("telefono", "")),
        "estado": limpiar(datos.get("estado"), 40),
        "ciudad": limpiar(datos.get("ciudad"), 60),
        "cedula": normalizar_cedula(datos.get("cedula", "")),
        "direccion": limpiar(datos.get("direccion"), 1000),
        "referencia": limpiar(datos.get("referencia"), 1000),
        "oficina": None,
    }
    errores = {}
    if not limpio["nombre"]:
        errores["nombre"] = "Escribe tu nombre"
    if not limpio["apellido"]:
        errores["apellido"] = "Escribe tu apellido"
    if not limpio["telefono"]:
        errores["telefono"] = "Revisa el número: debe ser venezolano, ej. 0414 123 4567"
    if not limpio["cedula"]:
        errores["cedula"] = "Revisa la cédula: de 7 a 9 números, ej. 20216018"

    limpio["domicilio"] = es_domicilio(limpio["estado"], limpio["ciudad"])
    if limpio["domicilio"]:
        if (limpio["estado"], limpio["ciudad"]) not in CIUDAD_ID:
            errores["ciudad"] = "Selecciona tu ciudad"
        if not limpio["direccion"]:
            errores["direccion"] = "Escribe la dirección de entrega"
        elif len(limpio["direccion"]) > MAX_DIRECCION:
            errores["direccion"] = f"La dirección es muy larga (máximo {MAX_DIRECCION} letras)"
        if len(limpio["referencia"]) > MAX_REFERENCIA:
            errores["referencia"] = f"El punto de referencia es muy largo (máximo {MAX_REFERENCIA} letras)"
    else:
        limpio["direccion"] = limpio["referencia"] = ""
        try:
            oficina = OFICINA_POR_ID.get(int(str(datos.get("oficina_id", "")).strip()))
        except ValueError:
            oficina = None
        if not oficina:
            errores["oficina"] = "Elige la oficina donde vas a retirar"
            if limpio["estado"] not in ESTADO_ID:
                errores["estado"] = "Selecciona tu estado"
            elif (limpio["estado"], limpio["ciudad"]) not in CIUDAD_ID:
                errores["ciudad"] = "Selecciona tu ciudad"
        else:
            limpio["oficina"] = oficina
            limpio["estado"], limpio["ciudad"] = oficina["estado"], oficina["ciudad"]
    if limpio["estado"] in ESTADO_ID and (limpio["estado"], limpio["ciudad"]) in CIUDAD_ID:
        limpio["estado_id"] = ESTADO_ID[limpio["estado"]]
        limpio["ciudad_id"] = CIUDAD_ID[(limpio["estado"], limpio["ciudad"])]
    return limpio, errores


UTM_CAMPOS = [("utm_term", "UTM term"), ("utm_content", "UTM content"), ("utm_campaign", "UTM campaign"),
              ("utm_medium", "UTM medium"), ("utm_source", "UTM source")]


def direccion_cliente(datos: dict) -> str:
    """Dirección del cliente para DroPanas (máx. 250): en domicilio la que escribió; en retiro, la de la oficina Tealca."""
    return (datos["direccion"] if datos["domicilio"] else datos["oficina"]["direccion"])[:MAX_DIRECCION]


def armar_pedido(datos: dict, variante_id: str, oferta: dict, moneda: str, ip: str, utm: dict | None = None) -> dict:
    """Arma el pedido tal como se envía a Shopify (orderCreate).
    En "Información adicional" van los datos exactos que necesita el puente Pancake → DroPanas
    (Oficina/Estado/Ciudad DroPanas ID, teléfono de 11 dígitos, cédula V-…), además de los de Releasit.
    Pago pendiente por "Cash on Delivery (COD)" y envío "Gratis"."""
    dinero = lambda valor: {"shopMoney": {"amount": f"{valor:.2f}", "currencyCode": moneda}}
    of = datos["oficina"]
    direccion = {
        "firstName": datos["nombre"],
        "lastName": datos["apellido"],
        "address1": direccion_cliente(datos),
        "address2": f"C.I. {datos['cedula']}",
        "city": datos["ciudad"],
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
        {"key": "Teléfono", "value": telefono_local(datos["telefono"])},
        {"key": "Cédula", "value": datos["cedula"]},
        {"key": "Estado", "value": datos["estado"].upper()},
        {"key": "Ciudad", "value": datos["ciudad"]},
        {"key": "Tipo de entrega", "value": "Entrega a domicilio" if datos["domicilio"] else "Retiro en oficina TEALCA"},
    ]
    # "Dirección" = dirección del cliente para DroPanas: la que escribió (domicilio) o la de la oficina donde retira.
    atributos += [{"key": "Dirección", "value": direccion_cliente(datos)}]
    if datos["domicilio"]:
        if datos["referencia"]:
            atributos += [{"key": "Punto de referencia", "value": datos["referencia"]}]
    else:
        atributos += [{"key": "Oficina de TEALCA", "value": of["nombre"]},
                      {"key": "Oficina DroPanas ID", "value": str(of["id"])}]
    atributos += [
        {"key": "Estado DroPanas ID", "value": str(datos["estado_id"])},
        {"key": "Ciudad DroPanas ID", "value": str(datos["ciudad_id"])},
        {"key": "IP address", "value": ip or "desconocida"},
    ]
    pedido = {
        "currency": moneda,
        "financialStatus": "PENDING",
        "phone": datos["telefono"],
        "lineItems": [{
            "variantId": f"gid://shopify/ProductVariant/{variante_id}",
            "quantity": oferta["cantidad"],
            "requiresShipping": True,  # sin esto Shopify marca "No se requiere envío" (pedido #3805)
            "priceSet": dinero(oferta["lista"]),
        }],
        "shippingAddress": direccion,
        "billingAddress": direccion,
        "shippingLines": [{"title": "Entrega a domicilio" if datos["domicilio"] else "Gratis", "priceSet": dinero(0)}],
        "transactions": [{"kind": "SALE", "status": "PENDING", "gateway": PASARELA_COD, "amountSet": dinero(oferta["precio"])}],
        "tags": ETIQUETAS_PEDIDO + (["DOMICILIO"] if datos["domicilio"] else ["TEALCA"]),
        "customAttributes": atributos,
    }
    descuento = oferta["antes"] - oferta["precio"]
    if descuento > 0:
        pedido["discountCode"] = {"itemFixedDiscountCode": {
            "code": f"OFERTA {oferta['cantidad']} UNIDADES", "amountSet": dinero(descuento)}}
    return pedido
