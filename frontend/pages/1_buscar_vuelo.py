# =============================================
# AEROLÍNEAS RAFAEL PABON
# pages/1_buscar_vuelo.py — Búsqueda incremental de vuelos
# =============================================

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from utils.node_client import NodeClient
from utils.timezone_helper import flight_times

st.set_page_config(page_title="Buscar vuelo — ARLP", page_icon="🔍", layout="wide")

# ─────────────────────────────────────────
# VERIFICAR NODO SELECCIONADO
# ─────────────────────────────────────────
if "node_url" not in st.session_state:
    st.warning("Primero selecciona tu región en la página principal.")
    st.page_link("streamlit_app.py", label="Ir a inicio", icon="🏠")
    st.stop()

client = NodeClient(st.session_state.node_url)

st.title("🔍 Buscar vuelo")
st.caption(f"Conectado al nodo {st.session_state.node_id} — {st.session_state.node_url}")

# ─────────────────────────────────────────
# FORMULARIO DE BÚSQUEDA INCREMENTAL
# ─────────────────────────────────────────
# Los campos son opcionales: el usuario puede buscar con cualquier combinación.
# El backend filtra solo los campos que se envían.
# ─────────────────────────────────────────
with st.expander("Filtros de búsqueda", expanded=True):
    col1, col2, col3 = st.columns(3)

    with col1:
        # Cargar aeropuertos para los selectores
        try:
            aeropuertos = client.get_airports()
            opciones_ap = ["— Cualquier origen —"] + [
                f"{a['codigo']} — {a['ciudad']} ({a['pais']})"
                for a in aeropuertos
            ]
        except Exception:
            aeropuertos = []
            opciones_ap = ["— Cualquier origen —"]

        sel_origen = st.selectbox("Origen", opciones_ap, key="sb_origen")
        origen_cod = sel_origen[:3] if sel_origen != opciones_ap[0] else None

    with col2:
        # Destinos alcanzables desde el origen elegido
        if origen_cod:
            try:
                alcanzables = client.get_reachable(origen_cod)
                opciones_dst = ["— Cualquier destino —"] + [
                    f"{a['codigo']} — {a['ciudad']} ({a['pais']})"
                    for a in alcanzables
                ]
            except Exception:
                opciones_dst = opciones_ap
        else:
            opciones_dst = opciones_ap.copy()
            opciones_dst[0] = "— Cualquier destino —"

        sel_destino = st.selectbox("Destino", opciones_dst, key="sb_destino")
        destino_cod = sel_destino[:3] if sel_destino != opciones_dst[0] else None

    with col3:
        fecha = st.date_input("Fecha", value=None, key="di_fecha")
        fecha_str = fecha.strftime("%Y-%m-%d") if fecha else None

# ─────────────────────────────────────────
# RUTA SUGERIDA POR DIJKSTRA
# ─────────────────────────────────────────
if origen_cod and destino_cod:
    try:
        ruta = client.get_shortest_route(origen_cod, destino_cod)
        if ruta:
            if ruta["es_directo"]:
                st.info(f"✈ Ruta directa: **{origen_cod} → {destino_cod}** "
                        f"({ruta['distancia_total_km']:,} km)")
            else:
                escalas = " → ".join(ruta["path"])
                st.info(
                    f"🛑 No hay vuelo directo. "
                    f"Ruta sugerida: **{escalas}** "
                    f"({ruta['distancia_total_km']:,} km · "
                    f"{ruta['num_escalas']} escala(s))"
                )
        else:
            st.warning(f"No existe ruta entre {origen_cod} y {destino_cod}.")
    except Exception:
        pass   # silenciar error si la ruta falla

# ─────────────────────────────────────────
# RESULTADOS
# ─────────────────────────────────────────
st.subheader("Vuelos disponibles")

try:
    vuelos = client.search_flights(
        origen  = origen_cod,
        destino = destino_cod,
        fecha   = fecha_str,
    )
except Exception as e:
    st.error(f"Error al consultar vuelos: {e}")
    st.stop()

if not vuelos:
    st.info("No se encontraron vuelos con los filtros seleccionados.")
    st.stop()

st.caption(f"{len(vuelos)} vuelo(s) encontrado(s)")

# ─────────────────────────────────────────
# TARJETAS DE VUELOS
# ─────────────────────────────────────────
for vuelo in vuelos:
    try:
        tiempos = flight_times(vuelo)
    except Exception:
        tiempos = {
            "salida_local":  vuelo["hora_salida"],
            "salida_utc":    "--",
            "llegada_local": vuelo["hora_llegada"],
            "llegada_utc":   "--",
        }

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 3, 3, 1.5])

        with c1:
            st.markdown(f"### {vuelo['vuelo_id']}")
            st.caption(vuelo.get("aeronave", ""))

        with c2:
            st.markdown(
                f"**{vuelo['origen']}** {vuelo.get('ciudad_origen','')}\n\n"
                f"Salida: `{tiempos['salida_local']}` → `{tiempos['salida_utc']}`"
            )

        with c3:
            st.markdown(
                f"**{vuelo['destino']}** {vuelo.get('ciudad_destino','')}\n\n"
                f"Llegada: `{tiempos['llegada_local']}` → `{tiempos['llegada_utc']}`"
            )

        with c4:
            st.markdown(f"📅 `{vuelo['fecha']}`")
            if st.button("Seleccionar", key=f"sel_{vuelo['vuelo_id']}",
                         use_container_width=True, type="primary"):
                st.session_state.vuelo = vuelo
                st.switch_page("pages/2_mapa_asientos.py")
