"""Revisiones automáticas. Se corren con:  python -m pytest -q"""
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["MODO_PRUEBA"] = "1"

import config  # noqa: E402
import reglas  # noqa: E402
import sheets  # noqa: E402
import shopify  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import app as servidor  # noqa: E402

BUENOS = {"nombre": "Juan", "apellido": "Hernández", "telefono": "0412-123.45.67",
          "estado": "Carabobo", "ciudad": "Valencia", "oficina_id": "667", "cedula": "v-12.345.678",
          "variante": "123", "oferta": 0}


@pytest.fixture(autouse=True)
def limpiar_memoria():
    servidor._recientes.clear()
    servidor._intentos.clear()


def test_servidor_modo_prueba():
    c = TestClient(servidor.app)
    assert c.get("/salud").json()["ok"]
    assert "Rebajitas COD" in c.get("/").text
    assert "rebajitas-cod" in c.get("/prueba").text
    assert c.get("/formulario.js").status_code == 200
    prod = c.get("/api/producto/prueba").json()
    assert [o["precio"] for o in prod["ofertas"]] == [37500.0, 57500.0, 65500.0] and "Zulia" in prod["estados"]
    assert prod["whatsapp"] == "584122254027"

    r = c.post("/api/pedido", json=BUENOS)
    assert r.status_code == 200 and r.json()["numero"].startswith("#PRUEBA")
    # El mismo cliente vuelve a tocar el botón: no se crea un pedido repetido
    r2 = c.post("/api/pedido", json=BUENOS)
    assert r2.json()["repetido"] and r2.json()["numero"] == r.json()["numero"]


def test_servidor_rechaza_datos_malos():
    c = TestClient(servidor.app)
    r = c.post("/api/pedido", json={**BUENOS, "telefono": "123"})
    assert r.status_code == 422 and "telefono" in r.json()["errores"]


def test_limite_por_conexion():
    c = TestClient(servidor.app)
    for i in range(servidor.MAX_PEDIDOS_POR_IP):
        assert c.post("/api/pedido", json={**BUENOS, "telefono": f"41200000{i:02d}"}).status_code == 200
    assert c.post("/api/pedido", json={**BUENOS, "telefono": "4129999999"}).status_code == 429


def test_shopify_real_simulado(monkeypatch):
    """Simula a Shopify para revisar que se le envía lo correcto (sin conectarse de verdad)."""
    monkeypatch.setattr(config, "MODO_PRUEBA", False)
    monkeypatch.setattr(config, "SHOPIFY_TIENDA", "tienda.myshopify.com")
    monkeypatch.setattr(config, "SHOPIFY_TOKEN", "x")
    enviados = []

    def responder(request):
        cuerpo = json.loads(request.content)
        enviados.append(cuerpo)
        if "productVariant" in cuerpo["query"]:
            return httpx.Response(200, json={"data": {
                "productVariant": {"title": "Default Title", "price": "32450.00", "availableForSale": True,
                                   "product": {"title": "AO Black Maca Potencia Brutal", "handle": "ao-black-maca-potencia-brutal"}},
                "shop": {"currencyCode": "VES"}}})
        return httpx.Response(200, json={"data": {"orderCreate": {
            "order": {"id": "gid://shopify/Order/1", "name": "#1001"}, "userErrors": []}}})

    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    v = shopify.leer_variante("123", cliente)
    assert v["precio"] == Decimal("32450.00") and v["moneda"] == "VES" and v["variante"] == ""
    datos, _ = reglas.validar_datos(BUENOS)
    r = shopify.crear_pedido(reglas.armar_pedido(datos, "123", reglas.ofertas_de("123", v["titulo"], v["precio"], v["direccion"])[2], "VES", ""), cliente)
    assert r["numero"] == "#1001"
    assert enviados[1]["variables"]["options"]["sendReceipt"] is False


def test_ofertas_ao_black_maca():
    assert reglas.ofertas_de("999", "AO Black Maca Potencia Brutal", Decimal("32450"), "ao-black-maca-potencia-brutal")[2]["precio"] == Decimal("65500")
    o = reglas.ofertas_de("999", "Otro nombre", Decimal("32450"), "AO-Black-Maca-Potencia-Brutal")
    assert [(x["cantidad"], x["precio"], x["antes"]) for x in o] == [
        (1, Decimal("37500"), Decimal("37500.00")), (2, Decimal("57500"), Decimal("75000.00")), (3, Decimal("65500"), Decimal("112500.00"))]
    datos, _ = reglas.validar_datos(BUENOS)
    p = reglas.armar_pedido(datos, "999", o[2], "VES", "")
    assert p["lineItems"][0]["quantity"] == 3 and p["lineItems"][0]["priceSet"]["shopMoney"]["amount"] == "37500.00"
    assert p["discountCode"]["itemFixedDiscountCode"]["amountSet"]["shopMoney"]["amount"] == "47000.00"  # 112.500 - 65.500


def test_modo_prueba_lee_producto_real_pero_no_crea_pedidos(monkeypatch):
    monkeypatch.setattr(config, "MODO_PRUEBA", True)
    monkeypatch.setattr(config, "SHOPIFY_TIENDA", "tienda.myshopify.com")
    monkeypatch.setattr(config, "SHOPIFY_TOKEN", "x")
    llamadas = []

    def responder(request):
        llamadas.append(json.loads(request.content)["query"])
        return httpx.Response(200, json={"data": {
            "productVariant": {"title": "Default Title", "price": "37500.00", "availableForSale": True,
                               "product": {"title": "AO Black Maca"}},
            "shop": {"currencyCode": "VES"}}})

    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    assert shopify.leer_variante("123", cliente)["precio"] == Decimal("37500.00")
    assert shopify.leer_variante("prueba", cliente)["precio"] == Decimal("32450.00")  # página de prueba
    assert shopify.crear_pedido({}, cliente)["numero"].startswith("#PRUEBA")
    assert len(llamadas) == 1 and "orderCreate" not in llamadas[0]


def test_vista_previa_de_shopify_permitida():
    c = TestClient(servidor.app)
    r = c.get("/api/producto/prueba", headers={"Origin": "https://abc123xyz.shopifypreview.com"})
    assert r.headers.get("access-control-allow-origin") == "https://abc123xyz.shopifypreview.com"
    r = c.get("/api/producto/prueba", headers={"Origin": "https://otra-tienda.com"})
    assert "access-control-allow-origin" not in r.headers


def test_sheets_fila_igual_a_releasit(monkeypatch):
    from datetime import datetime
    monkeypatch.setattr(config, "SHEETS_URL", "https://script.google.com/macros/s/x/exec")
    monkeypatch.setattr(config, "SHEETS_CLAVE", "k")
    monkeypatch.setattr(config, "SHEETS_HOJA", "Tealca COD {mes}")
    assert sheets.nombre_hoja(datetime(2026, 11, 16)) == "Tealca COD Noviembre"
    assert sheets.nombre_hoja(datetime(2026, 12, 1)) == "Tealca COD Diciembre"
    datos, _ = reglas.validar_datos(BUENOS)
    oferta = reglas.ofertas_de("1", "AO", Decimal("37500"), "ao-black-maca-potencia-brutal")[1]
    fila = sheets.armar_fila(datos, "AO BLACK MACA - Potencia Brutal", oferta, {"utm_source": "Facebook_Mobile_Feed"},
                             datetime(2026, 11, 1, 0, 16, 0))
    assert fila["fecha"] == "2026-11-01 0:16:00" and fila["nombre"] == "Juan Hernández"
    assert fila["telefono"] == "+584121234567" and fila["estado"] == "CARABOBO" and fila["oficina"] == "Tealca San Diego"
    assert fila["cantidad"] == 2 and fila["valor"] == 57500.0 and fila["utm_source"] == "Facebook_Mobile_Feed"

    enviados = []
    def responder(request):
        enviados.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "hoja": "Tealca COD Noviembre"})
    assert sheets.enviar("#1001", datos, "AO", oferta, {}, httpx.Client(transport=httpx.MockTransport(responder)))
    assert enviados[0]["clave"] == "k" and enviados[0]["fila"]["oficina"] == "Tealca San Diego"

    fallos = []
    def falla(request):
        fallos.append(1)
        return httpx.Response(200, json={"ok": False, "error": "clave incorrecta"})
    assert not sheets.enviar("#1002", datos, "AO", oferta, {}, httpx.Client(transport=httpx.MockTransport(falla)))
    assert len(fallos) == 3


def test_sheets_solo_en_modo_real(monkeypatch):
    llamadas = []
    monkeypatch.setattr(sheets, "activo", lambda: True)
    monkeypatch.setattr(sheets, "enviar_en_segundo_plano", lambda *a: llamadas.append(a))
    c = TestClient(servidor.app)
    assert c.post("/api/pedido", json=BUENOS).status_code == 200
    assert llamadas == []  # modo prueba: no se escribe en la hoja


def test_sheets_cedula_y_verificacion(monkeypatch):
    from datetime import datetime
    datos, _ = reglas.validar_datos(BUENOS)
    fila = sheets.armar_fila(datos, "AO", reglas.ofertas_de("1", "x", Decimal("10"))[0], {}, datetime(2026, 11, 16))
    assert fila["cedula"] == "V-12345678"
    monkeypatch.setattr(config, "SHEETS_URL", "https://script.google.com/macros/s/x/exec")
    monkeypatch.setattr(config, "SHEETS_CLAVE", "k")
    casos = [
        (httpx.Response(200, json={"ok": True, "hoja": "h", "existe": True}), True, "conectado"),
        (httpx.Response(200, json={"ok": True, "hoja": "h", "existe": False}), False, "NO existe"),
        (httpx.Response(200, json={"ok": False, "error": "clave incorrecta"}), False, "clave no coincide"),
        (httpx.Response(200, text="<html>Sign in - Google Accounts accounts.google.com</html>"), False, "Cualquier persona"),
        (httpx.Response(200, text="<html>TypeError: Cannot read properties of undefined</html>"), False, "TypeError"),
        (httpx.Response(404, text="<html><title>Error 404 (Not Found)</title><script>Error(String(a))</script></html>"), False, "Not Found"),
    ]
    for respuesta, ok, texto in casos:
        cliente = httpx.Client(transport=httpx.MockTransport(lambda r, x=respuesta: x))
        resultado = sheets.verificar(cliente)
        assert resultado[0] == ok and texto in resultado[1], resultado


def test_cliente_buscar_o_crear(monkeypatch):
    monkeypatch.setattr(config, "MODO_PRUEBA", False)
    monkeypatch.setattr(config, "SHOPIFY_TIENDA", "tienda.myshopify.com")
    monkeypatch.setattr(config, "SHOPIFY_TOKEN", "x")

    def con(respuestas):
        cola = list(respuestas)
        return httpx.Client(transport=httpx.MockTransport(lambda r: cola.pop(0)))
    existe = con([httpx.Response(200, json={"data": {"customers": {"nodes": [{"id": "gid://shopify/Customer/7"}]}}})])
    assert shopify.buscar_o_crear_cliente("Ana", "Rojas", "+584241234567", existe) == "gid://shopify/Customer/7"
    nuevo = con([httpx.Response(200, json={"data": {"customers": {"nodes": []}}}),
                 httpx.Response(200, json={"data": {"customerCreate": {"customer": {"id": "gid://shopify/Customer/8"}, "userErrors": []}}})])
    assert shopify.buscar_o_crear_cliente("Ana", "Rojas", "+584241234567", nuevo) == "gid://shopify/Customer/8"
    # Sin permiso de clientes: no falla, el pedido sale sin cliente
    sin_permiso = con([httpx.Response(200, json={"errors": [{"message": "Access denied for customers field."}]})])
    assert shopify.buscar_o_crear_cliente("Ana", "Rojas", "+584241234567", sin_permiso) is None


def test_pedido_requiere_envio():
    datos, _ = reglas.validar_datos(BUENOS)
    p = reglas.armar_pedido(datos, "1", reglas.ofertas_de("1", "x", Decimal("10"))[0], "VED", "")
    assert p["lineItems"][0]["requiresShipping"] is True



# ---------- Reglas de DroPanas ----------

@pytest.mark.parametrize("texto,esperado", [
    ("4141234567", "+584141234567"), ("04141234567", "+584141234567"), ("+58 414-1234567", "+584141234567"),
    ("0212 123 4567", "+582121234567"), ("584261234567", "+584261234567"),
    ("+1 305 555 1234", None), ("0414123456", None), ("0314 123 4567", None), ("", None),
])
def test_telefono_dropanas(texto, esperado):
    assert reglas.normalizar_telefono(texto) == esperado
    if esperado:
        local = reglas.telefono_local(esperado)
        assert len(local) == 11 and local[:2] in ("04", "02")


@pytest.mark.parametrize("texto,esperado", [
    ("20216018", "V-20216018"), ("v-20.216.018", "V-20216018"), ("E 1234567", "E-1234567"),
    ("P-123456789", "P-123456789"), ("J123456789", "J-123456789"),
    ("123456", None), ("1234567890", None), ("X-1234567", None), ("abc", None), ("", None),
])
def test_cedula_dropanas(texto, esperado):
    assert reglas.normalizar_cedula(texto) == esperado


def test_catalogo_oficinas():
    assert len(reglas.OFICINAS) == 134 and len(reglas.ESTADOS) == 23
    assert set(reglas.ESTADOS) <= set(reglas.CODIGO_ESTADO)
    o = reglas.OFICINA_POR_ID[687]
    assert (o["estado"], o["estado_id"], o["ciudad"], o["ciudad_id"]) == ("Zulia", 23, "Maracaibo", 487)
    assert o["nombre"] == "Tealca Delicias 5 de Julio" and o["horario"]
    c = TestClient(servidor.app).get("/api/producto/prueba").json()
    assert len(c["oficinas"]) == 134 and c["ciudades"]["Zulia"] and set(c["tipos_cedula"]) == {"V", "E", "P", "J"}


def test_validacion_marca_campos_vacios():
    _, errores = reglas.validar_datos({})
    assert {"nombre", "apellido", "telefono", "cedula", "oficina", "estado"} <= set(errores)


def test_oficina_por_numero_no_por_nombre():
    # El cliente manda un estado/ciudad equivocados: manda el número de oficina, y de ahí sale todo.
    datos, errores = reglas.validar_datos({**BUENOS, "oficina_id": "687", "estado": "Lara", "ciudad": "Carora"})
    assert not errores and datos["estado"] == "Zulia" and datos["ciudad"] == "Maracaibo"
    _, errores = reglas.validar_datos({**BUENOS, "oficina_id": "Tealca San Diego"})
    assert "oficina" in errores
    _, errores = reglas.validar_datos({**BUENOS, "oficina_id": "999999"})
    assert "oficina" in errores


def test_largos_dropanas():
    datos, _ = reglas.validar_datos({**BUENOS, "nombre": "N" * 80, "apellido": "A" * 80})
    assert len(datos["nombre"]) == 50 and len(datos["apellido"]) == 50
    base = {**BUENOS, "estado": "Distrito Capital", "ciudad": "Caracas", "oficina_id": ""}
    _, e = reglas.validar_datos({**base, "direccion": "x" * 251})
    assert "direccion" in e
    _, e = reglas.validar_datos({**base, "direccion": "Av. Sucre, edif. Pinos, apto 3B", "referencia": "r" * 301})
    assert "referencia" in e
    _, e = reglas.validar_datos({**base, "direccion": "Av. Sucre, edif. Pinos, apto 3B", "referencia": "r" * 300})
    assert not e


def atributos(p):
    return {a["key"]: a["value"] for a in p["customAttributes"]}


def test_pedido_tealca_informacion_adicional():
    datos, errores = reglas.validar_datos({**BUENOS, "oficina_id": "687", "telefono": "0414-123.45.67"})
    assert not errores
    oferta = reglas.ofertas_de("1", "x", Decimal("37500"), "ao-black-maca-potencia-brutal")[1]
    p = reglas.armar_pedido(datos, "1", oferta, "VED", "1.2.3.4", {"utm_source": "Facebook_Mobile_Feed"})
    a = atributos(p)
    assert a["Oficina DroPanas ID"] == "687" and a["Estado DroPanas ID"] == "23" and a["Ciudad DroPanas ID"] == "487"
    assert a["Tipo de entrega"] == "Retiro en oficina TEALCA" and a["Oficina de TEALCA"] == "Tealca Delicias 5 de Julio"
    assert a["Teléfono"] == "04141234567" and a["Cédula"] == "V-12345678" and a["Estado"] == "ZULIA" and a["Ciudad"] == "Maracaibo"
    assert a["UTM source"] == "Facebook_Mobile_Feed"
    assert a["Dirección"] == reglas.OFICINA_POR_ID[687]["direccion"] and p["shippingAddress"]["address1"] == a["Dirección"]
    d = p["shippingAddress"]
    assert d["city"] == "Maracaibo" and d["provinceCode"] == "V" and d["address2"] == "C.I. V-12345678"
    assert d["phone"] == "+584141234567" and "TEALCA" in p["tags"] and p["lineItems"][0]["requiresShipping"]


def test_pedido_domicilio_caracas_y_miranda():
    base = {**BUENOS, "oficina_id": "", "direccion": "Av. Urdaneta, edif. Centro Plaza, piso 4, apto 4B",
            "referencia": "Frente a la panadería"}
    datos, errores = reglas.validar_datos({**base, "estado": "Distrito Capital", "ciudad": "Caracas"})
    assert not errores and datos["domicilio"]
    a = atributos(reglas.armar_pedido(datos, "1", reglas.ofertas_de("1", "x", Decimal("10"))[0], "VED", ""))
    assert a["Tipo de entrega"] == "Entrega a domicilio" and a["Estado DroPanas ID"] == "24" and a["Ciudad DroPanas ID"] == "149"
    assert a["Dirección"].startswith("Av. Urdaneta") and a["Punto de referencia"] == "Frente a la panadería"
    assert "Oficina DroPanas ID" not in a
    _, errores = reglas.validar_datos({**base, "estado": "Distrito Capital", "ciudad": "Caracas", "direccion": "Catia"})
    assert not errores  # cualquier texto es válido
    _, errores = reglas.validar_datos({**base, "estado": "Distrito Capital", "ciudad": "Caracas", "direccion": "  "})
    assert "direccion" in errores
    datos, errores = reglas.validar_datos({**base, "estado": "Miranda", "ciudad": "Guarenas"})
    assert not errores and datos["domicilio"] and datos["ciudad_id"] == 275
    # El Junquito (Distrito Capital) sigue siendo retiro en oficina
    datos, errores = reglas.validar_datos({**BUENOS, "oficina_id": "1036"})
    assert not errores and not datos["domicilio"] and datos["ciudad"] == "El Junquito"
