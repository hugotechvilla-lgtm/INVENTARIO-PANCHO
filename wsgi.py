import sys
import os
import json
import mimetypes
import urllib.parse
from datetime import datetime
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import (
    RUTA_INVENTARIO, RUTA_CLIENTES, RUTA_HISTORIAL,
    TICKETS_DIR, STATIC_DIR, BASE_DIR,
    leer_json, guardar_json, data_lock, get_local_ip,
    generar_ticket_cobro
)

def application(environ, start_response):
    path = environ.get('PATH_INFO', '/')
    method = environ.get('REQUEST_METHOD', 'GET').upper()

    # CORS OPTIONS
    if method == 'OPTIONS':
        start_response('200 OK', [
            ('Content-Type', 'text/plain'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Content-Type')
        ])
        return [b'']

    def respond_json(data, status='200 OK'):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        start_response(status, [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Content-Length', str(len(body))),
            ('Access-Control-Allow-Origin', '*')
        ])
        return [body]

    def respond_file(filepath, content_type):
        if not os.path.exists(filepath):
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return [b'File not found']
        with open(filepath, 'rb') as f:
            content = f.read()
        start_response('200 OK', [
            ('Content-Type', content_type),
            ('Content-Length', str(len(content))),
            ('Access-Control-Allow-Origin', '*')
        ])
        return [content]

    if method == 'GET':
        if path == '/api/estado':
            return respond_json({
                "ok": True,
                "ip_local": get_local_ip(),
                "port": 5000,
                "hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        elif path == '/api/inventario':
            with data_lock:
                inv = leer_json(RUTA_INVENTARIO, [])
            return respond_json(inv)
        elif path == '/api/clientes':
            with data_lock:
                cli = leer_json(RUTA_CLIENTES, [])
            return respond_json(cli)
        elif path == '/api/historial':
            with data_lock:
                hist = leer_json(RUTA_HISTORIAL, [])
            return respond_json(hist)
        elif path.startswith('/tickets/'):
            filename = os.path.basename(path)
            ticket_path = os.path.join(TICKETS_DIR, filename)
            return respond_file(ticket_path, 'image/png')
        elif path == '/logo.png':
            return respond_file(os.path.join(BASE_DIR, 'logo.png'), 'image/png')
        elif path == '/manifest.json':
            return respond_json({
                "name": "PANCHO Bebidas",
                "short_name": "PANCHO",
                "start_url": "/",
                "display": "standalone",
                "background_color": "#121214",
                "theme_color": "#FFAA00",
                "icons": [{"src": "/logo.png", "sizes": "192x192 512x512", "type": "image/png"}]
            })
        elif path in ['/', '/index.html']:
            return respond_file(os.path.join(STATIC_DIR, 'index.html'), 'text/html; charset=utf-8')
        else:
            static_file = os.path.join(STATIC_DIR, path.lstrip('/'))
            if os.path.exists(static_file) and os.path.isfile(static_file):
                mime_type, _ = mimetypes.guess_type(static_file)
                return respond_file(static_file, mime_type or 'application/octet-stream')
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return [b'Not found']

    elif method == 'POST':
        try:
            content_length = int(environ.get('CONTENT_LENGTH', 0))
        except (ValueError, TypeError):
            content_length = 0
        body_data = environ['wsgi.input'].read(content_length) if content_length > 0 else b'{}'
        try:
            body = json.loads(body_data.decode('utf-8'))
        except Exception:
            body = {}

        if path == "/api/clientes/crear":
            nombre = body.get("nombre", "").strip().upper()
            if not nombre:
                return respond_json({"ok": False, "error": "Nombre requerido"}, '400 Bad Request')
            slug = re.sub(r'[^a-zA-Z0-9_\-]', '', nombre.replace(' ', '-').lower())
            with data_lock:
                clientes = leer_json(RUTA_CLIENTES, [])
                existente = next((c for c in clientes if c["nombre"] == nombre), None)
                if existente:
                    return respond_json(existente)
                nuevo_cli = {
                    "id": slug + f"-{len(clientes)+1}",
                    "nombre": nombre,
                    "saldo_actual": 0,
                    "consumos_semana": [],
                    "fecha_inicio_semana": datetime.now().strftime("%Y-%m-%d")
                }
                clientes.append(nuevo_cli)
                guardar_json(RUTA_CLIENTES, clientes)
            return respond_json(nuevo_cli)

        elif path == "/api/clientes/eliminar":
            cliente_id = body.get("cliente_id")
            if not cliente_id:
                return respond_json({"ok": False, "error": "ID de cliente requerido"}, '400 Bad Request')
            with data_lock:
                clientes = leer_json(RUTA_CLIENTES, [])
                clientes = [c for c in clientes if c["id"] != cliente_id]
                guardar_json(RUTA_CLIENTES, clientes)
            return respond_json({"ok": True, "clientes": clientes})

        elif path == "/api/clientes/reiniciar-cuenta":
            cliente_id = body.get("cliente_id")
            with data_lock:
                clientes = leer_json(RUTA_CLIENTES, [])
                cli = next((c for c in clientes if c["id"] == cliente_id), None)
                if cli:
                    cli["saldo_actual"] = 0
                    cli["consumos_semana"] = []
                    guardar_json(RUTA_CLIENTES, clientes)
            return respond_json({"ok": True, "clientes": clientes})

        elif path == "/api/clientes/borrar-todos":
            with data_lock:
                guardar_json(RUTA_CLIENTES, [])
            return respond_json({"ok": True, "clientes": []})

        elif path == "/api/clientes/consumo":
            cliente_id = body.get("cliente_id")
            items = body.get("items", [])
            if not cliente_id or not items:
                return respond_json({"ok": False, "error": "Faltan datos"}, '400 Bad Request')
            with data_lock:
                clientes = leer_json(RUTA_CLIENTES, [])
                inventario = leer_json(RUTA_INVENTARIO, [])
                cliente = next((c for c in clientes if c["id"] == cliente_id), None)
                if not cliente:
                    return respond_json({"ok": False, "error": "Cliente no encontrado"}, '404 Not Found')
                for item in items:
                    prod = next((p for p in inventario if p["id"] == item["id"]), None)
                    if prod:
                        id_base = prod.get("descuenta_de_id") or prod["id"]
                        prod_base = next((p for p in inventario if p["id"] == id_base), prod)
                        if "stock" in prod_base:
                            prod_base["stock"] = max(0, prod_base["stock"] - item["cantidad"])
                ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                subtotal_pedido = 0
                for item in items:
                    sub = item.get("subtotal", item["precio_unitario"] * item["cantidad"])
                    subtotal_pedido += sub
                    p_obj = next((p for p in inventario if p["id"] == item["id"]), None)
                    costo_u = p_obj.get("precio_costo", 0) if p_obj else 0
                    cliente["consumos_semana"].append({
                        "fecha": ahora_str,
                        "producto_id": item["id"],
                        "nombre": item["nombre"],
                        "cantidad": item["cantidad"],
                        "precio_unitario": item["precio_unitario"],
                        "precio_costo": costo_u,
                        "subtotal": sub
                    })
                cliente["saldo_actual"] += subtotal_pedido
                guardar_json(RUTA_INVENTARIO, inventario)
                guardar_json(RUTA_CLIENTES, clientes)
            return respond_json({"ok": True, "cliente": cliente, "inventario": inventario})

        elif path == "/api/clientes/cerrar-semana":
            cliente_id = body.get("cliente_id")
            with data_lock:
                clientes = leer_json(RUTA_CLIENTES, [])
                historial = leer_json(RUTA_HISTORIAL, [])
                cliente = next((c for c in clientes if c["id"] == cliente_id), None)
                if not cliente or cliente["saldo_actual"] <= 0:
                    return respond_json({"ok": False, "error": "No hay saldo"}, '400 Bad Request')
                items_resumen = {}
                for c in cliente["consumos_semana"]:
                    items_resumen[c["nombre"]] = items_resumen.get(c["nombre"], 0) + c["cantidad"]
                concepto_texto = " + ".join([f"{cant} {nom}" for nom, cant in items_resumen.items()])
                total_saldo = cliente["saldo_actual"]
                ruta_img, filename, comprobante = generar_ticket_cobro(
                    cliente=cliente["nombre"],
                    concepto=concepto_texto,
                    monto_val=total_saldo,
                    titular_nequi="HUGO BRION"
                )
                registro = {
                    "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "cliente": cliente["nombre"],
                    "total": total_saldo,
                    "comprobante": comprobante,
                    "concepto": concepto_texto,
                    "consumos": list(cliente["consumos_semana"]),
                    "ticket_url": f"/tickets/{filename}"
                }
                historial.append(registro)
                guardar_json(RUTA_HISTORIAL, historial)
                cliente["saldo_actual"] = 0
                cliente["consumos_semana"] = []
                cliente["fecha_inicio_semana"] = datetime.now().strftime("%Y-%m-%d")
                guardar_json(RUTA_CLIENTES, clientes)
            return respond_json({
                "ok": True,
                "ticket_url": f"/tickets/{filename}",
                "cliente_nombre": cliente["nombre"],
                "total": total_saldo,
                "comprobante": comprobante,
                "concepto": concepto_texto
            })

        elif path == "/api/historial/borrar-todos":
            with data_lock:
                guardar_json(RUTA_HISTORIAL, [])
                try:
                    with open(os.path.join(BASE_DIR, "contador.txt"), "w", encoding="utf-8") as f:
                        f.write("1")
                except Exception:
                    pass
            return respond_json({"ok": True, "historial": []})

        elif path == "/api/inventario/reponer":
            producto_id = body.get("producto_id")
            cantidad = int(body.get("cantidad", 0))
            if not producto_id or cantidad <= 0:
                return respond_json({"ok": False, "error": "Datos inválidos"}, '400 Bad Request')
            with data_lock:
                inventario = leer_json(RUTA_INVENTARIO, [])
                prod = next((p for p in inventario if p["id"] == producto_id), None)
                if not prod:
                    return respond_json({"ok": False, "error": "No encontrado"}, '404 Not Found')
                prod["stock"] += cantidad
                guardar_json(RUTA_INVENTARIO, inventario)
            return respond_json({"ok": True, "inventario": inventario})

        elif path == "/api/inventario/ajustar-stock":
            producto_id = body.get("producto_id")
            stock_nuevo = int(body.get("stock", 0))
            if not producto_id or stock_nuevo < 0:
                return respond_json({"ok": False, "error": "Datos inválidos"}, '400 Bad Request')
            with data_lock:
                inventario = leer_json(RUTA_INVENTARIO, [])
                prod = next((p for p in inventario if p["id"] == producto_id), None)
                if not prod:
                    return respond_json({"ok": False, "error": "No encontrado"}, '404 Not Found')
                prod["stock"] = stock_nuevo
                guardar_json(RUTA_INVENTARIO, inventario)
            return respond_json({"ok": True, "inventario": inventario})

        elif path == "/api/inventario/agregar":
            nombre = body.get("nombre", "").strip()
            categoria = body.get("categoria", "Cervezas").strip()
            precio = int(body.get("precio", 0))
            stock = int(body.get("stock", 0))
            min_stock = int(body.get("min_stock", 6))
            if not nombre or precio <= 0:
                return respond_json({"ok": False, "error": "Datos requeridos"}, '400 Bad Request')
            slug = re.sub(r'[^a-zA-Z0-9_\-]', '', nombre.replace(' ', '-').lower())
            with data_lock:
                inventario = leer_json(RUTA_INVENTARIO, [])
                nuevo_prod = {
                    "id": slug + f"-{len(inventario)+1}",
                    "nombre": nombre,
                    "categoria": categoria,
                    "precio": precio,
                    "stock": stock,
                    "min_stock": min_stock
                }
                inventario.append(nuevo_prod)
                guardar_json(RUTA_INVENTARIO, inventario)
            return respond_json({"ok": True, "inventario": inventario})

        elif path == "/api/inventario/editar-precio":
            producto_id = body.get("producto_id")
            nuevo_precio = int(body.get("precio", 0))
            if not producto_id or nuevo_precio <= 0:
                return respond_json({"ok": False, "error": "Datos inválidos"}, '400 Bad Request')
            with data_lock:
                inventario = leer_json(RUTA_INVENTARIO, [])
                prod = next((p for p in inventario if p["id"] == producto_id), None)
                if not prod:
                    return respond_json({"ok": False, "error": "No encontrado"}, '404 Not Found')
                prod["precio"] = nuevo_precio
                guardar_json(RUTA_INVENTARIO, inventario)
            return respond_json({"ok": True, "inventario": inventario})

        elif path == "/api/inventario/editar-costo":
            producto_id = body.get("producto_id")
            nuevo_costo = int(body.get("costo", 0))
            if not producto_id or nuevo_costo < 0:
                return respond_json({"ok": False, "error": "Datos inválidos"}, '400 Bad Request')
            with data_lock:
                inventario = leer_json(RUTA_INVENTARIO, [])
                prod = next((p for p in inventario if p["id"] == producto_id), None)
                if not prod:
                    return respond_json({"ok": False, "error": "No encontrado"}, '404 Not Found')
                diferencia = nuevo_costo - prod.get("precio_costo", 0)
                prod["precio_costo"] = nuevo_costo
                for derivado in inventario:
                    if derivado.get("descuenta_de_id") == producto_id:
                        derivado["precio_costo"] = max(0, derivado.get("precio_costo", nuevo_costo) + diferencia)
                guardar_json(RUTA_INVENTARIO, inventario)
            return respond_json({"ok": True, "inventario": inventario})

        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return [b'Endpoint no encontrado']

    start_response('405 Method Not Allowed', [('Content-Type', 'text/plain')])
    return [b'Method not allowed']

