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
# Extraer productos (función original)
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
# Nueva función: revisar qué campos faltan
# ---------------------------------------------
def campos_faltantes(num_sol, num_ped, num_doc, productos):
    faltantes = []

    if not num_sol:
        faltantes.append("num_sol")
    if not num_ped:
        faltantes.append("num_ped")
    if not num_doc:
        faltantes.append("num_doc")

    # Revisar productos
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
# STREAMLIT UI (principal)
# ---------------------------------------------
st.set_page_config(page_title="OCR Pendientes", layout="centered")
st.title("📄 OCR de Tickets de Pendientes")

# Inicializar session_state para productos manuales
if "manual_products" not in st.session_state:
    st.session_state.manual_products = []

# Campo de documento (puede ingresarlo el usuario)
num_doc = st.text_input("Número de Documento del Usuario", value="")

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
    # readtext con detail=0 devuelve lista de strings
    lines = reader.readtext(img_np, detail=0, paragraph=False)

ocr_text = "\n".join(lines)

st.subheader("📝 Texto detectado (OCR)")
st.code(ocr_text)

# ---------------------------------------------
# Extracción automática y valores clave
# ---------------------------------------------
productos = extract_products(ocr_text)

m1 = re.search(r"solicitud\s*(\d{4,12})", ocr_text, re.IGNORECASE)
num_sol = m1.group(1) if m1 else ""

m2 = re.search(r"pendiente\s*(\d{4,12})", ocr_text, re.IGNORECASE)
num_ped = m2.group(1) if m2 else ""

# ---------------------------------------------
# Lógica para activar modo manual (Opción A)
# ---------------------------------------------
# Si no hay productos detectados pero hay otras líneas, permitir entrada manual también.
ocr_failed_basic = (len(lines) == 0) or (len(productos) == 0)

# Revisar campos faltantes exactos (incluso si hay algo detectado)
faltantes = campos_faltantes(num_sol, num_ped, num_doc, productos)

# Si hay faltantes o el OCR básico falló, habilitar edición/entrada manual (Opción A)
if faltantes:
    st.warning("⚠️ Algunos campos no fueron detectados. Completa lo que falta antes de enviar.")

    # Mostrar campos principales con lo que se detectó (si algo)
    num_sol = st.text_input("Número de Solicitud", value=num_sol)
    num_ped = st.text_input("Pedido Pendiente", value=num_ped)
    num_doc = st.text_input("Número de Documento del Usuario", value=num_doc)

    # Si no hay productos detectados inicialmente, permitir agregar manualmente múltiples
    if not productos:
        st.subheader("📝 Agregar productos manualmente")
        with st.form("manual_product_form", clear_on_submit=True):
            codigo_manual = st.text_input("Código del producto")
            descripcion_manual = st.text_input("Descripción del producto")
            unidad_manual = st.text_input("Unidad (ej: TAB, FCO, AMP, ML, UND)")
            cantidad_manual = st.text_input("Cantidad")
            add_clicked = st.form_submit_button("➕ Agregar producto")

        if add_clicked:
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

        # Mostrar lista manual si existe
        if st.session_state.manual_products:
            st.markdown("**Productos manuales agregados:**")
            for idx, p in enumerate(st.session_state.manual_products, start=1):
                st.write(f"{idx}. Código: {p['codigo']} | Desc: {p['descripcion']} | Unidad: {p['unidad']} | Cantidad: {p['cantidad']}")

        # Si hay productos manuales en sesión, úsalos
        if st.session_state.manual_products:
            productos = st.session_state.manual_products

    else:
        # Hay productos detectados: permitir editar solo los campos que falten (se muestran todos para comodidad)
        st.subheader("✏ Revisa y completa los productos detectados")
        nuevos_productos = []
        for i, p in enumerate(productos):
            st.markdown(f"### Producto {i+1}")

            # Si algún campo estaba vacío, el input quedará vacío; si tenía valor, se prellena
            codigo_val = p.get("codigo", "") or ""
            descripcion_val = p.get("descripcion", "") or ""
            unidad_val = p.get("unidad", "") or ""
            cantidad_val = p.get("cantidad", "") or ""

            codigo_in = st.text_input(f"Código Producto {i+1}", value=codigo_val, key=f"cod_{i}")
            descripcion_in = st.text_input(f"Descripción Producto {i+1}", value=descripcion_val, key=f"desc_{i}")
            unidad_in = st.text_input(f"Unidad Producto {i+1}", value=unidad_val, key=f"und_{i}")
            cantidad_in = st.text_input(f"Cantidad Producto {i+1}", value=cantidad_val, key=f"cant_{i}")

            nuevos_productos.append({
                "codigo": codigo_in.strip(),
                "descripcion": descripcion_in.strip(),
                "unidad": unidad_in.strip(),
                "cantidad": cantidad_in.strip()
            })

        # Permitir añadir productos adicionales manuales si hace falta
        st.markdown("**¿Falta algún producto? Añádelo abajo:**")
        with st.form("agregar_extra", clear_on_submit=True):
            extra_cod = st.text_input("Código (nuevo)")
            extra_desc = st.text_input("Descripción (nuevo)")
            extra_und = st.text_input("Unidad (nuevo)")
            extra_cant = st.text_input("Cantidad (nuevo)")
            add_extra = st.form_submit_button("➕ Agregar producto extra")
        if add_extra:
            if extra_cod.strip() and extra_desc.strip() and extra_und.strip() and extra_cant.strip():
                nuevos_productos.append({
                    "codigo": extra_cod.strip(),
                    "descripcion": extra_desc.strip(),
                    "unidad": extra_und.strip(),
                    "cantidad": extra_cant.strip()
                })
                st.success("Producto extra agregado.")
            else:
                st.error("Completa todos los campos del producto extra para agregar.")

        productos = nuevos_productos

# Si no hay faltantes y OCR produjo productos, mostramos lo detectado (modo normal)
if not campos_faltantes(num_sol, num_ped, num_doc, productos):
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
# Validación final: asegurar que no falte nada antes de enviar
# ---------------------------------------------
faltantes_final = campos_faltantes(num_sol, num_ped, num_doc, productos)
if faltantes_final:
    st.error("⚠ Aún faltan campos por completar. Revisa el formulario y completa los campos vacíos.")
    st.stop()

# ---------------------------------------------
# Envío al Google Form (una fila por producto)
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

    # limpiar productos manuales si los hubo y se enviaron
    if enviados > 0 and st.session_state.get("manual_products"):
        st.session_state.manual_products = []

    st.success(f"Se enviaron {enviados} productos correctamente. Errores: {errores}")
