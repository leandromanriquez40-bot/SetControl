
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# =================================
# 1. CONFIGURACION
# =================================

st.set_page_config(
    page_title="SetControl",
    page_icon="💪",
    layout="wide"
)

DB_NAME = "setcontrol.db"


# =================================
# 2. CREAR BASE DE DATOS
# =================================

def inicializar_base_datos():

    with sqlite3.connect(DB_NAME) as conexion:

        conexion.execute("""
            CREATE TABLE IF NOT EXISTS entrenamientos (

                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                deportista TEXT NOT NULL,
                ejercicio TEXT NOT NULL,
                peso REAL NOT NULL,
                series INTEGER NOT NULL,
                repeticiones INTEGER NOT NULL,
                rir INTEGER NOT NULL,
                volumen REAL NOT NULL,
                rm_estimado REAL

            )
        """)


# =================================
# 3. GUARDAR ENTRENAMIENTO
# =================================

def guardar_entrenamiento(datos):

    with sqlite3.connect(DB_NAME) as conexion:

        conexion.execute("""
            INSERT INTO entrenamientos (
                fecha,
                deportista,
                ejercicio,
                peso,
                series,
                repeticiones,
                rir,
                volumen,
                rm_estimado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, datos)


# =================================
# 4. CONSULTAR HISTORIAL
# =================================

def obtener_historial():

    with sqlite3.connect(DB_NAME) as conexion:

        df = pd.read_sql_query("""
            SELECT
                fecha AS Fecha,
                deportista AS Deportista,
                ejercicio AS Ejercicio,
                peso AS 'Peso (kg)',
                series AS Series,
                repeticiones AS Repeticiones,
                rir AS RIR,
                volumen AS 'Volumen (kg)',
                rm_estimado AS '1RM estimado (kg)'

            FROM entrenamientos

            ORDER BY fecha DESC, id DESC
        """, conexion)

    return df


# Crear la base de datos al iniciar
inicializar_base_datos()


# =================================
# 5. INTERFAZ PRINCIPAL
# =================================

st.title("💪 SetControl")

st.subheader(
    "Sistema de control del entrenamiento de fuerza"
)

st.write(
    "Registra, analiza y controla "
    "el rendimiento de tus deportistas."
)

st.divider()


# =================================
# 6. FORMULARIO
# =================================

st.header("📋 Registrar entrenamiento")

with st.form("formulario_entrenamiento"):

    deportista = st.text_input(
        "Nombre del deportista"
    )

    ejercicio = st.selectbox(
        "Ejercicio",
        [
            "Sentadilla",
            "Press banca",
            "Peso muerto",
            "Press militar",
            "Remo",
            "Otro"
        ]
    )

    peso = st.number_input(
        "Peso utilizado (kg)",
        min_value=0.0,
        value=60.0,
        step=2.5
    )

    series = st.number_input(
        "Cantidad de series",
        min_value=1,
        max_value=20,
        value=3
    )

    repeticiones = st.number_input(
        "Repeticiones por serie",
        min_value=1,
        max_value=100,
        value=10
    )

    rir = st.selectbox(
        "Repeticiones en reserva (RIR)",
        [0, 1, 2, 3, 4, 5]
    )

    guardar = st.form_submit_button(
        "Guardar entrenamiento"
    )

    if guardar:

        if deportista.strip():

            volumen = peso * series * repeticiones

            if repeticiones <= 12:
                rm = peso * (1 + repeticiones / 30)
            else:
                rm = None

            datos = (
                datetime.now().isoformat(timespec="seconds"),
                deportista.strip(),
                ejercicio,
                peso,
                int(series),
                int(repeticiones),
                int(rir),
                volumen,
                rm
            )

            guardar_entrenamiento(datos)

            st.success(
                "¡Entrenamiento guardado permanentemente!"
            )

        else:

            st.error(
                "Debes ingresar el nombre del deportista."
            )


# =================================
# 7. ANALISIS DE RESULTADOS
# =================================

st.divider()

st.header("📊 Análisis del entrenamiento")

df = obtener_historial()

if not df.empty:

    volumen_total = df["Volumen (kg)"].sum()

    col1, col2 = st.columns(2)

    col1.metric(
        "Volumen acumulado",
        f"{volumen_total:,.1f} kg"
    )

    col2.metric(
        "Registros realizados",
        len(df)
    )

    st.subheader("Historial de entrenamientos")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Evolución del volumen")

    grafico = df.copy()

    grafico["Fecha"] = pd.to_datetime(
        grafico["Fecha"]
    )

    grafico = grafico.sort_values("Fecha")

    st.line_chart(
        grafico,
        x="Fecha",
        y="Volumen (kg)"
    )

    # Descargar informacion
    csv = df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "📥 Descargar historial CSV",
        data=csv,
        file_name="historial_setcontrol.csv",
        mime="text/csv"
    )

else:

    st.info(
        "Todavía no existen entrenamientos registrados."
    )


# =================================
# 8. PIE DE PAGINA
# =================================

st.divider()

st.caption(
    "SetControl | Sistema de innovación deportiva"
)
