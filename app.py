# ==============================================================================
# 🧠 APP.PY - EL CEREBRO PRINCIPAL DEL SISTEMA PANCHO
# Coordina las ventas, el inventario, los clientes y la generación de tickets.
# ==============================================================================

# 1. HERRAMIENTAS Y LIBRERÍAS DE PYTHON
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler # Servidor web multihilo para atender varios celulares
import urllib.parse  # Analiza y limpia las direcciones web (URLs)
import threading     # Permite atender múltiples pedidos al mismo tiempo sin congelarse
import mimetypes     # Reconoce tipos de archivos (.html, .png, .css, etc.)
import socket        # Conexión de red (detecta la dirección IP de tu Wi-Fi)
import json          # Lee y escribe en la base de datos (archivos .json)
import os            # Habla con el sistema operativo Windows (carpetas y rutas)
import re            # Limpieza de textos y caracteres especiales
from datetime import datetime # Reloj del sistema (fechas, horas y comprobantes)

# Traemos el pintor de tickets y la agrupación inteligente desde generador_ticket.py
from generador_ticket import generar_ticket_cobro, agrupar_consumos_por_categoria

# 2. RUTAS DE LAS CARPETAS DEL PROYECTO
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Carpeta principal C:\REDONDEADO
DATOS_DIR = os.path.join(BASE_DIR, "datos")           # Carpeta donde vive la base de datos
TICKETS_DIR = os.path.join(BASE_DIR, "tickets")       # Carpeta donde se guardan las imágenes PNG
STATIC_DIR = os.path.join(BASE_DIR, "static")         # Carpeta donde está el archivo web index.html

# Si las carpetas no existen en tu computador, las crea automáticamente:
os.makedirs(DATOS_DIR, exist_ok=True)
os.makedirs(TICKETS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Rutas exactas a los 3 archivos de la base de datos:
RUTA_INVENTARIO = os.path.join(DATOS_DIR, "inventario.json")       # Catálogo de cervezas, precios y stock
RUTA_CLIENTES = os.path.join(DATOS_DIR, "clientes.json")           # Lista de clientes y saldos pendientes
RUTA_HISTORIAL = os.path.join(DATOS_DIR, "historial_semanas.json") # Archivo histórico de todos los cobros

# Cerrojo de seguridad: evita que dos pedidos choquen si se tocan botones al mismo tiempo
data_lock = threading.Lock()

# 3. DETECTAR LA DIRECCIÓN IP DEL WI-FI DE TU CASA/LOCAL
def get_local_ip():
    """Obtiene la IP local de tu computador (ej: 192.168.1.15) para que entres desde el celular."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# 4. LEER DATOS CON COPIA DE SEGURIDAD AUTOMÁTICA
def leer_json(ruta, default_val):
    """Abre un archivo .json y lo convierte en datos de Python. Si falla, se recupera del backup."""
    if not os.path.exists(ruta):
        guardar_json(ruta, default_val)
        return default_val
    try:
        with open(ruta, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Error leyendo {ruta}: {e}")
        bak = ruta + ".bak"
        if os.path.exists(bak):
            try:
                with open(bak, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"[*] Recuperado exitosamente desde backup: {bak}")
                    return data
            except Exception:
                pass
        return default_val

# 5. GUARDAR DATOS DE FORMA SEGURA (Crea backup .bak antes de escribir)
def guardar_json(ruta, data):
    """Guarda los datos actualizados en el archivo .json sin riesgo de pérdida."""
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                old_data = f.read()
            with open(ruta + ".bak", "w", encoding="utf-8") as f:
                f.write(old_data)
        except Exception:
            pass
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class PanchoHandler(SimpleHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 1. API: ESTADO GENERAL
        if path == "/api/estado":
            self.send_json({
                "ok": True,
                "ip_local": get_local_ip(),
                "port": int(os.environ.get("PORT", 5000)),
                "hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            return

        # 2. API: INVENTARIO
        elif path == "/api/inventario":
            with data_lock:
                inv = leer_json(RUTA_INVENTARIO, [])
            self.send_json(inv)
            return

        # 3. API: CLIENTES
        elif path == "/api/clientes":
            with data_lock:
                cli = leer_json(RUTA_CLIENTES, [])
            self.send_json(cli)
            return

        # 4. API: HISTORIAL
        elif path == "/api/historial":
            with data_lock:
                hist = leer_json(RUTA_HISTORIAL, [])
            self.send_json(hist)
            return

        # 5. SERVIR TICKETS GENERADOS
        elif path.startswith("/tickets/"):
            filename = os.path.basename(path)
            ticket_path = os.path.join(TICKETS_DIR, filename)
            if os.path.exists(ticket_path) and os.path.isfile(ticket_path):
                self.serve_file(ticket_path, "image/png")
                return
            else:
                self.send_error(404, "Ticket no encontrado")
                return

        # 6. LOGO DE LA MARCA
        elif path == "/logo.png":
            logo_path = os.path.join(BASE_DIR, "logo.png")
            if os.path.exists(logo_path):
                self.serve_file(logo_path, "image/png")
                return
            else:
                self.send_error(404, "Logo no encontrado")
                return

        # 6.1 MANIFEST PARA INSTALACIÓN EN CELULAR (PWA)
        elif path == "/manifest.json":
            self.send_json({
                "name": "PANCHO Bebidas",
                "short_name": "PANCHO",
                "start_url": "/",
                "display": "standalone",
                "background_color": "#121214",
                "theme_color": "#FFAA00",
                "icons": [
                    {
                        "src": "/logo.png",
                        "sizes": "192x192 512x512",
                        "type": "image/png"
                    }
                ]
            })
            return

        # 7. SERVIR FRONTEND PRINCIPAL (SPA)
        elif path in ["/", "/index.html"]:
            index_path = os.path.join(STATIC_DIR, "index.html")
            if os.path.exists(index_path):
                self.serve_file(index_path, "text/html; charset=utf-8")
                return

        # 8. CUALQUIER ARCHIVO ESTÁTICO
        static_file = os.path.join(STATIC_DIR, path.lstrip("/"))
        if os.path.exists(static_file) and os.path.isfile(static_file):
            mime_type, _ = mimetypes.guess_type(static_file)
            self.serve_file(static_file, mime_type or "application/octet-stream")
            return

        self.send_error(404, "Ruta no encontrada")

    def serve_file(self, full_path, content_type):
        try:
            with open(full_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error leyendo archivo: {e}")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            body = json.loads(raw_body)
        except:
            body = {}

        # 1. API: CREAR CLIENTE
        if path == "/api/clientes/crear":
            nombre = body.get("nombre", "").strip().upper()
            if not nombre:
                self.send_json({"ok": False, "error": "Nombre requerido"}, status=400)
                return
            slug = re.sub(r'[^a-zA-Z0-9_\-]', '', nombre.replace(' ', '-').lower())
            with data_lock:
                clientes = leer_json(RUTA_CLIENTES, [])
                # Verificar si ya existe
                existente = next((c for c in clientes if c["nombre"] == nombre), None)
                if existente:
                    self.send_json(existente)
                    return
                nuevo_cli = {
                    "id": slug + f"-{len(clientes)+1}",
                    "nombre": nombre,
                    "saldo_actual": 0,
                    "consumos_semana": [],
                    "fecha_inicio_semana": datetime.now().strftime("%Y-%m-%d")
                }
                clientes.append(nuevo_cli)
                guardar_json(RUTA_CLIENTES, clientes)
            self.send_json(nuevo_cli)
            return

        # 1.1 API: ELIMINAR CLIENTE ESPECÍFICO
        elif path == "/api/clientes/eliminar":
            cliente_id = body.get("cliente_id")
            if not cliente_id:
                self.send_json({"ok": False, "error": "ID de cliente requerido"}, status=400)
                return
            with data_lock:
                clientes = leer_json(RUTA_CLIENTES, [])
                clientes = [c for c in clientes if c["id"] != cliente_id]
                guardar_json(RUTA_CLIENTES, clientes)
            self.send_json({"ok": True, "clientes": clientes})
            return

        # 1.2 API: REINICIAR CUENTA DE CLIENTE A $0
        elif path == "/api/clientes/reiniciar-cuenta":
            cliente_id = body.get("cliente_id")
            with data_lock:
                clientes = leer_json(RUTA_CLIENTES, [])
                cli = next((c for c in clientes if c["id"] == cliente_id), None)
                if cli:
                    cli["saldo_actual"] = 0
                    cli["consumos_semana"] = []
                    guardar_json(RUTA_CLIENTES, clientes)
            self.send_json({"ok": True, "clientes": clientes})
            return

        # 1.3 API: BORRAR TODOS LOS CLIENTES (LIMPIEZA TOTAL)
        elif path == "/api/clientes/borrar-todos":
            with data_lock:
                guardar_json(RUTA_CLIENTES, [])
            self.send_json({"ok": True, "clientes": []})
            return

        # 1.4 API: ELIMINAR O RESTAR CONSUMO DE CUENTA (DEVUELVE STOCK AL INVENTARIO)
        elif path == "/api/clientes/eliminar-consumo":
            cliente_id = body.get("cliente_id")
            item_index = body.get("item_index")
            cant_quitar = body.get("cantidad")

            if not cliente_id or item_index is None:
                self.send_json({"ok": False, "error": "Faltan datos requeridos"}, status=400)
                return

            with data_lock:
                clientes = leer_json(RUTA_CLIENTES, [])
                inventario = leer_json(RUTA_INVENTARIO, [])

                cliente = next((c for c in clientes if c["id"] == cliente_id), None)
                if not cliente:
                    self.send_json({"ok": False, "error": "Cliente no encontrado"}, status=404)
                    return

                consumos = cliente.get("consumos_semana", [])
                try:
                    idx = int(item_index)
                    if idx < 0 or idx >= len(consumos):
                        self.send_json({"ok": False, "error": "Consumo no encontrado"}, status=404)
                        return
                except:
                    self.send_json({"ok": False, "error": "Índice de consumo inválido"}, status=400)
                    return

                item = consumos[idx]
                cant_total_item = item.get("cantidad", 1)
                precio_u = item.get("precio_unitario") or item.get("precio") or (item.get("subtotal", 0) // max(1, cant_total_item))

                if cant_quitar is not None and int(cant_quitar) > 0 and int(cant_quitar) < cant_total_item:
                    cant_a_devolver = int(cant_quitar)
                    item["cantidad"] -= cant_a_devolver
                    monto_a_restar = cant_a_devolver * precio_u
                    item["subtotal"] = max(0, item.get("subtotal", 0) - monto_a_restar)
                else:
                    cant_a_devolver = cant_total_item
                    monto_a_restar = item.get("subtotal", precio_u * cant_total_item)
                    consumos.pop(idx)

                # Restar valor de la deuda actual del cliente
                cliente["saldo_actual"] = max(0, cliente.get("saldo_actual", 0) - monto_a_restar)

                # DEVOLVER STOCK A LA BODEGA / INVENTARIO
                prod_id = item.get("producto_id") or item.get("id")
                prod = next((p for p in inventario if prod_id and p["id"] == prod_id), None)
                if not prod:
                    nom_item = item.get("nombre", "").strip().upper()
                    prod = next((p for p in inventario if p["nombre"].strip().upper() == nom_item), None)
                    if not prod:
                        prod = next((p for p in inventario if nom_item in p["nombre"].strip().upper() or p["nombre"].strip().upper() in nom_item), None)

                if prod:
                    id_base = prod.get("descuenta_de_id") or prod["id"]
                    prod_base = next((p for p in inventario if p["id"] == id_base), prod)
                    if "stock" in prod_base and prod_base.get("stock") is not None:
                        prod_base["stock"] += cant_a_devolver

                guardar_json(RUTA_INVENTARIO, inventario)
                guardar_json(RUTA_CLIENTES, clientes)

            self.send_json({
                "ok": True,
                "cliente": cliente,
                "clientes": clientes,
                "inventario": inventario
            })
            return

        # 2. API: REGISTRAR CONSUMO DIARIO (DESCUENTA INVENTARIO Y SUMA A LA SEMANA)
        elif path == "/api/clientes/consumo":
            cliente_id = body.get("cliente_id")
            items = body.get("items", []) # [{id, nombre, cantidad, precio_unitario, subtotal}]

            if not cliente_id or not items:
                self.send_json({"ok": False, "error": "Faltan datos de cliente o productos"}, status=400)
                return

            with data_lock:
                clientes = leer_json(RUTA_CLIENTES, [])
                inventario = leer_json(RUTA_INVENTARIO, [])

                cliente = next((c for c in clientes if c["id"] == cliente_id), None)
                if not cliente:
                    self.send_json({"ok": False, "error": "Cliente no encontrado"}, status=404)
                    return

                # Descontar stock de inventario (soporta recetas / bebidas preparadas)
                for item in items:
                    prod = next((p for p in inventario if p["id"] == item["id"]), None)
                    if prod:
                        id_base = prod.get("descuenta_de_id") or prod["id"]
                        prod_base = next((p for p in inventario if p["id"] == id_base), prod)
                        if "stock" in prod_base and prod_base.get("stock") is not None:
                            prod_base["stock"] = max(0, prod_base["stock"] - item["cantidad"])

                # Sumar a consumos del cliente
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

                # Guardar ambos
                guardar_json(RUTA_INVENTARIO, inventario)
                guardar_json(RUTA_CLIENTES, clientes)

            self.send_json({
                "ok": True,
                "cliente": cliente,
                "inventario": inventario
            })
            return

        # 2.1 API: REGISTRAR VENTA DE CONTADO (PAGO INMEDIATO)
        elif path == "/api/clientes/pago-contado":
            cliente_id = body.get("cliente_id")
            items = body.get("items", [])
            nombre_custom = body.get("nombre_cliente", "").strip().upper()

            if not items:
                self.send_json({"ok": False, "error": "No hay productos en el pedido"}, status=400)
                return

            with data_lock:
                clientes = leer_json(RUTA_CLIENTES, [])
                inventario = leer_json(RUTA_INVENTARIO, [])
                historial = leer_json(RUTA_HISTORIAL, [])

                cliente = next((c for c in clientes if c["id"] == cliente_id), None)
                nombre_cliente = cliente["nombre"] if cliente else (nombre_custom or "CLIENTE DE CONTADO")

                # 1. Descontar stock de inventario (soporta recetas)
                for item in items:
                    prod = next((p for p in inventario if p["id"] == item["id"]), None)
                    if prod:
                        id_base = prod.get("descuenta_de_id") or prod["id"]
                        prod_base = next((p for p in inventario if p["id"] == id_base), prod)
                        if "stock" in prod_base and prod_base.get("stock") is not None:
                            prod_base["stock"] = max(0, prod_base["stock"] - item["cantidad"])

                # 2. Calcular total y preparar consumos para balance y ganancia
                ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                subtotal_pedido = 0
                consumos_detallados = []
                for item in items:
                    sub = item.get("subtotal", item["precio_unitario"] * item["cantidad"])
                    subtotal_pedido += sub
                    p_obj = next((p for p in inventario if p["id"] == item["id"]), None)
                    costo_u = p_obj.get("precio_costo", 0) if p_obj else 0
                    consumos_detallados.append({
                        "fecha": ahora_str,
                        "producto_id": item["id"],
                        "nombre": item["nombre"],
                        "cantidad": item["cantidad"],
                        "precio_unitario": item["precio_unitario"],
                        "precio_costo": costo_u,
                        "subtotal": sub
                    })

                # 3. Armar texto del concepto agrupado por categoría (ej: 10 CERVEZAS)
                partes_concepto = agrupar_consumos_por_categoria(consumos_detallados)
                concepto_texto = " · ".join(partes_concepto)

                # 4. Generar el ticket oficial remodelado
                try:
                    ruta_img, filename, comprobante = generar_ticket_cobro(
                        cliente=nombre_cliente,
                        concepto=partes_concepto,
                        monto_val=subtotal_pedido
                    )
                except Exception as err:
                    print(f"[!] Error generando ticket contado: {err}")
                    self.send_json({"ok": False, "error": f"Error generando ticket: {err}"}, status=500)
                    return

                # 5. Registrar en historial de cobros (PAGADO - no suma deuda)
                registro_historial = {
                    "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "cliente": nombre_cliente,
                    "total": subtotal_pedido,
                    "comprobante": comprobante,
                    "concepto": concepto_texto,
                    "consumos": consumos_detallados,
                    "ticket_url": f"/tickets/{filename}",
                    "metodo": "CONTADO"
                }
                historial.append(registro_historial)

                guardar_json(RUTA_INVENTARIO, inventario)
                guardar_json(RUTA_HISTORIAL, historial)

            self.send_json({
                "ok": True,
                "ticket_url": f"/tickets/{filename}",
                "cliente_nombre": nombre_cliente,
                "total": subtotal_pedido,
                "comprobante": comprobante,
                "concepto": concepto_texto,
                "inventario": inventario,
                "historial": historial
            })
            return

        # 3. API: CERRAR SEMANA Y GENERAR TICKET OFICIAL PANCHO
        elif path == "/api/clientes/cerrar-semana":
            cliente_id = body.get("cliente_id")
            with data_lock:
                clientes = leer_json(RUTA_CLIENTES, [])
                cliente = next((c for c in clientes if c["id"] == cliente_id), None)
                if not cliente:
                    self.send_json({"ok": False, "error": "Cliente no encontrado"}, status=404)
                    return

                total_saldo = cliente["saldo_actual"]
                if total_saldo <= 0:
                    self.send_json({"ok": False, "error": "El cliente no tiene saldo pendiente"}, status=400)
                    return

                # Agrupar productos consumidos por categoría para un concepto limpio (ej: 10 CERVEZAS)
                partes_concepto = agrupar_consumos_por_categoria(cliente.get("consumos_semana", []))
                concepto_texto = " · ".join(partes_concepto)

                try:
                    # Generar el ticket usando Pillow oficial remodelado
                    ruta_img, filename, comprobante = generar_ticket_cobro(
                        cliente=cliente["nombre"],
                        concepto=partes_concepto,
                        monto_val=total_saldo
                    )
                except Exception as err:
                    print(f"[!] Error generando ticket: {err}")
                    self.send_json({"ok": False, "error": f"Error generando imagen de ticket: {err}"}, status=500)
                    return

                # Guardar referencia del ticket sin borrar la deuda ni los consumos (No suma a caja hasta que abone)
                cliente["ultimo_ticket"] = {
                    "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "comprobante": comprobante,
                    "ticket_url": f"/tickets/{filename}"
                }
                guardar_json(RUTA_CLIENTES, clientes)

            self.send_json({
                "ok": True,
                "ticket_url": f"/tickets/{filename}",
                "cliente_nombre": cliente["nombre"],
                "total": total_saldo,
                "comprobante": comprobante,
                "concepto": concepto_texto
            })
        # 3.1 API: REGISTRAR ABONO O PAGO A CUENTA DE CLIENTE
        elif path == "/api/clientes/abonar":
            cliente_id = body.get("cliente_id")
            monto_abono = int(body.get("monto", 0))
            metodo = body.get("metodo", "NEQUI").strip().upper()
            nota = body.get("nota", "").strip()

            if not cliente_id or monto_abono <= 0:
                self.send_json({"ok": False, "error": "Datos de abono inválidos"}, status=400)
                return

            with data_lock:
                clientes = leer_json(RUTA_CLIENTES, [])
                historial = leer_json(RUTA_HISTORIAL, [])
                cliente = next((c for c in clientes if c["id"] == cliente_id), None)
                if not cliente:
                    self.send_json({"ok": False, "error": "Cliente no encontrado"}, status=404)
                    return

                saldo_anterior = cliente.get("saldo_actual", 0)
                if saldo_anterior <= 0:
                    self.send_json({"ok": False, "error": "El cliente no tiene saldo pendiente"}, status=400)
                    return

                monto_real = min(monto_abono, saldo_anterior)
                nuevo_saldo = saldo_anterior - monto_real
                cliente["saldo_actual"] = nuevo_saldo

                ahora_dt = datetime.now()
                fecha_str = ahora_dt.strftime("%d/%m/%Y %H:%M")
                detalle_abono = {
                    "fecha": fecha_str,
                    "monto": monto_real,
                    "metodo": metodo,
                    "saldo_restante": nuevo_saldo,
                    "nota": nota
                }
                if "abonos" not in cliente:
                    cliente["abonos"] = []
                cliente["abonos"].append(detalle_abono)
                cliente["ultimo_abono"] = detalle_abono

                if nuevo_saldo == 0:
                    cliente["consumos_semana"] = []
                    cliente["fecha_inicio_semana"] = ahora_dt.strftime("%Y-%m-%d")

                comp_abono = f"ABONO-{ahora_dt.strftime('%Y%m%d%H%M%S')}"
                concepto_abono = f"ABONO · {metodo} (DEUDA: ${saldo_anterior:,} · RESTA: ${nuevo_saldo:,})".replace(",", ".")
                registro_h = {
                    "fecha": fecha_str,
                    "cliente": cliente["nombre"],
                    "total": monto_real,
                    "comprobante": comp_abono,
                    "concepto": concepto_abono,
                    "consumos": [],
                    "metodo": metodo,
                    "tipo": "ABONO"
                }
                historial.append(registro_h)

                guardar_json(RUTA_CLIENTES, clientes)
                guardar_json(RUTA_HISTORIAL, historial)

            self.send_json({
                "ok": True,
                "cliente": cliente,
                "saldo_anterior": saldo_anterior,
                "nuevo_saldo": nuevo_saldo,
                "monto_abonado": monto_real,
                "historial": historial
            })
            return

        # 3.15 API: REGISTRAR PAGO TOTAL Y ELIMINAR CLIENTE DEFINITIVAMENTE DEL SISTEMA
        elif path == "/api/clientes/pago-total":
            cliente_id = body.get("cliente_id")
            metodo = body.get("metodo", "EFECTIVO").strip().upper()
            if metodo not in ["EFECTIVO", "NEQUI"]:
                metodo = "EFECTIVO"
            nota = body.get("nota", "").strip()

            if not cliente_id:
                self.send_json({"ok": False, "error": "ID de cliente requerido"}, status=400)
                return

            with data_lock:
                clientes = leer_json(RUTA_CLIENTES, [])
                historial = leer_json(RUTA_HISTORIAL, [])

                cliente = next((c for c in clientes if c["id"] == cliente_id), None)
                if not cliente:
                    self.send_json({"ok": False, "error": "Cliente no encontrado"}, status=404)
                    return

                total_pagado = cliente.get("saldo_actual", 0)
                nombre_cliente = cliente.get("nombre", "")
                consumos_cliente = cliente.get("consumos_semana", [])
                ahora_dt = datetime.now()
                fecha_str = ahora_dt.strftime("%d/%m/%Y %H:%M")

                if total_pagado > 0 or consumos_cliente:
                    comp_pago = f"TOTAL-{ahora_dt.strftime('%Y%m%d%H%M%S')}"
                    partes_c = agrupar_consumos_por_categoria(consumos_cliente) if consumos_cliente else []
                    desc_consumos = " · ".join(partes_c) if partes_c else "CUENTA SALDADA"
                    concepto_pago = f"PAGO TOTAL · {metodo} · {desc_consumos}"
                    if nota:
                        concepto_pago += f" ({nota})"

                    registro_h = {
                        "fecha": fecha_str,
                        "cliente": nombre_cliente,
                        "total": total_pagado,
                        "comprobante": comp_pago,
                        "concepto": concepto_pago,
                        "consumos": consumos_cliente,
                        "metodo": metodo,
                        "tipo": "PAGO_TOTAL"
                    }
                    historial.append(registro_h)
                    guardar_json(RUTA_HISTORIAL, historial)

                # Eliminar definitivamente al cliente del sistema
                clientes = [c for c in clientes if c["id"] != cliente_id]
                guardar_json(RUTA_CLIENTES, clientes)

            self.send_json({
                "ok": True,
                "cliente_nombre": nombre_cliente,
                "total_pagado": total_pagado,
                "metodo": metodo,
                "clientes": clientes,
                "historial": historial
            })
            return

        # 3.2 API: BORRAR TODO EL HISTORIAL DE COBROS
        elif path == "/api/historial/borrar-todos":
            with data_lock:
                guardar_json(RUTA_HISTORIAL, [])
                try:
                    with open(os.path.join(BASE_DIR, "contador.txt"), "w", encoding="utf-8") as f:
                        f.write("1")
                except Exception:
                    pass
            self.send_json({"ok": True, "historial": []})
            return

        # 4. API: REPONER STOCK EN INVENTARIO
        elif path == "/api/inventario/reponer":
            producto_id = body.get("producto_id")
            cantidad = int(body.get("cantidad", 0))
            if not producto_id or cantidad <= 0:
                self.send_json({"ok": False, "error": "Datos inválidos"}, status=400)
                return

            with data_lock:
                inventario = leer_json(RUTA_INVENTARIO, [])
                prod = next((p for p in inventario if p["id"] == producto_id), None)
                if not prod:
                    self.send_json({"ok": False, "error": "Producto no encontrado"}, status=404)
                    return
                prod["stock"] += cantidad
                guardar_json(RUTA_INVENTARIO, inventario)

            self.send_json({"ok": True, "inventario": inventario})
            return

        # 4.1 API: AJUSTAR STOCK EXACTO DIRECTO
        elif path == "/api/inventario/ajustar-stock":
            producto_id = body.get("producto_id")
            stock_nuevo = int(body.get("stock", 0))
            if not producto_id or stock_nuevo < 0:
                self.send_json({"ok": False, "error": "Datos inválidos"}, status=400)
                return

            with data_lock:
                inventario = leer_json(RUTA_INVENTARIO, [])
                prod = next((p for p in inventario if p["id"] == producto_id), None)
                if not prod:
                    self.send_json({"ok": False, "error": "Producto no encontrado"}, status=404)
                    return
                prod["stock"] = stock_nuevo
                guardar_json(RUTA_INVENTARIO, inventario)

            self.send_json({"ok": True, "inventario": inventario})
            return

        # 5. API: AGREGAR NUEVA BEBIDA AL INVENTARIO
        elif path == "/api/inventario/agregar":
            nombre = body.get("nombre", "").strip()
            categoria = body.get("categoria", "Cervezas").strip()
            precio = int(body.get("precio", 0))
            stock = int(body.get("stock", 0))
            min_stock = int(body.get("min_stock", 6))

            if not nombre or precio <= 0:
                self.send_json({"ok": False, "error": "Nombre y precio válidos requeridos"}, status=400)
                return

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

            self.send_json({"ok": True, "inventario": inventario})
            return

        # 6. API: EDITAR PRECIO DE VENTA
        elif path == "/api/inventario/editar-precio":
            producto_id = body.get("producto_id")
            nuevo_precio = int(body.get("precio", 0))
            if not producto_id or nuevo_precio <= 0:
                self.send_json({"ok": False, "error": "Datos inválidos"}, status=400)
                return
            with data_lock:
                inventario = leer_json(RUTA_INVENTARIO, [])
                prod = next((p for p in inventario if p["id"] == producto_id), None)
                if not prod:
                    self.send_json({"ok": False, "error": "Producto no encontrado"}, status=404)
                    return
                prod["precio"] = nuevo_precio
                guardar_json(RUTA_INVENTARIO, inventario)
            self.send_json({"ok": True, "inventario": inventario})
            return

        # 7. API: EDITAR PRECIO DE COSTO (VALOR POR UNIDAD DE COMPRA)
        elif path == "/api/inventario/editar-costo":
            producto_id = body.get("producto_id")
            nuevo_costo = int(body.get("costo", 0))
            if not producto_id or nuevo_costo < 0:
                self.send_json({"ok": False, "error": "Datos inválidos"}, status=400)
                return
            with data_lock:
                inventario = leer_json(RUTA_INVENTARIO, [])
                prod = next((p for p in inventario if p["id"] == producto_id), None)
                if not prod:
                    self.send_json({"ok": False, "error": "Producto no encontrado"}, status=404)
                    return
                diferencia = nuevo_costo - prod.get("precio_costo", 0)
                prod["precio_costo"] = nuevo_costo
                # Si es cerveza base, actualizar automáticamente sus micheladas derivadas
                for derivado in inventario:
                    if derivado.get("descuenta_de_id") == producto_id:
                        derivado["precio_costo"] = max(0, derivado.get("precio_costo", nuevo_costo) + diferencia)
                guardar_json(RUTA_INVENTARIO, inventario)
            self.send_json({"ok": True, "inventario": inventario})
            return

        # 8. API: ELIMINAR PRODUCTO DE INVENTARIO
        elif path == "/api/inventario/eliminar":
            producto_id = body.get("producto_id")
            if not producto_id:
                self.send_json({"ok": False, "error": "ID de producto requerido"}, status=400)
                return
            with data_lock:
                inventario = leer_json(RUTA_INVENTARIO, [])
                inventario = [p for p in inventario if p["id"] != producto_id]
                guardar_json(RUTA_INVENTARIO, inventario)
            self.send_json({"ok": True, "inventario": inventario})
            return

        self.send_error(404, "Endpoint no encontrado")

import sys
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

def iniciar_servidor(puerto=5000):
    ip_local = get_local_ip()
    try:
        servidor = ThreadingHTTPServer(("0.0.0.0", puerto), PanchoHandler)
    except OSError as e:
        if getattr(e, 'winerror', None) == 10048 or "10048" in str(e):
            print("\n" + "=" * 62)
            print("  === PANCHO - SISTEMA DE BEBIDAS, CUENTAS Y TICKETS ===")
            print("=" * 62)
            print("  [OK] El servidor ya se encuentra encendido y activo!\n")
            print(f"  -> En este PC abre:")
            print(f"     http://localhost:{puerto}")
            print(f"\n  -> En tu Tablet o Celular abre:")
            print(f"     http://{ip_local}:{puerto}")
            print("=" * 62)
            return
        raise e

    print("\n" + "=" * 62)
    print("  === PANCHO - SISTEMA DE BEBIDAS, CUENTAS Y TICKETS ===")
    print("=" * 62)
    print("  [OK] Servidor web iniciado con exito!\n")
    print(f"  -> En tu PC abre en el navegador:")
    print(f"     http://localhost:{puerto}")
    print(f"\n  -> En tu Celular (conectado al mismo Wi-Fi) abre:")
    print(f"     http://{ip_local}:{puerto}")
    print("=" * 62)
    print("  Presiona Ctrl + C en esta ventana para detener el servidor.\n")

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Servidor detenido por el usuario.")
        servidor.server_close()

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    iniciar_servidor(puerto)

