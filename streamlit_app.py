import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import re
import requests
from typing import List, Dict

# -------------------------
# CONFIG: Google Form URL / entry IDs
# -------------------------
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfMsMmOaUhwpD9HQCuKf0Y4Y6oesiUO9GphNb5WMz3ItKKPjg/formResponse"

ENTRY_SOLICITUD = "entry.611673084"
ENTRY_PEDIDO = "entry.1680720626"
ENTRY_CODIGO = "entry.832344567"
ENTRY_DESCRIP = "entry.1533087800"
ENTRY_UNIDAD = "entry.728245219"
ENTRY_CANT = "entry.231047139"

# -------------------------
# Helpers / extractor
# -------------------------
@st.cache_resource
def get_reader():
    # carga una vez el lector (puede tardar un poco la primera vez)
    return easyocr.Reader(["es"], gpu=False)

def normalize_lines(text: str) -> List[str]:
    """Divide texto en líneas limpias y normaliza espacios"""
    lines = [ln.strip() for ln in text.splitlines()]
    # quitar líneas vacías
    lines = [ln for ln in lines if ln]
    return lines

def find_block_start(lines: List[str]) -> int:
    """Buscar índice donde comienza 'Detalle de Pendiente' o 'Cod' o 'Descripcion'"""
    for i, l in enumerate(lines):
        if re.search(r"detalle\s+de\s+pendiente", l, re.IGNORECASE):
            return i
    # fallback: buscar "Cod" o "Descripcion" directo
    for i, l in enumerate(lines):
        if re.search(r"^cod\b|^cod\.|descripcion\b", l, re.IGNORECASE):
            return i
    # si no encontramos, devolver 0 (usar todo)
    return 0

def is_probable_code_line(line: str) -> bool:
    """Detecta si una línea es probablemente un código de producto (solo dígitos 4-8)"""
    return bool(re.fullmatch(r"\d{4,8}", line.strip()))

def is_probable_unit(line: str) -> bool:
    """Detecta si una línea parece unidad (Fco, FCO, Tab, Amp, ML, UND, etc.)"""
    tokens = re.split(r"\s+", line.strip())
    if not tokens:
        return False
    u = tokens[0].upper().replace(".", "")
    return u in {"FCO", "FCOX", "FCOX", "TAB", "CAP", "CAPS", "AMP", "ML", "G", "UND", "UNID", "FCOX", "FCOX30ML"}

def extract_products_from_block(lines: List[str], start_idx: int) -> List[Dict]:
    """
    Extrae una lista de productos desde las líneas (asumiendo la parte de detalle).
    Lógica:
    - Buscar índices con líneas que sean solo código (4-8 dígitos).
    - Para cada índice de código, tomar:
        descripcion = líneas anteriores más cercanas (hasta el encabezado o hasta prev codigo)
        unidad = línea siguiente (si parece unidad)
        cantidad = siguiente línea que sea un número pequeño
    - Si OCR mezcló (código dentro línea), también detecta número dentro de línea.
    """
    block = lines[start_idx:]
    productos = []

    # construir lista de (index, value) en block
    for i, ln in enumerate(block):
        # detectar código en su propia línea
        if is_probable_code_line(ln):
            productos.append({"code_idx": i, "code": ln.strip()})
            continue
        # detectar código dentro de la línea (ej "... 391092 ...")
        m = re.search(r"\b(\d{5,6})\b", ln)
        if m:
            # si ya hay un producto con code_idx justo antes muy cercano, skip (evitar duplicados)
            productos.append({"code_idx": i, "code": m.group(1)})
            continue

    # si no halló códigos, intentar encontrar con patrón diferente: buscar números 5-6 dígitos en todo block
    if not productos:
        for i, ln in enumerate(block):
            m = re.search(r"\b(\d{5,6})\b", ln)
            if m:
                productos.append({"code_idx": i, "code": m.group(1)})

    # ordenar por posición en el bloque
    productos = sorted(productos, key=lambda x: x["code_idx"])

    # construir productos finales
    results = []
    # para delimitar descripción, buscamos "header_idx" dentro block: índice de "Cod" o "Descripcion" si existe
    header_idx = 0
    for j, ln in enumerate(block):
        if re.search(r"^cod\b|descripcion\b|unid\b|cant\b", ln, re.IGNORECASE):
            header_idx = j + 1
            break

    for p_idx, p in enumerate(productos):
        idx = p["code_idx"]
        code = p["code"]

        # descripción: desde header_idx (o prev_code_idx+1) hasta el índice donde se encontró el código (excluyendo esa línea)
        # si hay producto previo, iniciar después del prev
        prev_end = header_idx
        if p_idx > 0:
            prev_end = productos[p_idx - 1]["code_idx"] + 1

        # descripción_text: todas las líneas entre prev_end y idx (excluyendo la línea del código)
        descripcion_lines = []
        for k in range(prev_end, idx):
            # excluir líneas que parezcan encabezado ruídoso
            if re.search(r"^cod\b|descripcion\b|unid\b|cant\b", block[k], re.IGNORECASE):
                continue
            # excluir líneas que sean solo números largos (teléfonos) si están antes del código
            if re.fullmatch(r"\d{8,12}", block[k].strip()):
                continue
            descripcion_lines.append(block[k].strip())

        descripcion = " ".join(descripcion_lines).strip() if descripcion_lines else None

        # Unidad: buscar en las siguientes 1-3 líneas la que parezca unidad
        unidad = None
        for k in range(idx + 1, min(idx + 4, len(block))):
            if is_probable_unit(block[k]):
                unidad = block[k].strip()
                break
        # Cantidad: buscar en siguientes 1-4 líneas primer número pequeño (1-3 dígitos)
        cantidad = None
        for k in range(idx + 1, min(idx + 6, len(block))):
            if re.fullmatch(r"\d{1,3}", block[k].strip()):
                # evitar tomar número que coincida con número de solicitud o pedido (se filtra más abajo)
                cantidad = block[k].strip()
                break

        results.append({
            "codigo": code,
            "descripcion": descripcion,
            "unidad": unidad,
            "cantidad": cantidad
        })

    return results

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="OCR Pendientes", layout="centered")
st.title("📄 Cargue automático de Pendientes (OCR)")

st.markdown("Carga una foto del ticket; el sistema intentará detectar todos los productos y enviarlos al Google Sheet vía Form.")

uploaded = st.file_uploader("Sube la imagen (png/jpg/jpeg)", type=["png", "jpg", "jpeg"])
if not uploaded:
    st.info("Sube la imagen del ticket para procesar.")
    st.stop()

try:
    image = Image.open(uploaded).convert("RGB")
except Exception as e:
    st.error(f"No se pudo abrir la imagen: {e}")
    st.stop()

st.image(image, caption="Imagen cargada", use_column_width=True)

with st.spinner("Ejecutando OCR (EasyOCR)..."):
    reader = get_reader()
    img_np = np.array(image)
    ocr_lines = reader.readtext(img_np, detail=0, paragraph=False)

# unir resultados conservando saltos para analizar
ocr_text = "\n".join(ocr_lines)
st.subheader("📝 Texto detectado por OCR")
st.code(ocr_text)

# normalizar y buscar bloque
lines = normalize_lines(ocr_text)
start = find_block_start(lines)
products = extract_products_from_block(lines, start)

# extraer número solicitud y pedido (buscando en todo texto)
num_sol = None
pedido = None
m = re.search(r"n[uú]mero de solicitud\s*(\d{6,12})", ocr_text, re.IGNORECASE)
if m:
    num_sol = m.group(1)
m2 = re.search(r"pedido pendiente\s*(\d{6,12})", ocr_text, re.IGNORECASE)
if m2:
    pedido = m2.group(1)

st.subheader("📌 Datos extraídos (resumen)")
st.write("Número solicitud:", num_sol or "— vacío —")
st.write("Pedido pendiente:", pedido or "— vacío —")
st.write(f"Productos detectados: {len(products)}")

for i, prod in enumerate(products, start=1):
    st.markdown(f"**Producto {i}**")
    st.write("Código:", prod.get("codigo") or "— vacío —")
    st.write("Descripción:", prod.get("descripcion") or "— vacío —")
    st.write("Unidad:", prod.get("unidad") or "— vacío —")
    st.write("Cantidad:", prod.get("cantidad") or "— vacío —")
    st.write("---")

# botón para enviar (por producto) al Google Form
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
