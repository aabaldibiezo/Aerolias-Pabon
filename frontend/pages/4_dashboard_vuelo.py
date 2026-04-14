# =============================================
# AEROLÍNEAS RAFAEL PABON
# pages/4_dashboard_vuelo.py — Dashboard por vuelo
# =============================================

import streamlit as st
import httpx

from utils.i18n import t

st.set_page_config(
    page_title = "Dashboard Vuelo — ARLP",
    page_icon  = "📊",
    layout     = "wide",
)

# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────
st.markdown(f"""
<div style="background:linear-gradient(135deg,#1B3A6B,#2E6DB4);
            padding:20px 28px;border-radius:10px;margin-bottom:20px;">
  <h2 style="color:white;margin:0;">📊 {t("dashboard_flight")}</h2>
  <p style="color:#CBD5E1;margin:4px 0 0 0;font-size:0.9rem;">
      {t("occupancy")} · {t("revenue")} · {t("by_state")} · {t("by_class")}
  </p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# SELECTOR DE NODO
# ─────────────────────────────────────────
node_url = st.session_state.get("node_url", "http://localhost:8001")
node_id  = st.session_state.get("node_id", 1)
st.caption(f"{t('node')} {node_id}  |  `{node_url}`")

# ─────────────────────────────────────────
# INPUT
# ─────────────────────────────────────────
col_input, col_btn = st.columns([3, 1])

with col_input:
    vuelo_id = st.text_input(
        t("select_flight_id"),
        value = st.session_state.get("vuelo", {}).get("vuelo_id", ""),
        placeholder = "Ej: RP001",
    ).upper()

with col_btn:
    st.write("")
    buscar = st.button(t("load_dashboard"), use_container_width=True, type="primary")

# ─────────────────────────────────────────
# CARGA Y VISUALIZACIÓN
# ─────────────────────────────────────────
if buscar and vuelo_id:
    with st.spinner(f"Cargando estadísticas de {vuelo_id}…"):
        try:
            # Datos del vuelo
            r_vuelo = httpx.get(f"{node_url}/flights/{vuelo_id}", timeout=8)
            r_stats = httpx.get(f"{node_url}/flights/{vuelo_id}/stats", timeout=8)

            if r_vuelo.status_code == 404 or r_stats.status_code == 404:
                st.error(f"Vuelo '{vuelo_id}' no encontrado en este nodo.")
                st.stop()

            vuelo = r_vuelo.json()
            stats = r_stats.json()

        except Exception as exc:
            st.error(f"Error conectando al nodo: {exc}")
            st.stop()

    # ── Encabezado del vuelo ──
    st.markdown(f"""
<div style="background:#f0f4f8;border-radius:8px;padding:14px 20px;margin-bottom:16px;
            border-left:4px solid #1B3A6B;">
  <b style="font-size:1.1rem;">{vuelo_id}</b> &nbsp;·&nbsp;
  <b>{vuelo.get("origen","?")} → {vuelo.get("destino","?")}</b> &nbsp;·&nbsp;
  {vuelo.get("fecha","?")} &nbsp;·&nbsp;
  {vuelo.get("hora_salida","??")} – {vuelo.get("hora_llegada","??")} &nbsp;·&nbsp;
  {vuelo.get("aeronave","?")}
  <br><small style="color:#64748b;">
    {vuelo.get("ciudad_origen","?")} → {vuelo.get("ciudad_destino","?")}
  </small>
</div>
""", unsafe_allow_html=True)

    # ── KPIs ──
    total    = stats.get("total_asientos", 0)
    vendidos = stats.get("por_estado", {}).get("Venta", 0)
    ingresos = stats.get("ingresos_usd", 0)
    ocup_pct = stats.get("ocupacion_pct", 0)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric(t("total_seats"),  total)
    k2.metric(t("sold"),         vendidos)
    k3.metric(t("occupancy"),    f"{ocup_pct}%")
    k4.metric(t("revenue"),      f"USD {ingresos:,.2f}")

    st.divider()
    c_state, c_class = st.columns(2)

    # ── Distribución por estado ──
    with c_state:
        st.markdown(f"**{t('by_state')}**")
        por_estado = stats.get("por_estado", {})
        COLOR_ESTADO = {
            "Libre":      "#94a3b8",
            "Reserva":    "#f59e0b",
            "Venta":      "#22c55e",
            "Devolucion": "#ef4444",
        }
        for estado, cantidad in sorted(por_estado.items(), key=lambda x: -x[1]):
            pct = cantidad / total * 100 if total else 0
            color = COLOR_ESTADO.get(estado, "#888")
            st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
  <div style="width:12px;height:12px;border-radius:50%;background:{color};flex-shrink:0;"></div>
  <div style="flex:1;">
    <div style="display:flex;justify-content:space-between;font-size:0.85rem;">
      <b>{estado}</b><span>{cantidad} ({pct:.1f}%)</span>
    </div>
    <div style="height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;">
      <div style="width:{pct:.1f}%;height:100%;background:{color};"></div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Distribución por clase ──
    with c_class:
        st.markdown(f"**{t('by_class')}**")
        por_clase = stats.get("por_clase", {})
        COLOR_CLASE = {
            "primera":  "#8b5cf6",
            "business": "#3b82f6",
            "economica": "#06b6d4",
        }
        LABEL_CLASE = {"primera": t("primera"), "business": t("business"), "economica": t("economica")}
        for clase, cantidad in [("primera", por_clase.get("primera", 0)),
                                  ("business", por_clase.get("business", 0)),
                                  ("economica", por_clase.get("economica", 0))]:
            if cantidad == 0:
                continue
            pct = cantidad / total * 100 if total else 0
            color = COLOR_CLASE.get(clase, "#888")
            label = LABEL_CLASE.get(clase, clase)
            st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
  <div style="width:12px;height:12px;border-radius:50%;background:{color};flex-shrink:0;"></div>
  <div style="flex:1;">
    <div style="display:flex;justify-content:space-between;font-size:0.85rem;">
      <b>{label}</b><span>{cantidad} ({pct:.1f}%)</span>
    </div>
    <div style="height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;">
      <div style="width:{pct:.1f}%;height:100%;background:{color};"></div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

elif buscar:
    st.warning("Ingrese un ID de vuelo válido.")

# ─────────────────────────────────────────
# DOWNLOAD BOARDING PASS
# ─────────────────────────────────────────
if vuelo_id and not buscar:
    with st.expander(f"🎫 {t('boarding_pass')} — {t('download_pdf')}"):
        asiento_num = st.text_input(t("seat_number"), placeholder="Ej: 12A").upper()
        if st.button(t("download_pdf")) and asiento_num:
            try:
                r = httpx.get(
                    f"{node_url}/boarding-pass/pdf",
                    params={"vuelo_id": vuelo_id, "asiento": asiento_num},
                    timeout=15,
                )
                if r.status_code == 200:
                    st.download_button(
                        label    = f"⬇ boarding_{vuelo_id}_{asiento_num}.pdf",
                        data     = r.content,
                        file_name = f"boarding_{vuelo_id}_{asiento_num}.pdf",
                        mime     = "application/pdf",
                    )
                else:
                    detail = r.json().get("detail", r.text)
                    st.error(f"Error: {detail}")
            except Exception as exc:
                st.error(str(exc))
