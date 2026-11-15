"""Configuración del proyecto, leída del archivo .env (en tu computador) o de Render."""
import os
from pathlib import Path

CARPETA = Path(__file__).parent


def cargar_env(ruta=CARPETA / ".env"):
    """Lee el archivo .env sin mostrar nada. Lo que ya esté definido (Render) tiene prioridad."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


cargar_env()

MODO_PRUEBA = os.environ.get("MODO_PRUEBA", "1") == "1"

SHOPIFY_TIENDA = os.environ.get("SHOPIFY_TIENDA", "").strip().removeprefix("https://").rstrip("/")
SHOPIFY_TOKEN = os.environ.get("SHOPIFY_TOKEN", "").strip()
SHOPIFY_CLIENT_ID = os.environ.get("SHOPIFY_CLIENT_ID", "").strip()
SHOPIFY_CLIENT_SECRET = os.environ.get("SHOPIFY_CLIENT_SECRET", "").strip()
SHOPIFY_VERSION_API = os.environ.get("SHOPIFY_VERSION_API", "2025-10")

TIENDA_ORIGENES = [o.strip().rstrip("/") for o in os.environ.get("TIENDA_ORIGENES", "").split(",") if o.strip()]

PUERTO = int(os.environ.get("PORT", "8001"))
HOST = os.environ.get("HOST", "127.0.0.1")
