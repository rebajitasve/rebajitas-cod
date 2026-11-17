/* Menú "Ofertas" de la app Rebajitas Form (se abre dentro del panel de Shopify). */
(function () {
  "use strict";
  var $ = function (s) { return document.querySelector(s); };
  var COLORES = { negro: "#14181b", verde: "#0d7a50", rojo: "#c2372f", dorado: "#b7862b", morado: "#6b3fa0", azul: "#1f5fbf" };
  var NOMBRE_COLOR = { negro: "Negro", verde: "Verde", rojo: "Rojo", dorado: "Dorado", morado: "Morado", azul: "Azul" };
  var ETIQUETAS = ["Más vendido", "Mayor ahorro", "Mejor precio", "Recomendado", "Oferta", "🔥 Más vendido", "⭐ Favorito", "🎁 Regalo"];
  var datos = null, producto = null, cfg = null, original = "";

  function esc(t) { return String(t == null ? "" : t).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function dinero(n) { return "Bs.S. " + Number(n).toFixed(2).replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, "."); }
  function unidades(q) { return q + (q === 1 ? " unidad" : " unidades"); }
  function avisar(texto, error) {
    if (window.shopify && shopify.toast) shopify.toast.show(texto, { isError: !!error });
    else alert(texto);
  }

  // Pide los datos con la sesión de Shopify (el servidor la revisa).
  function api(ruta, opciones) {
    opciones = opciones || {};
    var token = (window.shopify && shopify.idToken) ? shopify.idToken() : Promise.resolve("");
    return token.then(function (t) {
      opciones.headers = Object.assign({ "Content-Type": "application/json" }, opciones.headers || {}, t ? { Authorization: "Bearer " + t } : {});
      return fetch(ruta, opciones);
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, estado: r.status, j: j }; });
    });
  }

  // ---------- Lista de productos ----------
  function cargar() {
    api("/panel-api/productos").then(function (res) {
      if (!res.ok) { $("#lista").innerHTML = '<div class="vacio">' + esc(res.j.error || "No pudimos cargar los productos.") + "</div>"; return; }
      datos = res.j;
      pintarLista();
    }).catch(function () { $("#lista").innerHTML = '<div class="vacio">No pudimos conectar con la app. Recarga la página.</div>'; });
  }

  function pintarLista() {
    var q = ($("#buscar").value || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    var lista = datos.productos.filter(function (p) {
      return !q || p.titulo.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").indexOf(q) >= 0;
    });
    if (!lista.length) { $("#lista").innerHTML = '<div class="vacio">No hay productos con ese nombre.</div>'; return; }
    $("#lista").innerHTML = lista.map(function (p) {
      var n = (p.config.ofertas || []).length, act = p.config.activo && n;
      return '<div class="fila" role="button" tabindex="0" data-id="' + esc(p.id) + '">' +
        '<div class="mini" style="background-image:url(\'' + esc(p.foto) + '\')"></div>' +
        '<div class="txt"><div class="nombre">' + esc(p.titulo) + '</div><div class="ayuda" style="margin:0">' + dinero(p.precio) +
        (p.estado !== "ACTIVE" ? ' · <span class="chip borrador">' + (p.estado === "DRAFT" ? "Borrador" : "Archivado") + "</span>" : "") + "</div></div>" +
        '<span class="chip' + (act ? " si" : "") + '">' + (act ? n + (n === 1 ? " oferta activa" : " ofertas activas") : n ? "Ofertas apagadas" : "Sin ofertas") + "</span></div>";
    }).join("");
  }

  // ---------- Editor ----------
  function abrir(id) {
    producto = datos.productos.filter(function (p) { return p.id === id; })[0];
    if (!producto) return;
    cfg = JSON.parse(JSON.stringify(producto.config || { activo: false, ofertas: [] }));
    if (!cfg.ofertas) cfg.ofertas = [];
    original = JSON.stringify(cfg);
    $("#ed-titulo").textContent = producto.titulo;
    $("#ed-precio").textContent = "Precio de 1 unidad en Shopify: " + dinero(producto.precio);
    $("#ed-foto").style.backgroundImage = "url('" + (producto.foto || "") + "')";
    $("#vista-lista").hidden = true;
    $("#vista-editor").hidden = false;
    window.scrollTo(0, 0);
    pintarEditor();
  }

  function cerrar() {
    if (JSON.stringify(cfg) !== original && !confirm("Tienes cambios sin guardar. ¿Salir sin guardar?")) return;
    $("#vista-editor").hidden = true;
    $("#vista-lista").hidden = false;
    pintarLista();
  }

  function nueva(cantidad, tipo, valor, etiqueta) {
    return { cantidad: cantidad, tipo: tipo || "normal", valor: valor || 0, titulo: "", subtitulo: "", etiqueta: etiqueta || "",
      color: "negro", imagen: "", preseleccionada: false };
  }

  function campoTexto(i, clave, etiqueta, placeholder, max) {
    return '<label class="campo">' + etiqueta + '<input data-i="' + i + '" data-k="' + clave + '" maxlength="' + max + '" value="' +
      esc(cfg.ofertas[i][clave] || "") + '" placeholder="' + esc(placeholder) + '"></label>';
  }

  function pintarEditor() {
    $("#ed-activo").checked = !!cfg.activo;
    $("#ed-agregar").disabled = cfg.ofertas.length >= datos.maximo;
    $("#ed-ofertas").innerHTML = cfg.ofertas.length ? cfg.ofertas.map(function (o, i) {
      var fotos = (producto.fotos || []).slice(0, 12);
      return '<div class="of">' +
        '<div class="of-cab"><b>Oferta ' + (i + 1) + "</b>" +
        '<label class="interruptor" style="font-weight:500"><input type="radio" name="presel" data-i="' + i + '" data-k="preseleccionada"' + (o.preseleccionada ? " checked" : "") + "> Viene marcada</label>" +
        '<button class="boton chico fantasma peligro" data-quitar="' + i + '" type="button">Quitar</button></div>' +
        '<div class="rejilla">' +
          '<label class="campo">Cantidad<input type="number" min="1" max="' + datos.max_cantidad + '" data-i="' + i + '" data-k="cantidad" value="' + o.cantidad + '"></label>' +
          '<label class="campo">Precio<select data-i="' + i + '" data-k="tipo">' +
            '<option value="normal"' + (o.tipo === "normal" ? " selected" : "") + ">Precio normal</option>" +
            '<option value="precio"' + (o.tipo === "precio" ? " selected" : "") + ">Precio fijo total</option>" +
            '<option value="porcentaje"' + (o.tipo === "porcentaje" ? " selected" : "") + ">% de descuento</option></select></label>" +
          '<label class="campo"' + (o.tipo === "normal" ? " hidden" : "") + ">" + (o.tipo === "porcentaje" ? "Descuento (%)" : "Precio total (Bs.S.)") +
            '<input type="number" min="0" step="any" data-i="' + i + '" data-k="valor" value="' + (o.valor || "") + '"></label>' +
        "</div>" +
        '<div class="rejilla dos">' +
          campoTexto(i, "titulo", "Título (opcional)", unidades(o.cantidad || 1), 60) +
          campoTexto(i, "subtitulo", "Texto debajo (opcional)", "Se calcula solo: «Ahorras …»", 80) +
        "</div>" +
        '<div class="rejilla dos">' +
          '<label class="campo">Etiqueta / sticker<input list="etiquetas" data-i="' + i + '" data-k="etiqueta" maxlength="30" value="' + esc(o.etiqueta || "") + '" placeholder="Ninguna"></label>' +
          '<label class="campo">Color de la etiqueta<select data-i="' + i + '" data-k="color">' +
            Object.keys(COLORES).map(function (c) { return '<option value="' + c + '"' + (o.color === c ? " selected" : "") + ">" + NOMBRE_COLOR[c] + "</option>"; }).join("") +
          "</select></label>" +
        "</div>" +
        '<div class="campo" style="font-size:13px;font-weight:500">Imagen (opcional)' +
          '<div class="fotos"><button type="button" class="ninguna' + (!o.imagen ? " sel" : "") + '" data-foto="' + i + '" data-url="">Sin<br>foto</button>' +
          fotos.map(function (u) { return '<button type="button" data-foto="' + i + '" data-url="' + esc(u) + '" style="background-image:url(\'' + esc(u) + '\')"' + (o.imagen === u ? ' class="sel"' : "") + ' aria-label="Usar esta foto"></button>'; }).join("") +
          "</div>" +
          '<input data-i="' + i + '" data-k="imagen" value="' + esc(o.imagen || "") + '" placeholder="…o pega un enlace https:// a una imagen">' +
        "</div></div>";
    }).join("") : '<div class="aviso">Este producto no tiene ofertas. Agrega una, o usa la plantilla 1-2-3.</div>';
    pintarPrevia();
  }

  function calcular(o) {
    var lista = Number(producto.precio), antes = lista * (o.cantidad || 1), precio = antes;
    if (o.tipo === "precio" && o.valor > 0) precio = Number(o.valor);
    if (o.tipo === "porcentaje" && o.valor > 0 && o.valor < 100) precio = Math.round(antes * (100 - o.valor)) / 100;
    return { antes: Math.max(antes, precio), precio: precio };
  }

  function pintarPrevia() {
    if (!cfg.activo || !cfg.ofertas.length) {
      $("#ed-previa").innerHTML = '<div class="aviso">Ofertas apagadas: el cliente compra 1 unidad a ' + dinero(producto.precio) + ".</div>";
      return;
    }
    var orden = cfg.ofertas.slice().sort(function (a, b) { return (a.cantidad || 0) - (b.cantidad || 0); });
    var marcada = orden.filter(function (o) { return o.preseleccionada; })[0] || orden[0];
    $("#ed-previa").innerHTML = orden.map(function (o) {
      var c = calcular(o), ahorro = c.antes - c.precio;
      return '<div class="p-of' + (o === marcada ? " sel" : "") + '">' +
        (o.etiqueta ? '<span class="p-badge" style="background:' + (COLORES[o.color] || COLORES.negro) + '">' + esc(o.etiqueta) + "</span>" : "") +
        '<span class="p-dot"></span>' + (o.imagen ? '<span class="p-img" style="background-image:url(\'' + esc(o.imagen) + '\')"></span>' : "") +
        '<span class="p-main"><span class="p-name">' + esc(o.titulo || unidades(o.cantidad || 1)) + '</span><br><span class="p-save">' +
        esc(o.subtitulo || (ahorro > 0 ? "Ahorras " + dinero(ahorro) : "Precio normal")) + "</span></span>" +
        '<span class="p-price"><b>' + dinero(c.precio) + "</b>" + (ahorro > 0 ? "<s>" + dinero(c.antes) + "</s>" : "") + "</span></div>";
    }).join("");
  }

  function cambiar(e) {
    var el = e.target, i = el.getAttribute("data-i"), k = el.getAttribute("data-k");
    if (i === null || !k) return;
    var o = cfg.ofertas[+i];
    if (k === "preseleccionada") { cfg.ofertas.forEach(function (x, j) { x.preseleccionada = j === +i; }); }
    else if (k === "cantidad") { o.cantidad = parseInt(el.value, 10) || 0; }
    else if (k === "valor") { o.valor = parseFloat(el.value) || 0; }
    else { o[k] = el.value; }
    if (k === "tipo" || k === "imagen") pintarEditor(); else pintarPrevia();
  }

  function guardar() {
    var b = $("#ed-guardar");
    b.disabled = true; b.textContent = "Guardando…";
    $("#ed-errores").hidden = true;
    api("/panel-api/ofertas/" + encodeURIComponent(producto.id), { method: "PUT", body: JSON.stringify({ direccion: producto.direccion, config: cfg }) })
      .then(function (res) {
        if (!res.ok) {
          var errs = res.j.errores || [res.j.error || "No se pudo guardar"];
          $("#ed-errores").innerHTML = errs.map(esc).join("<br>"); $("#ed-errores").hidden = false;
          avisar("Revisa los datos de las ofertas", true);
          return;
        }
        cfg = res.j.config; producto.config = JSON.parse(JSON.stringify(cfg)); original = JSON.stringify(cfg);
        pintarEditor();
        avisar("Ofertas guardadas");
      })
      .catch(function () { avisar("No se pudo guardar. Revisa tu conexión.", true); })
      .then(function () { b.disabled = false; b.textContent = "Guardar"; });
  }

  // ---------- Eventos ----------
  var dl = document.createElement("datalist"); dl.id = "etiquetas";
  dl.innerHTML = ETIQUETAS.map(function (t) { return '<option value="' + esc(t) + '">'; }).join("");
  document.body.appendChild(dl);

  $("#buscar").addEventListener("input", function () { if (datos) pintarLista(); });
  $("#lista").addEventListener("click", function (e) { var f = e.target.closest(".fila"); if (f) abrir(f.getAttribute("data-id")); });
  $("#lista").addEventListener("keydown", function (e) { var f = e.target.closest(".fila"); if (f && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); abrir(f.getAttribute("data-id")); } });
  $("#volver").addEventListener("click", cerrar);
  $("#ed-cancelar").addEventListener("click", function () { cfg = JSON.parse(original); pintarEditor(); });
  $("#ed-guardar").addEventListener("click", guardar);
  $("#ed-activo").addEventListener("change", function (e) { cfg.activo = e.target.checked; pintarPrevia(); });
  $("#ed-agregar").addEventListener("click", function () {
    var siguiente = cfg.ofertas.reduce(function (m, o) { return Math.max(m, o.cantidad || 0); }, 0) + 1;
    cfg.ofertas.push(nueva(siguiente)); if (cfg.ofertas.length === 1) cfg.activo = true; pintarEditor();
  });
  $("#ed-plantilla").addEventListener("click", function () {
    if (cfg.ofertas.length && !confirm("Esto reemplaza las ofertas de este producto por 1, 2 y 3 unidades. ¿Continuar?")) return;
    cfg.activo = true;
    cfg.ofertas = [nueva(1), nueva(2, "porcentaje", 15, "Más vendido"), nueva(3, "porcentaje", 25, "Mayor ahorro")];
    cfg.ofertas[1].preseleccionada = true; cfg.ofertas[2].color = "verde";
    pintarEditor();
  });
  var ofs = $("#ed-ofertas");
  ofs.addEventListener("input", cambiar);
  ofs.addEventListener("change", cambiar);
  ofs.addEventListener("click", function (e) {
    var q = e.target.closest("[data-quitar]"), f = e.target.closest("[data-foto]");
    if (q) { cfg.ofertas.splice(+q.getAttribute("data-quitar"), 1); pintarEditor(); }
    if (f) { cfg.ofertas[+f.getAttribute("data-foto")].imagen = f.getAttribute("data-url"); pintarEditor(); }
  });
  window.addEventListener("beforeunload", function (e) { if (cfg && JSON.stringify(cfg) !== original) { e.preventDefault(); e.returnValue = ""; } });

  cargar();
})();
