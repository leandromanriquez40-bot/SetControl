import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


# =========================================================
# CONFIGURACION
# =========================================================

st.set_page_config(
    page_title="SetControl",
    page_icon="💪",
    layout="wide"
)

# La base de datos debe estar en la misma carpeta que app.py.
DB_NAME = Path(__file__).resolve().parent / "setcontrol.db"


# =========================================================
# BASE DE DATOS
# =========================================================

def conectar():
    return sqlite3.connect(DB_NAME)


def inicializar_base_datos():
    """Crea la tabla de deportistas y recupera nombres antiguos."""
    with conectar() as conexion:
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

        conexion.execute("""
            CREATE TABLE IF NOT EXISTS deportistas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL COLLATE NOCASE UNIQUE,
                fecha_registro TEXT NOT NULL
            )
        """)

        # Migración segura: agrega a Deportistas los nombres que ya
        # existen en entrenamientos, sin modificar ni borrar registros.
        nombres_antiguos = conexion.execute("""
            SELECT DISTINCT TRIM(deportista)
            FROM entrenamientos
            WHERE deportista IS NOT NULL
              AND TRIM(deportista) <> ''
        """).fetchall()

        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        for (nombre,) in nombres_antiguos:
            conexion.execute("""
                INSERT OR IGNORE INTO deportistas (nombre, fecha_registro)
                VALUES (?, ?)
            """, (nombre, fecha_hoy))


def obtener_deportistas():
    with conectar() as conexion:
        filas = conexion.execute("""
            SELECT nombre
            FROM deportistas
            ORDER BY nombre COLLATE NOCASE
        """).fetchall()
    return [fila[0] for fila in filas]


def guardar_deportista(nombre):
    with conectar() as conexion:
        conexion.execute("""
            INSERT INTO deportistas (nombre, fecha_registro)
            VALUES (?, ?)
        """, (nombre, datetime.now().strftime("%Y-%m-%d")))


def guardar_entrenamiento(datos):
    with conectar() as conexion:
        conexion.execute("""
            INSERT INTO entrenamientos (
                fecha, deportista, ejercicio, peso,
                series, repeticiones, rir, volumen, rm_estimado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, datos)


def obtener_historial():
    with conectar() as conexion:
        return pd.read_sql_query("""
            SELECT
                id AS ID,
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


# Inicializa y migra antes de mostrar la interfaz.
inicializar_base_datos()


# =========================================================
# INTERFAZ
# =========================================================

st.title("💪 SetControl")
st.caption("Sistema de control del entrenamiento de fuerza")

pagina = st.sidebar.radio(
    "Menú principal",
    ["Inicio", "Deportistas", "Registrar entrenamiento", "Historial"]
)


# =========================================================
# INICIO
# =========================================================

if pagina == "Inicio":
    st.header("Panel principal")
    historial = obtener_historial()
    deportistas = obtener_deportistas()

    col1, col2, col3 = st.columns(3)
    col1.metric("Deportistas registrados", len(deportistas))
    col2.metric("Entrenamientos registrados", len(historial))
    volumen_total = (
        historial["Volumen (kg)"].sum() if not historial.empty else 0
    )
    col3.metric("Volumen acumulado", f"{volumen_total:,.1f} kg")

    st.divider()
    st.write(
        "Utiliza el menú para administrar deportistas, registrar sesiones "
        "y revisar el historial de entrenamiento."
    )


# =========================================================
# DEPORTISTAS
# =========================================================

elif pagina == "Deportistas":
    st.header("👥 Administración de deportistas")
    st.write("Registra y consulta las personas cuyo entrenamiento controlarás.")

    with st.form("formulario_deportista", clear_on_submit=True):
        nombre = st.text_input("Nombre del deportista")
        enviar = st.form_submit_button("Registrar deportista")

        if enviar:
            nombre = nombre.strip()
            if not nombre:
                st.warning("Debes ingresar un nombre.")
            else:
                try:
                    guardar_deportista(nombre)
                    st.success(f"{nombre} fue registrado correctamente.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.warning("Ese deportista ya está registrado.")

    st.divider()
    st.subheader("Deportistas registrados")
    deportistas = obtener_deportistas()

    if deportistas:
        st.dataframe(
            pd.DataFrame({
                "N.º": range(1, len(deportistas) + 1),
                "Nombre": deportistas
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Todavía no hay deportistas registrados.")


# =========================================================
# REGISTRAR ENTRENAMIENTO
# =========================================================

elif pagina == "Registrar entrenamiento":
    st.header("📋 Registrar entrenamiento")
    deportistas = obtener_deportistas()

    if not deportistas:
        st.warning(
            "Primero registra al menos un deportista en la sección Deportistas."
        )
    else:
        with st.form("formulario_entrenamiento", clear_on_submit=True):
            deportista = st.selectbox("Deportista", deportistas)

            ejercicio_opciones = [
                "Sentadilla",
                "Press banca",
                "Peso muerto",
                "Press militar",
                "Remo",
                "Otro"
            ]
            ejercicio = st.selectbox("Ejercicio", ejercicio_opciones)
            if ejercicio == "Otro":
                ejercicio = st.text_input("Escribe el nombre del ejercicio")

            col1, col2 = st.columns(2)
            with col1:
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
                    value=3,
                    step=1
                )
            with col2:
                repeticiones = st.number_input(
                    "Repeticiones por serie",
                    min_value=1,
                    max_value=100,
                    value=10,
                    step=1
                )
                rir = st.selectbox("Repeticiones en reserva (RIR)", [0, 1, 2, 3, 4, 5])

            guardar = st.form_submit_button("Guardar entrenamiento")

            if guardar:
                ejercicio = ejercicio.strip()
                if not ejercicio:
                    st.warning("Debes indicar el ejercicio.")
                elif peso <= 0:
                    st.warning("El peso debe ser mayor que cero.")
                else:
                    volumen = float(peso) * int(series) * int(repeticiones)
                    rm = (
                        float(peso) * (1 + int(repeticiones) / 30)
                        if int(repeticiones) <= 12 else None
                    )
                    datos = (
                        datetime.now().isoformat(timespec="seconds"),
                        deportista,
                        ejercicio,
                        float(peso),
                        int(series),
                        int(repeticiones),
                        int(rir),
                        volumen,
                        rm
                    )
                    guardar_entrenamiento(datos)
                    st.success("¡Entrenamiento guardado correctamente!")
                    st.write(f"**Deportista:** {deportista}")
                    st.write(f"**Volumen de carga:** {volumen:,.1f} kg")
                    if rm is not None:
                        st.write(f"**1RM estimado:** {rm:.1f} kg")


# =========================================================
# HISTORIAL
# =========================================================

elif pagina == "Historial":
    st.header("📊 Historial de entrenamientos")
    historial = obtener_historial()

    if historial.empty:
        st.info("Todavía no hay entrenamientos registrados.")
    else:
        deportistas = ["Todos"] + obtener_deportistas()
        seleccionado = st.selectbox("Filtrar por deportista", deportistas)

        if seleccionado != "Todos":
            historial = historial[historial["Deportista"] == seleccionado]

        ejercicios = ["Todos"] + sorted(
            historial["Ejercicio"].dropna().unique().tolist()
        )
        ejercicio_seleccionado = st.selectbox("Filtrar por ejercicio", ejercicios)

        if ejercicio_seleccionado != "Todos":
            historial = historial[historial["Ejercicio"] == ejercicio_seleccionado]

        if historial.empty:
            st.info("No hay registros para los filtros seleccionados.")
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Sesiones registradas", len(historial))
            col2.metric(
                "Volumen acumulado",
                f"{historial['Volumen (kg)'].sum():,.1f} kg"
            )
            rm_validos = historial["1RM estimado (kg)"].dropna()
            col3.metric(
                "Mayor 1RM estimado",
                f"{rm_validos.max():.1f} kg" if not rm_validos.empty else "Sin datos"
            )

            st.divider()
            st.subheader("Registros")
            st.dataframe(
                historial.drop(columns=["ID"]),
                use_container_width=True,
                hide_index=True
            )

            st.subheader("Evolución del volumen por sesión")
            grafico = historial[["Fecha", "Volumen (kg)"]].copy()
            grafico["Fecha"] = pd.to_datetime(grafico["Fecha"], errors="coerce")
            grafico = grafico.dropna(subset=["Fecha"]).sort_values("Fecha")
            if not grafico.empty:
                st.line_chart(grafico.set_index("Fecha"))

            csv = historial.drop(columns=["ID"]).to_csv(
                index=False
            ).encode("utf-8-sig")
            st.download_button(
                "📥 Descargar historial CSV",
                data=csv,
                file_name="historial_setcontrol.csv",
                mime="text/csv"
            )


# =========================================================
# PIE DE PAGINA
# =========================================================

st.divider()
st.caption("SetControl | Sistema de innovación deportiva")
