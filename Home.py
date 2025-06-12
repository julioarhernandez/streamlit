import streamlit as st

# Set page config
# st.set_page_config(
#     page_title="Sistema de Gestión Estudiantil",
#     page_icon="🎓",
#     layout="centered"
# )

pages = {
    "Inicio": [
        st.Page("Login.py", title="Login")
    ],
    "Datos": [
        st.Page("pages/1_Estudiantes.py", title="Estudiantes"),
        st.Page("pages/2_Asistencia.py", title="Asistencia"),
        st.Page("pages/4_Modulos.py", title="Módulos"),
        st.Page("pages/0_Semanas_Descanso.py", title="Vacaciones")
    ],
    "Reportes": [
        st.Page("pages/3_Reportes.py", title="Asistencia"),
        st.Page("pages/5_Reporte_estudiantes.py", title="Estudiantes")
    ],
}

pg = st.navigation(pages)
pg.run()



    # When logged in, pages from the 'pages' directory will appear in the sidebar.
    # Ensure those pages have a login check.