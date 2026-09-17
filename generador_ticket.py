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

def generar_ticket_cobro(cliente, concepto, monto_val, titular_nequi="HUGO BRION", guardar_en_tickets=True):
    """
    Genera la imagen oficial del ticket de cobro de PANCHO.
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

    # Dimensiones
    ancho, alto = 560, 680
    radio_externo = 22
    radio_tarjeta = 14

    color_top = hex_to_rgb("#FFAA00")
    color_bot = hex_to_rgb("#E8003A")
    color_marco = "#1A1A1A"
    color_texto = "#1A1A1A"
    color_secundario = "#4A4A4A"

    # Degradado (100% nativo Pillow, sin depender de librerías externas)
    grad_base = Image.new("RGB", (1, alto))
    for y in range(alto):
        t = y / alto
        r = int(color_top[0] + (color_bot[0] - color_top[0]) * t)
        g = int(color_top[1] + (color_bot[1] - color_top[1]) * t)
        b = int(color_top[2] + (color_bot[2] - color_top[2]) * t)
        grad_base.putpixel((0, y), (r, g, b))

    ticket = grad_base.resize((ancho, alto), Image.Resampling.BILINEAR).convert("RGBA")

    # Mascara redondeada
    mask = Image.new("L", (ancho, alto), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), (ancho - 1, alto - 1)], radius=radio_externo, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=1.5))
    ticket.putalpha(mask)

    # Logo en esquina superior derecha
    ruta_logo = os.path.join(BASE_DIR, "logo.png")
    if os.path.exists(ruta_logo):
        try:
            logo_base = Image.open(ruta_logo).convert("RGBA")
            logo_w = 80
            logo_h = int(logo_base.height * (logo_w / logo_base.width))
            logo_corner = logo_base.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            ticket.paste(logo_corner, (ancho - logo_w - 22, 16), logo_corner)
        except Exception:
            pass

    draw = ImageDraw.Draw(ticket)
    draw.rounded_rectangle([(4, 4), (ancho - 5, alto - 5)], radius=radio_externo, outline=color_marco, width=2)

    # Tipografías
    def cargar_fuente(nombre, tam):
        for candidate in [nombre, nombre.lower(), nombre.upper()]:
            ruta = os.path.join(BASE_DIR, candidate)
            if os.path.exists(ruta):
                try:
                    return ImageFont.truetype(ruta, tam)
                except:
                    pass
        return ImageFont.load_default()

    font_titulo = cargar_fuente("PANCHO15.OTF", 46)
    font_sub = cargar_fuente("PANCHO6.OTF", 14)
    font_lbl_cobro = cargar_fuente("PANCHO6.OTF", 15)
    font_monto = cargar_fuente("PANCHO15.OTF", 48)
    font_campo_lbl = cargar_fuente("PANCHO6.OTF", 15)
    font_campo_val = cargar_fuente("PANCHO15.OTF", 20)
    font_pago_tit = cargar_fuente("PANCHO15.OTF", 18)
    font_pago_num = cargar_fuente("PANCHO15.OTF", 26)
    font_nota = cargar_fuente("PANCHO6.OTF", 13)
    font_pie = cargar_fuente("PANCHO6.OTF", 14)

    cx = ancho // 2

    # Encabezado
    titulo = "PANCHO"
    bbox_t = draw.textbbox((0, 0), titulo, font=font_titulo)
    draw.text((cx - (bbox_t[2] - bbox_t[0]) // 2, 22), titulo, font=font_titulo, fill=color_texto)

    badge_tipo = "CUENTA DE COBRO DIGITAL"
    bbox_bt = draw.textbbox((0, 0), badge_tipo, font=font_sub)
    ancho_bt = bbox_bt[2] - bbox_bt[0]
    draw.rounded_rectangle(
        [(cx - ancho_bt // 2 - 12, 72), (cx + ancho_bt // 2 + 12, 94)],
        radius=11,
        fill="#FFFFFF",
        outline=color_marco,
        width=1
    )
    draw.text((cx - ancho_bt // 2, 75), badge_tipo, font=font_sub, fill=color_texto)

    # Caja Hero: TOTAL A PAGAR
    box1_x1, box1_y1 = 30, 110
    box1_x2, box1_y2 = ancho - 30, 205

    overlay1 = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    d_ov1 = ImageDraw.Draw(overlay1)
    d_ov1.rounded_rectangle([(box1_x1, box1_y1), (box1_x2, box1_y2)], radius=radio_tarjeta, fill=(255, 255, 255, 235), outline=(30, 30, 30, 180), width=1)
    ticket = Image.alpha_composite(ticket, overlay1)
    draw = ImageDraw.Draw(ticket)

    lbl_saldo = "TOTAL A PAGAR:"
    bbox_ls = draw.textbbox((0, 0), lbl_saldo, font=font_lbl_cobro)
    draw.text((cx - (bbox_ls[2] - bbox_ls[0]) // 2, box1_y1 + 16), lbl_saldo, font=font_lbl_cobro, fill=color_secundario)

    bbox_m = draw.textbbox((0, 0), txt_monto, font=font_monto)
    draw.text((cx - (bbox_m[2] - bbox_m[0]) // 2, box1_y1 + 38), txt_monto, font=font_monto, fill=color_texto)

    # Tarjeta de Detalles
    box2_x1, box2_y1 = 30, 235
    box2_x2, box2_y2 = ancho - 30, 395

    overlay2 = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    d_ov2 = ImageDraw.Draw(overlay2)
    d_ov2.rounded_rectangle([(box2_x1, box2_y1), (box2_x2, box2_y2)], radius=radio_tarjeta, fill=(255, 255, 255, 235), outline=(30, 30, 30, 180), width=1)
    ticket = Image.alpha_composite(ticket, overlay2)
    draw = ImageDraw.Draw(ticket)

    # Si el concepto es muy largo, recortarlo con elipsis
    concepto_mostrar = concepto.upper()
    if len(concepto_mostrar) > 28:
        concepto_mostrar = concepto_mostrar[:25] + "..."

    detalles = [
        ("CLIENTE", cliente.upper()),
        ("FECHA DE EMISIÓN", datetime.now().strftime("%d / %m / %Y")),
        ("CONCEPTO", concepto_mostrar),
        ("N° DE COMPROBANTE", numero_comprobante)
    ]

    y_det = box2_y1 + 18
    for i, (lbl, val) in enumerate(detalles):
        draw.text((box2_x1 + 20, y_det), lbl, font=font_campo_lbl, fill=color_secundario)
        bbox_v = draw.textbbox((0, 0), val, font=font_campo_val)
        draw.text((box2_x2 - 20 - (bbox_v[2] - bbox_v[0]), y_det - 2), val, font=font_campo_val, fill=color_texto)
        if i < len(detalles) - 1:
            draw.line([(box2_x1 + 16, y_det + 26), (box2_x2 - 16, y_det + 26)], fill=(220, 220, 220, 255), width=1)
        y_det += 38

    # Caja Canal de Pago (Nequi)
    box3_x1, box3_y1 = 30, 410
    box3_x2, box3_y2 = ancho - 30, 520

    overlay3 = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    d_ov3 = ImageDraw.Draw(overlay3)
    d_ov3.rounded_rectangle([(box3_x1, box3_y1), (box3_x2, box3_y2)], radius=radio_tarjeta, fill=(255, 255, 255, 245), outline=(20, 20, 20, 220), width=2)
    ticket = Image.alpha_composite(ticket, overlay3)
    draw = ImageDraw.Draw(ticket)

    tit_transf = "CANAL DE PAGO"
    bbox_pt = draw.textbbox((0, 0), tit_transf, font=font_pago_tit)
    draw.text((cx - (bbox_pt[2] - bbox_pt[0]) // 2, box3_y1 + 14), tit_transf, font=font_pago_tit, fill=color_secundario)

    draw.line([(box3_x1 + 25, box3_y1 + 42), (box3_x2 - 25, box3_y1 + 42)], fill=(210, 210, 210, 255), width=1)

    nequi_txt = "NEQUI: 301 343 27 75"
    bbox_nq = draw.textbbox((0, 0), nequi_txt, font=font_pago_num)
    draw.text((cx - (bbox_nq[2] - bbox_nq[0]) // 2, box3_y1 + 54), nequi_txt, font=font_pago_num, fill="#111111")

    sub_nequi = f"A NOMBRE DE: {titular_nequi.upper()}"
    bbox_sn = draw.textbbox((0, 0), sub_nequi, font=font_nota)
    draw.text((cx - (bbox_sn[2] - bbox_sn[0]) // 2, box3_y1 + 88), sub_nequi, font=font_nota, fill=color_secundario)

    # Footer
    nota1 = "POR FAVOR ENVÍA EL COMPROBANTE DE PAGO A ESTE CHAT"
    nota2 = "UNA VEZ REALIZADA LA TRANSFERENCIA."
    bbox_n1 = draw.textbbox((0, 0), nota1, font=font_nota)
    bbox_n2 = draw.textbbox((0, 0), nota2, font=font_nota)
    draw.text((cx - (bbox_n1[2] - bbox_n1[0]) // 2, 538), nota1, font=font_nota, fill="#FFFFFF")
    draw.text((cx - (bbox_n2[2] - bbox_n2[0]) // 2, 558), nota2, font=font_nota, fill="#FFFFFF")

    for x in range(80, ancho - 80, 8):
        draw.line([(x, 595), (x + 4, 595)], fill="#FFFFFF", width=1)

    pie = "¡MUCHAS GRACIAS POR SU PREFERENCIA!"
    bbox_pie = draw.textbbox((0, 0), pie, font=font_pie)
    draw.text((cx - (bbox_pie[2] - bbox_pie[0]) // 2, 615), pie, font=font_pie, fill="#FFFFFF")

    contacto = "DOMICILIO  ·  301 343 27 75"
    bbox_cnt = draw.textbbox((0, 0), contacto, font=font_nota)
    draw.text((cx - (bbox_cnt[2] - bbox_cnt[0]) // 2, 642), contacto, font=font_nota, fill="#FFD0D0")

    # Guardado de imagen
    cli_slug = limpiar_nombre_archivo(cliente)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"{cli_slug}_{numero_comprobante.replace('#', '').replace('-', '_')}.png"
    
    if guardar_en_tickets:
        ruta_guardado = os.path.join(DIR_TICKETS, nombre_archivo)
    else:
        ruta_guardado = os.path.join(BASE_DIR, nombre_archivo)

    ticket.save(ruta_guardado, quality=95)

    # También actualizar el ticket.png principal por compatibilidad
    try:
        ticket.save(os.path.join(BASE_DIR, "ticket.png"), quality=95)
    except:
        pass

    # Incrementar contador
    incrementar_consecutivo(consecutivo_num)

    return ruta_guardado, nombre_archivo, numero_comprobante
