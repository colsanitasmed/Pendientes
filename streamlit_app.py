import streamlit as st
import easyocr
import numpy as np
import requests
from PIL import Image
import re

# ---------------------------------------------
# CONFIGURACIÓN GOOGLE FORM (tus valores)
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
# Extraer productos (tu función original)
# ---------------------------------------------
def extract_products(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    productos = []

    for i, line in enumerate(lines):

        if re.fullmatch(r"\d{5,6}", line):
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

# Campo de documento (usuario lo ingresa)
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

st.subheader("📝 Texto detectado (OCR)")
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
# Si OCR falla o no detecta productos -> formulario manual
# ---------------------------------------------
# Inicializar session_state para productos manuales (lista)
if "manual_products" not in st.session_state:
    st.session_state.manual_products = []

# Determinar si consideramos que OCR falló
ocr_failed = (len(lines) == 0) or (len(productos) == 0)

if ocr_failed:
    st.warning("⚠️ No fue posible extraer productos automáticamente. Por favor ingrésalos manualmente.")

    # Permitir al usuario editar/confirmar num_sol, num_ped, num_doc
    num_sol = st.text_input("Número de Solicitud (manual)", value=num_sol)
    num_ped = st.text_input("Pedido Pendiente (manual)", value=num_ped)
    num_doc = st.text_input("Número de Documento del Usuario (manual)", value=num_doc)

    st.subheader("📝 Agregar productos manualmente")
    with st.form("manual_product_form", clear_on_submit=True):
        codigo_manual = st.text_input("Código del producto")
        descripcion_manual = st.text_input("Descripción del producto")
        unidad_manual = st.text_input("Unidad (ej: TAB, FCO, AMP, ML, UND)")
        cantidad_manual = st.text_input("Cantidad")

        add_clicked = st.form_submit_button("➕ Agregar producto")

    if add_clicked:
        # validar campos mínimos
        if codigo_manual.strip() and descripcion_manual.strip() and unidad_manual.strip() and cantidad_manual.strip():
            st.session_state.manual_products.append({
                "codigo": codigo_manual.strip(),
                "descripcion": descripcion_manual.strip(),
                "unidad": unidad_manual.strip(),
                "cantidad": cantidad_manual.strip()
            })
            st.success("Producto agregado a la lista manual.")
        else:
            st.error("Por favor completa todos los campos del producto antes de agregar.")

    # Mostrar lista manual
    if st.session_state.manual_products:
        st.markdown("**Productos manuales agregados:**")
        for idx, p in enumerate(st.session_state.manual_products, start=1):
            st.write(f"{idx}. Código: {p['codigo']} | Desc: {p['descripcion']} | Unidad: {p['unidad']} | Cantidad: {p['cantidad']}")

    # Si ya hay productos manuales, reemplazamos `productos` por ellos para envío
    if st.session_state.manual_products:
        productos = st.session_state.manual_products
else:
    # OCR tuvo éxito en detectar productos: mostrar resultados detectados
    st.subheader("📌 Datos extraídos automáticamente")
    st.write("Número solicitud:", num_sol or "— vacío —")
    st.write("Pedido pendiente:", num_ped or "— vacío —")
    st.write("Documento usuario:", num_doc or "— vacío —")
    st.write(f"Productos detectados: {len(productos)}")

    for i, p in enumerate(productos, start=1):
        st.markdown(f"### Producto {i}")
        st.write("Código:", p["codigo"] or "— vacío —")
        st.write("Descripción:", p["descripcion"] or "— vacío —")
        st.write("Unidad:", p["unidad"] or "— vacío —")
        st.write("Cantidad:", p["cantidad"] or "— vacío —")
        st.write("---")

# ---------------------------------------------
# VALIDACIÓN DE CAMPOS VACÍOS (antes de enviar)
# ---------------------------------------------
campos_invalidos = (
    not num_doc or
    not num_sol or
    not num_ped or
    not productos or
    any(not p["codigo"] or not p["descripcion"] or not p["unidad"] or not p["cantidad"] for p in productos)
)

if campos_invalidos:
    st.error("⚠️ Faltan datos obligatorios para enviar. Si usaste la entrada manual, asegúrate de agregar al menos un producto completo.")
else:
    # ---------------------------------------------
    # ENVÍO AL GOOGLE FORM (una fila por producto)
    # ---------------------------------------------
    if st.button("📤 Enviar productos al Google Sheet"):
        enviados = 0
        errores = 0
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
                resp = requests.post(FORM_URL, data=payload, timeout=10)
                # Google Forms típicamente devuelve 200 o 0 (redirección). Solo asumimos éxito si no lanza excepción.
                enviados += 1
            except Exception as e:
                errores += 1
                st.write(f"Error enviando producto {p.get('codigo','')}: {e}")

        # limpiar productos manuales si los hubo y se enviaron
        if enviados > 0 and st.session_state.get("manual_products"):
            st.session_state.manual_products = []

        st.success(f"Se enviaron {enviados} productos correctamente. Errores: {errores}")
