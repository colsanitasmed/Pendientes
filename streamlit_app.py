import streamlit as st
import easyocr
import numpy as np
import requests
from PIL import Image
import re

# ---------------------------------------------
# CONFIGURACIÓN GOOGLE FORM
# ---------------------------------------------
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfMsMmOaUhwpD9HQCuKf0Y4Y6oesiUO9GphNb5WMz3ItKKPjg/formResponse"

ENTRY_SOLICITUD = "entry.611673084"
ENTRY_PEDIDO = "entry.1680720626"
ENTRY_CODIGO = "entry.832344567"
ENTRY_DESCRIP = "entry.1533087800"
ENTRY_UNIDAD = "entry.728245219"
ENTRY_CANT = "entry.231047139"
ENTRY_DOC = "entry.412830053"

# ---------------------------------------------
# Cargar OCR
# ---------------------------------------------
@st.cache_resource
def load_reader():
    return easyocr.Reader(["es"], gpu=False)

# ---------------------------------------------
# Extraer productos
# ---------------------------------------------
def extract_products(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    productos = []

    for i, line in enumerate(lines):
        if re.fullmatch(r"\d{5,6}", line):  # Códigos de producto
            codigo = line
            desc_lines = []

            k = i - 1
            while k >= 0 and not re.search(r"(cod|descrip|unid|cant)", lines[k], re.IGNORECASE):
                if not re.fullmatch(r"\d{8,12}", lines[k]):
                    desc_lines.append(lines[k])
                k -= 1

            desc_lines.reverse()
            descripcion = " ".join(desc_lines).strip()

            unidad = ""
            unidad_idx = None
            for j in range(i + 1, min(i + 6, len(lines))):
                if re.fullmatch(r"(fco|tab|caps?|amp|ml|und)", lines[j], re.IGNORECASE):
                    unidad = lines[j]
                    unidad_idx = j
                    break

            cantidad = ""
            if unidad_idx is not None:
                for j in range(unidad_idx + 1, min(unidad_idx + 8, len(lines))):
                    nums = re.findall(r"\b(\d{1,3})\b", lines[j])
                    if nums:
                        cantidad = nums[-1]

            if not cantidad:
                for j in range(i + 1, min(i + 4, len(lines))):
                    nums = re.findall(r"\b(\d{1,3})\b", lines[j])
                    if nums:
                        cantidad = nums[0]
                        break

            if not cantidad:
                for j in range(i + 1, min(i + 4, len(lines))):
                    m = re.search(r"(\d{1,3})\D", lines[j])
                    if m:
                        cantidad = m.group(1)
                        break

            productos.append({
                "codigo": codigo,
                "descripcion": descripcion,
                "unidad": unidad,
                "cantidad": cantidad
            })

    return productos

# ---------------------------------------------
# STREAMLIT UI
# ---------------------------------------------
st.set_page_config(page_title="OCR Pendientes", layout="centered")
st.title("📄 OCR de Tickets de Pendientes")

# Campo de documento
num_doc = st.text_input("Número de Documento del Usuario")

# Carga de imagen
uploaded = st.file_uploader("Sube la imagen del ticket", type=["png", "jpg", "jpeg"])

if not uploaded:
    st.info("Por favor sube una imagen para procesar.")
    st.stop()

image = Image.open(uploaded).convert("RGB")
st.image(image, caption="Imagen cargada", use_column_width=True)

# OCR
reader = load_reader()
with st.spinner("Ejecutando OCR..."):
    img_np = np.array(image)
    lines = reader.readtext(img_np, detail=0, paragraph=False)

ocr_text = "\n".join(lines)

st.subheader("📝 Texto detectado")
st.code(ocr_text)

# ---------------------------------------------
# Extracción automática
# ---------------------------------------------
productos = extract_products(ocr_text)

m1 = re.search(r"solicitud\s*(\d{6,12})", ocr_text, re.IGNORECASE)
num_sol = m1.group(1) if m1 else ""

m2 = re.search(r"pendiente\s*(\d{6,12})", ocr_text, re.IGNORECASE)
num_ped = m2.group(1) if m2 else ""

# ---------------------------------------------
# SI EL OCR NO DETECTÓ LOS CAMPOS → HABILITAR CAPTURA MANUAL
# ---------------------------------------------
st.subheader("✏️ Corrección manual si faltan datos detectados")

if not num_sol:
    num_sol = st.text_input("Número de solicitud (no detectado por OCR)", "")

if not num_ped:
    num_ped = st.text_input("Pedido pendiente (no detectado por OCR)", "")

# ---------------------------------------------
# MOSTRAR RESULTADOS
# ---------------------------------------------
st.subheader("📌 Datos extraídos")
st.write("Número solicitud:", num_sol or "— vacío —")
st.write("Pedido pendiente:", num_ped or "— vacío —")
st.write("Documento usuario:", num_doc or "— vacío —")
st.write(f"Productos detectados: {len(productos)}")

# ---------------------------------------------
# EDITOR MANUAL + ELIMINAR + AGREGAR
# ---------------------------------------------
st.subheader("✏️ Correcciones manuales de productos")

productos_editados = []

for idx, p in enumerate(productos):
    st.markdown(f"### Producto detectado {idx+1}")

    col1, col2 = st.columns([4,1])

    with col1:
        codigo = st.text_input(f"Código {idx+1}", p["codigo"])
        descripcion = st.text_input(f"Descripción {idx+1}", p["descripcion"])
        unidad = st.text_input(f"Unidad {idx+1}", p["unidad"])
        cantidad = st.text_input(f"Cantidad {idx+1}", p["cantidad"])

    with col2:
        eliminar = st.checkbox(f"❌ Quitar {idx+1}")

    if not eliminar:
        productos_editados.append({
            "codigo": codigo,
            "descripcion": descripcion,
            "unidad": unidad,
            "cantidad": cantidad
        })

st.write("---")

# Agregar producto manual
if st.button("➕ Agregar producto manualmente"):
    productos_editados.append({
        "codigo": "",
        "descripcion": "",
        "unidad": "",
        "cantidad": ""
    })

productos = productos_editados

# ---------------------------------------------
# VALIDACIÓN DE CAMPOS VACÍOS
# ---------------------------------------------
campos_invalidos = (
    not num_doc or
    not num_sol or
    not num_ped or
    not productos or
    any(not p["codigo"] or not p["descripcion"] or not p["unidad"] or not p["cantidad"] for p in productos)
)

if campos_invalidos:
    st.error("⚠️ Datos incompletos. Por favor corregir antes de enviar.")
    st.stop()

# ---------------------------------------------
# ENVÍO
# ---------------------------------------------
if st.button("📤 Enviar productos al Google Sheet"):

    enviados = 0
    for p in productos:
        payload = {
            ENTRY_SOLICITUD: num_sol,
            ENTRY_PEDIDO: num_ped,
            ENTRY_CODIGO: p["codigo"],
            ENTRY_DESCRIP: p["descripcion"],
            ENTRY_UNIDAD: p["unidad"],
            ENTRY_CANT: p["cantidad"],
            ENTRY_DOC: num_doc
        }

        try:
            requests.post(FORM_URL, data=payload, timeout=10)
            enviados += 1
        except:
            pass

    st.success(f"Se enviaron {enviados} productos correctamente.")
