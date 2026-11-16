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
          "estado": "Carabobo", "ciudad": "Valencia", "oficina": "SAN DIEGO", "cedula": "v-12.345.678",
          "variante": "123", "oferta": 0}


@pytest.fixture(autouse=True)
def limpiar_memoria():
    servidor._recientes.clear()
    servidor._intentos.clear()


@pytest.mark.parametrize("texto,esperado", [
    ("4121234567", "+584121234567"), ("0414 123 4567", "+584141234567"), ("+58 424-1234567", "+584241234567"),
    ("584261234567", "+584261234567"), ("0212 123 4567", None), ("412123456", None), ("", None),
])
def test_telefono(texto, esperado):
    assert reglas.normalizar_telefono(texto) == esperado


def test_validacion_marca_campos_vacios():
    _, errores = reglas.validar_datos({})
    assert set(errores) == {"nombre", "apellido", "telefono", "estado", "ciudad", "oficina", "cedula"}


def test_pedido_bien_armado():
    datos, errores = reglas.validar_datos(BUENOS)
    assert not errores
    oferta = reglas.ofertas_de("123", "Otro producto", Decimal("32450"))[0]
    p = reglas.armar_pedido(datos, "123", oferta, "VES", "1.2.3.4", {"utm_source": "Facebook_Mobile_Feed"})
    assert p["lineItems"][0]["variantId"] == "gid://shopify/ProductVariant/123"
    assert p["lineItems"][0]["priceSet"]["shopMoney"]["amount"] == "32450.00"
    assert "discountCode" not in p
    atr = {a["key"]: a["value"] for a in p["customAttributes"]}
    assert atr["Teléfono"] == "4121234567" and atr["Estado"] == "CARABOBO" and atr["Oficina de TEALCA"] == "SAN DIEGO"
    assert atr["IP address"] == "1.2.3.4" and atr["UTM source"] == "Facebook_Mobile_Feed" and "UTM term" not in atr
    assert p["shippingAddress"]["phone"] == "+584121234567"
    assert p["shippingAddress"]["address1"] == "Valencia" and p["shippingAddress"]["city"] == "SAN DIEGO"
    assert p["shippingAddress"]["provinceCode"] == "G" and "province" not in p["shippingAddress"]
    assert p["transactions"][0]["gateway"] == "Cash on Delivery (COD)" and p["transactions"][0]["status"] == "PENDING"
    assert p["transactions"][0]["amountSet"]["shopMoney"]["amount"] == "32450.00"
    assert p["shippingLines"][0]["title"] == "Gratis" and "note" not in p
    assert "customer" not in p  # Shopify exige correo para enlazar cliente (pedido real del 16-nov rechazado)
    assert "COD" in p["tags"] and p["financialStatus"] == "PENDING"


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


def test_oficinas_tealca():
    assert all(e in reglas.ESTADOS for e in reglas.OFICINAS_TEALCA)
    assert "SAN DIEGO" in reglas.OFICINAS_TEALCA["Carabobo"]
    _, errores = reglas.validar_datos({**BUENOS, "oficina": "OFICINA INVENTADA"})
    assert "oficina" in errores
    _, errores = reglas.validar_datos({**BUENOS, "estado": "Amazonas", "oficina": "Puerto Ayacucho"})
    assert not errores  # estado sin lista: se acepta lo que escriba el cliente


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


def test_ciudades_por_estado():
    assert set(reglas.CIUDADES) == set(reglas.ESTADOS)
    assert all(reglas.CIUDADES[e] for e in reglas.ESTADOS)
    assert "Valencia" in reglas.CIUDADES["Carabobo"] and "Caracas" in reglas.CIUDADES["Distrito Capital"]
    assert "Catia La Mar" in reglas.CIUDADES["La Guaira"] and "Chaguaramas" in reglas.CIUDADES["Guárico"]
    c = TestClient(servidor.app)
    assert c.get("/api/producto/prueba").json()["ciudades"]["Zulia"][0]


def test_codigos_de_estado_completos():
    assert set(reglas.CODIGO_ESTADO) == set(reglas.ESTADOS)
    assert reglas.CODIGO_ESTADO["Anzoátegui"] == "B"  # igual que el pedido de Releasit (LECHERÍA - B)


def test_sheets_fila_igual_a_releasit(monkeypatch):
    from datetime import datetime
    monkeypatch.setattr(config, "SHEETS_URL", "https://script.google.com/macros/s/x/exec")
    monkeypatch.setattr(config, "SHEETS_CLAVE", "k")
    monkeypatch.setattr(config, "SHEETS_HOJA", "Tealca {mes} COD")
    assert sheets.nombre_hoja(datetime(2026, 11, 16)) == "Tealca Noviembre COD"
    assert sheets.nombre_hoja(datetime(2026, 12, 1)) == "Tealca Diciembre COD"
    datos, _ = reglas.validar_datos(BUENOS)
    oferta = reglas.ofertas_de("1", "AO", Decimal("37500"), "ao-black-maca-potencia-brutal")[1]
    fila = sheets.armar_fila(datos, "AO BLACK MACA - Potencia Brutal", oferta, {"utm_source": "Facebook_Mobile_Feed"},
                             datetime(2026, 11, 1, 0, 16, 0))
    assert fila["fecha"] == "2026-11-01 0:16:00" and fila["nombre"] == "Juan Hernández"
    assert fila["telefono"] == "+584121234567" and fila["estado"] == "CARABOBO" and fila["oficina"] == "SAN DIEGO"
    assert fila["cantidad"] == 2 and fila["valor"] == 57500.0 and fila["utm_source"] == "Facebook_Mobile_Feed"

    enviados = []
    def responder(request):
        enviados.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "hoja": "Tealca Noviembre COD"})
    assert sheets.enviar("#1001", datos, "AO", oferta, {}, httpx.Client(transport=httpx.MockTransport(responder)))
    assert enviados[0]["clave"] == "k" and enviados[0]["fila"]["oficina"] == "SAN DIEGO"

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


@pytest.mark.parametrize("texto,esperado", [
    ("12345678", "V-12345678"), ("v-12.345.678", "V-12345678"), ("E 1234567", "E-1234567"), ("V012345678", "V-12345678"),
    ("abc", None), ("1234", None), ("", None),
])
def test_cedula(texto, esperado):
    assert reglas.normalizar_cedula(texto) == esperado


def test_oficina_lleva_cedula():
    datos, errores = reglas.validar_datos(BUENOS)
    assert not errores and not datos["domicilio"]
    p = reglas.armar_pedido(datos, "1", reglas.ofertas_de("1", "x", Decimal("10"))[0], "VED", "")
    assert p["shippingAddress"]["address2"] == "C.I. V-12345678" and p["shippingAddress"]["city"] == "SAN DIEGO"
    atr = {a["key"]: a["value"] for a in p["customAttributes"]}
    assert atr["Cédula"] == "V-12345678" and atr["Tipo de entrega"] == "Retiro en oficina TEALCA" and "Dirección" not in atr
    assert "DOMICILIO" not in p["tags"]


def test_caracas_entrega_a_domicilio():
    base = {**BUENOS, "estado": "Distrito Capital", "ciudad": "Caracas", "oficina": ""}
    _, errores = reglas.validar_datos(base)
    assert "direccion" in errores and "oficina" not in errores
    datos, errores = reglas.validar_datos({**base, "direccion": "Av. Sucre, edif. Los Pinos, piso 3, apto 3B, Catia"})
    assert not errores and datos["domicilio"] and datos["oficina"] == ""
    p = reglas.armar_pedido(datos, "1", reglas.ofertas_de("1", "x", Decimal("10"))[0], "VED", "")
    d = p["shippingAddress"]
    assert d["address1"].startswith("Av. Sucre") and d["city"] == "Caracas" and d["provinceCode"] == "A"
    atr = {a["key"]: a["value"] for a in p["customAttributes"]}
    assert atr["Oficina de TEALCA"] == "ENTREGA A DOMICILIO" and atr["Dirección"].startswith("Av. Sucre")
    assert atr["Tipo de entrega"] == "Entrega a domicilio" and "DOMICILIO" in p["tags"]
    assert p["shippingLines"][0]["title"] == "Entrega a domicilio"
    from datetime import datetime
    fila = sheets.armar_fila(datos, "AO", reglas.ofertas_de("1", "x", Decimal("10"))[0], {}, datetime(2026, 11, 16))
    assert fila["oficina"].startswith("DOMICILIO: Av. Sucre")
    # Otra ciudad del Distrito Capital (escrita a mano) sigue siendo retiro en oficina
    _, errores = reglas.validar_datos({**BUENOS, "estado": "Distrito Capital", "ciudad": "El Junquito", "oficina": "JUNQUITO"})
    assert not errores
