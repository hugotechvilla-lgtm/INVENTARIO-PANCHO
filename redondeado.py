from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime
import numpy as np
import os

# ==========================================
# 0. CONTROL DE CONSECUTIVO AUTOMÁTICO
# ==========================================
archivo_contador = "contador.txt"

if os.path.exists(archivo_contador):
    try:
        with open(archivo_contador, "r", encoding="utf-8") as f:
            consecutivo_num = int(f.read().strip())
    except:
        consecutivo_num = 1
else:
    consecutivo_num = 1

numero_comprobante = f"#CC-{datetime.now().year}-{consecutivo_num:04d}"

# ==========================================
# 1. ENTRADA INTERACTIVA DE DATOS
# ==========================================
print("\n" + "=" * 50)
print("  🎫 GENERADOR DE CUENTAS DE COBRO · PANCHO")
print("=" * 50)
print(f"-> Consecutivo asignado: {numero_comprobante}\n")

cliente = input("1. Nombre del cliente: ").strip().upper()
if not cliente:
    cliente = "IVONNE"

concepto = input("2. Concepto o detalle [Ej: SALDO]: ").strip().upper()
if not concepto:
    concepto = "SALDO"

monto_in = input("3. Valor a pagar [Ej: 24000 o 24.000]: ").strip()
if not monto_in:
    monto_in = "24.000"

# Formatear el monto automáticamente si escriben sólo números
monto_limpio = monto_in.replace("$", "").replace(" ", "").strip()
if monto_limpio.isdigit():
    val_int = int(monto_limpio)
    txt_monto = f"$ {val_int:,.0f}".replace(",", ".")
else:
    txt_monto = f"$ {monto_limpio}" if not monto_limpio.startswith("$") else monto_limpio

print(f"\n[+] Generando ticket para '{cliente}' por {txt_monto}...")

# ==========================================
# 2. CONFIGURACIÓN GENERAL Y DIMENSIONES
# ==========================================
ancho, alto = 560, 680
radio_externo = 22
radio_tarjeta = 14

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

color_top = hex_to_rgb("#FFAA00")
color_bot = hex_to_rgb("#E8003A")

color_marco = "#1A1A1A"
color_texto = "#1A1A1A"
color_secundario = "#4A4A4A"

# ==========================================
# 3. DEGRADADO DE FONDO
# ==========================================
gradient = np.zeros((alto, ancho, 3), dtype=np.uint8)
for y in range(alto):
    t = y / alto
    r = int(color_top[0] + (color_bot[0] - color_top[0]) * t)
    g = int(color_top[1] + (color_bot[1] - color_top[1]) * t)
    b = int(color_top[2] + (color_bot[2] - color_top[2]) * t)
    gradient[y, :] = [r, g, b]

ticket = Image.fromarray(gradient).convert("RGBA")

# Máscara redondeada
mask = Image.new("L", (ancho, alto), 0)
mask_draw = ImageDraw.Draw(mask)
mask_draw.rounded_rectangle([(0, 0), (ancho - 1, alto - 1)], radius=radio_externo, fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(radius=1.5))
ticket.putalpha(mask)

# ==========================================
# 4. LOGO DE PANCHO EN LA ESQUINA SUPERIOR DERECHA (A TODO COLOR)
# ==========================================
try:
    logo_base = Image.open("logo.png").convert("RGBA")
    logo_corner_w = 80
    logo_corner_h = int(logo_base.height * (logo_corner_w / logo_base.width))
    logo_corner = logo_base.resize((logo_corner_w, logo_corner_h), Image.Resampling.LANCZOS)
    corner_x = ancho - logo_corner_w - 22
    corner_y = 16
    ticket.paste(logo_corner, (corner_x, corner_y), logo_corner)
except Exception as e:
    pass

draw = ImageDraw.Draw(ticket)
draw.rounded_rectangle([(4, 4), (ancho - 5, alto - 5)], radius=radio_externo, outline=color_marco, width=2)

# ==========================================
# 5. FUENTES TIPOGRÁFICAS
# ==========================================
try:
    font_titulo = ImageFont.truetype("PANCHO15.OTF", 46)
    font_sub = ImageFont.truetype("PANCHO15.OTF", 14)
    font_lbl_cobro = ImageFont.truetype("PANCHO15.OTF", 15)
    font_monto = ImageFont.truetype("PANCHO15.OTF", 48)
    font_badge = ImageFont.truetype("PANCHO15.OTF", 13)
    font_campo_lbl = ImageFont.truetype("PANCHO15.OTF", 15)
    font_campo_val = ImageFont.truetype("PANCHO15.OTF", 20)
    font_pago_tit = ImageFont.truetype("PANCHO15.OTF", 18)
    font_pago_num = ImageFont.truetype("PANCHO15.OTF", 26)
    font_nota = ImageFont.truetype("PANCHO15.OTF", 13)
    font_pie = ImageFont.truetype("PANCHO15.OTF", 14)
except:
    font_titulo = ImageFont.load_default()
    font_sub = ImageFont.load_default()
    font_lbl_cobro = ImageFont.load_default()
    font_monto = ImageFont.load_default()
    font_badge = ImageFont.load_default()
    font_campo_lbl = ImageFont.load_default()
    font_campo_val = ImageFont.load_default()
    font_pago_tit = ImageFont.load_default()
    font_pago_num = ImageFont.load_default()
    font_nota = ImageFont.load_default()
    font_pie = ImageFont.load_default()

cx = ancho // 2

# ==========================================
# 6. ENCABEZADO
# ==========================================
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

# ==========================================
# 7. CAJA HERO: SALDO A PAGAR
# ==========================================
box1_x1, box1_y1 = 30, 110
box1_x2, box1_y2 = ancho - 30, 205

overlay1 = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
d_ov1 = ImageDraw.Draw(overlay1)
d_ov1.rounded_rectangle([(box1_x1, box1_y1), (box1_x2, box1_y2)], radius=radio_tarjeta, fill=(255, 255, 255, 235), outline=(30, 30, 30, 180), width=1)
ticket = Image.alpha_composite(ticket, overlay1)
draw = ImageDraw.Draw(ticket)

# Etiqueta "TOTAL A PAGAR:"
lbl_saldo = "TOTAL A PAGAR:"
bbox_ls = draw.textbbox((0, 0), lbl_saldo, font=font_lbl_cobro)
draw.text((cx - (bbox_ls[2] - bbox_ls[0]) // 2, box1_y1 + 16), lbl_saldo, font=font_lbl_cobro, fill=color_secundario)

# Monto Gigante (ej: $ 12.000)
bbox_m = draw.textbbox((0, 0), txt_monto, font=font_monto)
draw.text((cx - (bbox_m[2] - bbox_m[0]) // 2, box1_y1 + 38), txt_monto, font=font_monto, fill=color_texto)

# ==========================================
# 8. TARJETA DE DETALLES DEL CLIENTE
# ==========================================
box2_x1, box2_y1 = 30, 235
box2_x2, box2_y2 = ancho - 30, 395

overlay2 = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
d_ov2 = ImageDraw.Draw(overlay2)
d_ov2.rounded_rectangle([(box2_x1, box2_y1), (box2_x2, box2_y2)], radius=radio_tarjeta, fill=(255, 255, 255, 235), outline=(30, 30, 30, 180), width=1)
ticket = Image.alpha_composite(ticket, overlay2)
draw = ImageDraw.Draw(ticket)

detalles = [
    ("CLIENTE", cliente),
    ("FECHA DE EMISIÓN", datetime.now().strftime("%d / %m / %Y")),
    ("CONCEPTO", concepto),
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

# ==========================================
# 9. CAJA DESTACADA: DATOS PARA TRANSFERIR (NEQUI)
# ==========================================
box3_x1, box3_y1 = 30, 410
box3_x2, box3_y2 = ancho - 30, 520

overlay3 = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
d_ov3 = ImageDraw.Draw(overlay3)
d_ov3.rounded_rectangle([(box3_x1, box3_y1), (box3_x2, box3_y2)], radius=radio_tarjeta, fill=(255, 255, 255, 245), outline=(20, 20, 20, 220), width=2)
ticket = Image.alpha_composite(ticket, overlay3)
draw = ImageDraw.Draw(ticket)

tit_transf = "📲 CANAL DE PAGO "
bbox_pt = draw.textbbox((0, 0), tit_transf, font=font_pago_tit)
draw.text((cx - (bbox_pt[2] - bbox_pt[0]) // 2, box3_y1 + 14), tit_transf, font=font_pago_tit, fill=color_secundario)

draw.line([(box3_x1 + 25, box3_y1 + 42), (box3_x2 - 25, box3_y1 + 42)], fill=(210, 210, 210, 255), width=1)

nequi_txt = "NEQUI: 301 343 27 75"
bbox_nq = draw.textbbox((0, 0), nequi_txt, font=font_pago_num)
draw.text((cx - (bbox_nq[2] - bbox_nq[0]) // 2, box3_y1 + 54), nequi_txt, font=font_pago_num, fill="#111111")

sub_nequi = "A nombre de: HUGO BRION"
bbox_sn = draw.textbbox((0, 0), sub_nequi, font=font_nota)
draw.text((cx - (bbox_sn[2] - bbox_sn[0]) // 2, box3_y1 + 88), sub_nequi, font=font_nota, fill=color_secundario)

# ==========================================
# 10. MENSAJE Y LLAMADO A LA ACCIÓN (CHAT)
# ==========================================
nota1 = "Por favor envía el comprobante de pago a este chat"
nota2 = "una vez realizada la transferencia."
bbox_n1 = draw.textbbox((0, 0), nota1, font=font_nota)
bbox_n2 = draw.textbbox((0, 0), nota2, font=font_nota)
draw.text((cx - (bbox_n1[2] - bbox_n1[0]) // 2, 538), nota1, font=font_nota, fill="#FFFFFF")
draw.text((cx - (bbox_n2[2] - bbox_n2[0]) // 2, 558), nota2, font=font_nota, fill="#FFFFFF")

for x in range(80, ancho - 80, 8):
    draw.line([(x, 595), (x + 4, 595)], fill="#FFFFFF", width=1)

pie = "¡Muchas gracias por su preferencia!"
bbox_pie = draw.textbbox((0, 0), pie, font=font_pie)
draw.text((cx - (bbox_pie[2] - bbox_pie[0]) // 2, 615), pie, font=font_pie, fill="#FFFFFF")

contacto = "DOMICILIO  ·  301 343 27 75"
bbox_cnt = draw.textbbox((0, 0), contacto, font=font_nota)
draw.text((cx - (bbox_cnt[2] - bbox_cnt[0]) // 2, 642), contacto, font=font_nota, fill="#FFD0D0")

# ==========================================
# 11. GUARDAR IMAGEN Y ACTUALIZAR CONSECUTIVO
# ==========================================
ticket.save("ticket.png", quality=95)

try:
    with open(archivo_contador, "w", encoding="utf-8") as f:
        f.write(str(consecutivo_num + 1))
except:
    pass

print(f"\n[OK] Ticket generado con exito como 'ticket.png'")
print(f"[OK] Consecutivo #{numero_comprobante} registrado. Proximo ticket sera #{consecutivo_num + 1:04d}.")

