# =============================================
# AEROLÍNEAS RAFAEL PABON
# streamlit_app.py — Página principal
# Selector de nodo (región), idioma y estado del sistema
# =============================================

import os
import streamlit as st
import httpx

from utils.i18n import t, set_lang, get_lang

st.set_page_config(
    page_title = "Aerolíneas Rafael Pabón",
    page_icon  = "✈",
    layout     = "wide",
)

# ─────────────────────────────────────────
# SELECTOR DE IDIOMA (barra lateral)
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    idioma = st.selectbox(
        t("lang_selector"),
        options=["Español", "English"],
        index=0 if get_lang() == "es" else 1,
        key="lang_select_widget",
    )
    set_lang("es" if idioma == "Español" else "en")

    st.divider()
    st.caption("Aerolíneas Rafael Pabón v1.0")

# ─────────────────────────────────────────
# URLs de los nodos (desde variables de entorno)
# ─────────────────────────────────────────
NODOS = {
    t("nodo1_label"): {
        "url":    os.environ.get("NODO1_URL", "http://localhost:8001"),
        "id":     1,
        "region": "Europa / Frankfurt",
        "engine": "SQL Server",
        "icon":   "🌍",
        "color":  "#1A3A5C",
    },
    t("nodo2_label"): {
        "url":    os.environ.get("NODO2_URL", "http://localhost:8002"),
        "id":     2,
        "region": "Asia / Tokio",
        "engine": "SQL Server",
        "icon":   "🌏",
        "color":  "#1A5C3A",
    },
    t("nodo3_label"): {
        "url":    os.environ.get("NODO3_URL", "http://localhost:8003"),
        "id":     3,
        "region": "Sudamérica / La Paz",
        "engine": "MongoDB",
        "icon":   "🌎",
        "color":  "#5C1A3A",
    },
}

# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────
st.markdown(f"""
<div style="background:linear-gradient(135deg,#1B3A6B,#2E6DB4);
            padding:28px 32px; border-radius:12px; margin-bottom:24px;">
  <h1 style="color:white;margin:0;font-size:2.2rem;">✈ {t("app_title")}</h1>
  <p style="color:#CBD5E1;margin:6px 0 0 0;font-size:1rem;">
      {t("app_subtitle")}
  </p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# SELECTOR DE NODO / REGIÓN
# ─────────────────────────────────────────
st.subheader(t("select_region"))
st.caption(t("region_caption"))

opcion = st.radio(
    label     = t("select_region"),
    options   = list(NODOS.keys()),
    index     = st.session_state.get("nodo_opcion_idx", 0),
    horizontal = True,
    label_visibility = "collapsed",
)

nodo = NODOS[opcion]

# Persistir en session_state
st.session_state.node_url  = nodo["url"]
st.session_state.node_id   = nodo["id"]
st.session_state.nodo_opcion_idx = list(NODOS.keys()).index(opcion)

# ─────────────────────────────────────────
# INFO + VERIFICAR CONEXIÓN
# ─────────────────────────────────────────
col_info, col_clock = st.columns([2, 1])

with col_info:
    st.markdown(
        f"**{t('node')}:** {nodo['id']}  |  "
        f"**{t('engine')}:** {nodo['engine']}  |  "
        f"**{t('url')}:** `{nodo['url']}`  |  "
        f"**{t('region_caption').split('.')[0]}:** {nodo['region']}"
    )

with col_clock:
    if st.button(t("check_connection"), use_container_width=True):
        try:
            resp = httpx.get(f"{nodo['url']}/sync/status", timeout=5)
            data = resp.json()
            st.success(f"{t('connected')} — {t('clock')}: {data['reloj_vectorial']}")
            if data["timers_activos"] > 0:
                st.info(f"{data['timers_activos']} {t('seats_in_refund')}")
        except Exception as e:
            st.error(f"{t('no_connection')}: {e}")

st.divider()

# ─────────────────────────────────────────
# ESTADO DE TODOS LOS NODOS
# ─────────────────────────────────────────
st.subheader(t("system_status"))

cols = st.columns(3)
for i, (label, info) in enumerate(NODOS.items()):
    with cols[i]:
        # Tarjeta con borde de color por región
        try:
            resp = httpx.get(f"{info['url']}/", timeout=3)
            data = resp.json()
            st.markdown(f"""
<div style="border:2px solid {info['color']};border-radius:8px;padding:12px;
            background:#f8fafc;">
  <b style="color:{info['color']}">{info['icon']} {t('node')} {info['id']} — {info['region']}</b><br>
  <span style="color:#16a34a;font-size:0.9rem;">● {t('online')}</span><br>
  <small>{t('engine')}: {info['engine']}</small>
</div>
""", unsafe_allow_html=True)
        except Exception:
            st.markdown(f"""
<div style="border:2px solid #ef4444;border-radius:8px;padding:12px;
            background:#fef2f2;">
  <b style="color:#991b1b">{info['icon']} {t('node')} {info['id']} — {info['region']}</b><br>
  <span style="color:#dc2626;font-size:0.9rem;">● {t('offline')}</span><br>
  <small>{t('engine')}: {info['engine']}</small>
</div>
""", unsafe_allow_html=True)

st.divider()

# ─────────────────────────────────────────
# NAVEGACIÓN
# ─────────────────────────────────────────
st.subheader(t("what_to_do"))
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.page_link("pages/1_buscar_vuelo.py", label=t("search_flight"), icon="🔍")
    st.caption(t("search_caption"))

with c2:
    if st.session_state.get("vuelo"):
        vuelo = st.session_state.vuelo
        st.page_link("pages/2_mapa_asientos.py", label=t("seat_map"), icon="💺")
        st.caption(f"**{vuelo['vuelo_id']}** {vuelo['origen']}→{vuelo['destino']}")
    else:
        st.markdown(f"💺 **{t('seat_map')}**")
        st.caption(t("seat_map_caption"))

with c3:
    if st.session_state.get("boarding_pass"):
        st.page_link("pages/3_boarding_pass.py", label=t("boarding_pass"), icon="🎫")
        st.caption(t("boarding_caption"))
    else:
        st.markdown(f"🎫 **{t('boarding_pass')}**")
        st.caption(t("boarding_caption"))

with c4:
    st.page_link("pages/4_dashboard_vuelo.py", label=t("dashboard_flight"), icon="📊")
    st.caption(t("occupancy") + " / " + t("revenue"))

with c5:
    st.page_link("pages/5_dashboard_global.py", label=t("dashboard_global"), icon="🌐")
    st.caption(t("total_flights") + " · " + t("total_seats"))

# ─────────────────────────────────────────
# PIE DE PÁGINA
# ─────────────────────────────────────────
st.markdown("---")
st.caption(t("footer"))
