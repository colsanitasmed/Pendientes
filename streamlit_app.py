import streamlit as st
import requests
import base64

st.title("📄 Cargue de Documentos Pendientes")

API_URL = "https://script.google.com/macros/s/AKfycbweOuq4IBBS58cemM_H35zc7sUnz0bVQPnlggK18eziLppYejiY15hU8sjG1cYighEN/exec"   # <-- reemplazar por la URL del despliegue

# 1. Tipo de documento
tipo = st.selectbox("Tipo de Documento", ["PDF", "JPG", "PNG", "Otros"])

# 2. Cargar archivo
archivo = st.file_uploader("Cargar Documento", type=None)

if archivo is not None:
    st.success("Archivo cargado. Listo para procesar.")

    if st.button("Procesar archivo"):
        # Convertir archivo a base64
        archivo_b64 = base64.b64encode(archivo.getvalue()).decode()

        data = {
            "accion": "ocr",
            "tipo": tipo,
            "nombre_archivo": archivo.name,
            "archivo_base64": archivo_b64
        }

        # Enviar como JSON
        response = requests.post(API_URL, json=data)

        # Validar respuesta
        try:
            resultado = response.json()
        except:
            st.error("⚠️ La API respondió algo que NO es JSON.")
            st.write(response.text)
            st.stop()

        if resultado.get("estado") == "ok":
            st.subheader("Datos extraídos del archivo 📄")
            st.json(resultado["data"])
        else:
            st.error("❌ Error en la API")
            st.write(resultado)
