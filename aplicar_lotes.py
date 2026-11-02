import json
import os

ruta = os.path.join(os.path.dirname(__file__), "datos", "inventario.json")
if not os.path.exists(ruta):
    print("No se encontro datos/inventario.json")
    exit(1)

with open(ruta, "r", encoding="utf-8") as f:
    inv = json.load(f)

for p in inv:
    if p.get("id") == "tamarindo-20":
        p["lotes"] = [
            {"cantidad": 52, "costo": 1733, "fecha": "Lote Anterior"},
            {"cantidad": 150, "costo": 1666, "fecha": "30/10/2026"}
        ]
        p["stock"] = 202
    elif p.get("id") == "soda-19":
        p["lotes"] = [
            {"cantidad": 38, "costo": 1933, "fecha": "Lote Anterior"},
            {"cantidad": 180, "costo": 1866, "fecha": "02/11/2026"}
        ]
        p["stock"] = 218
    elif "stock" in p and p.get("stock") is not None and not p.get("descuenta_de_id"):
        if "lotes" not in p or not p["lotes"]:
            p["lotes"] = [{"cantidad": p["stock"], "costo": p.get("precio_costo", 0), "fecha": "Inicial"}]

with open(ruta, "w", encoding="utf-8") as f:
    json.dump(inv, f, ensure_ascii=False, indent=2)

print("LOTES ACTIVADOS CON EXITO!")
