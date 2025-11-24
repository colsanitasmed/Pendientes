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
        try:
            # Enviar archivo correctamente como multipart/form-data
            files = {
                "archivo": (archivo.name, archivo.getvalue())
            }

            data = {
                "accion": "ocr",
                "tipo": tipo,
                "nombre_archivo": archivo.name
            }

            response = requests.post(API_URL, data=data, files=files)

            # Validamos si el servidor responde correctamente
            if response.status_code == 200:
                try:
                    resultado = response.json()  # 👈 aquí fallaba antes
                except Exception:
                    st.error("⚠️ La API respondió algo que NO es JSON.")
                    st.write("Respuesta cruda desde el servidor:")
                    st.code(response.text)
                    st.stop()

                # Todo bien
                if resultado.get("estado") == "ok":
                    st.subheader("Datos extraídos del archivo 📄")
                    st.json(resultado["data"])
                else:
                    st.error("❌ No se pudieron extraer datos del archivo.")
                    st.write(resultado)

            else:
                st.error(f"❌ Error en el OCR. Código HTTP: {response.status_code}")
                st.write(response.text)

        except Exception as e:
            st.error("⚠️ Error inesperado enviando el archivo a la API.")
            st.exception(e)
