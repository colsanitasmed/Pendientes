import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import re
import requests
from typing import List, Dict, Optional

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
    # Carga easyocr una sola vez
    return easyocr.Reader(["es"], gpu=False)

def normalize_lines(text: str) -> List[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln]

def find_block_start(lines: List[str]) -> int:
    # Buscar "Detalle de Pendiente" o encabezados similares
    for i, l in enumerate(lines):
        if re.search(r"detalle\s+de\s+pendiente", l, re.IGNORECASE):
            return i
    for i, l in enumerate(lines):
        if re.search(r"^cod\b|^cod\.|descripcion\b|unid\b|cant\b", l, re.IGNORECASE):
            return i
    return 0

def is_probable_code_line(line: str) -> bool:
    return bool(re.fullmatch(r"\d{4,8}", line.strip()))

def is_probable_unit(line: str) -> bool:
    token = line.strip().upper().replace(".", "")
    unidades = {"FCO","TAB","CAP","CAPS","AMP","ML","G","UND","UNID","FRASCO","FCOX"}
    return token in unidades or any(token.startswith(u) for u in unidades)

def extract_products_from_block(lines: List[str], start_idx: int) -> List[Dict]:
    """
    Extrae productos desde `lines[start_idx:]`.
    Devuelve lista de dicts: {codigo, descripcion, unidad, cantidad}
    """
    block = lines[start_idx:]
    productos_raw = []

    # 1) detectar posibles códigos (línea solo dígitos 4-8) o números 5-6 en línea
    for i, ln in enumerate(block):
        if is_probable_code_line(ln):
            productos_raw.append({"code_idx": i, "code": ln.strip()})
            continue
        m = re.search(r"\b(\d{5,6})\b", ln)
        if m:
            productos_raw.append({"code_idx": i, "code": m.group(1)})

    if not productos_raw:
        return []

    productos_raw = sorted(productos_raw, key=lambda x: x["code_idx"])

    # 2) buscar encabezado (para delimitar donde empiezan las descripciones)
    header_idx = 0
    for j, ln in enumerate(block):
        if re.search(r"^cod\b|descripcion\b|unid\b|cant\b", ln, re.IGNORECASE):
            header_idx = j + 1
            break

    # 3) construir productos
    productos = []
    for idx, p in enumerate(productos_raw):
        pos = p["code_idx"]
        code = p["code"]

        # Descripción = líneas entre prev_end y pos (excluyendo encabezados y números largos)
        prev_end = header_idx if idx == 0 else productos_raw[idx-1]["code_idx"] + 1
        desc_lines = []
        for k in range(prev_end, pos):
            if re.search(r"^cod\b|descripcion\b|unid\b|cant\b", block[k], re.IGNORECASE):
                continue
            # evitar tomar teléfonos grandes
            if re.fullmatch(r"\d{8,12}", block[k].strip()):
                continue
            desc_lines.append(block[k].strip())
        descripcion = " ".join(desc_lines).strip() if desc_lines else None

        # Unidad: buscar en siguientes 1..5 líneas la que parezca unidad
        unidad = None
        unidad_pos: Optional[int] = None
        for k in range(pos + 1, min(pos + 6, len(block))):
            if is_probable_unit(block[k]):
                unidad = block[k].strip()
                unidad_pos = k
                break

        # Cantidad: buscar número independiente (1-3 dígitos) después de la unidad.
        cantidad = None
        # primero buscar después de unidad (si existe)
        if unidad_pos is not None:
            for k in range(unidad_pos + 1, min(unidad_pos + 12, len(block))):
                linea = block[k].strip()
                # evitar teléfonos
                if re.fullmatch(r"\d{8,12}", linea):
                    continue
                # cantidad válida
                if re.fullmatch(r"\d{1,3}", linea):
                    cantidad = linea
                    break

        # si no encontramos cantidad, buscar en rango extendido tras el código
        if cantidad is None:
            for k in range(pos + 1, min(pos + 12, len(block))):
                linea = block[k].strip()
                if re.fullmatch(r"\d{1,3}", linea) and not re.fullmatch(r"\d{6,12}", linea):
                    cantidad = linea
                    break

        productos.append({
            "codigo": code,
            "descripcion": descripcion,
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
    st.info("Sube la imagen del ticket para procesar.")
    st.stop()

# Abrir imagen
try:
    image = Image.open(uploaded).convert("RGB")
except Exception as e:
    st.error(f"No se pudo abrir la imagen: {e}")
    st.stop()

st.image(image, caption="Imagen cargada", use_column_width=True)

# Ejecutar OCR
with st.spinner("Ejecutando OCR (easyocr)..."):
    reader = get_reader()
    img_np = np.array(image)
    ocr_lines = reader.readtext(img_np, detail=0, paragraph=False)

ocr_text = "\n".join(ocr_lines)
st.subheader("📝 Texto detectado por OCR")
st.code(ocr_text)

# Normalizar y extraer bloque de detalle
lines = normalize_lines(ocr_text)
start = find_block_start(lines)
products = extract_products_from_block(lines, start)

# Extraer número solicitud y pedido (desde todo el texto)
num_sol = None
pedido = None
m = re.search(r"n[uú]mero de solicitud\s*(\d{6,12})", ocr_text, re.IGNORECASE)
if m:
    num_sol = m.group(1)
m2 = re.search(r"pedido pendiente\s*(\d{6,12})", ocr_text, re.IGNORECASE)
if m2:
    pedido = m2.group(1)

# Mostrar resultados
st.subheader("📌 Datos extraídos")
st.write("Número solicitud:", num_sol or "— vacío —")
st.write("Pedido pendiente:", pedido or "— vacío —")
st.write(f"Productos detectados: {len(products)}")

for i, p in enumerate(products, start=1):
    st.markdown(f"**Producto {i}**")
    st.write("Código:", p.get("codigo") or "— vacío —")
    st.write("Descripción:", p.get("descripcion") or "— vacío —")
    st.write("Unidad:", p.get("unidad") or "— vacío —")
    st.write("Cantidad:", p.get("cantidad") or "— vacío —")
    st.write("---")

# -----------------------------------------
# Enviar al Google Form (una fila por producto)
# -----------------------------------------
if products:
    if st.button("📤 Enviar todos los productos al Google Sheet"):
        sent = 0
        errors = []
        for prod in products:
            payload = {
                ENTRY_SOLICITUD: num_sol or "",
                ENTRY_PEDIDO: pedido or "",
                ENTRY_CODIGO: prod.get("codigo") or "",
                ENTRY_DESCRIP: prod.get("descripcion") or "",
                ENTRY_UNIDAD: prod.get("unidad") or "",
                ENTRY_CANT: prod.get("cantidad") or ""
            }
            try:
                resp = requests.post(FORM_URL, data=payload, timeout=10)
            except Exception as e:
                errors.append(str(e))
                continue
            if resp.status_code == 200:
                sent += 1
            else:
                errors.append(f"HTTP {resp.status_code}")

        if errors:
            st.warning(f"Se enviaron {sent}/{len(products)}. Errores: {errors[:5]}")
            if len(errors) > 5:
                st.write("...más errores")
        else:
            st.success(f"Se enviaron {sent}/{len(products)} productos correctamente.")
else:
    st.info("No se detectaron productos. Revisa la imagen o prueba con otra foto.")
