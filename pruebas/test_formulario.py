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
import shopify  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import app as servidor  # noqa: E402

BUENOS = {"nombre": "Juan", "apellido": "Hernández", "telefono": "0412-123.45.67",
          "estado": "Carabobo", "ciudad": "Valencia", "oficina": "SAN DIEGO", "variante": "123", "oferta": 0}


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
    assert set(errores) == {"nombre", "apellido", "telefono", "estado", "ciudad", "oficina"}


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
    assert p["shippingAddress"]["address1"] == "Oficina TEALCA: SAN DIEGO"
    assert "COD" in p["tags"] and p["financialStatus"] == "PENDING"


def test_servidor_modo_prueba():
    c = TestClient(servidor.app)
    assert c.get("/salud").json()["ok"]
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
                                   "product": {"title": "AO Black Maca"}},
                "shop": {"currencyCode": "VES"}}})
        return httpx.Response(200, json={"data": {"orderCreate": {
            "order": {"id": "gid://shopify/Order/1", "name": "#1001"}, "userErrors": []}}})

    cliente = httpx.Client(transport=httpx.MockTransport(responder))
    v = shopify.leer_variante("123", cliente)
    assert v["precio"] == Decimal("32450.00") and v["moneda"] == "VES" and v["variante"] == ""
    datos, _ = reglas.validar_datos(BUENOS)
    r = shopify.crear_pedido(reglas.armar_pedido(datos, "123", reglas.ofertas_de("123", v["titulo"], v["precio"])[2], "VES", ""), cliente)
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
    o = reglas.ofertas_de("999", "AO Black Maca", Decimal("32450"))
    assert [(x["cantidad"], x["precio"], x["antes"]) for x in o] == [
        (1, Decimal("37500"), Decimal("37500.00")), (2, Decimal("57500"), Decimal("75000.00")), (3, Decimal("65500"), Decimal("112500.00"))]
    datos, _ = reglas.validar_datos(BUENOS)
    p = reglas.armar_pedido(datos, "999", o[2], "VES", "")
    assert p["lineItems"][0]["quantity"] == 3 and p["lineItems"][0]["priceSet"]["shopMoney"]["amount"] == "37500.00"
    assert p["discountCode"]["itemFixedDiscountCode"]["amountSet"]["shopMoney"]["amount"] == "47000.00"  # 112.500 - 65.500
