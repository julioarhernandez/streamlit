import streamlit as st
import pandas as pd
import os
import glob
import io
from datetime import datetime

# 🗂️ Carpeta donde están los archivos de asistencia
CARPETA_ONEDRIVE = r"C:\Users\JulioRodriguez\OneDrive - InterAmerican Technical Institute\Attendance"

# 📋 Lista maestra de residentes
ARCHIVO_RESIDENTES = "residentes.csv"

def cargar_lista_residentes():
    path_residentes = os.path.join(CARPETA_ONEDRIVE, ARCHIVO_RESIDENTES)
    return pd.read_csv(path_residentes)

def buscar_archivos_asistencia(fecha_str, tipo="Tarde"):
    patron = f"*{tipo}*{fecha_str}*.csv"
    ruta = os.path.join(CARPETA_ONEDRIVE, patron)
    archivos = glob.glob(ruta)
    return archivos

def combinar_asistencias(archivos):
    dfs = []
    for archivo in archivos:
        try:
            df = pd.read_csv(archivo)
            dfs.append(df)
        except:
            st.warning(f"No se pudo leer: {archivo}")
    if dfs:
        return pd.concat(dfs).drop_duplicates(subset=["nombre"])
    else:
        return pd.DataFrame(columns=["nombre"])

st.title("📋 Seguimiento de Asistencia - JulioRodriguez")

# Fecha seleccionada
fecha = st.date_input("Selecciona la fecha", value=datetime.today())
fecha_str = fecha.strftime(f"{fecha.month}-{fecha.day}-{fecha.year % 100}")

# Cargar lista de residentes
residentes = cargar_lista_residentes()

# Buscar y combinar asistencias registradas
archivos_manana = buscar_archivos_asistencia(fecha_str, "Manana")
archivos_tarde = buscar_archivos_asistencia(fecha_str, "Tarde")

asistencia_manana = combinar_asistencias(archivos_manana)
asistencia_tarde = combinar_asistencias(archivos_tarde)

# Marcar en la tabla quién asistió
residentes["mañana"] = residentes["nombre"].isin(asistencia_manana["nombre"])
residentes["tarde"] = residentes["nombre"].isin(asistencia_tarde["nombre"])

# Mostrar tabla editable
st.subheader(f"Asistencia del {fecha_str}")
columnas_mostrar = ["nombre", "mañana", "tarde"]

editable_table = st.data_editor(
    residentes[columnas_mostrar],
    column_config={
        "mañana": st.column_config.CheckboxColumn("mañana"),
        "tarde": st.column_config.CheckboxColumn("tarde"),
    },
    disabled=["nombre"],
    use_container_width=True
)

# Botón para guardar archivos de asistencia
if st.button("💾 Guardar asistencia marcada"):
    fecha_base = fecha.strftime(f"{fecha.month}-{fecha.day}-{fecha.year % 100}")

    df_manana = editable_table[editable_table["mañana"] == True][["nombre"]]
    df_tarde = editable_table[editable_table["tarde"] == True][["nombre"]]

    archivo_manana = os.path.join(CARPETA_ONEDRIVE, f"Asistencia_Manana_{fecha_base}.csv")
    archivo_tarde = os.path.join(CARPETA_ONEDRIVE, f"Asistencia_Tarde_{fecha_base}.csv")

    df_manana.to_csv(archivo_manana, index=False)
    df_tarde.to_csv(archivo_tarde, index=False)

    st.success("✅ Asistencia guardada correctamente.")

# Botón para descargar reporte completo
if st.button("📥 Descargar reporte Excel"):
    output = io.BytesIO()
    editable_table.to_excel(output, index=False)
    output.seek(0)
    st.download_button(
        label="Descargar Excel",
        data=output,
        file_name=f"reporte_asistencia_{fecha_str}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
