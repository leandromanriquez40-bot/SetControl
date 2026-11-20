from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client
from postgrest.exceptions import APIError

st.set_page_config(page_title="SetControl", page_icon="💪", layout="wide")


supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)


def obtener_deportistas():
    r = supabase.table("deportistas").select("id,nombre,fecha_registro").order("nombre").execute()
    return r.data or []


def guardar_deportista(nombre):
    existente = supabase.table("deportistas").select("id").ilike("nombre", nombre).execute()
    if existente.data:
        raise ValueError("Ese deportista ya existe.")
    return supabase.table("deportistas").insert({
        "nombre": nombre,
        "fecha_registro": datetime.now().strftime("%Y-%m-%d")
    }).execute()


def eliminar_deportista(deportista_id):
    nombre = obtener_nombre_deportista(deportista_id)
    r = supabase.table("entrenamientos").select("id").eq("deportista", nombre).execute()
    cantidad = len(r.data or [])
    if cantidad:
        return False, cantidad
    supabase.table("deportistas").delete().eq("id", deportista_id).execute()
    return True, 0


def obtener_nombre_deportista(deportista_id):
    r = supabase.table("deportistas").select("nombre").eq("id", deportista_id).single().execute()
    return r.data["nombre"]


def guardar_entrenamiento(datos):
    fecha, deportista, ejercicio, peso, series, reps, rir, volumen, rm = datos
    # La columna de Supabase se llama "serie" (singular).
    registro = {
        "fecha": fecha, "deportista": deportista, "ejercicio": ejercicio,
        "peso": peso, "serie": series, "repeticiones": reps, "rir": rir,
        "volumen": volumen, "rm_estimado": rm
    }
    return supabase.table("entrenamientos").insert(registro).execute()


def actualizar_entrenamiento(registro_id, deportista, ejercicio, peso, series, reps, rir):
    volumen = float(peso) * int(series) * int(reps)
    rm = float(peso) * (1 + int(reps) / 30) if int(reps) <= 12 else None
    cambios = {
        "deportista": deportista, "ejercicio": ejercicio, "peso": float(peso),
        "serie": int(series), "repeticiones": int(reps), "rir": int(rir),
        "volumen": volumen, "rm_estimado": rm
    }
    return supabase.table("entrenamientos").update(cambios).eq("id", int(registro_id)).execute()


def eliminar_entrenamiento(registro_id):
    return supabase.table("entrenamientos").delete().eq("id", int(registro_id)).execute()


def obtener_historial():
    r = supabase.table("entrenamientos").select(
        "id,fecha,deportista,ejercicio,peso,serie,repeticiones,rir,volumen,rm_estimado"
    ).order("fecha", desc=True).order("id", desc=True).execute()
    filas = r.data or []
    columnas = ["ID", "Fecha", "Deportista", "Ejercicio", "Peso (kg)", "Series",
                "Repeticiones", "RIR", "Volumen (kg)", "1RM estimado (kg)"]
    if not filas:
        return pd.DataFrame(columns=columnas)
    return pd.DataFrame(filas).rename(columns={
        "id": "ID", "fecha": "Fecha", "deportista": "Deportista",
        "ejercicio": "Ejercicio", "peso": "Peso (kg)", "serie": "Series",
        "repeticiones": "Repeticiones", "rir": "RIR", "volumen": "Volumen (kg)",
        "rm_estimado": "1RM estimado (kg)"
    })


st.title("💪 SetControl")
st.caption("Sistema de control del entrenamiento de fuerza")
pagina = st.sidebar.radio("Menú principal", ["Inicio", "Deportistas", "Registrar entrenamiento", "Historial"])

try:
    if pagina == "Inicio":
        h, d = obtener_historial(), obtener_deportistas()
        st.header("Panel principal")
        a, b, c = st.columns(3)
        a.metric("Deportistas", len(d))
        b.metric("Entrenamientos", len(h))
        total = pd.to_numeric(h["Volumen (kg)"], errors="coerce").fillna(0).sum() if not h.empty else 0
        c.metric("Volumen acumulado", f"{total:,.1f} kg")
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
                    st.success("Deportista registrado en Supabase.")
                    st.rerun()
                except ValueError as e:
                    st.warning(str(e))
                except APIError as e:
                    st.error(f"Supabase no pudo guardar el deportista: {e}")
        lista = obtener_deportistas()
        st.subheader("Registrados")
        if lista:
            st.dataframe(pd.DataFrame([{"Nombre": d["nombre"]} for d in lista]),
                         use_container_width=True, hide_index=True)
            st.subheader("Eliminar deportista")
            elegido = st.selectbox("Selecciona deportista", lista,
                                   format_func=lambda d: d["nombre"], key="borrar_deportista")
            if st.button("Eliminar deportista seleccionado"):
                ok, cantidad = eliminar_deportista(elegido["id"])
                if ok:
                    st.success("Deportista eliminado de Supabase.")
                    st.rerun()
                else:
                    st.error(f"No se eliminó: tiene {cantidad} entrenamiento(s). Primero conserva o elimina esos registros desde Historial.")
        else:
            st.info("Todavía no hay deportistas.")

    elif pagina == "Registrar entrenamiento":
        st.header("📋 Registrar entrenamiento")
        deportistas = obtener_deportistas()
        nombres = [d["nombre"] for d in deportistas]
        if not nombres:
            st.warning("Primero registra un deportista.")
        else:
            with st.form("nuevo_entrenamiento", clear_on_submit=True):
                deportista = st.selectbox("Deportista", nombres)
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
                    try:
                        guardar_entrenamiento((datetime.now().isoformat(timespec="seconds"),
                            deportista, ejercicio, float(peso), int(series), int(reps),
                            int(rir), volumen, rm))
                        st.success(f"Entrenamiento guardado en Supabase. Volumen: {volumen:,.1f} kg" +
                                   (f" | 1RM estimado: {rm:.1f} kg" if rm is not None else ""))
                    except APIError as e:
                        st.error(f"Supabase no pudo guardar el entrenamiento: {e}")

    elif pagina == "Historial":
        st.header("📊 Historial de entrenamientos")
        h = obtener_historial()
        if h.empty:
            st.info("Todavía no hay entrenamientos registrados.")
        else:
            fd = ["Todos"] + sorted(h["Deportista"].dropna().unique().tolist())
            filtro_d = st.selectbox("Filtrar deportista", fd)
            if filtro_d != "Todos":
                h = h[h["Deportista"] == filtro_d]
            fe = ["Todos"] + sorted(h["Ejercicio"].dropna().unique().tolist())
            filtro_e = st.selectbox("Filtrar ejercicio", fe)
            if filtro_e != "Todos":
                h = h[h["Ejercicio"] == filtro_e]
            st.metric("Registros encontrados", len(h))
            st.dataframe(h.drop(columns=["ID"]), use_container_width=True, hide_index=True)
            st.download_button("Descargar historial CSV",
                h.drop(columns=["ID"]).to_csv(index=False).encode("utf-8-sig"),
                "historial_setcontrol.csv", "text/csv")
            st.divider()
            st.subheader("Corregir o eliminar un entrenamiento")
            registro_id = st.selectbox("ID del registro", h["ID"].astype(int).tolist())
            fila = h[h["ID"] == registro_id].iloc[0]
            nombres = [d["nombre"] for d in obtener_deportistas()]
            indice = nombres.index(fila["Deportista"]) if fila["Deportista"] in nombres else 0
            with st.form("editar_entrenamiento"):
                nuevo_deportista = st.selectbox("Deportista", nombres, index=indice)
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
                    try:
                        actualizar_entrenamiento(registro_id, nuevo_deportista,
                            nuevo_ejercicio.strip(), nuevo_peso, nuevas_series, nuevas_reps, nuevo_rir)
                        st.success("Registro corregido en Supabase.")
                        st.rerun()
                    except APIError as e:
                        st.error(f"No se pudo actualizar: {e}")
            confirmar = st.checkbox("Confirmo que quiero eliminar este entrenamiento")
            if st.button("Eliminar entrenamiento seleccionado", disabled=not confirmar):
                try:
                    eliminar_entrenamiento(registro_id)
                    st.success("Entrenamiento eliminado de Supabase.")
                    st.rerun()
                except APIError as e:
                    st.error(f"No se pudo eliminar: {e}")

except APIError as e:
    st.error(f"Error de comunicación con Supabase: {e}")
    st.info("Comprueba que los nombres de las columnas coincidan con los usados por SetControl.")

st.divider()
st.caption("SetControl | Control del entrenamiento de fuerza")

