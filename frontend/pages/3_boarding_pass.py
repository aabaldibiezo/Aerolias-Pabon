# =============================================
# AEROLÍNEAS RAFAEL PABON
# pages/3_boarding_pass.py — Boarding Pass
# =============================================

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

st.set_page_config(page_title="Boarding Pass — ARLP", page_icon="🎫", layout="centered")

# ─────────────────────────────────────────
# GUARDS
# ─────────────────────────────────────────
if not st.session_state.get("boarding_pass"):
    st.warning("No hay ningún boarding pass generado aún.")
    st.page_link("pages/1_buscar_vuelo.py", label="Buscar vuelo", icon="🔍")
    st.stop()

bp      = st.session_state.boarding_pass
vuelo   = bp["vuelo"]
asiento = bp["asiento"]
pasajero = bp["pasajero"]
tiempos  = bp["tiempos"]

# ─────────────────────────────────────────
# BARCODE SIMULADO
# ─────────────────────────────────────────
def fake_barcode(text: str) -> str:
    """Genera un 'código de barras' ASCII con el texto dado."""
    bars = ""
    for c in text:
        v = ord(c) % 7
        bars += "█" * (v + 2) + "▌" * (v % 3 + 1)
    return bars[:60]

barcode_text = f"{vuelo['vuelo_id']}-{asiento['numero_asiento']}-{pasajero['pasaporte']}"
barcode      = fake_barcode(barcode_text)

# ─────────────────────────────────────────
# CLASE FORMATEADA
# ─────────────────────────────────────────
CLASE_LABEL = {
    "primera":   "PRIMERA CLASE",
    "business":  "BUSINESS",
    "economica": "ECONÓMICA",
}
clase_label = CLASE_LABEL.get(asiento.get("clase", "economica"), "ECONÓMICA")

# ─────────────────────────────────────────
# BOARDING PASS HTML
# ─────────────────────────────────────────
boarding_html = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Courier+Prime&display=swap');
.bp-wrap {{
    max-width: 580px; margin: 0 auto;
    font-family: 'Courier Prime', 'Courier New', monospace;
}}
.bp-card {{
    background: white;
    border: 2px solid #1B3A6B;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(27,58,107,.18);
}}
.bp-header {{
    background: linear-gradient(135deg,#1B3A6B,#2E6DB4);
    color: white; padding: 18px 24px;
    display: flex; justify-content: space-between; align-items: center;
}}
.bp-header-title {{ font-size: 1.1rem; font-weight: bold; letter-spacing: 1px; }}
.bp-header-sub {{ font-size: .8rem; opacity: .8; margin-top: 2px; }}
.bp-logo {{ font-size: 2rem; }}
.bp-body {{ padding: 20px 24px; }}
.bp-row {{ display: flex; gap: 12px; margin-bottom: 14px; }}
.bp-field {{ flex: 1; }}
.bp-label {{
    font-size: 9px; letter-spacing: 1.5px; color: #888;
    text-transform: uppercase; margin-bottom: 2px;
}}
.bp-value {{ font-size: 1rem; font-weight: bold; color: #1A1A2E; }}
.bp-value-lg {{ font-size: 1.6rem; font-weight: bold; color: #1B3A6B; }}
.bp-divider {{
    border: none; border-top: 2px dashed #CBD5E1;
    margin: 14px 0;
}}
.bp-route {{
    display: flex; align-items: center; justify-content: center;
    gap: 16px; padding: 12px 0;
}}
.bp-iata {{
    font-size: 2.4rem; font-weight: bold; color: #1B3A6B;
    letter-spacing: 2px;
}}
.bp-arrow {{ font-size: 1.8rem; color: #2E6DB4; }}
.bp-barcode {{
    background: #f8f9fa; border-radius: 8px;
    padding: 12px 16px; margin-top: 10px;
    font-size: 10px; letter-spacing: -1px;
    color: #1A1A2E; word-break: break-all;
    text-align: center;
}}
.bp-barcode-text {{
    font-size: 9px; color: #888; margin-top: 4px;
    letter-spacing: 2px;
}}
.bp-clase-badge {{
    display: inline-block; background: #1B3A6B; color: white;
    padding: 3px 10px; border-radius: 20px; font-size: 10px;
    letter-spacing: 1px; font-weight: bold;
}}
</style>

<div class="bp-wrap">
<div class="bp-card">

  <div class="bp-header">
    <div>
      <div class="bp-header-title">AEROLÍNEAS RAFAEL PABON</div>
      <div class="bp-header-sub">BOARDING PASS · TARJETA DE EMBARQUE</div>
    </div>
    <div class="bp-logo">✈</div>
  </div>

  <div class="bp-body">

    <div class="bp-row">
      <div class="bp-field">
        <div class="bp-label">Nombre del pasajero</div>
        <div class="bp-value" style="font-size:1.2rem;">
            {pasajero['nombre'].upper()}
        </div>
      </div>
      <div class="bp-field">
        <div class="bp-label">Pasaporte</div>
        <div class="bp-value">{pasajero['pasaporte']}</div>
      </div>
    </div>

    <hr class="bp-divider">

    <div class="bp-route">
      <div style="text-align:center;">
        <div class="bp-iata">{vuelo['origen']}</div>
        <div style="font-size:.75rem;color:#888;">{vuelo.get('ciudad_origen','')}</div>
      </div>
      <div class="bp-arrow">→</div>
      <div style="text-align:center;">
        <div class="bp-iata">{vuelo['destino']}</div>
        <div style="font-size:.75rem;color:#888;">{vuelo.get('ciudad_destino','')}</div>
      </div>
    </div>

    <hr class="bp-divider">

    <div class="bp-row">
      <div class="bp-field">
        <div class="bp-label">Vuelo</div>
        <div class="bp-value-lg">{vuelo['vuelo_id']}</div>
      </div>
      <div class="bp-field">
        <div class="bp-label">Fecha</div>
        <div class="bp-value">{vuelo['fecha']}</div>
      </div>
      <div class="bp-field">
        <div class="bp-label">Asiento</div>
        <div class="bp-value-lg">{asiento['numero_asiento']}</div>
      </div>
    </div>

    <div class="bp-row">
      <div class="bp-field">
        <div class="bp-label">Salida (local)</div>
        <div class="bp-value">{tiempos['salida_local']}</div>
        <div style="font-size:10px;color:#888;">{tiempos['salida_utc']}</div>
      </div>
      <div class="bp-field">
        <div class="bp-label">Llegada (local)</div>
        <div class="bp-value">{tiempos['llegada_local']}</div>
        <div style="font-size:10px;color:#888;">{tiempos['llegada_utc']}</div>
      </div>
      <div class="bp-field">
        <div class="bp-label">Clase</div>
        <div style="margin-top:4px;">
            <span class="bp-clase-badge">{clase_label}</span>
        </div>
      </div>
    </div>

    <div class="bp-row">
      <div class="bp-field">
        <div class="bp-label">Aeronave</div>
        <div class="bp-value" style="font-size:.9rem;">
            {vuelo.get('aeronave','')}
        </div>
      </div>
      <div class="bp-field">
        <div class="bp-label">Precio pagado</div>
        <div class="bp-value">USD {asiento.get('precio', 0):,.2f}</div>
      </div>
    </div>

    <hr class="bp-divider">

    <div class="bp-barcode">
      {barcode}
      <div class="bp-barcode-text">{barcode_text.upper()}</div>
    </div>

  </div>
</div>
</div>
"""

st.title("🎫 Boarding Pass")
st.markdown(boarding_html, unsafe_allow_html=True)

st.markdown("")
col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/1_buscar_vuelo.py", label="Nueva búsqueda", icon="🔍")
with col2:
    st.page_link("pages/2_mapa_asientos.py", label="Volver al mapa", icon="💺")
