# =============================================
# AEROLÍNEAS RAFAEL PABON
# pages/2_mapa_asientos.py — Mapa interactivo del avión
# =============================================

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from utils.node_client import NodeClient
from utils.seat_renderer import resumen_disponibilidad
from utils.timezone_helper import flight_times

st.set_page_config(page_title="Asientos — ARLP", page_icon="💺", layout="wide")

# ─────────────────────────────────────────
# GUARDS
# ─────────────────────────────────────────
if "node_url" not in st.session_state:
    st.warning("Selecciona tu región primero.")
    st.page_link("streamlit_app.py", label="Inicio", icon="🏠")
    st.stop()

if "vuelo" not in st.session_state or not st.session_state.vuelo:
    st.warning("Selecciona un vuelo primero.")
    st.page_link("pages/1_buscar_vuelo.py", label="Buscar vuelo", icon="🔍")
    st.stop()

# ─────────────────────────────────────────
# CSS — botones de asiento compactos y coloreados
# ─────────────────────────────────────────
st.markdown("""
<style>
/* Botones de asiento: compactos */
div[data-testid="stColumn"] div[data-testid="stButton"] button {
    padding: 2px 1px !important;
    font-size: 0.58rem !important;
    min-height: 2.1rem !important;
    line-height: 1.15 !important;
    border-radius: 5px !important;
}
/* Panel derecho: info del asiento */
.seat-card {
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 14px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# ESTADO DE SESIÓN
# ─────────────────────────────────────────
if "seat_selected" not in st.session_state:
    st.session_state.seat_selected = None
if "motivos" not in st.session_state:
    st.session_state.motivos = {}   # {"{vuelo_id}:{seat}": motivo_str}

client = NodeClient(st.session_state.node_url)
vuelo  = st.session_state.vuelo

# ─────────────────────────────────────────
# HEADER DEL VUELO
# ─────────────────────────────────────────
try:
    tiempos = flight_times(vuelo)
except Exception:
    tiempos = {"salida_local": vuelo["hora_salida"], "salida_utc": "--",
               "llegada_local": vuelo["hora_llegada"], "llegada_utc": "--"}

st.markdown(f"""
<div style="background:linear-gradient(135deg,#1B3A6B,#2E6DB4);
            padding:14px 20px; border-radius:10px; margin-bottom:12px; color:white;">
  <div style="font-size:1.3rem; font-weight:bold;">
      ✈ {vuelo['vuelo_id']} &nbsp;|&nbsp;
      {vuelo['origen']} → {vuelo['destino']}
  </div>
  <div style="font-size:.85rem; margin-top:4px; color:#CBD5E1;">
      {vuelo.get('ciudad_origen','')} → {vuelo.get('ciudad_destino','')}
      &nbsp;|&nbsp;
      Salida: <b>{tiempos['salida_local']}</b> ({tiempos['salida_utc']})
      &nbsp;|&nbsp;
      Llegada: <b>{tiempos['llegada_local']}</b> ({tiempos['llegada_utc']})
      &nbsp;|&nbsp; {vuelo.get('aeronave','')} &nbsp;|&nbsp; {vuelo['fecha']}
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# CARGAR ASIENTOS
# ─────────────────────────────────────────
try:
    asientos = client.get_seats(vuelo["vuelo_id"])
except Exception as e:
    st.error(f"Error al cargar asientos: {e}")
    st.stop()

seats_dict = {a["numero_asiento"]: a for a in asientos}

# Métricas resumen
res = resumen_disponibilidad(asientos)
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.metric("🟢 Libres",     res.get("Libre",     0))
mc2.metric("🟡 Reservados", res.get("Reserva",   0))
mc3.metric("🔴 Vendidos",   res.get("Venta",     0))
mc4.metric("⚫ Devolución",  res.get("Devolucion",0))
mc5.metric("✈ Total",       len(asientos))

# ─────────────────────────────────────────
# LAYOUT PRINCIPAL
# ─────────────────────────────────────────
col_mapa, col_panel = st.columns([3, 2])

# ═══════════════════════════════════════
# COLUMNA IZQUIERDA — MAPA INTERACTIVO
# ═══════════════════════════════════════
with col_mapa:

    hdr1, hdr2 = st.columns([5, 1])
    hdr1.subheader("Mapa del avión — haz clic en un asiento")
    with hdr2:
        if st.button("🔄 Actualizar", use_container_width=True):
            st.session_state.seat_selected = None
            st.rerun()

    # Leyenda
    leg = st.columns(5)
    leg[0].markdown("🟢 **Libre**")
    leg[1].markdown("🟡 **Reserva**")
    leg[2].markdown("🔴 **Venta**")
    leg[3].markdown("⚫ **Devolución**")
    leg[4].markdown("**▶** Seleccionado")

    ESTADO_EMOJI = {
        "Libre":      "🟢",
        "Reserva":    "🟡",
        "Venta":      "🔴",
        "Devolucion": "⚫",
    }
    selected = st.session_state.seat_selected

    def _seat_btn(fila: int, letra: str):
        """Renderiza un botón de asiento en la columna actual."""
        seat_id = f"{fila}{letra}"
        seat    = seats_dict.get(seat_id)
        if seat is None:
            st.empty()
            return
        emoji    = ESTADO_EMOJI.get(seat["estado"], "🟢")
        is_sel   = seat_id == selected
        # El marcador ▶ indica el asiento actualmente seleccionado
        label    = f"{'▶' if is_sel else emoji}\n{seat_id}"
        btn_type = "primary" if is_sel else "secondary"
        if st.button(label, key=f"s_{seat_id}",
                     use_container_width=True, type=btn_type):
            st.session_state.seat_selected = seat_id
            st.rerun()

    # ── Primera Clase (filas 1-3, columnas A-D) ──────────────────────
    st.markdown("---")
    st.caption("✦ PRIMERA CLASE — Filas 1 a 3")
    for fila in range(1, 4):
        cols = st.columns([0.55, 1, 1, 1, 1, 0.5, 0.5])
        cols[0].caption(f"**{fila}**")
        for i, letra in enumerate(["A", "B", "C", "D"]):
            with cols[i + 1]:
                _seat_btn(fila, letra)

    # ── Business (filas 4-9, columnas A-F) ───────────────────────────
    st.markdown("---")
    st.caption("◆ BUSINESS — Filas 4 a 9")
    for fila in range(4, 10):
        cols = st.columns([0.55, 1, 1, 1, 1, 1, 1])
        cols[0].caption(f"**{fila}**")
        for i, letra in enumerate(["A", "B", "C", "D", "E", "F"]):
            with cols[i + 1]:
                _seat_btn(fila, letra)

    # ── Económica (filas 10-30, columnas A-F) ────────────────────────
    st.markdown("---")
    st.caption("● ECONÓMICA — Filas 10 a 30")
    for fila in range(10, 31):
        cols = st.columns([0.55, 1, 1, 1, 1, 1, 1])
        cols[0].caption(f"**{fila}**")
        for i, letra in enumerate(["A", "B", "C", "D", "E", "F"]):
            with cols[i + 1]:
                _seat_btn(fila, letra)


# ═══════════════════════════════════════
# COLUMNA DERECHA — PANEL DEL ASIENTO
# ═══════════════════════════════════════
with col_panel:

    if not selected:
        st.markdown("""
        <div style="background:#F0F4FF; border:1px solid #CBD5E1;
                    border-radius:10px; padding:20px; text-align:center;
                    margin-top:60px; color:#64748B;">
            <div style="font-size:2rem;">💺</div>
            <b>Ningún asiento seleccionado</b><br>
            <span style="font-size:.85rem;">Haz clic en cualquier asiento del mapa</span>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    asiento_data = seats_dict.get(selected)
    if not asiento_data:
        st.error(f"Asiento {selected} no encontrado.")
        st.stop()

    estado = asiento_data["estado"]
    clase  = asiento_data["clase"].title()
    precio = asiento_data["precio"]

    COLOR_MAP = {
        "Libre":      "#4CAF50",
        "Reserva":    "#FFC107",
        "Venta":      "#EF5350",
        "Devolucion": "#9E9E9E",
    }
    LABEL_MAP = {
        "Libre":      "Libre",
        "Reserva":    "Reservado",
        "Venta":      "Vendido",
        "Devolucion": "En Devolución",
    }
    color = COLOR_MAP.get(estado, "#ccc")
    label = LABEL_MAP.get(estado, estado)

    # ── Tarjeta de estado del asiento ────────────────────────────────
    st.markdown(f"""
    <div style="background:{color}1A; border-left:5px solid {color};
                padding:14px 16px; border-radius:8px; margin-bottom:16px;">
      <div style="font-size:1.5rem; font-weight:bold; color:{color};">
          Asiento {selected}
      </div>
      <div style="font-size:.9rem; color:#444; margin-top:4px;">
          Clase: <b>{clase}</b> &nbsp;·&nbsp;
          Precio: <b>USD {precio:,.2f}</b> &nbsp;·&nbsp;
          Estado: <b style="color:{color};">{label}</b>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────
    # Función auxiliar para ejecutar operaciones
    # ─────────────────────────────────────────
    def _hacer_operacion(accion: str, pasaporte: str = None,
                         nombre: str = None, email: str = None,
                         motivo: str = None):
        vid = vuelo["vuelo_id"]
        num = selected
        try:
            if accion == "reservar":
                result = client.reservar(vid, num, pasaporte, nombre, email)
            elif accion == "vender":
                result = client.vender(vid, num, pasaporte, nombre, email)
                # Guardar boarding pass
                st.session_state.boarding_pass = {
                    "vuelo":    vuelo,
                    "asiento":  asiento_data | {"numero_asiento": num,
                                                "estado": "Venta"},
                    "pasajero": {"pasaporte": pasaporte, "nombre": nombre,
                                 "email": email},
                    "tiempos":  tiempos,
                }
            elif accion == "devolver":
                result = client.devolver(vid, num, motivo)
                if motivo:
                    st.session_state.motivos[f"{vid}:{num}"] = motivo

            st.success(f"✅ {result.get('mensaje', 'Operación exitosa')}")
            st.session_state.seat_selected = None
            # Limpiar inputs de pasajero
            for k in ["inp_pasaporte", "inp_nombre", "inp_email", "inp_motivo"]:
                st.session_state.pop(k, None)
            st.rerun()
        except Exception as exc:
            st.error(f"Error: {exc}")

    # ══════════════════════════════════════════
    # PANELES POR ESTADO
    # ══════════════════════════════════════════

    # ── LIBRE: formulario de venta / reserva ─────────────────────────
    if estado == "Libre":
        st.markdown("### 🎫 Formulario de venta")

        pasaporte = st.text_input(
            "Número de pasaporte", key="inp_pasaporte",
            max_chars=20, placeholder="US1234567"
        ).upper().strip()

        nombre_auto = ""
        if pasaporte and len(pasaporte) >= 5:
            try:
                pax = client.get_passenger(pasaporte)
                if pax:
                    nombre_auto = pax["nombre"]
                    st.success(f"✅ Pasajero encontrado: **{nombre_auto}**")
            except Exception:
                pass

        nombre = st.text_input(
            "Nombre completo", value=nombre_auto,
            key="inp_nombre", placeholder="James Wilson"
        ).strip()
        email = st.text_input(
            "Email (opcional)", key="inp_email",
            placeholder="pasajero@email.com"
        ).strip() or None

        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("📋 Reservar", use_container_width=True, type="secondary"):
                if not pasaporte or not nombre:
                    st.error("Pasaporte y nombre son obligatorios.")
                else:
                    _hacer_operacion("reservar", pasaporte, nombre, email)
        with bc2:
            if st.button("✈ Comprar", use_container_width=True, type="primary"):
                if not pasaporte or not nombre:
                    st.error("Pasaporte y nombre son obligatorios.")
                else:
                    _hacer_operacion("vender", pasaporte, nombre, email)

    # ── RESERVA: info pasajero + confirmar / devolver ─────────────────
    elif estado == "Reserva":
        pasaporte_actual = asiento_data.get("pasaporte_pasajero") or "—"

        # Buscar nombre del pasajero
        nombre_actual = "—"
        email_actual  = "—"
        if pasaporte_actual and pasaporte_actual != "—":
            try:
                pax = client.get_passenger(pasaporte_actual)
                if pax:
                    nombre_actual = pax["nombre"]
                    email_actual  = pax.get("email") or "—"
            except Exception:
                pass

        st.markdown("### 👤 Pasajero con reserva")
        st.markdown(f"""
        <div style="background:#FFC10715; border:1px solid #FFC107;
                    padding:12px 14px; border-radius:8px; margin-bottom:14px;
                    font-size:.9rem;">
            <b>Pasaporte:</b> {pasaporte_actual}<br>
            <b>Nombre:</b> {nombre_actual}<br>
            <b>Email:</b> {email_actual}
        </div>
        """, unsafe_allow_html=True)

        tab_venta, tab_devolver = st.tabs(["✈ Confirmar venta", "↩ Devolver asiento"])

        with tab_venta:
            st.markdown("Confirmar la compra definitiva del asiento para este pasajero.")
            if st.button("Confirmar compra", type="primary", use_container_width=True,
                         key="btn_confirmar"):
                _hacer_operacion("vender",
                                 pasaporte=pasaporte_actual,
                                 nombre=nombre_actual)

        with tab_devolver:
            motivo_dev = st.text_area(
                "Motivo de devolución",
                key="inp_motivo",
                placeholder="Ej: El pasajero canceló el viaje, cambio de fecha, error en la reserva...",
                max_chars=500,
                height=100,
            )
            if st.button("Devolver asiento", type="secondary", use_container_width=True,
                         key="btn_devolver"):
                _hacer_operacion("devolver",
                                 pasaporte=pasaporte_actual,
                                 motivo=motivo_dev.strip() or None)

    # ── VENTA: descripción del pasajero ──────────────────────────────
    elif estado == "Venta":
        pasaporte_venta = asiento_data.get("pasaporte_pasajero") or "—"

        nombre_venta = "—"
        email_venta  = "—"
        if pasaporte_venta and pasaporte_venta != "—":
            try:
                pax = client.get_passenger(pasaporte_venta)
                if pax:
                    nombre_venta = pax["nombre"]
                    email_venta  = pax.get("email") or "—"
            except Exception:
                pass

        st.markdown("### 🧾 Descripción del pasajero")
        st.markdown(f"""
        <div style="background:#EF535015; border:1px solid #EF5350;
                    padding:14px 16px; border-radius:8px; font-size:.9rem;">
            <div style="font-size:1rem; font-weight:bold; color:#EF5350; margin-bottom:10px;">
                ✈ Asiento vendido
            </div>
            <table style="width:100%; border-collapse:collapse;">
                <tr>
                    <td style="color:#888; padding:4px 0; width:40%;">Pasaporte</td>
                    <td><b>{pasaporte_venta}</b></td>
                </tr>
                <tr>
                    <td style="color:#888; padding:4px 0;">Nombre</td>
                    <td><b>{nombre_venta}</b></td>
                </tr>
                <tr>
                    <td style="color:#888; padding:4px 0;">Email</td>
                    <td>{email_venta}</td>
                </tr>
                <tr>
                    <td style="color:#888; padding:4px 0;">Clase</td>
                    <td><b>{clase}</b></td>
                </tr>
                <tr>
                    <td style="color:#888; padding:4px 0;">Precio pagado</td>
                    <td><b>USD {precio:,.2f}</b></td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("")
        if st.session_state.get("boarding_pass"):
            st.page_link("pages/3_boarding_pass.py",
                         label="Ver Boarding Pass", icon="🎫")

    # ── DEVOLUCIÓN: motivo y estado del proceso ───────────────────────
    elif estado == "Devolucion":
        pasaporte_dev = asiento_data.get("pasaporte_pasajero") or "—"
        clave_motivo  = f"{vuelo['vuelo_id']}:{selected}"
        motivo_guardado = st.session_state.motivos.get(clave_motivo, "")

        motivo_html = (
            f'<tr><td style="color:#888; padding:4px 0; width:40%;">Motivo</td>'
            f'<td><b>{motivo_guardado}</b></td></tr>'
            if motivo_guardado else ""
        )

        st.markdown("### ⏳ En proceso de devolución")
        st.markdown(f"""
        <div style="background:#9E9E9E15; border:1px solid #9E9E9E;
                    padding:14px 16px; border-radius:8px; font-size:.9rem;">
            <table style="width:100%; border-collapse:collapse;">
                <tr>
                    <td style="color:#888; padding:4px 0; width:40%;">Pasajero</td>
                    <td><b>{pasaporte_dev}</b></td>
                </tr>
                {motivo_html}
            </table>
            <div style="margin-top:10px; padding:8px; background:#FFF3CD;
                        border-radius:6px; font-size:.82rem; color:#856404;">
                ⏱ Este asiento se liberará automáticamente en ~5 minutos.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Si no hay motivo guardado, permitir agregar uno ahora
        if not motivo_guardado:
            st.markdown("")
            st.caption("¿Quieres agregar una nota sobre esta devolución?")
            nota = st.text_area("Nota (opcional)", key="inp_motivo",
                                placeholder="Ej: Cancelación voluntaria del pasajero",
                                max_chars=500, height=80)
            if st.button("Guardar nota", type="secondary"):
                if nota.strip():
                    st.session_state.motivos[clave_motivo] = nota.strip()
                    st.rerun()
