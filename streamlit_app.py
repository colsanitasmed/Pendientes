import streamlit as st
import requests
import datetime

st.title("📄 Cargue de Documentos Pendientes")

API_URL = "https://script.google.com/macros/s/AKfycbwIH-E6KaiQzKMIiagOPrKtkSO6cC0lcVGueC-71VtNgEL0QeUCBBbbQGxnAkyG4cGKww/exec"

# 1. Tipo de documento
tipo = st.selectbox("Tipo de Documento", ["PDF", "JPG", "PNG", "Otros"])

# 2. Cargar archivo
archivo = st.file_uploader("Cargar Documento", type=None)

# Cuando ya subió un archivo
if archivo is not None:
    st.success("Archivo cargado. Procesa para extraer datos automáticamente.")
    
    if st.button("Procesar archivo"):
        files = {
            "archivo": (archivo.name, archivo.getvalue())
        }

        data = {
            "accion": "ocr",
            "tipo": tipo,
            "nombre_archivo": archivo.name
        }

        response = requests.post(API_URL, data=data, files=files)

        if response.status_code == 200:
            resultado = response.json()

            if resultado.get("estado") == "ok":
                st.subheader("Datos extraídos del archivo 📄")
                st.json(resultado["data"])
            else:
                st.error("No se pudieron extraer datos del archivo.")
                st.write(resultado)
        else:
            st.error("Error en el OCR.")
            st.write(response.text)
