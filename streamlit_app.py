import streamlit as st
import pytesseract
from PIL import Image
import re
import requests

# =============================
#  CONFIGURACIÓN GOOGLE FORM
# =============================
ENTRY_SOLICITUD = "entry.611673084"
ENTRY_PEDIDO = "entry.1680720626"
ENTRY_CODIGO = "entry.832344567"
ENTRY_DESCRIP = "entry.1533087800"
ENTRY_UNIDAD = "entry.728245219"
ENTRY_CANT = "entry.231047139"

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdXXXXXXX/formResponse"  # ← REEMPLAZA TU URL REAL


# =============================
#  FUNCIONES DE EXTRACCIÓN
# =============================

def extract_numbers(text):
    """Extrae el primer número de 6+ dígitos."""
    match = re.search(r"\b\d{6,}\b", text)
    return match.group(0) if match else ""


def extract_numero_solicitud(text):
    m = re.search(r"(?i)número de solicitud\s*\n?(\d+)", text)
    return m.group(1) if m else ""


def extract_pedido_pendiente(text):
    m = re.search(r"(?i)pedido pendiente\s*\n?(\d+)", text)
    return m.group(1) if m else ""


def extract_products(text):
    """
    Busca el patrón del producto:
    Código (6 dígitos)
    Descripción
    Unidad (Fco, Tab, Caps, etc.)
    Cantidad (último número suelto en el bloque)
    """

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    productos = []

    # 1. buscar códigos de 6 dígitos
    for i, line in enumerate(lines):
        if re.fullmatch(r"\d{6}", line):  # línea con código exacto
            codigo = line

            # 2. descripción en las líneas superiores inmediatas
            desc_lines = []
            k = i - 1
            while k >= 0 and not re.fullmatch(r"Cod\.?|Unid\.?|Cant\.?|Descripción|Descripcion", lines[k], re.IGNORECASE):
                if not re.fullmatch(r"\d{6}", lines[k]):
                    desc_lines.append(lines[k])
                k -= 1
            desc_lines.reverse()
            descripcion = " ".join(desc_lines).strip()

            # 3. Unidad: debe estar en líneas cercanas debajo del código
            unidad = ""
            for j in range(i + 1, min(i + 4, len(lines))):
                if re.fullmatch(r"(Fco|Tab|Caps?|Unidad|Ampolla)", lines[j], re.IGNORECASE):
                    unidad = lines[j]
                    break

            # 4. Cantidad: último número independiente después del bloque
            cantidad = ""
            for j in range(i + 1, len(lines)):
                if re.fullmatch(r"\d+", lines[j]):
                    cantidad = lines[j]

            productos.append({
                "codigo": codigo,
                "descripcion": descripcion,
                "unidad": unidad,
                "cantidad": cantidad,
            })

    return productos


# =============================
#  INTERFAZ STREAMLIT
# =============================

st.title("📄 OCR Automático de Pendientes")
st.write("Carga una imagen nítida del pendiente para extraer la información automáticamente.")

uploaded_file = st.file_uploader("Sube la imagen del pendiente", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Imagen cargada", use_column_width=True)

    with st.spinner("Procesando OCR..."):
        text = pytesseract.image_to_string(image, lang="spa")

    st.subheader("📝 Texto detectado:")
    st.text(text)

    # Extraer datos
    numero_solicitud = extract_numero_solicitud(text)
    pedido_pendiente = extract_pedido_pendiente(text)
    productos = extract_products(text)

    # Mostrar resumen
    st.subheader("📌 Datos extraídos")

    st.write(f"**Número solicitud:** {numero_solicitud or '— vacío —'}")
    st.write(f"**Pedido pendiente:** {pedido_pendiente or '— vacío —'}")
    st.write(f"**Productos detectados:** {len(productos)}")

    if productos:
        for idx, p in enumerate(productos, 1):
            st.write(f"### Producto {idx}")
            st.write(f"**Código:** {p['codigo'] or '— vacío —'}")
            st.write(f"**Descripción:** {p['descripcion'] or '— vacío —'}")
            st.write(f"**Unidad:** {p['unidad'] or '— vacío —'}")
            st.write(f"**Cantidad:** {p['cantidad'] or '— vacío —'}")

    # =============================
    #  BOTÓN PARA ENVIAR
    # =============================

    if productos:
        producto = productos[0]   # solo enviamos el primer producto

        if st.button("Enviar al Formulario"):
            payload = {
                ENTRY_SOLICITUD: numero_solicitud,
                ENTRY_PEDIDO: pedido_pendiente,
                ENTRY_CODIGO: producto["codigo"],
                ENTRY_DESCRIP: producto["descripcion"],
                ENTRY_UNIDAD: producto["unidad"],
                ENTRY_CANT: producto["cantidad"],
            }

            response = requests.post(FORM_URL, data=payload)

            if response.status_code == 200:
                st.success("Datos enviados correctamente.")
            else:
                st.error("Hubo un error al enviar los datos.")

