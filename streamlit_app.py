import streamlit as st
import pytesseract
from PIL import Image
import requests
from io import BytesIO

# ==============================
# IDS DEL FORMULARIO DE GOOGLE
# ==============================
ENTRY_SOLICITUD = "entry.611673084"
ENTRY_PEDIDO = "entry.1680720626"
ENTRY_CODIGO = "entry.832344567"
ENTRY_DESCRIP = "entry.1533087800"
ENTRY_UNIDAD = "entry.728245219"
ENTRY_CANT = "entry.231047139"
ENTRY_DOCUMENTO = "entry.412830053"   # <<< NUEVO CAMPO (Actualiza este ID!!)

# URL del formulario
GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScQHnVAdEz_udkq8AjtG7NfCQbHcsHFt3c1_xxxxx/formResponse"

st.title("📄 Lector de Ticket y Envío Automático")

# ==================================
# 1️⃣ NUEVO CAMPO: DOCUMENTO USUARIO
# ==================================
documento_usuario = st.text_input("Número de Documento del Usuario")

# ==============================
# 2️⃣ SUBIR IMAGEN DEL TICKET
# ==============================
uploaded_file = st.file_uploader("Cargar imagen del ticket", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)

    # OCR
    text = pytesseract.image_to_string(image, lang="spa")

    st.subheader("📌 Datos extraídos")

    # ======================
    # EXTRAER DATOS DEL TICKET
    # ======================
    def find_value(pattern, text):
        import re
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    nro_solicitud = find_value(r"Solicitud[:\- ]+(\d+)", text)
    nro_pedido = find_value(r"Pedido[:\- ]+(\d+)", text)
    codigo = find_value(r"C[oó]digo[:\- ]+(\d+)", text)
    descripcion = find_value(r"Descripci[oó]n[:\- ]+(.+)", text)
    unidad = find_value(r"Unidad[:\- ]+(\w+)", text)
    cantidad = find_value(r"Cantidad[:\- ]+(\d+)", text)

    # Mostrar datos detectados
    st.write(f"**Número solicitud:** {nro_solicitud or '— vacío —'}")
    st.write(f"**Pedido pendiente:** {nro_pedido or '— vacío —'}")
    st.write(f"**Código:** {codigo or '— vacío —'}")
    st.write(f"**Descripción:** {descripcion or '— vacío —'}")
    st.write(f"**Unidad:** {unidad or '— vacío —'}")
    st.write(f"**Cantidad:** {cantidad or '— vacío —'}")

    # =========================================
    # 3️⃣ VALIDAR QUE TODOS LOS CAMPOS EXISTEN
    # =========================================
    campos = {
        "Documento del Usuario": documento_usuario,
        "Solicitud": nro_solicitud,
        "Pedido": nro_pedido,
        "Código": codigo,
        "Descripción": descripcion,
        "Unidad": unidad,
        "Cantidad": cantidad,
    }

    datos_incompletos = [campo for campo, valor in campos.items() if not valor]

    if datos_incompletos:
        st.error("❌ No se pudieron leer correctamente todos los campos. "
                 "Por favor cargue un ticket más legible.")

    else:
        # =========================================
        # 4️⃣ ENVIAR FORMULARIO SI TODO ESTÁ COMPLETO
        # =========================================
        if st.button("📨 Enviar datos al formulario"):
            
            payload = {
                ENTRY_DOCUMENTO: documento_usuario,
                ENTRY_SOLICITUD: nro_solicitud,
                ENTRY_PEDIDO: nro_pedido,
                ENTRY_CODIGO: codigo,
                ENTRY_DESCRIP: descripcion,
                ENTRY_UNIDAD: unidad,
                ENTRY_CANT: cantidad
            }

            response = requests.post(GOOGLE_FORM_URL, data=payload)

            if response.status_code == 200:
                st.success("✅ Datos enviados correctamente.")
            else:
                st.error("⚠️ Error enviando los datos. Verifique la URL del formulario.")
