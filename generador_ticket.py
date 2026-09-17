from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_CONTADOR = os.path.join(BASE_DIR, "contador.txt")
DIR_TICKETS = os.path.join(BASE_DIR, "tickets")
os.makedirs(DIR_TICKETS, exist_ok=True)

def obtener_siguiente_consecutivo():
    if os.path.exists(ARCHIVO_CONTADOR):
        try:
            with open(ARCHIVO_CONTADOR, "r", encoding="utf-8") as f:
                num = int(f.read().strip())
        except:
            num = 1
    else:
        num = 1
    return num

def incrementar_consecutivo(num_actual):
    try:
        with open(ARCHIVO_CONTADOR, "w", encoding="utf-8") as f:
            f.write(str(num_actual + 1))
    except Exception as e:
        print(f"[!] Error al actualizar contador: {e}")

def limpiar_nombre_archivo(texto):
    s = re.sub(r'[^a-zA-Z0-9_\- ]', '', texto).strip()
    return s.replace(' ', '_').upper()

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def agrupar_consumos_por_categoria(consumos):
    """
    Agrupa una lista de consumos por categoría general según la directriz de Hugo:
    Ejemplo: 5 Águila Light + 3 Poker + 2 Corona -> "10 CERVEZAS"
    Retorna una lista de strings: ["10 CERVEZAS", "2 MICHELADAS"]
    """
    if not consumos:
        return ["CONSUMO SEMANAL"]

    categorias_cuenta = {
        "CERVEZAS": 0,
        "MICHELADAS": 0,
        "SHOTS": 0,
        "BOTELLAS": 0,
        "BEBIDAS": 0,
        "SNACKS": 0
    }
    otros_cuenta = {}

    for item in consumos:
        cant = item.get("cantidad", 1)
        nom = item.get("nombre", "").upper()
        cat = item.get("categoria", "").upper()

        if "MICHELADA" in nom or "MICHELADA" in cat:
            categorias_cuenta["MICHELADAS"] += cant
        elif any(k in nom for k in ["CERVEZA", "POKER", "AGUILA", "CORONA", "CLUB", "PILSEN", "HEINEKEN", "STELLA", "COSTENA", "ANDINA"]) or "CERVEZA" in cat:
            categorias_cuenta["CERVEZAS"] += cant
        elif any(k in nom for k in ["SHOT", "TRAGO"]) or "TRAGO" in cat or "SHOT" in cat:
            categorias_cuenta["SHOTS"] += cant
        elif any(k in nom for k in ["BOTELLA", "MEDIA"]) or "LICOR" in cat or any(k in nom for k in ["AGUARDIENTE", "RON ", "WHISKY", "VODKA", "TEQUILA"]):
            categorias_cuenta["BOTELLAS"] += cant
        elif any(k in nom for k in ["SODA", "AGUA", "LIMONADA", "GATORADE", "RED BULL", "JUGO"]) or "BEBIDA" in cat:
            categorias_cuenta["BEBIDAS"] += cant
        elif "SNACK" in cat or any(k in nom for k in ["PAPAS", "MANI", "PLÁTANO", "PLATANO"]):
            categorias_cuenta["SNACKS"] += cant
        else:
            nom_limpio = nom.replace("CERVEZA ", "").replace("TRAGO / SHOT DE ", "SHOT ").strip()
            otros_cuenta[nom_limpio] = otros_cuenta.get(nom_limpio, 0) + cant

    resultado = []
    if categorias_cuenta["CERVEZAS"] > 0:
        resultado.append(f"{categorias_cuenta['CERVEZAS']} CERVEZAS" if categorias_cuenta['CERVEZAS'] > 1 else "1 CERVEZA")
    if categorias_cuenta["MICHELADAS"] > 0:
        resultado.append(f"{categorias_cuenta['MICHELADAS']} MICHELADAS" if categorias_cuenta['MICHELADAS'] > 1 else "1 MICHELADA")
    if categorias_cuenta["SHOTS"] > 0:
        resultado.append(f"{categorias_cuenta['SHOTS']} SHOTS" if categorias_cuenta['SHOTS'] > 1 else "1 SHOT")
    if categorias_cuenta["BOTELLAS"] > 0:
        resultado.append(f"{categorias_cuenta['BOTELLAS']} BOTELLAS" if categorias_cuenta['BOTELLAS'] > 1 else "1 BOTELLA")
    if categorias_cuenta["BEBIDAS"] > 0:
        resultado.append(f"{categorias_cuenta['BEBIDAS']} BEBIDAS" if categorias_cuenta['BEBIDAS'] > 1 else "1 BEBIDA")
    if categorias_cuenta["SNACKS"] > 0:
        resultado.append(f"{categorias_cuenta['SNACKS']} SNACKS" if categorias_cuenta['SNACKS'] > 1 else "1 SNACK")

    for nom, cant in otros_cuenta.items():
        resultado.append(f"{cant} {nom}")

    if not resultado:
        return ["CONSUMO SEMANAL"]

    return resultado

def generar_ticket_cobro(cliente, concepto, monto_val, titular_nequi="HUGO BRION", guardar_en_tickets=True):
    """
    Genera la imagen oficial del ticket de cobro de PANCHO remodelado.
    Retorna una tupla: (ruta_archivo_absoluta, nombre_archivo_relativo, numero_comprobante)
    """
    consecutivo_num = obtener_siguiente_consecutivo()
    numero_comprobante = f"#CC-{datetime.now().year}-{consecutivo_num:04d}"
    
    # Formateo de monto
    if isinstance(monto_val, (int, float)):
        txt_monto = f"$ {int(monto_val):,.0f}".replace(",", ".")
    else:
        m_str = str(monto_val).replace("$", "").replace(" ", "").replace(".", "").strip()
        if m_str.isdigit():
            txt_monto = f"$ {int(m_str):,.0f}".replace(",", ".")
        else:
            txt_monto = f"$ {monto_val}"

    # Procesar líneas de concepto/consumo de forma limpia
    if isinstance(concepto, list):
        lineas_concepto = [str(c).strip().upper() for c in concepto if str(c).strip()]
    elif isinstance(concepto, str):
        c_str = concepto.strip().upper()
        if "\n" in c_str:
            lineas_concepto = [l.strip() for l in c_str.split("\n") if l.strip()]
        elif " · " in c_str:
            lineas_concepto = [l.strip() for l in c_str.split(" · ") if l.strip()]
        elif " + " in c_str:
            lineas_concepto = [l.strip() for l in c_str.split(" + ") if l.strip()]
        else:
            lineas_concepto = [c_str]
    else:
        lineas_concepto = [str(concepto).strip().upper()]

    if not lineas_concepto:
        lineas_concepto = ["CONSUMO SEMANAL"]

    # Dimensiones
    ancho, alto = 560, 680
    radio_externo = 22
    radio_tarjeta = 14

    color_top = hex_to_rgb("#FFAA00")
    color_bot = hex_to_rgb("#E8003A")
    color_marco = "#1A1A1A"
    color_texto = "#1A1A1A"
    color_secundario = "#555555"

    # Degradado oficial PANCHO (100% nativo Pillow)
    grad_base = Image.new("RGB", (1, alto))
    for y in range(alto):
        t = y / alto
        r = int(color_top[0] + (color_bot[0] - color_top[0]) * t)
        g = int(color_top[1] + (color_bot[1] - color_top[1]) * t)
        b = int(color_top[2] + (color_bot[2] - color_top[2]) * t)
        grad_base.putpixel((0, y), (r, g, b))

    ticket = grad_base.resize((ancho, alto), Image.Resampling.BILINEAR).convert("RGBA")

    # Máscara redondeada
    mask = Image.new("L", (ancho, alto), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), (ancho - 1, alto - 1)], radius=radio_externo, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=1.5))
    ticket.putalpha(mask)

    # Logo oficial como marca de agua en la esquina superior derecha
    ruta_logo = os.path.join(BASE_DIR, "logo.png")
    if os.path.exists(ruta_logo):
        try:
            logo_base = Image.open(ruta_logo).convert("RGBA")
            logo_w = 90
            logo_h = int(logo_base.height * (logo_w / logo_base.width))
            logo_corner = logo_base.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            
            # Efecto marca de agua suave (opacidad al 38%)
            r, g, b, a = logo_corner.split()
            a = a.point(lambda p: int(p * 0.38))
            logo_corner.putalpha(a)

            # Integrar como marca de agua con alpha blending perfecto
            overlay_logo = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
            overlay_logo.paste(logo_corner, (ancho - logo_w - 20, 14))
            ticket = Image.alpha_composite(ticket, overlay_logo)
        except Exception as e:
            print(f"[!] Error al aplicar logo como marca de agua: {e}")

    draw = ImageDraw.Draw(ticket)
    draw.rounded_rectangle([(4, 4), (ancho - 5, alto - 5)], radius=radio_externo, outline=color_marco, width=2)

    # Carga de tipografías
    def cargar_fuente(nombre, tam):
        ruta_directa = os.path.join(BASE_DIR, nombre)
        if os.path.exists(ruta_directa):
            try:
                return ImageFont.truetype(ruta_directa, tam)
            except Exception as e:
                print(f"[!] Error cargando fuente directa {nombre}: {e}")

        nombre_clean = os.path.splitext(os.path.basename(nombre))[0].lower()
        nombre_lower = os.path.basename(nombre).lower()
        if os.path.exists(BASE_DIR):
            for archivo in os.listdir(BASE_DIR):
                arch_lower = archivo.lower()
                arch_clean = os.path.splitext(arch_lower)[0]
                if arch_lower == nombre_lower or arch_clean == nombre_clean:
                    ruta_real = os.path.join(BASE_DIR, archivo)
                    try:
                        return ImageFont.truetype(ruta_real, tam)
                    except Exception as e:
                        print(f"[!] Error cargando fuente {archivo}: {e}")
        return ImageFont.load_default()

    font_titulo = cargar_fuente("PANCHO15.otf", 44)
    font_sub = cargar_fuente("PANCHO6.otf", 13)
    font_lbl_cobro = cargar_fuente("PANCHO6.otf", 14)
    font_monto = cargar_fuente("PANCHO15.otf", 46)
    font_campo_lbl = cargar_fuente("PANCHO6.otf", 14)
    font_campo_val = cargar_fuente("PANCHO15.otf", 19)
    font_consumo = cargar_fuente("PANCHO15.otf", 17)
    font_pago_tit = cargar_fuente("PANCHO15.otf", 17)
    font_pago_num = cargar_fuente("PANCHO15.otf", 26)
    font_nota = cargar_fuente("PANCHO6.otf", 13)
    font_pie = cargar_fuente("PANCHO15.otf", 18)

    cx = ancho // 2

    # Encabezado PANCHO
    titulo = "PANCHO"
    bbox_t = draw.textbbox((0, 0), titulo, font=font_titulo)
    draw.text((cx - (bbox_t[2] - bbox_t[0]) // 2, 22), titulo, font=font_titulo, fill=color_texto)

    badge_tipo = "CUENTA DE COBRO DIGITAL"
    bbox_bt = draw.textbbox((0, 0), badge_tipo, font=font_sub)
    ancho_bt = bbox_bt[2] - bbox_bt[0]
    draw.rounded_rectangle(
        [(cx - ancho_bt // 2 - 12, 70), (cx + ancho_bt // 2 + 12, 92)],
        radius=11,
        fill="#FFFFFF",
        outline=color_marco,
        width=1
    )
    draw.text((cx - ancho_bt // 2, 73), badge_tipo, font=font_sub, fill=color_texto)

    # 1. Caja Hero: TOTAL A PAGAR
    box1_x1, box1_y1 = 30, 106
    box1_x2, box1_y2 = ancho - 30, 196

    overlay1 = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    d_ov1 = ImageDraw.Draw(overlay1)
    d_ov1.rounded_rectangle([(box1_x1 + 1, box1_y1 + 2), (box1_x2 + 1, box1_y2 + 2)], radius=radio_tarjeta, fill=(0, 0, 0, 35))
    d_ov1.rounded_rectangle([(box1_x1, box1_y1), (box1_x2, box1_y2)], radius=radio_tarjeta, fill=(255, 255, 255, 245), outline=(30, 30, 30, 180), width=1)
    ticket = Image.alpha_composite(ticket, overlay1)
    draw = ImageDraw.Draw(ticket)

    lbl_saldo = "TOTAL A PAGAR:"
    bbox_ls = draw.textbbox((0, 0), lbl_saldo, font=font_lbl_cobro)
    draw.text((cx - (bbox_ls[2] - bbox_ls[0]) // 2, box1_y1 + 14), lbl_saldo, font=font_lbl_cobro, fill=color_secundario)

    bbox_m = draw.textbbox((0, 0), txt_monto, font=font_monto)
    draw.text((cx - (bbox_m[2] - bbox_m[0]) // 2, box1_y1 + 36), txt_monto, font=font_monto, fill=color_texto)

    # 2. Tarjeta de Detalles y Consumos
    box2_x1, box2_y1 = 30, 210
    box2_x2, box2_y2 = ancho - 30, 420

    overlay2 = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    d_ov2 = ImageDraw.Draw(overlay2)
    d_ov2.rounded_rectangle([(box2_x1 + 1, box2_y1 + 2), (box2_x2 + 1, box2_y2 + 2)], radius=radio_tarjeta, fill=(0, 0, 0, 35))
    d_ov2.rounded_rectangle([(box2_x1, box2_y1), (box2_x2, box2_y2)], radius=radio_tarjeta, fill=(255, 255, 255, 245), outline=(30, 30, 30, 180), width=1)
    ticket = Image.alpha_composite(ticket, overlay2)
    draw = ImageDraw.Draw(ticket)

    # Fila 1: CLIENTE
    y_r1 = box2_y1 + 14
    draw.text((box2_x1 + 18, y_r1), "CLIENTE", font=font_campo_lbl, fill=color_secundario)
    nom_cli = cliente.upper()
    bbox_cli = draw.textbbox((0, 0), nom_cli, font=font_campo_val)
    draw.text((box2_x2 - 18 - (bbox_cli[2] - bbox_cli[0]), y_r1 - 2), nom_cli, font=font_campo_val, fill=color_texto)
    draw.line([(box2_x1 + 16, y_r1 + 26), (box2_x2 - 16, y_r1 + 26)], fill=(225, 225, 225, 255), width=1)

    # Fila 2: FECHA DE EMISIÓN
    y_r2 = y_r1 + 34
    draw.text((box2_x1 + 18, y_r2), "FECHA DE EMISIÓN", font=font_campo_lbl, fill=color_secundario)
    txt_fecha = datetime.now().strftime("%d / %m / %Y")
    bbox_fec = draw.textbbox((0, 0), txt_fecha, font=font_campo_val)
    draw.text((box2_x2 - 18 - (bbox_fec[2] - bbox_fec[0]), y_r2 - 2), txt_fecha, font=font_campo_val, fill=color_texto)
    draw.line([(box2_x1 + 16, y_r2 + 26), (box2_x2 - 16, y_r2 + 26)], fill=(225, 225, 225, 255), width=1)

    # Fila 3: N° DE COMPROBANTE
    y_r3 = y_r2 + 34
    draw.text((box2_x1 + 18, y_r3), "N° DE COMPROBANTE", font=font_campo_lbl, fill=color_secundario)
    bbox_comp = draw.textbbox((0, 0), numero_comprobante, font=font_campo_val)
    draw.text((box2_x2 - 18 - (bbox_comp[2] - bbox_comp[0]), y_r3 - 2), numero_comprobante, font=font_campo_val, fill=color_texto)
    draw.line([(box2_x1 + 16, y_r3 + 26), (box2_x2 - 16, y_r3 + 26)], fill=(225, 225, 225, 255), width=1)

    # Fila 4: CONSUMO(S)
    y_r4 = y_r3 + 34
    draw.text((box2_x1 + 18, y_r4), "CONSUMOS:", font=font_campo_lbl, fill=color_secundario)

    if len(lineas_concepto) == 1:
        it = lineas_concepto[0]
        bbox_it = draw.textbbox((0, 0), it, font=font_consumo)
        ancho_it = bbox_it[2] - bbox_it[0]
        if ancho_it < (box2_x2 - box2_x1 - 190):
            draw.text((box2_x2 - 18 - ancho_it, y_r4 - 2), it, font=font_consumo, fill=color_texto)
        else:
            it_txt = it if len(it) <= 32 else it[:29] + "..."
            draw.text((box2_x1 + 22, y_r4 + 22), f"•  {it_txt}", font=font_consumo, fill=color_texto)
    else:
        badge_sem = "SEMANA"
        bbox_bs = draw.textbbox((0, 0), badge_sem, font=font_sub)
        draw.text((box2_x2 - 18 - (bbox_bs[2] - bbox_bs[0]), y_r4), badge_sem, font=font_sub, fill=color_secundario)

        y_item = y_r4 + 22
        for item in lineas_concepto[:3]:
            it_txt = item if len(item) <= 32 else item[:29] + "..."
            draw.text((box2_x1 + 22, y_item), f"•  {it_txt}", font=font_consumo, fill=color_texto)
            y_item += 22

    # 3. Caja Canal de Pago (Nequi)
    box3_x1, box3_y1 = 30, 434
    box3_x2, box3_y2 = ancho - 30, 546

    overlay3 = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    d_ov3 = ImageDraw.Draw(overlay3)
    d_ov3.rounded_rectangle([(box3_x1 + 1, box3_y1 + 2), (box3_x2 + 1, box3_y2 + 2)], radius=radio_tarjeta, fill=(0, 0, 0, 35))
    d_ov3.rounded_rectangle([(box3_x1, box3_y1), (box3_x2, box3_y2)], radius=radio_tarjeta, fill=(255, 255, 255, 245), outline=(20, 20, 20, 200), width=2)
    ticket = Image.alpha_composite(ticket, overlay3)
    draw = ImageDraw.Draw(ticket)

    tit_transf = "CANAL DE PAGO"
    bbox_pt = draw.textbbox((0, 0), tit_transf, font=font_pago_tit)
    draw.text((cx - (bbox_pt[2] - bbox_pt[0]) // 2, box3_y1 + 14), tit_transf, font=font_pago_tit, fill=color_secundario)

    draw.line([(box3_x1 + 25, box3_y1 + 38), (box3_x2 - 25, box3_y1 + 38)], fill=(215, 215, 215, 255), width=1)

    nequi_txt = "NEQUI: 301 343 27 75"
    bbox_nq = draw.textbbox((0, 0), nequi_txt, font=font_pago_num)
    draw.text((cx - (bbox_nq[2] - bbox_nq[0]) // 2, box3_y1 + 48), nequi_txt, font=font_pago_num, fill="#111111")

    sub_nequi = f"A NOMBRE DE: {titular_nequi.upper()}"
    bbox_sn = draw.textbbox((0, 0), sub_nequi, font=font_nota)
    draw.text((cx - (bbox_sn[2] - bbox_sn[0]) // 2, box3_y1 + 82), sub_nequi, font=font_nota, fill=color_secundario)

    # 4. Footer Minimalista (Solicitado por Hugo: Única y exclusivamente la frase de agradecimiento)
    pie = "¡MUCHAS GRACIAS POR SU PREFERENCIA!"
    bbox_pie = draw.textbbox((0, 0), pie, font=font_pie)
    pie_w = bbox_pie[2] - bbox_pie[0]
    pie_h = bbox_pie[3] - bbox_pie[1]
    pie_x = cx - pie_w // 2
    pie_y = 612 - pie_h // 2

    # Sombra sutil de 1px para máximo relieve y legibilidad sobre el rojo
    draw.text((pie_x + 1, pie_y + 1), pie, font=font_pie, fill=(0, 0, 0, 90))
    draw.text((pie_x, pie_y), pie, font=font_pie, fill="#FFFFFF")

    # Guardado de imagen
    cli_slug = limpiar_nombre_archivo(cliente)
    nombre_archivo = f"{cli_slug}_{numero_comprobante.replace('#', '').replace('-', '_')}.png"
    
    if guardar_en_tickets:
        ruta_guardado = os.path.join(DIR_TICKETS, nombre_archivo)
    else:
        ruta_guardado = os.path.join(BASE_DIR, nombre_archivo)

    ticket.save(ruta_guardado, quality=95)

    try:
        ticket.save(os.path.join(BASE_DIR, "ticket.png"), quality=95)
    except:
        pass

    incrementar_consecutivo(consecutivo_num)

    return ruta_guardado, nombre_archivo, numero_comprobante
