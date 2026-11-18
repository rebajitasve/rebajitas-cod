/* Formulario Rebajitas COD: botón "Pagar al recibir" + formulario emergente.
   Se instala en la tienda con un bloque "Liquid personalizado" (ver LEEME.md). */
(function () {
  "use strict";
  var script = document.currentScript || document.querySelector('script[src*="formulario.js"]');
  var SERVIDOR = script && script.src ? new URL(script.src).origin : "https://rebajitas-cod.onrender.com";
  // Diagnóstico: abriendo el producto con ?rcod=1 aparece una franja abajo que dice en qué paso se traba.
  var DIAG = /[?&](rcod|preview_theme_id|oseid)=/.test(location.search) || /shopifypreview\.com$/.test(location.hostname) ||
    !!(window.Shopify && window.Shopify.designMode);
  function aviso(texto, ok) {
    if (window.console) console[ok ? "log" : "warn"]("Rebajitas COD: " + texto);
    if (!DIAG || !document.body) return;
    var b = document.getElementById("rebajitas-cod-diag");
    if (!b) {
      b = document.createElement("div");
      b.id = "rebajitas-cod-diag";
      b.style.cssText = "position:fixed;left:8px;right:8px;top:8px;z-index:2147483646;background:#14181b;color:#fff;" +
        "font:13px/1.4 system-ui,sans-serif;padding:10px 40px 10px 12px;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.35);" +
        "max-height:35vh;overflow:auto";
      b.innerHTML = '<b>Rebajitas COD · diagnóstico (solo lo ves tú)</b><button type="button" aria-label="Cerrar diagnóstico" ' +
        'style="position:absolute;top:6px;right:6px;width:28px;height:28px;border:0;border-radius:50%;background:#333;color:#fff;font-size:16px;cursor:pointer">×</button>';
      b.querySelector("button").addEventListener("click", function () { b.remove(); });
      document.body.appendChild(b);
    }
    var l = document.createElement("div");
    l.textContent = (ok ? "✔ " : "✖ ") + texto;
    l.style.color = ok ? "#7ee2b0" : "#ff9b93";
    b.appendChild(l);
  }
  // Esconde "Add to cart", la cantidad y "Comprar ya" del tema (solo se llama si nuestro botón ya está visible).
  function ocultarCompraDelTema() {
    var f = formProducto();
    if (!f) return;
    var cont = f.closest("product-form") || f;
    var partes = [].slice.call(cont.querySelectorAll('button[name="add"], [type="submit"], .shopify-payment-button, .product-form__buttons'));
    var cantidad = document.querySelector('.product-form__quantity, quantity-input');
    if (cantidad) partes.push(cantidad.closest(".product-form__input") || cantidad);
    var raizBoton = document.getElementById("rebajitas-cod");
    partes.forEach(function (el) {
      if (raizBoton && el.contains(raizBoton)) return;  // nunca esconder nuestro propio botón
      el.style.setProperty("display", "none", "important");
    });
  }

  // Formulario de compra del producto principal (se ignora el de cuotas que algunos temas tienen).
  function formProducto() {
    var forms = [].slice.call(document.querySelectorAll('form[action*="/cart/add"]'))
      .filter(function (f) { return !/installment/i.test((f.id || "") + " " + (f.className || "")) && f.querySelector('[name="id"]'); });
    var principal = forms.filter(function (f) { return f.closest("main, #MainContent, .product, product-info"); });
    return principal[0] || forms[0] || null;
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", arrancar);
  else arrancar();

  function arrancar() {
  aviso("El programa del botón cargó desde " + SERVIDOR, true);
  // Puede haber un bloque pegado a mano en la plantilla y/o el automático del tema (data-auto).
  // Gana el pegado a mano; el automático se coloca solo debajo del botón de compra del producto.
  var raices = [].slice.call(document.querySelectorAll('[id="rebajitas-cod"]'));
  var manuales = raices.filter(function (r) { return !r.dataset.auto; });
  var raiz = manuales[0] || raices[0];
  if (!raiz) { aviso("No encontré el bloque del botón en esta página. Revisa que el código esté en el tema (theme.liquid) o el bloque en la plantilla.", false); return; }
  if (raiz.dataset.listo) return;
  raices.forEach(function (r) { if (r !== raiz && !r.dataset.listo) r.remove(); });
  if (manuales.length > 1) aviso("El bloque del botón está pegado más de una vez en esta página: deja solo uno.", false);
  // Un bloque pegado a mano FUERA de la información del producto (ej. una sección "Liquid personalizado" suelta
  // al final de la página, como pasó en Pysta) se trata igual que el automático: se mueve bajo la compra o el precio.
  var ZONA_PRODUCTO = "product-info, .product__info-container, .product__info-wrapper, .product-single__meta, .product__info";
  var fueraDeLugar = !raiz.dataset.auto && !raiz.closest(ZONA_PRODUCTO) && document.querySelector(ZONA_PRODUCTO);
  if (fueraDeLugar) aviso("El bloque del botón estaba fuera de la información del producto: lo moví debajo del botón de compra o del precio.", true);
  if (raiz.dataset.auto || fueraDeLugar) {
    // Debajo del botón de compra; si la plantilla no lo tiene, debajo del precio o del título del producto.
    var anclaForm = formProducto();
    var ancla = anclaForm ? (anclaForm.closest("product-form") || anclaForm)
      : document.querySelector('product-info [id^="price-"], .product__info-container [id^="price-"], .product__info-container .price, product-info .price') ||
        document.querySelector("product-info .product__title, .product__info-container .product__title, .product__title, .product-single__title");
    if (!ancla) { aviso("No encontré dónde poner el botón (ni botón de compra, ni precio, ni título del producto).", false); return; }
    ancla.parentNode.insertBefore(raiz, ancla.nextSibling);
    raiz.hidden = false;
    raiz.style.marginTop = "12px";
  }
  raiz.dataset.listo = "1";
  var VARIANTE = raiz.dataset.variante || "";
  var IMAGEN = raiz.dataset.imagen || "";

  var CSS = `
:host{display:block}
*{box-sizing:border-box}
.w{--ink:#14181b;--muted:#5d6865;--line:#dfe5e2;--field:#f4f7f5;--sheet:#fff;--accent:#0d7a50;--accent-soft:#e3f3ec;--danger:#c2372f;--r:14px;
  font-family:inherit;color:var(--ink);font-size:15px;line-height:1.45;letter-spacing:normal;text-transform:none;text-align:left;-webkit-font-smoothing:antialiased}
button{font-family:inherit}
.abrir{width:100%;border:0;border-radius:var(--r);background:var(--accent);color:#fff;cursor:pointer;padding:15px 16px;display:flex;flex-direction:column;align-items:center;gap:2px;
  box-shadow:0 10px 24px -10px rgba(13,122,80,.7);transition:filter .15s,transform .1s;animation:latido 2.6s ease-in-out 1.5s infinite}
.abrir:hover{filter:brightness(1.06)} .abrir:active{transform:translateY(1px)}
.abrir:focus-visible,.cta:focus-visible{outline:3px solid var(--ink);outline-offset:2px}
.abrir b{font-size:17px;font-weight:800;letter-spacing:.01em} .abrir span{font-size:13px;opacity:.92}
@keyframes latido{0%,100%{transform:scale(1)}50%{transform:scale(1.015)}}
.fondo{position:fixed;inset:0;z-index:2147483000;background:rgba(14,22,18,.55);display:flex;align-items:flex-end;justify-content:center;opacity:0;transition:opacity .2s}
.fondo.vis{opacity:1}
.sheet{width:100%;max-width:460px;max-height:94vh;overflow-y:auto;background:var(--sheet);border-radius:22px 22px 0 0;box-shadow:0 30px 80px -20px rgba(20,40,30,.45);
  transform:translateY(24px);transition:transform .25s cubic-bezier(.2,.8,.2,1);padding-bottom:env(safe-area-inset-bottom,0px);overscroll-behavior:contain}
.fondo.vis .sheet{transform:none}
@media (min-width:600px){.fondo{align-items:center;padding:24px}.sheet{border-radius:24px;max-height:92vh}}
.head{display:flex;gap:14px;align-items:center;padding:18px 20px 14px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--sheet);z-index:1}
.thumb{width:54px;height:54px;border-radius:14px;flex:none;background:var(--field) center/cover no-repeat}
.head-txt{min-width:0;flex:1}
.head h2{margin:0;font-size:17px;font-weight:800;letter-spacing:-.01em}
.head p{margin:2px 0 0;color:var(--muted);font-size:13px}
.cerrar{width:36px;height:36px;border-radius:50%;border:0;background:var(--field);color:var(--ink);font-size:20px;line-height:1;cursor:pointer;flex:none}
.aviso{display:inline-block;margin-top:6px;font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#8a5a00;background:#fbf0d9;padding:3px 8px;border-radius:999px}
form{padding:20px;display:flex;flex-direction:column;gap:22px;margin:0}
.sec{margin:0 0 10px;font-size:12.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.ofertas{display:flex;flex-direction:column;gap:10px}
.oferta{position:relative;display:flex;align-items:center;gap:12px;padding:14px;border:1.5px solid var(--line);border-radius:var(--r);cursor:pointer;transition:border-color .15s,background .15s}
.oferta input{position:absolute;opacity:0;pointer-events:none}
.dot{width:20px;height:20px;border-radius:50%;border:2px solid #b9c4bf;flex:none;display:grid;place-items:center}
.dot::after{content:"";width:10px;height:10px;border-radius:50%;background:var(--accent);transform:scale(0);transition:transform .15s}
.oferta.sel{border-color:var(--accent);background:var(--accent-soft)} .oferta.sel .dot{border-color:var(--accent)} .oferta.sel .dot::after{transform:scale(1)}
.oferta:focus-within{outline:2px solid var(--accent);outline-offset:2px}
.o-main{flex:1;min-width:0}
.o-img{width:48px;height:48px;border-radius:10px;flex:none;background:var(--field) center/cover no-repeat} .o-name{font-weight:700} .o-save{font-size:12.5px;color:var(--accent);font-weight:600}
.o-price{text-align:right;font-variant-numeric:tabular-nums} .o-price b{display:block;font-weight:800} .o-price s{color:var(--muted);font-size:12.5px}
.badge{position:absolute;top:-9px;right:14px;background:var(--ink);color:#fff;font-size:10.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:3px 8px;border-radius:999px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px} .full{grid-column:1/-1}
@media (max-width:360px){.grid{grid-template-columns:1fr}}
.campo{display:flex;flex-direction:column;gap:6px;min-width:0}
.campo label{font-size:13px;font-weight:600}
.of-info{background:var(--field);border-radius:12px;padding:10px 12px;font-size:13px;color:var(--muted);line-height:1.4}
.of-info b{color:var(--ink);font-weight:600}
.ctrl select.tipo{width:auto;flex:none;padding:0 6px 0 14px;font-weight:700;border-right:1.5px solid var(--line);border-radius:12px 0 0 12px}
.ctrl textarea{width:100%;min-width:0;min-height:76px;border:0;background:transparent;font:inherit;font-size:16px;color:var(--ink);padding:12px 14px;outline:none;resize:vertical;border-radius:12px}
.ctrl{position:relative;display:flex;align-items:center;background:var(--field);border:1.5px solid transparent;border-radius:12px;transition:border-color .15s,background .15s,box-shadow .15s}
.ctrl:focus-within{background:#fff;border-color:var(--accent);box-shadow:0 0 0 4px var(--accent-soft)}
.ctrl input,.ctrl select{width:100%;min-width:0;height:50px;border:0;background:transparent;font:inherit;font-size:16px;color:var(--ink);padding:0 14px;outline:none;appearance:none;-webkit-appearance:none;border-radius:12px}
.ctrl select{padding-right:40px;cursor:pointer}
.chev{position:absolute;right:14px;pointer-events:none;color:var(--muted)}
.prefijo{padding-left:14px;font-weight:600;color:var(--muted);display:flex;align-items:center;gap:6px;white-space:nowrap}
.prefijo + input{padding-left:8px}
.ayuda{font-size:12px;color:var(--muted)}
.campo.mal .ctrl{border-color:var(--danger);background:#fff} .campo.mal .ayuda{color:var(--danger)}
.resumen{border-top:1px dashed var(--line);padding-top:16px;display:flex;flex-direction:column;gap:6px;font-variant-numeric:tabular-nums}
.fila{display:flex;justify-content:space-between;gap:12px;color:var(--muted);font-size:14px}
.fila.total{color:var(--ink);font-weight:800;font-size:17px;margin-top:4px}
.incl{color:var(--accent);font-weight:600}
.cta{width:100%;border:0;border-radius:var(--r);background:var(--accent);color:#fff;cursor:pointer;padding:14px 16px;display:flex;flex-direction:column;align-items:center;gap:2px;box-shadow:0 10px 24px -10px rgba(13,122,80,.7)}
.cta b{font-size:16.5px;font-weight:800} .cta span{font-size:12.5px;opacity:.9}
.cta[disabled]{opacity:.7;cursor:progress}
.error{background:#fdecea;color:var(--danger);border-radius:12px;padding:12px 14px;font-size:14px;font-weight:600}
.confianza{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;font-size:12px;color:var(--muted)}
.confianza div{display:flex;align-items:center;gap:6px} .confianza svg{color:var(--accent);flex:none}
.listo{padding:36px 24px 28px;text-align:center;display:flex;flex-direction:column;gap:14px;align-items:center}
.check{width:64px;height:64px;border-radius:50%;background:var(--accent-soft);display:grid;place-items:center;color:var(--accent)}
.listo h2{margin:0;font-size:22px;font-weight:800}
.listo p{margin:0;color:var(--muted);max-width:32ch}
.recap{width:100%;background:var(--field);border-radius:var(--r);padding:14px 16px;text-align:left;font-size:14px;display:flex;flex-direction:column;gap:6px}
.recap div{display:flex;justify-content:space-between;gap:12px} .recap span:first-child{color:var(--muted)} .recap span:last-child{font-weight:600;text-align:right}
.wa{width:100%;border-radius:var(--r);background:#1fa855;color:#fff;text-decoration:none;font-weight:800;font-size:16.5px;padding:15px 16px;display:flex;align-items:center;justify-content:center;gap:10px;box-shadow:0 10px 24px -10px rgba(31,168,85,.75)}
.wa:hover{filter:brightness(1.05)} .wa:focus-visible{outline:3px solid var(--ink);outline-offset:2px}
[hidden]{display:none!important}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
`;

  var CHEV = '<svg class="chev" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>';
  var WHATSAPP = '<svg width="16" height="16" viewBox="0 0 24 24" fill="#25a35a" aria-hidden="true"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm5.3 14.2c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .2-3.3-.7-2.8-1.1-4.5-4-4.7-4.2-.1-.2-1.1-1.5-1.1-2.8s.7-2 1-2.3c.2-.3.5-.3.7-.3h.5c.2 0 .4 0 .6.5l.9 2.1c.1.2.1.4 0 .5l-.4.6-.4.4c-.1.2-.3.3-.1.6.2.3.8 1.3 1.7 2.1 1.2 1 2.1 1.3 2.4 1.5.3.1.5.1.6-.1l.9-1c.2-.3.4-.2.6-.1l2 .9c.3.2.5.2.5.4.1.1.1.7-.1 1.3z"/></svg>';

  var datos = null, elegida = 0;
  var COLOR_ETIQUETA = { negro: "#14181b", verde: "#0d7a50", rojo: "#c2372f", dorado: "#b7862b", morado: "#6b3fa0", azul: "#1f5fbf" };

  // UTM de la publicidad: se guardan al llegar a la tienda para enviarlas con el pedido aunque el cliente navegue.
  var UTM = (function () {
    var campos = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"], u = {}, hay = false;
    // Se leen "en crudo" para conservar los "+" tal como los manda Facebook (ej. IMG+5), igual que Releasit.
    location.search.replace(/^\?/, "").split("&").forEach(function (par) {
      var i = par.indexOf("="), k = i < 0 ? par : par.slice(0, i), val = i < 0 ? "" : par.slice(i + 1);
      try { val = decodeURIComponent(val); } catch (e) { /* se deja tal cual */ }
      if (campos.indexOf(k) >= 0 && val) { u[k] = val; hay = true; }
    });
    try {
      if (hay) sessionStorage.setItem("rebajitas_cod_utm", JSON.stringify(u));
      else u = JSON.parse(sessionStorage.getItem("rebajitas_cod_utm") || "{}");
    } catch (e) { /* sin almacenamiento: se usan solo las de esta página */ }
    return u;
  })();

  function esc(t) { return String(t == null ? "" : t).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function dinero(n, moneda) {
    var s = Number(n).toFixed(2).replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return (moneda === "VES" || moneda === "VED" ? "Bs.S. " : (moneda || "") + " ") + s;
  }
  function unidades(q) { return q + (q === 1 ? " unidad" : " unidades"); }

  // ---- Botón en la página del producto ----
  // Algunos temas (como Dawn) esconden las cajas "vacías" (div:empty). La nuestra se dibuja por dentro,
  // así que forzamos que se muestre.
  raiz.style.setProperty("display", "block", "important");
  var sombraBoton = raiz.attachShadow({ mode: "open" });
  sombraBoton.innerHTML = "<style>" + CSS + '</style><div class="w"><button class="abrir" type="button" hidden><b>Pedir ahora · Pago al recibir</b><span>Retiro en TEALCA · Domicilio en Caracas y Miranda</span></button></div>';
  var boton = sombraBoton.querySelector(".abrir");

  function cargar(luegoAbrir) {
  boton.hidden = true;
  fetch(SERVIDOR + "/api/producto/" + encodeURIComponent(VARIANTE))
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) {
      datos = d;
      aviso("Bloque encontrado y producto leído: " + d.titulo + " (" + d.ofertas.length + " oferta" + (d.ofertas.length === 1 ? "" : "s") + ")" +
        (d.modo_prueba ? " · modo prueba" : ""), true);
      if (!d.disponible) { aviso("Shopify dice que el producto está agotado: por eso el botón no se muestra.", false); return; }
      elegida = Math.max(0, d.ofertas.map(function (o) { return !!o.preseleccionada; }).indexOf(true));
      boton.querySelector("b").textContent = "Pedir ahora · " + dinero(d.ofertas[0].precio, d.moneda);
      boton.hidden = false;
      if (d.ocultar_carrito) ocultarCompraDelTema();
      if (luegoAbrir) abrir();
    })
    .catch(function (err) {
      // Si el servidor no responde, no se muestra el botón y la tienda sigue normal.
      var motivo = !VARIANTE ? "falta el producto en el bloque"
        : err && err.message === "502" ? "el servidor no pudo leer el producto en Shopify (revisa la conexión en " + SERVIDOR + ")"
        : err && /^\d+$/.test(err.message) ? "el servidor respondió con error " + err.message
        : "no se pudo conectar con el servidor (" + SERVIDOR + ") desde esta dirección: " + location.hostname;
      aviso(motivo, false);
    });
  }
  cargar(false);

  // Si el producto tiene variantes (talla, sabor…), se usa la que el cliente tenga elegida en la página.
  function varianteActual() {
    var f = formProducto(), i = f && f.querySelector('[name="id"]');
    return (i && i.value) || VARIANTE;
  }
  function cambiarVariante(luegoAbrir) {
    var v = varianteActual();
    if (!v || v === VARIANTE) return false;
    VARIANTE = v;
    datos = null;
    if (capa) { capa.remove(); capa = null; }
    cargar(luegoAbrir);
    return true;
  }
  document.addEventListener("change", function (e) {
    var f = formProducto();
    if (f && (f.contains(e.target) || (e.target.closest && e.target.closest("variant-selects, variant-radios, .product-form__input")))) {
      setTimeout(function () { cambiarVariante(false); }, 150);
    }
  });
  boton.addEventListener("click", function () { if (!cambiarVariante(true)) abrir(); });

  // ---- Ventana del formulario ----
  var capa = null, sombra = null, ultimoFoco = null, scrollPrevio = "";

  function abrir() {
    if (!datos) return;
    ultimoFoco = document.activeElement;
    if (!capa) construir();
    sombra.querySelector("form").hidden = false;
    sombra.querySelector(".listo").hidden = true;
    capa.style.setProperty("display", "block", "important");
    scrollPrevio = document.documentElement.style.overflow;
    document.documentElement.style.overflow = "hidden";
    requestAnimationFrame(function () { sombra.querySelector(".fondo").classList.add("vis"); });
    setTimeout(function () { sombra.querySelector("#nombre").focus({ preventScroll: true }); }, 250);
    pixel("abrir");
  }
  function cerrar() {
    sombra.querySelector(".fondo").classList.remove("vis");
    document.documentElement.style.overflow = scrollPrevio;
    setTimeout(function () { capa.style.setProperty("display", "none", "important"); if (ultimoFoco) ultimoFoco.focus(); }, 200);
  }
  // ---- Píxel de Meta: InitiateCheckout al abrir, Purchase al crear el pedido ----
  // El Purchase lleva el mismo número de evento que el que manda el servidor (API de conversiones): Meta lo cuenta una vez.
  var pixelesIniciados = {};
  function prepararPixel(cfg) {
    if (!window.fbq) {
      /* Código base oficial de Meta */
      !function (f, b, e, v, n, t, s) { if (f.fbq) return; n = f.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); };
        if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = "2.0"; n.queue = []; t = b.createElement(e); t.async = !0; t.src = v;
        s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s); }(window, document, "script", "https://connect.facebook.net/en_US/fbevents.js");
    }
    cfg.ids.forEach(function (id) { if (!pixelesIniciados[id]) { window.fbq("init", id); pixelesIniciados[id] = 1; } });
  }
  function pixel(tipo, extra) {
    var cfg = datos && datos.pixel;
    if (!cfg || !cfg.activo || !cfg.ids || !cfg.ids.length) return;
    try {
      prepararPixel(cfg);
      var o = oferta(), id = String(datos.producto_id || VARIANTE);
      var params = { value: o.precio, currency: cfg.moneda, content_type: "product", content_ids: [id], content_name: datos.titulo,
        num_items: o.cantidad, contents: [{ id: id, quantity: o.cantidad }] };
      if (tipo === "abrir" && cfg.iniciar_compra) {
        cfg.ids.forEach(function (pid) { window.fbq("trackSingle", pid, "InitiateCheckout", params); });
      }
      if (tipo === "compra" && extra && extra.evento) {
        var evento = { eventID: extra.evento };
        cfg.ids.forEach(function (pid) { window.fbq("trackSingle", pid, "Purchase", params, evento); });
      }
      aviso("Píxel: " + (tipo === "abrir" ? "InitiateCheckout" : "Purchase") + " enviado a " + cfg.ids.join(", "), true);
    } catch (e) { /* el píxel nunca debe impedir una compra */ }
  }
  // Cookies del píxel (_fbp, _fbc) para que Meta reconozca la compra hecha desde un anuncio.
  function datosNavegador() {
    var c = function (n) { var m = document.cookie.match(new RegExp("(?:^|; )" + n + "=([^;]*)")); return m ? decodeURIComponent(m[1]) : ""; };
    var fbc = c("_fbc"), clic = (location.search.match(/[?&]fbclid=([^&]+)/) || [])[1];
    if (!fbc && clic) fbc = "fb.1." + Date.now() + "." + clic;
    return { fbp: c("_fbp"), fbc: fbc, url: location.href.split("#")[0] };
  }

  function construir() {
    var d = datos;
    capa = document.createElement("div");
    capa.id = "rebajitas-cod-ventana";
    capa.style.setProperty("display", "block", "important");
    document.body.appendChild(capa);
    sombra = capa.attachShadow({ mode: "open" });
    var titulo = d.titulo + (d.variante ? " · " + d.variante : "");
    var ofertas = d.ofertas.map(function (o, i) {
      var ahorro = o.antes - o.precio;
      return '<label class="oferta"' + (d.ofertas.length === 1 ? ' hidden' : '') + '>' +
        (o.etiqueta ? '<span class="badge" style="background:' + (COLOR_ETIQUETA[o.color] || COLOR_ETIQUETA.negro) + '">' + esc(o.etiqueta) + '</span>' : '') +
        '<input type="radio" name="oferta" value="' + i + '"' + (i === elegida ? ' checked' : '') + '>' +
        '<span class="dot"></span>' + (o.imagen ? '<span class="o-img" style="background-image:url(\'' + esc(o.imagen) + '\')"></span>' : '') +
        '<span class="o-main"><span class="o-name">' + esc(o.titulo || unidades(o.cantidad)) + '</span><br>' +
        '<span class="o-save">' + esc(o.subtitulo || (ahorro > 0 ? 'Ahorras ' + dinero(ahorro, d.moneda) : 'Precio normal')) + '</span></span>' +
        '<span class="o-price"><b>' + dinero(o.precio, d.moneda) + '</b>' + (ahorro > 0 ? '<s>' + dinero(o.antes, d.moneda) + '</s>' : '') + '</span></label>';
    }).join("");
    var estados = d.estados.map(function (e) { return '<option>' + esc(e) + '</option>'; }).join("");

    sombra.innerHTML = "<style>" + CSS + "</style>" +
      '<div class="w"><div class="fondo"><div class="sheet" role="dialog" aria-modal="true" aria-labelledby="t">' +
      '<div class="head">' + (IMAGEN ? '<div class="thumb" style="background-image:url(\'' + esc(IMAGEN) + '\')"></div>' : '') +
      '<div class="head-txt"><h2 id="t">' + esc(titulo) + '</h2><p id="h-sub">Pagas al retirar en tu oficina TEALCA</p>' +
      (d.modo_prueba ? '<span class="aviso">Modo prueba · no crea pedidos reales</span>' : '') + '</div>' +
      '<button class="cerrar" type="button" aria-label="Cerrar">×</button></div>' +
      '<form novalidate>' +
      (d.ofertas.length > 1 ? '<section><h3 class="sec">Elige tu oferta</h3><div class="ofertas">' + ofertas + '</div></section>' : '<div hidden>' + ofertas + '</div>') +
      '<section><h3 class="sec">Datos para el envío</h3><div class="grid">' +
      campo("nombre", "Nombre", '<input id="nombre" autocomplete="given-name" placeholder="Juan" maxlength="50">') +
      campo("apellido", "Apellido", '<input id="apellido" autocomplete="family-name" placeholder="Hernández" maxlength="50">') +
      campo("telefono", "WhatsApp", '<span class="prefijo">' + WHATSAPP + '+58</span><input id="telefono" type="tel" inputmode="numeric" autocomplete="tel-national" placeholder="414 123 4567" maxlength="20">', "full", "Te escribiremos por aquí para confirmar tu pedido") +
      campo("estado", "Estado", '<select id="estado"><option value="">Selecciona tu estado</option>' + estados + '</select>' + CHEV, "full") +
      '<div class="campo full" data-campo="ciudad"><label for="ciudad">Ciudad</label><div class="ctrl" id="ctrl-ciudad"></div>' +
      '<div class="ayuda" hidden></div></div>' +
      '<div class="campo full" data-campo="oficina"><label for="oficina">Oficina TEALCA para retirar</label><div class="ctrl" id="ctrl-oficina"></div><div class="of-info" id="of-info" hidden></div><div class="ayuda" hidden></div></div>' +
      '<div class="campo full" data-campo="direccion" hidden><label for="direccion">Dirección de entrega</label><div class="ctrl">' +
      '<textarea id="direccion" autocomplete="street-address" maxlength="250" placeholder="Calle o avenida, edificio o casa, piso/apto"></textarea></div>' +
      '<div class="ayuda" data-normal="Entrega a domicilio: escribe la dirección completa">Entrega a domicilio: escribe la dirección completa</div></div>' +
      '<div class="campo full" data-campo="referencia" hidden><label for="referencia">Punto de referencia (opcional)</label><div class="ctrl">' +
      '<input id="referencia" maxlength="300" placeholder="Ej: frente a la panadería, portón negro"></div><div class="ayuda" hidden></div></div>' +
      '<div class="campo full" data-campo="cedula"><label for="cedula" id="l-cedula">Cédula de quien retira</label><div class="ctrl">' +
      '<select id="cedula-tipo" class="tipo" aria-label="Tipo de documento">' + (d.tipos_cedula || ["V", "E"]).map(function (t) { return "<option>" + esc(t) + "</option>"; }).join("") + '</select>' +
      '<input id="cedula" inputmode="numeric" placeholder="12345678" maxlength="10"></div><div class="ayuda" hidden></div></div>' +
      '</div></section>' +
      '<div class="resumen"><div class="fila"><span id="r-cant"></span><span id="r-sub"></span></div>' +
      '<div class="fila"><span id="r-envio">Envío a oficina TEALCA</span><span class="incl">Incluido</span></div>' +
      '<div class="fila total"><span id="r-total-txt">Total a pagar al retirar</span><span id="r-total"></span></div></div>' +
      '<div class="error" hidden></div>' +
      '<button class="cta" type="submit"><b>Confirmar pedido</b><span>No pagas nada ahora</span></button>' +
      '<div class="confianza"><div><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M3 7h18v10H3z"/><circle cx="12" cy="12" r="2.5"/></svg>Pagas al recibir</div>' +
      '<div><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 12a9 9 0 1 1-4-7.5L21 3v5h-5"/></svg>Confirmación por WhatsApp</div>' +
      '<div><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>Datos protegidos</div></div>' +
      '</form>' +
      '<div class="listo" hidden><div class="check"><svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><path d="m5 12 5 5 9-10"/></svg></div>' +
      '<h2 id="l-t"></h2><p>Te enviamos un mensaje por WhatsApp para confirmar tu pedido. Respóndelo para que podamos despacharlo.</p><div class="recap" id="recap"></div>' +
      '<a class="wa" id="l-wa" target="_blank" rel="noopener">' + WHATSAPP.replace('fill="#25a35a"', 'fill="#fff"').replace('width="16" height="16"', 'width="22" height="22"') + 'Ir a WhatsApp a confirmar mi pedido</a></div>' +
      '</div></div></div>';

    var $ = function (s) { return sombra.querySelector(s); };
    $(".cerrar").addEventListener("click", cerrar);
    $(".fondo").addEventListener("click", function (e) { if (e.target === e.currentTarget) cerrar(); });
    sombra.addEventListener("keydown", function (e) { if (e.key === "Escape") cerrar(); });

    sombra.querySelectorAll('input[name=oferta]').forEach(function (r) { r.addEventListener("change", resumen); });
    $("#estado").addEventListener("change", function () { ciudades(); oficinas(); entrega(); });
    $("#cedula").addEventListener("input", function (e) { e.target.value = e.target.value.replace(/\D/g, "").slice(0, 9); });
    $("#telefono").addEventListener("input", function (e) {
      // Acepta 4141234567, 04141234567 o +58 414-1234567 (escrito o pegado) y lo deja como "414 123 4567".
      var n = e.target.value.replace(/\D/g, "");
      if (/^58[24]\d{9}/.test(n)) n = n.slice(2);
      n = n.replace(/^0/, "").slice(0, 10);
      e.target.value = n.replace(/^(\d{3})(\d{0,3})(\d{0,4}).*/, function (m, a, b, c) { return [a, b, c].filter(Boolean).join(" "); });
    });
    sombra.addEventListener("input", function (e) { var c = e.target.closest(".campo"); if (c && e.target.value.trim()) marcar(c.dataset.campo, null); });
    $("form").addEventListener("submit", enviar);
    ciudades();
    oficinas();
    entrega();
    resumen();
  }

  function campo(id, etiqueta, control, clase, ayuda) {
    return '<div class="campo ' + (clase || "") + '" data-campo="' + id + '"><label for="' + id + '">' + etiqueta + '</label><div class="ctrl">' + control + '</div>' +
      '<div class="ayuda"' + (ayuda ? ' data-normal="' + esc(ayuda) + '"' : ' hidden') + '>' + esc(ayuda || "") + '</div></div>';
  }

  // Cascada Estado → Ciudad → Oficina, todo desde el catálogo de oficinas de DroPanas.
  function ciudades() {
    var estado = sombra.querySelector("#estado").value;
    var lista = (datos.ciudades || {})[estado] || [];
    var ctrl = sombra.querySelector("#ctrl-ciudad");
    ctrl.innerHTML = !estado
      ? '<select id="ciudad" disabled><option value="">Primero elige tu estado</option></select>' + CHEV
      : '<select id="ciudad"><option value="">Selecciona tu ciudad</option>' +
        lista.map(function (c) { return "<option>" + esc(c) + "</option>"; }).join("") + "</select>" + CHEV;
    var sel = sombra.querySelector("#ciudad");
    if (lista.length === 1) sel.value = lista[0];
    sel.addEventListener("change", function () { oficinas(); entrega(); });
  }
  function ciudadElegida() { return sombra.querySelector("#ciudad").value; }
  // Entrega a domicilio (ej. Caracas): se cambia la oficina por la dirección y se ajustan los textos.
  function esDomicilio() {
    var estado = sombra.querySelector("#estado").value, ciudad = sombra.querySelector("#ciudad").value;
    var regla = (datos.domicilio || {})[estado] || [];
    return regla === "*" ? !!estado : regla.indexOf(ciudad) >= 0;
  }
  function entrega() {
    var dom = esDomicilio(), $ = function (q) { return sombra.querySelector(q); };
    $('[data-campo="oficina"]').hidden = dom;
    $('[data-campo="direccion"]').hidden = !dom;
    $('[data-campo="referencia"]').hidden = !dom;
    $("#l-cedula").textContent = dom ? "Cédula de quien recibe" : "Cédula de quien retira";
    $("#h-sub").textContent = dom ? "Entrega a domicilio · Pagas al recibir" : "Pagas al retirar en tu oficina TEALCA";
    $("#r-envio").textContent = dom ? "Entrega a domicilio" : "Envío a oficina TEALCA";
    $("#r-total-txt").textContent = dom ? "Total a pagar al recibir" : "Total a pagar al retirar";
  }

  function oficinas() {
    var estado = sombra.querySelector("#estado").value, ciudad = ciudadElegida();
    var lista = (datos.oficinas || []).filter(function (o) { return o.e === estado && o.c === ciudad; });
    var ctrl = sombra.querySelector("#ctrl-oficina"), info = sombra.querySelector("#of-info");
    ctrl.innerHTML = !ciudad
      ? '<select id="oficina" disabled><option value="">Primero elige tu ciudad</option></select>' + CHEV
      : '<select id="oficina"><option value="">Selecciona una oficina</option>' +
        lista.map(function (o) { return '<option value="' + o.id + '">' + esc(o.n) + "</option>"; }).join("") + "</select>" + CHEV;
    var sel = sombra.querySelector("#oficina");
    if (lista.length === 1) sel.value = String(lista[0].id);
    function mostrar() {
      var o = lista.filter(function (x) { return String(x.id) === sel.value; })[0];
      info.hidden = !o;
      info.innerHTML = o ? "<b>" + esc(o.n) + "</b><br>" + esc(o.d) + (o.h ? "<br>Horario: " + esc(o.h) : "") : "";
    }
    sel.addEventListener("change", mostrar);
    mostrar();
  }

  function oferta() { var r = sombra.querySelector('input[name=oferta]:checked'); return datos.ofertas[r ? +r.value : 0]; }
  function resumen() {
    var o = oferta(), m = datos.moneda;
    sombra.querySelectorAll(".oferta").forEach(function (l) { l.classList.toggle("sel", l.querySelector("input").checked); });
    sombra.querySelector("#r-cant").textContent = datos.titulo + " × " + o.cantidad;
    sombra.querySelector("#r-sub").textContent = dinero(o.precio, m);
    sombra.querySelector("#r-total").textContent = dinero(o.precio, m);
    sombra.querySelector(".cta b").textContent = "Confirmar pedido · " + dinero(o.precio, m);
  }

  function marcar(id, mensaje) {
    var c = sombra.querySelector('[data-campo="' + id + '"]');
    if (!c) return;
    var a = c.querySelector(".ayuda");
    c.classList.toggle("mal", !!mensaje);
    if (mensaje) { a.textContent = mensaje; a.hidden = false; }
    else if (a.dataset.normal) { a.textContent = a.dataset.normal; }
    else { a.hidden = true; }
  }

  function enviar(e) {
    e.preventDefault();
    var $ = function (s) { return sombra.querySelector(s); };
    var valores = {
      nombre: $("#nombre").value, apellido: $("#apellido").value, telefono: $("#telefono").value,
      estado: $("#estado").value, ciudad: ciudadElegida(), oficina_id: $("#oficina").value,
      direccion: $("#direccion").value, referencia: $("#referencia").value,
      cedula: $("#cedula-tipo").value + "-" + $("#cedula").value
    };
    var dom = esDomicilio();
    if (dom) valores.oficina_id = ""; else { valores.direccion = ""; valores.referencia = ""; }
    var ofi = (datos.oficinas || []).filter(function (o) { return String(o.id) === valores.oficina_id; })[0];
    var errores = {};
    if (!valores.nombre.trim()) errores.nombre = "Escribe tu nombre";
    if (!valores.apellido.trim()) errores.apellido = "Escribe tu apellido";
    if (!/^(4(12|14|16|22|24|26)|2\d\d)\d{7}$/.test(valores.telefono.replace(/\D/g, ""))) errores.telefono = "Revisa el número: debe ser venezolano, ej. 0414 123 4567";
    if (!valores.estado) errores.estado = "Selecciona tu estado";
    if (!valores.ciudad.trim()) errores.ciudad = "Selecciona tu ciudad";
    if (!dom && !ofi) errores.oficina = "Elige la oficina donde vas a retirar";
    if (dom && !valores.direccion.trim()) errores.direccion = "Escribe la dirección de entrega";
    if (!/^\d{7,9}$/.test($("#cedula").value)) errores.cedula = "Revisa la cédula: de 7 a 9 números, ej. 20216018";
    if (mostrarErrores(errores)) return;

    var cta = $(".cta"), caja = $(".error");
    caja.hidden = true;
    cta.disabled = true;
    cta.querySelector("b").textContent = "Enviando tu pedido…";
    valores.variante = VARIANTE;
    valores.oferta = datos.ofertas.indexOf(oferta());
    valores.utm = UTM;
    valores.navegador = datosNavegador();

    fetch(SERVIDOR + "/api/pedido", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(valores) })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.j && res.j.errores) { mostrarErrores(res.j.errores); return; }
        if (!res.ok || !res.j.ok) throw new Error((res.j && res.j.error) || "");
        // Todo lo que se muestra viene del servidor: es exactamente el pedido que se acaba de guardar en Shopify.
        var r = res.j;
        $("#l-t").textContent = "¡Listo, " + valores.nombre.trim().split(" ")[0] + "! Recibimos tu pedido";
        // El número de pedido NO se muestra al cliente (es confidencial).
        $("#recap").innerHTML = [["Producto", r.producto + " × " + r.cantidad],
          [r.domicilio ? "Total al recibir" : "Total al retirar", dinero(r.total, r.moneda)],
          ["Teléfono", r.telefono], r.domicilio ? ["Entrega", r.entrega] : ["Retiro", r.entrega], ["Cédula", r.cedula]]
          .map(function (f) { return "<div><span>" + esc(f[0]) + "</span><span>" + esc(f[1]) + "</span></div>"; }).join("");
$("#l-wa").href = "https://wa.me/" + (datos.whatsapp || "");
        $("form").hidden = true;
        $(".listo").hidden = false;
        $(".sheet").scrollTop = 0;
        pixel("compra", res.j);
      })
      .catch(function (err) {
        caja.textContent = (err && err.message) || "No pudimos registrar tu pedido. Revisa tu conexión e intenta de nuevo.";
        caja.hidden = false;
      })
      .then(function () { cta.disabled = false; resumen(); });
  }

  function mostrarErrores(errores) {
    var primero = null;
    ["nombre", "apellido", "telefono", "estado", "ciudad", "oficina", "direccion", "referencia", "cedula"].forEach(function (id) {
      marcar(id, errores[id] || null);
      if (errores[id] && !primero) primero = sombra.querySelector("#" + id);
    });
    if (primero) primero.focus();
    return !!primero;
  }
  }
})();
