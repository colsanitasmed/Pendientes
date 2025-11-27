import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import re
import requests
from typing import List, Dict

# -----------------------------------------
# CONFIG: Google Form URL / entry IDs
# -----------------------------------------
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfMsMmOaUhwpD9HQCuKf0Y4Y6oesiUO9GphNb5WMz3ItKKPjg/formResponse"

ENTRY_SOLICITUD = "entry.611673084"
ENTRY_PEDIDO = "entry.1680720626"
ENTRY_CODIGO = "entry.832344567"
ENTRY_DESCRIP = "entry.1533087800"
ENTRY_UNIDAD = "entry.728245219"
ENTRY_CANT = "entry.231047139"

# -----------------------------------------
# Helpers
# -----------------------------------------
@st.cache_resource
def get_reader():
    return easyocr.Reader(["es"], gpu=False)

def normalize_lines(text: str) -> List[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln]

def find_block_start(lines: List[str]) -> int:
    for i, l in enumerate(lines):
        if re.search(r"detalle\s+de\s+pendiente", l, re.IGNORECASE):
            return i
    for i, l in enumerate(lines):
        if re.search(r"^cod\b|descripcion\b", l, re.IGNORECASE):
            return i
    return 0

def is_probable_code_line(line: str) -> bool:
    return bool(re.fullmatch(r"\d{4,8}", line.strip()))

def is_probable_unit(line: str) -> bool:
    u = line.strip().upper().replace(".", "")
    unidades = {"FCO","TAB","CAP","CAPS","AMP","ML","G","UND","UNID","FCOX"}
    return u in unidades

def extract_products_from_block(lines: List[str], start_idx: int) -> List[Dict]]:
    block = lines[start_idx:]
    productos_raw = []

    # 1. Detectar códigos
    for i, ln in enumerate(block):
        if is_probable_code_line(ln):
            productos_raw.append({"code_idx": i, "code": ln})
            continue

        m = re.search(r"\b(\d{5,6})\b", ln)
        if m:
            productos_raw.append({"code_idx": i, "code": m.group(1)})

    if not productos_raw:
        return []

    productos_raw = sorted(productos_raw, key=lambda x: x["code_idx"])

    # 2. Extraer productos completos
    productos = []
    for idx, p in enumerate(productos_raw):
        pos = p["code_idx"]
        code = p["code"]

        # DESCRIPCIÓN = líneas antes del código
        desc_lines = []
        inicio_desc = productos_raw[idx-1]["code_idx"]+1 if idx>0 else 0
        for k in range(inicio_desc, pos):
            if re.search(r"^cod\b|descripcion\b|unid\b|cant\b", block[k], re.IGNORECASE):
                continue
            desc_lines.append(block[k])
        descripcion = " ".join(desc_lines).strip()

        # UNIDAD = siguiente línea que sea unidad
        unidad = None
        for k in range(pos+1, min(pos+5, len(block))):
            if is_probable_unit(block[k]):
                unidad = block[k].strip()
                break

        # CANTIDAD = número pequeño, normalmente cerca del final
        cantidad = None
        for k in range(pos+1, len(block)):
            if re.fullmatch(r"\d{1,3}", block[k].strip()):
                cantidad = block[k].strip()
                break

        productos.append({
            "codigo": code,
            "descripcion": descripcion or None,
            "unidad": unidad,
            "cantidad": cantidad
        })

    return productos

# -----------------------------------------
# Streamlit UI
# -----------------------------------------
st.set_page_config(page_title="OCR Pendientes", layout="centered")
st.title("📄 Cargue automático de Pendientes (OCR)")

uploaded = st.file_uploader("Sube la imagen (png/jpg/jpeg)", type=["png", "jpg", "jpeg"])
if not uploaded:
    st.stop()

image = Image.open(uploaded).convert("RGB")
st.image(image, caption="Imagen cargada", use_column_width=True)

with st.spinner("Ejecutando OCR..."):
    reader = get_reader()
    img_np = np.array(image)
    ocr_lines = reader.readtext(img_np, detail=0, paragraph=False)

ocr_text = "\n".join(ocr_lines)
lines = normalize_lines(ocr_text)
start = find_block_start(lines)
productos = extract_products_from_block(lines, start)

# Extraer solicitud/pedido en todo el texto
num_sol = None
pedido = None

m = re.search(r"n[uú]mero de solicitud\s*(\d{6,12})", ocr_text, re.IGNORECASE)
if m:
    num_sol = m.group(1)

m2 = re.search(r"pedido pendiente\s*(\d{6,12})", ocr_text, re.IGNORECASE)
if m2:
    pedido = m2.group(1)

# Mostrar resultados
st.subheader("📝 Texto detectado")
st.code(ocr_text)

st.subheader("📌 Datos extraídos")
st.write("Número solicitud:", num_sol or "— vacío —")
st.write("Pedido pendiente:", pedido or "— vacío —")
st.write(f"Productos detectados: {len(productos)}")

for i, p in enumerate(productos, 1):
    st.markdown(f"### Producto {i}")
    st.write("Código:", p["codigo"])
    st.write("Descripción:", p["descripcion"])
    st.write("Unidad:", p["unidad"])
    st.write("Cantidad:", p["cantidad"])
    st.write("---")

# -----------------------------------------
# Enviar al Google Form
# -----------------------------------------
if st.button("📤 Enviar todos al Google Form"):
    sent = 0
    errors = []

    for prod in productos:
        payload = {
            ENTRY_SOLICITUD: num_sol or "",
            ENTRY_PEDIDO: pedido or "",
            ENTRY_CODIGO: prod["codigo"] or "",
            ENTRY_DESCRIP: prod["descripcion"] or "",
            ENTRY_UNIDAD: prod["unidad"] or "",
            ENTRY_CANT: prod["cantidad"] or ""
        }

        try:
            resp = requests.post(FORM_URL, data=payload)
            if resp.status_code == 200:
                sent += 1
            else:
                errors.append(str(resp.status_code))
        except Exception as e:
            errors.append(str(e))

    if errors:
        st.warning(f"Se enviaron {sent}/{len(productos)}. Errores: {errors}")
    else:
        st.success(f"{sent} productos enviados correctamente.")
