import streamlit as st
import easyocr
import re
import requests
from PIL import Image
import numpy as np

# ===============================
#  FUNCIÓN DE EXTRACCIÓN
# ===============================
def extraer_datos(texto):

    # ----------------------------------------
    # 1. Extraer número de solicitud y pedido
    # ----------------------------------------
    num_sol = None
    pedido = None

    sol_match = re.search(r"solicitud\s*(\d+)", texto.lower())
    if sol_match:
        num_sol = sol_match.group(1)

    ped_match = re.search(r"pendiente\s*(\d+)", texto.lower())
    if ped_match:
        pedido = ped_match.group(1)

    # ----------------------------------------
    # 2. Separar líneas limpias
    # ----------------------------------------
    lineas = [l.strip() for l in texto.split("\n") if l.strip() != ""]

    # ----------------------------------------
    # 3. Detectar código (primer número de 5–6 dígitos)
    # ----------------------------------------
    codigo = None
    for linea in lineas:
        cod_match = re.search(r"\b(\d{5,6})\b", linea)
        if cod_match:
            codigo = cod_match.group(1)
            break

    # ----------------------------------------
    # 4. Detectar unidad posible
    # ----------------------------------------
    posibles_unidades = ["FCO", "Fco", "TAB", "CAPS", "AMP", "ML", "G", "UND", "UNID"]

    unidad = None
    for linea in lineas:
        if any(linea.upper().startswith(u.upper()) for u in posibles_unidades):
            unidad = linea
            break

    # ----------------------------------------
    # 5. Detectar cantidad (una línea que sea solo un número)
    # ----------------------------------------
    cantidad = None
    for linea in lineas:
        if re.fullmatch(r"\d+", linea):
            cantidad = linea
            break

    # ----------------------------------------
    # 6. Descripción (todo menos código/unidad/cantidad)
    # ----------------------------------------
    descripcion_partes = []
    for linea in lineas:
        l = linea

        if codigo and codigo in l:
            l = l.replace(codigo, "").strip()

        if cantidad and l == cantidad:
            continue

        if unidad and l == unidad:
            continue

        if "Cod" in l or "Descripcion" in l or "Unid" in l:
            continue

        if re.search(r"[A-Za-z]", l):
            descripcion_partes.append(l)

    descripcion = " ".join(descripcion_partes).strip()
    if descripcion == "":
        descripcion = None

    return {
        "numero_solicitud": num_sol,
        "pedido_pendiente": pedido,
        "codigo": codigo,
        "descripcion": descripcion,
        "unidad": unidad,
        "cantidad": cantidad
    }


# ===============================
#  CONFIG STREAMLIT UI
# ===============================

st.title("📸 OCR Automático para Pendientes")

uploaded = st.file_uploader("Carga la imagen del ticket:", type=["png", "jpg", "jpeg"])

if uploaded:
    image = Image.open(uploaded)
    st.image(image, caption="Imagen cargada", use_column_width=True)

    # Convertir imagen a formato para easyocr
    img_np = np.array(image)

    st.write("🔍 Ejecutando OCR...")

    reader = easyocr.Reader(["es"], gpu=False)
    result = reader.readtext(img_np, detail=0)

    texto = "\n".join(result)

    st.subheader("📝 Texto detectado:")
    st.text(texto)

    # EXTRAER DATOS
    datos = extraer_datos(texto)

    st.subheader("📌 Datos extraídos:")
    st.write(f"**Número Solicitud:** {datos['numero_solicitud']}")
    st.write(f"**Pedido Pendiente:** {datos['pedido_pendiente']}")
    st.write(f"**Código:** {datos['codigo']}")
    st.write(f"**Descripción:** {datos['descripcion']}")
    st.write(f"**Unidad:** {datos['unidad']}")
    st.write(f"**Cantidad:** {datos['cantidad']}")

    st.write("———")

    # ===============================
    #  ENVIAR A GOOGLE FORM
    # ===============================

    if st.button("📤 Enviar al Formulario"):
        url = "https://docs.google.com/forms/d/e/1FAIpQLSfMsMmOaUhwpD9HQCuKf0Y4Y6oesiUO9GphNb5WMz3ItKKPjg/formResponse"

        payload = {
            "entry.611673084": datos["numero_solicitud"],
            "entry.1680720626": datos["pedido_pendiente"],
            "entry.832344567": datos["codigo"],
            "entry.1533087800": datos["descripcion"],
            "entry.728245219": datos["unidad"],
            "entry.231047139": datos["cantidad"],
        }

        r = requests.post(url, data=payload)

        if r.status_code == 200:
            st.success("✅ Datos enviados correctamente")
        else:
            st.error(f"❌ Error al enviar: {r.status_code}")
