import streamlit as st
import easyocr
import numpy as np
import requests
from PIL import Image
import re

# ---------------------------------------------
# CONFIGURACIÓN GOOGLE FORM
# ---------------------------------------------
# Usamos los nombres exactos que tu script de Google espera
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfMsMmOaUhwpD9HQCuKf0Y4Y6oesiUO9GphNb5WMz3ItKKPjg/formResponse"

ENTRY_SOLICITUD = "entry.611673084"      # "Número de solicitud "
ENTRY_PEDIDO = "entry.1680720626"         # "Número Pedido"
ENTRY_CODIGO = "entry.832344567"         # "  Código  "
ENTRY_DESCRIP = "entry.1533087800"       # "  Descripción  "
ENTRY_UNIDAD = "entry.728245219"         # "Unidad" (si existe en el form)
ENTRY_CANT = "entry.231047139"           # "  Cantidad  "
ENTRY_DOC = "entry.412830053"            # "Numero de documento del Usuario"

# ---------------------------------------------
# Cargar OCR
# ---------------------------------------------
@st.cache_resource
def load_reader():
    return easyocr.Reader(["es"], gpu=False)

# ---------------------------------------------
# Lógica de Extracción Espacial
# ---------------------------------------------
def process_ocr_results(results):
    """
    Agrupa los resultados de OCR en filas basadas en la coordenada Y.
    results: lista de [bbox, text, confidence]
    """
    if not results:
        return []

    # 1. Ordenar por coordenada Y (superior)
    results.sort(key=lambda x: x[0][0][1])

    rows = []
    if not results:
        return rows

    current_row = [results[0]]
    threshold = 15  # Píxeles de tolerancia para considerar la misma fila

    for i in range(1, len(results)):
        current_y = results[i][0][0][1]
        prev_y = current_row[-1][0][0][1]

        if abs(current_y - prev_y) < threshold:
            current_row.append(results[i])
        else:
            # Ordenar la fila actual por X antes de guardarla
            current_row.sort(key=lambda x: x[0][0][0])
            rows.append(current_row)
            current_row = [results[i]]
    
    current_row.sort(key=lambda x: x[0][0][0])
    rows.append(current_row)
    return rows

def extract_products_spatial(rows):
    productos = []
    
    for row in rows:
        row_text = " ".join([item[1] for item in row])
        
        # Buscar el código (5-6 dígitos)
        codigo_match = re.search(r"\b(\d{5,6})\b", row_text)
        if codigo_match:
            codigo = codigo_match.group(1)
            
            # Intentar identificar otros campos en la misma fila
            # La descripción suele estar a la izquierda o derecha del código
            # La cantidad suele ser un número pequeño (1-3 dígitos)
            
            items_text = [item[1] for item in row]
            
            # Buscamos la cantidad: usualmente al final de la fila o después de la unidad
            cantidad = ""
            for text in reversed(items_text):
                nums = re.findall(r"\b(\d{1,3})\b", text)
                if nums and text != codigo:
                    cantidad = nums[-1]
                    break
            
            # Buscamos la unidad
            unidad = ""
            for text in items_text:
                if re.search(r"(fco|tab|caps?|amp|ml|und|unid)", text, re.IGNORECASE):
                    unidad = text
                    break
            
            # La descripción es todo lo que no es código, cantidad o unidad
            desc_parts = []
            for text in items_text:
                if text != codigo and text != cantidad and text != unidad:
                    # Evitar ruidos comunes
                    if len(text) > 2:
                        desc_parts.append(text)
            
            descripcion = " ".join(desc_parts).strip()

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
st.set_page_config(page_title="OCR Pendientes v2", layout="centered")
st.title("📄 OCR de Tickets de Pendientes")
st.markdown("### Sistema de Captura Inteligente")

# Campo de documento
num_doc = st.text_input("Número de Documento del Usuario", placeholder="Ej: 12345678")

# Carga de imagen
uploaded = st.file_uploader("Sube la imagen del ticket", type=["png", "jpg", "jpeg"])

if not uploaded:
    st.info("Por favor sube una imagen para procesar.")
    st.stop()

image = Image.open(uploaded).convert("RGB")
st.image(image, caption="Imagen cargada", use_column_width=True)

# OCR
reader = load_reader()
with st.spinner("Analizando composición del ticket..."):
    img_np = np.array(image)
    # detail=1 nos da las coordenadas
    ocr_results = reader.readtext(img_np, detail=1)

# Procesamiento espacial
rows = process_ocr_results(ocr_results)
full_text = "\n".join([" ".join([item[1] for item in r]) for r in rows])

with st.expander("Ver texto detectado (Raw)"):
    st.code(full_text)

# Extracción de datos maestros (Solicitud y Pedido)
# Buscamos variaciones como "Solicitud:", "No. Solicitud", "Sol:", "Nro Solicitud", etc.
m1 = re.search(r"(?:solicitud|sol|nro\s*sol|num\s*sol)\s*[:\s#]*(\d{6,12})", full_text, re.IGNORECASE)
num_sol = m1.group(1) if m1 else ""

# Buscamos variaciones de "Pedido" o "Pendiente"
m2 = re.search(r"(?:pendiente|pedido|ped|nro\s*ped)\s*[:\s#]*(\d{6,12})", full_text, re.IGNORECASE)
num_ped = m2.group(1) if m2 else ""

# Extracción de productos
productos = extract_products_spatial(rows)

# ---------------------------------------------
# MOSTRAR RESULTADOS
# ---------------------------------------------
st.subheader("📌 Datos extraídos")
col_a, col_b, col_c = st.columns(3)
with col_a: st.write("**Solicitud:**", num_sol or "—")
with col_b: st.write("**Pedido:**", num_ped or "—")
with col_c: st.write("**Documento:**", num_doc or "—")

st.markdown(f"**Productos detectados:** {len(productos)}")

# Tabla editable o lista de productos
if productos:
    edited_products = []
    for i, p in enumerate(productos):
        with st.container():
            st.markdown(f"#### Producto {i+1}")
            c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
            with c1: cod = st.text_input(f"Código #{i+1}", p["codigo"], key=f"cod_{i}")
            with c2: des = st.text_input(f"Descripción #{i+1}", p["descripcion"], key=f"des_{i}")
            with c3: uni = st.text_input(f"Unidad #{i+1}", p["unidad"], key=f"uni_{i}")
            with c4: can = st.text_input(f"Cantidad #{i+1}", p["cantidad"], key=f"can_{i}")
            edited_products.append({"codigo": cod, "descripcion": des, "unidad": uni, "cantidad": can})
            st.divider()

# ---------------------------------------------
# VALIDACIÓN
# ---------------------------------------------
incompleto = not num_doc or not num_sol or not num_ped or not productos

if incompleto:
    st.warning("⚠️ Faltan datos críticos. Por favor revisa la imagen o completa los campos manualmente.")

# ---------------------------------------------
# ENVÍO
# ---------------------------------------------
if st.button("📤 Enviar a Google Sheets", type="primary", disabled=incompleto):
    enviados = 0
    errores = 0
    
    for p in edited_products:
        # IMPORTANTE: Los nombres de los entries deben estar mapeados a las columnas del sheet
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
            if resp.status_code == 200:
                enviados += 1
            else:
                errores += 1
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            errores += 1

    if enviados > 0:
        st.success(f"✅ {enviados} productos enviados correctamente.")
    if errores > 0:
        st.error(f"❌ {errores} productos no pudieron enviarse.")

st.info("💡 Tu script de Google enviará los correos automáticamente según la configuración de la hoja.")
