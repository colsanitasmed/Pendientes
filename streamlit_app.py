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
# Cargar OCR (EasyOCR)
# ---------------------------------------------
@st.cache_resource
def load_reader():
    return easyocr.Reader(["es"], gpu=False)

# ---------------------------------------------
# EXTRACTOR DE PRODUCTOS MEJORADO (MULTILÍNEA)
# ---------------------------------------------
def extract_products(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    productos = []

    patron_codigo = r"^\d{5,7}$"

    for i, line in enumerate(lines):

        if re.fullmatch(patron_codigo, line):
            codigo = line

            # -------------------------------
            # 1) Descripción MULTILÍNEA
            # -------------------------------
            descripcion_partes = []
            k = i - 1

            while k >= 0:
                linea = lines[k]

                if re.fullmatch(patron_codigo, linea):
                    break
                if re.search(r"(unidad|cant|detalle|pendiente|solicitud|pedido)", linea, re.I):
                    break
                if re.fullmatch(r"\d{8,12}", linea):  # cédula, teléfono
                    break

                descripcion_partes.append(linea)
                k -= 1

            descripcion_partes.reverse()
            descripcion = " ".join(descripcion_partes).strip()

            # -------------------------------
            # 2) Unidad
            # -------------------------------
            unidad = ""
            unidad_idx = None

            for j in range(i + 1, min(i + 10, len(lines))):
                if re.fullmatch(r"(fco|tab|caps?|amp|ml|und)", lines[j], re.I):
                    unidad = lines[j].upper()
                    unidad_idx = j
                    break

            # -------------------------------
            # 3) Cantidad
            # -------------------------------
            cantidad = ""

            if unidad_idx is not None:
                for j in range(unidad_idx + 1, min(unidad_idx + 6, len(lines))):
                    nums = re.findall(r"\b(\d{1,3})\b", lines[j])
                    if nums:
                        cantidad = nums[-1]
                        break

            if not cantidad:
                for j in range(i + 1, min(i + 6, len(lines))):
                    nums = re.findall(r"\b(\d{1,3})\b", lines[j])
                    if nums:
                        cantidad = nums[0]
                        break

            productos.append({
                "codigo": codigo,
                "descripcion": descripcion,
                "unidad": unidad,
                "cantidad": cantidad
            })

    return productos

# ---------------------------------------------
# Revisar qué campos faltan
# ---------------------------------------------
def campos_faltantes(num_sol, num_ped, num_doc, productos):
    faltantes = []

    if not num_sol:
        faltantes.append("num_sol")
    if not num_ped:
        faltantes.append("num_ped")
    if not num_doc:
        faltantes.append("num_doc")

    for i, p in enumerate(productos):
        if not p.get("codigo"):
            faltantes.append(f"codigo_{i}")
        if not p.get("descripcion"):
            faltantes.append(f"descripcion_{i}")
        if not p.get("unidad"):
            faltantes.append(f"unidad_{i}")
        if not p.get("cantidad"):
            faltantes.append(f"cantidad_{i}")

    return faltantes

# ---------------------------------------------
# STREAMLIT UI
# ---------------------------------------------
st.set_page_config(page_title="OCR Pendientes", layout="centered")
st.title("📄 OCR de Tickets de Pendientes")

# Inicializar session_state
if "manual_products" not in st.session_state:
    st.session_state.manual_products = []

if "productos_detectados" not in st.session_state:
    st.session_state.productos_detectados = []

# Número de documento
num_doc = st.text_input("Número de Documento del Usuario", value="")

# Cargar imagen
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

# ---------------------------------------------
# Extraer productos
# ---------------------------------------------
productos = extract_products(ocr_text)
st.session_state.productos_detectados = productos.copy()

# Extraer solicitud/pedido
m1 = re.search(r"solicitud\s*(\d{4,12})", ocr_text, re.IGNORECASE)
num_sol = m1.group(1) if m1 else ""

m2 = re.search(r"pendiente\s*(\d{4,12})", ocr_text, re.IGNORECASE)
num_ped = m2.group(1) if m2 else ""

# ---------------------------------------------
# Validar faltantes
# ---------------------------------------------
faltantes = campos_faltantes(num_sol, num_ped, num_doc, productos)

if faltantes:
    st.warning("⚠️ Algunos campos no fueron detectados. Completa lo que falta antes de enviar.")

    num_sol = st.text_input("Número de Solicitud", value=num_sol)
    num_ped = st.text_input("Pedido Pendiente", value=num_ped)
    num_doc = st.text_input("Número de Documento del Usuario", value=num_doc)

    st.subheader("✏ Editar productos detectados o eliminarlos")

    nuevos_productos = []
    for i, p in enumerate(productos):
        col1, col2 = st.columns([4,1])
        with col1:
            st.markdown(f"### Producto {i+1}")

            codigo_in = st.text_input(f"Código Producto {i+1}", value=p.get("codigo",""), key=f"cod_{i}")
            descripcion_in = st.text_input(f"Descripción Producto {i+1}", value=p.get("descripcion",""), key=f"desc_{i}")
            unidad_in = st.text_input(f"Unidad Producto {i+1}", value=p.get("unidad",""), key=f"und_{i}")
            cantidad_in = st.text_input(f"Cantidad Producto {i+1}", value=p.get("cantidad",""), key=f"cant_{i}")

        with col2:
            borrar = st.button("🗑️ Quitar", key=f"del_{i}")
            if borrar:
                continue  # NO agregar este producto, se elimina

        nuevos_productos.append({
            "codigo": codigo_in.strip(),
            "descripcion": descripcion_in.strip(),
            "unidad": unidad_in.strip(),
            "cantidad": cantidad_in.strip()
        })

    productos = nuevos_productos

    st.markdown("**Agregar producto manualmente:**")
    with st.form("agregar_extra", clear_on_submit=True):
        extra_cod = st.text_input("Código")
        extra_desc = st.text_input("Descripción")
        extra_und = st.text_input("Unidad")
        extra_cant = st.text_input("Cantidad")
        add_extra = st.form_submit_button("➕ Agregar Producto")

    if add_extra:
        if extra_cod and extra_desc and extra_und and extra_cant:
            productos.append({
                "codigo": extra_cod,
                "descripcion": extra_desc,
                "unidad": extra_und,
                "cantidad": extra_cant
            })
            st.success("Producto agregado.")
        else:
            st.error("Todos los campos del producto son obligatorios.")

# ---------------------------------------------
# Mostrar datos si NO faltan
# ---------------------------------------------
if not campos_faltantes(num_sol, num_ped, num_doc, productos):
    st.subheader("📌 Datos detectados automáticamente")
    st.write("Número solicitud:", num_sol)
    st.write("Pedido pendiente:", num_ped)
    st.write("Documento usuario:", num_doc)

    for i, p in enumerate(productos, start=1):
        st.markdown(f"### Producto {i}")
        st.write("Código:", p["codigo"])
        st.write("Descripción:", p["descripcion"])
        st.write("Unidad:", p["unidad"])
        st.write("Cantidad:", p["cantidad"])

# ---------------------------------------------
# Validación FINAL
# ---------------------------------------------
faltantes_final = campos_faltantes(num_sol, num_ped, num_doc, productos)
if faltantes_final:
    st.error("⚠ Aún faltan campos por completar. Revisa el formulario.")
    st.stop()

# ---------------------------------------------
# Enviar a Google Form
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
            requests.post(FORM_URL, data=payload, timeout=10)
            enviados += 1
        except Exception as e:
            errores += 1
            st.write(f"Error enviando producto {p.get('codigo','')}: {e}")

    st.success(f"Se enviaron {enviados} productos correctamente. Errores: {errores}")
