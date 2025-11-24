import streamlit as st
import requests
import datetime

st.title("📄 Cargue de Documentos Pendientes")

API_URL = "API_URL = "https://script.google.com/macros/s/AKfycbwCKSxDidCQw42KLBexjN_vWSCi7XaC982yKcG3O50z4AkUL8lno4tIGbvtvaxgsIzf/exec"
"

archivo = st.file_uploader("Cargar Documento")

if archivo:
    st.success("Archivo listo para procesar")

    if st.button("Enviar"):
        
        # Datos adicionales
        data = {
            "FechaCarga": str(datetime.date.today()),
            "DocumentoPaciente": "",
            "NumeroSolicitud": "",
            "PedidoPendiente": "",
            "Codigo": "",
            "Descripcion": "",
            "Unid": "",
            "Cant": "",
            "filename": archivo.name
        }

        # ❗ CAMBIO CLAVE: el backend espera "archivo", NO "file"
        files = {
            "file": (archivo.name, archivo.getvalue(), archivo.type)
        }

        response = requests.post(API_URL, data=data, files=files)

        try:
            st.json(response.json())
        except:
            st.error("La API devolvió algo que no es JSON")
            st.write(response.text)
