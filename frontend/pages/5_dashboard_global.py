# =============================================
# AEROLÍNEAS RAFAEL PABON
# pages/5_dashboard_global.py — Dashboard global del nodo
# =============================================

import os
import streamlit as st
import httpx

from utils.i18n import t

st.set_page_config(
    page_title = "Dashboard Global — ARLP",
    page_icon  = "🌐",
    layout     = "wide",
)

# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────
st.markdown(f"""
<div style="background:linear-gradient(135deg,#1B3A6B,#2E6DB4);
            padding:20px 28px;border-radius:10px;margin-bottom:20px;">
  <h2 style="color:white;margin:0;">🌐 {t("dashboard_global")}</h2>
  <p style="color:#CBD5E1;margin:4px 0 0 0;font-size:0.9rem;">
      {t("total_flights")} · {t("total_seats")} · {t("occupancy")} · {t("revenue")}
  </p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# CONFIG DE NODOS
# ─────────────────────────────────────────
NODOS_INFO = {
    1: {
        "url":    os.environ.get("NODO1_URL", "http://localhost:8001"),
        "label":  t("nodo1_label"),
        "color":  "#1A3A5C",
        "engine": "SQL Server",
    },
    2: {
        "url":    os.environ.get("NODO2_URL", "http://localhost:8002"),
        "label":  t("nodo2_label"),
        "color":  "#1A5C3A",
        "engine": "SQL Server",
    },
    3: {
        "url":    os.environ.get("NODO3_URL", "http://localhost:8003"),
        "label":  t("nodo3_label"),
        "color":  "#5C1A3A",
        "engine": "MongoDB",
    },
}

COLORES_ESTADO = {
    "Libre":      "#94a3b8",
    "Reserva":    "#f59e0b",
    "Venta":      "#22c55e",
    "Devolucion": "#ef4444",
}
COLORES_CLASE = {
    "primera":   "#8b5cf6",
    "business":  "#3b82f6",
    "economica": "#06b6d4",
}
LABEL_CLASE = {}

def _get_label_clase() -> dict:
    return {
        "primera":   t("primera"),
        "business":  t("business"),
        "economica": t("economica"),
    }


# ─────────────────────────────────────────
# SELECTOR DE NODOS A MOSTRAR
# ─────────────────────────────────────────
st.markdown(f"**{t('system_status')}** — {t('load_dashboard')}")

col_check, col_btn = st.columns([3, 1])
with col_check:
    nodos_seleccionados = st.multiselect(
        label    = t("node"),
        options  = [1, 2, 3],
        default  = [1, 2, 3],
        format_func = lambda x: f"{t('node')} {x}",
    )
with col_btn:
    st.write("")
    cargar = st.button(t("load_dashboard"), use_container_width=True, type="primary")

# ─────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────
if cargar:
    st.session_state["global_dash_data"] = {}
    for nid in nodos_seleccionados:
        info = NODOS_INFO[nid]
        try:
            r = httpx.get(f"{info['url']}/flights/stats", timeout=10)
            if r.status_code == 200:
                st.session_state["global_dash_data"][nid] = {
                    "stats": r.json(),
                    "info":  info,
                    "ok":    True,
                }
            else:
                st.session_state["global_dash_data"][nid] = {"ok": False, "info": info}
        except Exception as exc:
            st.session_state["global_dash_data"][nid] = {
                "ok": False, "info": info, "error": str(exc)
            }

data = st.session_state.get("global_dash_data", {})

if not data:
    st.info(f"Presiona **{t('load_dashboard')}** para ver las estadísticas del sistema.")
    st.stop()

# ─────────────────────────────────────────
# VISTA POR NODO
# ─────────────────────────────────────────
label_clase = _get_label_clase()

for nid, entry in data.items():
    info = entry["info"]
    color = info["color"]

    if not entry["ok"]:
        st.markdown(f"""
<div style="border:2px solid #ef4444;border-radius:8px;padding:12px;margin-bottom:16px;
            background:#fef2f2;">
  ❌ <b style="color:#991b1b">{t('node')} {nid} — {info.get('label','')}</b><br>
  <small>{entry.get('error','Sin conexión')}</small>
</div>
""", unsafe_allow_html=True)
        continue

    stats = entry["stats"]
    total    = stats.get("total_asientos", 0)
    vuelos   = stats.get("total_vuelos", 0)
    vendidos = stats.get("por_estado", {}).get("Venta", 0)
    ingresos = stats.get("ingresos_usd", 0)
    ocup_pct = stats.get("ocupacion_pct", 0)

    st.markdown(f"""
<div style="border:2px solid {color};border-radius:8px;padding:14px 18px;
            margin-bottom:20px;background:#f8fafc;">
  <b style="color:{color};font-size:1.05rem;">{info.get('label','')}</b>
</div>
""", unsafe_allow_html=True)

    # KPIs
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(t("total_flights"),  vuelos)
    k2.metric(t("total_seats"),    total)
    k3.metric(t("sold"),           vendidos)
    k4.metric(t("occupancy"),      f"{ocup_pct}%")
    k5.metric(t("revenue"),        f"USD {ingresos:,.0f}")

    # Barras de estado + clase
    col_s, col_c = st.columns(2)

    with col_s:
        st.markdown(f"**{t('by_state')}**")
        for estado, cantidad in sorted(
            stats.get("por_estado", {}).items(), key=lambda x: -x[1]
        ):
            pct = cantidad / total * 100 if total else 0
            bcolor = COLORES_ESTADO.get(estado, "#888")
            st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;">
  <div style="width:10px;height:10px;border-radius:50%;background:{bcolor};flex-shrink:0;"></div>
  <div style="flex:1;">
    <div style="display:flex;justify-content:space-between;font-size:0.82rem;">
      <b>{estado}</b><span>{cantidad:,} ({pct:.1f}%)</span>
    </div>
    <div style="height:7px;background:#e2e8f0;border-radius:4px;overflow:hidden;">
      <div style="width:{pct:.1f}%;height:100%;background:{bcolor};"></div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    with col_c:
        st.markdown(f"**{t('by_class')}**")
        for clase in ("primera", "business", "economica"):
            cantidad = stats.get("por_clase", {}).get(clase, 0)
            if cantidad == 0:
                continue
            pct    = cantidad / total * 100 if total else 0
            bcolor = COLORES_CLASE.get(clase, "#888")
            label  = label_clase.get(clase, clase)
            st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;">
  <div style="width:10px;height:10px;border-radius:50%;background:{bcolor};flex-shrink:0;"></div>
  <div style="flex:1;">
    <div style="display:flex;justify-content:space-between;font-size:0.82rem;">
      <b>{label}</b><span>{cantidad:,} ({pct:.1f}%)</span>
    </div>
    <div style="height:7px;background:#e2e8f0;border-radius:4px;overflow:hidden;">
      <div style="width:{pct:.1f}%;height:100%;background:{bcolor};"></div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    st.divider()

# ─────────────────────────────────────────
# TOTALES CONSOLIDADOS (todos los nodos)
# ─────────────────────────────────────────
nodos_ok = {nid: e for nid, e in data.items() if e["ok"]}
if len(nodos_ok) > 1:
    st.markdown(f"### 📈 {t('total_flights')} — {t('system_status')}")

    total_vuelos   = sum(e["stats"].get("total_vuelos",   0) for e in nodos_ok.values())
    total_asientos = sum(e["stats"].get("total_asientos", 0) for e in nodos_ok.values())
    total_ventas   = sum(e["stats"].get("por_estado", {}).get("Venta", 0) for e in nodos_ok.values())
    total_ingresos = sum(e["stats"].get("ingresos_usd",   0) for e in nodos_ok.values())
    ocup_global    = round(total_ventas / total_asientos * 100, 1) if total_asientos else 0

    t1, t2, t3, t4, t5 = st.columns(5)
    t1.metric(f"Total {t('total_flights')}",  total_vuelos)
    t2.metric(f"Total {t('total_seats')}",    total_asientos)
    t3.metric(f"Total {t('sold')}",           total_ventas)
    t4.metric(f"{t('occupancy')} global",     f"{ocup_global}%")
    t5.metric(f"Total {t('revenue')}",        f"USD {total_ingresos:,.0f}")

st.markdown("---")
st.caption(t("footer"))
