# streamlit_app.py (VERSIÓN RESTAURADA Y CORREGIDA)
import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import io
import re
import requests
from typing import List, Dict, Optional

# ----------------------------
# CONFIG: Google Form IDs
# ----------------------------
ENTRY_DOCUMENTO = "entry.412830053"   # <-- rellena si tienes el ID real
ENTRY_SOLICITUD  = "entry.611673084"
ENTRY_PEDIDO     = "entry.1680720626"
ENTRY_CODIGO     = "entry.832344567"
ENTRY_DESCRIP    = "entry.1533087800"
ENTRY_UNIDAD     = "entry.728245219"
ENTRY_CANT       = "entry.231047139"

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfMsMmOaUhwpD9HQCuKf0Y4Y6oesiUO9GphNb5WMz3ItKKPjg/formResponse"

# ----------------------------
# Inicializar OCR (EasyOCR)
# ----------------------------
@st.cache_resource
def get_reader():
    return easyocr.Reader(["es"], gpu=False)

reader = get_reader()

# ----------------------------
# Helpers: extracción y parseo
# ----------------------------
def ocr_image_bytes(image_bytes: bytes) -> str:
    """
    Recibe bytes de imagen y devuelve texto OCR (varias líneas).
    Usa EasyOCR y devuelve el texto concatenado por saltos.
    """
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_np = np.array(image)
    # detail=0 devuelve solo textos; paragraph=True junta en párrafos
    ocr_lines = reader.readtext(image_np, detail=0, paragraph=True)
    return "\n".join([ln.strip() for ln in ocr_lines if ln.strip()])

def parse_ticket_text(text: str) -> Dict[str, Optional[str]]:
    """
    Parseo robusto para tu formato:
    - busca Número de solicitud y Pedido pendiente (buscando palabras clave)
    - busca el bloque de detalle (aprovecha 'Cod.' si aparece)
    - detecta códigos (5-6 dígitos), descripción, unidad y cantidad
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    joined = " ".join(lines)

    # Buscar número de solicitud y pedido (flexible)
    num_solicitud = None
    pedido_pendiente = None

    m = re.search(r"n[uú]mero[\s:]*de[\s:]*solicitud[\s:]*[:\-]?\s*(\d{6,12})", joined, re.IGNORECASE)
    if m:
        num_solicitud = m.group(1)
    else:
        m2 = re.search(r"\b(\d{6,12})\b", joined)
        if m2:
            # fallback muy conservador: primer número grande
            num_solicitud = m2.group(1)

    p = re.search(r"pedido\s+pendiente[\s:]*[:\-]?\s*(\d{6,12})", joined, re.IGNORECASE)
    if p:
        pedido_pendiente = p.group(1)
    else:
        # intentar segundo número grande si existe
        all_big = re.findall(r"\b(\d{6,12})\b", joined)
        if len(all_big) >= 2 and num_solicitud and all_big[0] == num_solicitud:
            pedido_pendiente = all_big[1]

    # Buscar bloque de detalle: preferible "Cod." o "Cod" como encabezado
    block_start = None
    for i, ln in enumerate(lines):
        if re.search(r"^cod\.?$", ln, re.IGNORECASE) or re.search(r"detalle\s+de\s+pendiente", ln, re.IGNORECASE):
            block_start = i + 1
            break
    if block_start is None:
        # fallback: buscar la primera aparición de un código (5-6 dígitos) y tomar líneas a su alrededor
        for i, ln in enumerate(lines):
            if re.fullmatch(r"\d{5,6}", ln):
                block_start = max(0, i - 4)
                break

    # Si no encontramos block_start, considerar todo el documento
    block = lines[block_start:] if block_start is not None else lines

    # Detectar productos: buscar líneas con códigos (5-6 dígitos)
    productos = []
    indices_codigos = []
    for i, ln in enumerate(block):
        if re.fullmatch(r"\d{5,6}", ln):
            indices_codigos.append(i)

    # Si no detecta códigos en líneas separadas, buscar códigos dentro de las líneas
    if not indices_codigos:
        for i, ln in enumerate(block):
            m = re.search(r"\b(\d{5,6})\b", ln)
            if m:
                indices_codigos.append(i)

    for idx_pos, pos in enumerate(indices_codigos):
        codigo = None
        descripcion = None
        unidad = None
        cantidad = None

        # si la línea es un código exacto
        ln = block[pos]
        m = re.search(r"\b(\d{5,6})\b", ln)
        if m:
            codigo = m.group(1)

        # DESCRIPCION: líneas anteriores al código (hasta header o prev code)
        prev_cut = 0
        if idx_pos > 0:
            prev_cut = indices_codigos[idx_pos - 1] + 1
        else:
            # si hay header detectado en block_start, prev_cut = 0
            prev_cut = 0

        desc_lines = []
        for k in range(prev_cut, pos):
            if re.search(r"^(cod\.?|descripcion|unid|cant)\b", block[k], re.IGNORECASE):
                continue
            # evitar teléfonos largos antes del código
            if re.fullmatch(r"\d{8,12}", block[k]):
                continue
            desc_lines.append(block[k])
        descripcion = " ".join(desc_lines).strip() if desc_lines else None

        # UNIDAD: buscar en las próximas 1..6 líneas
        unidad_idx = None
        for k in range(pos + 1, min(pos + 7, len(block))):
            if re.fullmatch(r"(fco|fcox|tab|caps?|cap|amp|ml|mg|und|unid|frasco)\b", block[k], re.IGNORECASE):
                unidad = block[k].strip()
                unidad_idx = k
                break

        # CANTIDAD: lógica robusta — buscar NUMEROS pequeños en las líneas posteriores (tomar el último que aparezca en el área del producto)
        cantidad = None
        search_start = unidad_idx + 1 if unidad_idx is not None else pos + 1
        for k in range(search_start, min(search_start + 8, len(block))):
            nums = re.findall(r"\b(\d{1,3})\b", block[k])
            if nums:
                # tomamos el último número pequeño de la línea (puede haber varios)
                cantidad = nums[-1]

        productos.append({
            "codigo": codigo,
            "descripcion": descripcion,
            "unidad": unidad,
            "cantidad": cantidad
        })

    # Si no se detectó producto pero hay texto, intentar heurística simple: primer código grande en todo joined
    if not productos:
        m = re.search(r"\b(\d{5,6})\b", joined)
        if m:
            productos.append({
                "codigo": m.group(1),
                "descripcion": None,
                "unidad": None,
                "cantidad": None
            })

    # devolver primer producto (o lista completa si quieres ampliar)
    return {
        "numero_solicitud": num_solicitud,
        "pedido_pendiente": pedido_pendiente,
        "productos": productos,
        "raw_lines": lines
    }

# ----------------------------
# INTERFAZ STREAMLIT
# ----------------------------
st.set_page_config(page_title="OCR Pendientes", layout="centered")
st.title("📄 Cargue automático de Pendientes (OCR)")

# Nuevo campo: documento del usuario (tu petición)
documento_usuario = st.text_input("Número de Documento del Usuario")

# Subir imagen (mostramos la imagen — tal como pediste)
uploaded = st.file_uploader("Sube la imagen del ticket (png/jpg/jpeg)", type=["png", "jpg", "jpeg"])

if not uploaded:
    st.info("Sube una imagen para procesar.")
    st.stop()

# mostrar la imagen cargada (no la quité)
try:
    pil_img = Image.open(uploaded).convert("RGB")
    st.image(pil_img, caption="Imagen cargada", use_column_width=True)
except Exception as e:
    st.error(f"No se pudo abrir la imagen: {e}")
    st.stop()

# ejecutar OCR (EasyOCR) sobre la imagen en bytes
with st.spinner("Ejecutando OCR..."):
    img_bytes = uploaded.read()
    ocr_text = ocr_image_bytes = None
    try:
        ocr_text = ocr_image_bytes = (lambda b: ocr_image_bytes if False else (lambda x: reader.readtext(np.array(Image.open(io.BytesIO(x)).convert("RGB")), detail=0, paragraph=True))(b))(img_bytes)
        # The above line ensures we call reader.readtext with numpy array and paragraph=True
        # But to keep code clear, recreate text properly:
        image_np = np.array(pil_img)
        ocr_lines = reader.readtext(image_np, detail=0, paragraph=True)
        ocr_text = "\n".join([ln.strip() for ln in ocr_lines if ln.strip()])
    except Exception as e:
        st.error(f"Error al ejecutar OCR: {e}")
        st.stop()

st.subheader("📝 Texto detectado por OCR")
st.code(ocr_text)

# parsear
parsed = parse_ticket_text(ocr_text)

num_sol = parsed.get("numero_solicitud")
num_ped = parsed.get("pedido_pendiente")
productos = parsed.get("productos", [])

# mostrar resumen
st.subheader("📌 Datos extraídos")
st.write("Número solicitud:", num_sol or "— vacío —")
st.write("Pedido pendiente:", num_ped or "— vacío —")
st.write(f"Productos detectados: {len(productos)}")

for i, p in enumerate(products := productos, start=1):
    st.markdown(f"### Producto {i}")
    st.write("Código:", p.get("codigo") or "— vacío —")
    st.write("Descripción:", p.get("descripcion") or "— vacío —")
    st.write("Unidad:", p.get("unidad") or "— vacío —")
    st.write("Cantidad:", p.get("cantidad") or "— vacío —")
    st.write("---")

# Validación: listar campos que falten
missing = []
if not documento_usuario:
    missing.append("Documento del Usuario")
if not num_sol:
    missing.append("Número de Solicitud")
if not num_ped:
    missing.append("Pedido Pendiente")
# check first product fields
if productos:
    first = productos[0]
    if not first.get("codigo"):
        missing.append("Código")
    if not first.get("descripcion"):
        missing.append("Descripción")
    if not first.get("unidad"):
        missing.append("Unidad")
    if not first.get("cantidad"):
        missing.append("Cantidad")
else:
    missing.append("Producto (no detectado)")

if missing:
    st.error("❌ No se pudieron leer correctamente los siguientes campos: " + ", ".join(missing))
    st.info("Por favor cargue un ticket más legible o corrija manualmente los campos faltantes.")
else:
    # botón envío
    if st.button("📤 Enviar todos los productos al Google Sheet"):
        sent = 0
        errors = []
        for prod in productos:
            payload = {
                ENTRY_DOCUMENTO: documento_usuario,
                ENTRY_SOLICITUD: num_sol or "",
                ENTRY_PEDIDO: num_ped or "",
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
            # Google Forms típicamente devuelve 200 o 302; consideramos éxito si no hay excepción
            sent += 1

        if errors:
            st.warning(f"Se enviaron {sent}/{len(productos)}. Errores: {errors[:5]}")
        else:
            st.success(f"Se enviaron {sent}/{len(productos)} productos correctamente.")
