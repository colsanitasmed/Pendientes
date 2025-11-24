import streamlit as st
import base64
import requests
import datetime

st.title("📄 Cargue de Documentos Pendientes")

API_URL = "https://script.google.com/macros/s/AKfycbwIH-E6KaiQzKMIiagOPrKtkSO6cC0lcVGueC-71VtNgEL0QeUCBBbbQGxnAkyG4cGKww/exec"

archivo = st.file_uploader("Cargar Documento", type=None)

if archivo is not None:
    st.success("Archivo listo para procesar")

    if st.button("Enviar"):
        base64_file = base64.b64encode(archivo.getvalue()).decode()

        data = {
            "nombre_archivo": archivo.name,
            "mime": archivo.type,
            "base64": base64_file,

            "FechaCarga": str(datetime.date.today()),
            "DocumentoPaciente": "",
        }

        response = requests.post(API_URL, json=data)

        try:
            resultado = response.json()
            st.json(resultado)
        except:
            st.error("La API devolvió algo que no es JSON")
            st.write(response.text)
