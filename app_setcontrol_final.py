import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="SetControl", page_icon="💪", layout="wide")
DB_NAME = Path(__file__).resolve().parent / "setcontrol.db"


def conectar():
    return sqlite3.connect(DB_NAME)


def inicializar_base_datos():
    with conectar() as con:
        con.execute("""
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
        con.execute("""
            CREATE TABLE IF NOT EXISTS deportistas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL COLLATE NOCASE UNIQUE,
                fecha_registro TEXT NOT NULL
            )
        """)
        antiguos = con.execute("""
            SELECT DISTINCT TRIM(deportista) FROM entrenamientos
            WHERE deportista IS NOT NULL AND TRIM(deportista) <> ''
        """).fetchall()
        for (nombre,) in antiguos:
            con.execute(
                "INSERT OR IGNORE INTO deportistas(nombre, fecha_registro) VALUES (?, ?)",
                (nombre, datetime.now().strftime("%Y-%m-%d"))
            )


def obtener_deportistas():
    with conectar() as con:
        return [r[0] for r in con.execute(
            "SELECT nombre FROM deportistas ORDER BY nombre COLLATE NOCASE"
        ).fetchall()]


def guardar_deportista(nombre):
    with conectar() as con:
        con.execute(
            "INSERT INTO deportistas(nombre, fecha_registro) VALUES (?, ?)",
            (nombre, datetime.now().strftime("%Y-%m-%d"))
        )


def eliminar_deportista(nombre):
    with conectar() as con:
        cantidad = con.execute(
            "SELECT COUNT(*) FROM entrenamientos WHERE deportista = ?", (nombre,)
        ).fetchone()[0]
        if cantidad:
            return False, cantidad
        con.execute("DELETE FROM deportistas WHERE nombre = ?", (nombre,))
        return True, 0


def guardar_entrenamiento(datos):
    with conectar() as con:
        con.execute("""
            INSERT INTO entrenamientos
            (fecha, deportista, ejercicio, peso, series, repeticiones, rir, volumen, rm_estimado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, datos)


def actualizar_entrenamiento(registro_id, deportista, ejercicio, peso, series, reps, rir):
    volumen = float(peso) * int(series) * int(reps)
    rm = float(peso) * (1 + int(reps) / 30) if int(reps) <= 12 else None
    with conectar() as con:
        con.execute("""
            UPDATE entrenamientos
            SET deportista=?, ejercicio=?, peso=?, series=?, repeticiones=?,
                rir=?, volumen=?, rm_estimado=?
            WHERE id=?
        """, (deportista, ejercicio, float(peso), int(series), int(reps),
              int(rir), volumen, rm, int(registro_id)))


def eliminar_entrenamiento(registro_id):
    with conectar() as con:
        con.execute("DELETE FROM entrenamientos WHERE id=?", (int(registro_id),))


def obtener_historial():
    with conectar() as con:
        return pd.read_sql_query("""
            SELECT id AS ID, fecha AS Fecha, deportista AS Deportista,
                   ejercicio AS Ejercicio, peso AS 'Peso (kg)',
                   series AS Series, repeticiones AS Repeticiones, rir AS RIR,
                   volumen AS 'Volumen (kg)', rm_estimado AS '1RM estimado (kg)'
            FROM entrenamientos ORDER BY fecha DESC, id DESC
        """, con)


inicializar_base_datos()
st.title("💪 SetControl")
st.caption("Sistema de control del entrenamiento de fuerza")
pagina = st.sidebar.radio(
    "Menú principal",
    ["Inicio", "Deportistas", "Registrar entrenamiento", "Historial"]
)

if pagina == "Inicio":
    h = obtener_historial()
    d = obtener_deportistas()
    st.header("Panel principal")
    a, b, c = st.columns(3)
    a.metric("Deportistas", len(d))
    b.metric("Entrenamientos", len(h))
    c.metric("Volumen acumulado", f"{h['Volumen (kg)'].sum():,.1f} kg" if not h.empty else "0 kg")
    st.info("Usa el menú para registrar deportistas, entrenamientos y revisar o corregir el historial.")

elif pagina == "Deportistas":
    st.header("👥 Deportistas")
    with st.form("nuevo_deportista", clear_on_submit=True):
        nombre = st.text_input("Nombre del deportista")
        enviar = st.form_submit_button("Registrar deportista")
    if enviar:
        if not nombre.strip():
            st.warning("Escribe un nombre.")
        else:
            try:
                guardar_deportista(nombre.strip())
                st.success("Deportista registrado.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.warning("Ese deportista ya existe.")

    lista = obtener_deportistas()
    st.subheader("Registrados")
    if lista:
        st.dataframe(pd.DataFrame({"Nombre": lista}), use_container_width=True, hide_index=True)
        st.subheader("Eliminar deportista")
        elegido = st.selectbox("Selecciona deportista", lista, key="borrar_deportista")
        if st.button("Eliminar deportista seleccionado"):
            ok, cantidad = eliminar_deportista(elegido)
            if ok:
                st.success("Deportista eliminado.")
                st.rerun()
            else:
                st.error(f"No se eliminó: tiene {cantidad} entrenamiento(s). Primero conserva o elimina esos registros desde Historial.")
    else:
        st.info("Todavía no hay deportistas.")

elif pagina == "Registrar entrenamiento":
    st.header("📋 Registrar entrenamiento")
    deportistas = obtener_deportistas()
    if not deportistas:
        st.warning("Primero registra un deportista.")
    else:
        with st.form("nuevo_entrenamiento", clear_on_submit=True):
            deportista = st.selectbox("Deportista", deportistas)
            opciones = ["Sentadilla", "Press banca", "Peso muerto", "Press militar", "Remo", "Otro"]
            ejercicio_op = st.selectbox("Ejercicio", opciones)
            ejercicio_otro = st.text_input("Nombre del ejercicio (si elegiste Otro)")
            peso = st.number_input("Peso utilizado (kg)", min_value=0.0, value=60.0, step=2.5)
            series = st.number_input("Series", min_value=1, max_value=20, value=3, step=1)
            reps = st.number_input("Repeticiones por serie", min_value=1, max_value=100, value=10, step=1)
            rir = st.selectbox("RIR", [0, 1, 2, 3, 4, 5])
            guardar = st.form_submit_button("Guardar entrenamiento")
        if guardar:
            ejercicio = ejercicio_otro.strip() if ejercicio_op == "Otro" else ejercicio_op
            if not ejercicio:
                st.error("Indica el ejercicio.")
            elif peso <= 0:
                st.error("El peso debe ser mayor que cero.")
            else:
                volumen = float(peso) * int(series) * int(reps)
                rm = float(peso) * (1 + int(reps) / 30) if int(reps) <= 12 else None
                guardar_entrenamiento((
                    datetime.now().isoformat(timespec="seconds"), deportista,
                    ejercicio, float(peso), int(series), int(reps), int(rir), volumen, rm
                ))
                st.success(f"Guardado. Volumen: {volumen:,.1f} kg" +
                           (f" | 1RM estimado: {rm:.1f} kg" if rm is not None else ""))

elif pagina == "Historial":
    st.header("📊 Historial de entrenamientos")
    h = obtener_historial()
    if h.empty:
        st.info("Todavía no hay entrenamientos registrados.")
    else:
        deportistas_filtro = ["Todos"] + sorted(h["Deportista"].dropna().unique().tolist())
        filtro_d = st.selectbox("Filtrar deportista", deportistas_filtro)
        if filtro_d != "Todos":
            h = h[h["Deportista"] == filtro_d]
        ejercicios = ["Todos"] + sorted(h["Ejercicio"].dropna().unique().tolist())
        filtro_e = st.selectbox("Filtrar ejercicio", ejercicios)
        if filtro_e != "Todos":
            h = h[h["Ejercicio"] == filtro_e]
        st.metric("Registros encontrados", len(h))
        st.dataframe(h.drop(columns=["ID"]), use_container_width=True, hide_index=True)
        st.download_button(
            "Descargar historial CSV",
            h.drop(columns=["ID"]).to_csv(index=False).encode("utf-8-sig"),
            "historial_setcontrol.csv",
            "text/csv"
        )

        st.divider()
        st.subheader("Corregir o eliminar un entrenamiento")
        opciones_id = h["ID"].astype(int).tolist()
        registro_id = st.selectbox("ID del registro", opciones_id)
        fila = h[h["ID"] == registro_id].iloc[0]
        deportistas = obtener_deportistas()
        indice = deportistas.index(fila["Deportista"]) if fila["Deportista"] in deportistas else 0
        with st.form("editar_entrenamiento"):
            nuevo_deportista = st.selectbox("Deportista", deportistas, index=indice)
            nuevo_ejercicio = st.text_input("Ejercicio", str(fila["Ejercicio"]))
            nuevo_peso = st.number_input("Peso (kg)", min_value=0.1, value=float(fila["Peso (kg)"]), step=2.5)
            nuevas_series = st.number_input("Series", min_value=1, max_value=20, value=int(fila["Series"]))
            nuevas_reps = st.number_input("Repeticiones", min_value=1, max_value=100, value=int(fila["Repeticiones"]))
            nuevo_rir = st.selectbox("RIR", [0, 1, 2, 3, 4, 5], index=int(fila["RIR"]))
            guardar_cambios = st.form_submit_button("Guardar correcciones")
        if guardar_cambios:
            if not nuevo_ejercicio.strip():
                st.error("El ejercicio no puede quedar vacío.")
            else:
                actualizar_entrenamiento(registro_id, nuevo_deportista, nuevo_ejercicio.strip(),
                                         nuevo_peso, nuevas_series, nuevas_reps, nuevo_rir)
                st.success("Registro corregido.")
                st.rerun()
        confirmar = st.checkbox("Confirmo que quiero eliminar este entrenamiento")
        if st.button("Eliminar entrenamiento seleccionado", disabled=not confirmar):
            eliminar_entrenamiento(registro_id)
            st.success("Entrenamiento eliminado.")
            st.rerun()

st.divider()
st.caption("SetControl | Control del entrenamiento de fuerza")
