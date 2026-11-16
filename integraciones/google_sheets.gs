/**
 * Rebajitas COD → Google Sheets.
 * Se pega en la hoja "Rebajitas": Extensiones → Apps Script. Ver LEEME.md, sección Google Sheets.
 * Recibe cada pedido nuevo desde la app y lo agrega como fila en la pestaña del mes,
 * con las mismas columnas que usaba Releasit. Solo escribe A–H y T–W: las columnas del equipo no se tocan.
 */
const CLAVE = 'PEGA_AQUI_LA_CLAVE';  // la misma que SHEETS_CLAVE en Render

function doPost(e) {
  let datos;
  try { datos = JSON.parse(e.postData.contents); } catch (err) { return responder({ ok: false, error: 'datos no válidos' }); }
  if (datos.clave !== CLAVE) return responder({ ok: false, error: 'clave incorrecta' });

  const libro = SpreadsheetApp.getActiveSpreadsheet();
  let hoja = libro.getSheetByName(datos.hoja);
  let aviso = '';
  if (!hoja) {
    // Si todavía no existe la pestaña del mes, el pedido no se pierde: va a "Pedidos sin pestaña".
    aviso = 'No existe la pestaña "' + datos.hoja + '"';
    hoja = libro.getSheetByName('Pedidos sin pestaña') || libro.insertSheet('Pedidos sin pestaña');
  }

  const candado = LockService.getScriptLock();
  candado.waitLock(30000);
  try {
    const fila = ultimaFilaConDatos(hoja) + 1;
    const f = datos.fila;
    hoja.getRange(fila, 3).setNumberFormat('@');  // teléfono como texto, para que se vea el +58
    hoja.getRange(fila, 1, 1, 8).setValues([[f.fecha, f.nombre, f.telefono, f.estado, f.oficina, f.producto, f.cantidad, f.valor]]);
    hoja.getRange(fila, 20, 1, 4).setValues([[f.utm_source, f.utm_campaign, f.utm_medium, f.utm_content]]);
  } finally {
    candado.releaseLock();
  }
  return responder({ ok: true, hoja: hoja.getName(), aviso: aviso });
}

// Última fila con algo escrito en las columnas A–H (las listas desplegables vacías no cuentan).
function ultimaFilaConDatos(hoja) {
  const total = hoja.getLastRow();
  if (total === 0) return 0;
  const valores = hoja.getRange(1, 1, total, 8).getValues();
  for (let i = valores.length - 1; i >= 0; i--) {
    if (valores[i].some(function (v) { return v !== '' && v !== null; })) return i + 1;
  }
  return 0;
}

function responder(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
