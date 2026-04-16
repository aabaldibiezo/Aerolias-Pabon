"""
Aerolíneas Rafael Pabón - Página Principal
Estilo Qatar Airways - BUSCADOR DENTRO DEL CARD CON WIDGETS
"""
import streamlit as st
from datetime import datetime, timedelta
import requests
import os

# ------------------- CONFIGURACIÓN DE PÁGINA -------------------
st.set_page_config(
    page_title="Aerolíneas Rafael Pabón",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ------------------- CSS PERSONALIZADO -------------------
st.markdown("""
<style>
    /* Ocultar elementos por defecto de Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Fuente */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Header superior */
    .top-header {
        background-color: #6B0F1E;
        padding: 0.8rem 2rem;
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 1000;
    }
    
    .logo {
        font-size: 1.5rem;
        font-weight: bold;
        letter-spacing: 2px;
    }
    
    .logo small {
        font-size: 0.7rem;
        font-weight: normal;
    }
    
    .nav-links {
        display: flex;
        gap: 2rem;
    }
    
    .nav-links a {
        color: white;
        text-decoration: none;
        font-weight: 500;
        font-size: 0.9rem;
    }
    
    .user-area {
        display: flex;
        gap: 1rem;
        align-items: center;
        font-size: 0.9rem;
    }
    
    .login-btn {
        background: transparent;
        border: 1px solid white;
        padding: 0.3rem 1rem;
        border-radius: 20px;
    }
    
    /* Hero banner */
    .hero-banner {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 120px 0 80px 0;
        margin-top: 60px;
    }
    
    /* Tarjeta de búsqueda */
    .search-card {
        background: white;
        border-radius: 24px;
        padding: 2rem;
        margin: -60px 2rem 0 2rem;
        box-shadow: 0 20px 40px rgba(0,0,0,0.15);
        position: relative;
        z-index: 10;
    }
    
    .field-label {
        font-size: 0.7rem;
        font-weight: 700;
        color: #6B0F1E;
        margin-bottom: 0.5rem;
        letter-spacing: 0.5px;
    }
    
    /* Estilos para inputs de Streamlit dentro del card */
    .search-card .stTextInput input, 
    .search-card .stDateInput input,
    .search-card .stSelectbox select {
        border-radius: 8px !important;
        border: 1px solid #ddd !important;
        padding: 0.6rem !important;
    }
    
    /* Sección de destinos */
    .section-title {
        font-size: 1.8rem;
        font-weight: bold;
        margin: 3rem 2rem 0.5rem 2rem;
    }
    
    .section-subtitle {
        font-size: 1rem;
        color: #666;
        margin: 0 2rem 1.5rem 2rem;
    }
    
    .destinos-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.5rem;
        padding: 0 2rem;
    }
    
    .destino-card {
        background: white;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        transition: transform 0.2s;
        cursor: pointer;
    }
    
    .destino-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    
    .destino-img {
        height: 180px;
        background-size: cover;
        background-position: center;
    }
    
    .destino-info {
        padding: 1rem;
    }
    
    .destino-ciudad {
        font-weight: bold;
        font-size: 1.1rem;
    }
    
    .destino-fechas {
        font-size: 0.8rem;
        color: #666;
        margin: 0.5rem 0;
    }
    
    .destino-precio {
        color: #6B0F1E;
        font-weight: bold;
        font-size: 1.2rem;
    }
    
    /* Footer */
    .footer {
        background-color: #1a1a1a;
        color: white;
        padding: 2rem;
        margin-top: 3rem;
        text-align: center;
    }
    
    .footer-links {
        display: flex;
        justify-content: center;
        gap: 2rem;
        margin-bottom: 1rem;
        flex-wrap: wrap;
    }
    
    .footer-links a {
        color: white;
        text-decoration: none;
        font-size: 0.8rem;
    }
    
    /* Botón personalizado */
    .stButton button {
        background-color: #6B0F1E !important;
        color: white !important;
        border-radius: 40px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important;
        width: 100% !important;
    }
    
    @media (max-width: 768px) {
        .destinos-grid {
            grid-template-columns: 1fr;
        }
        .nav-links {
            display: none;
        }
        .search-card {
            margin: -20px 1rem 0 1rem;
            padding: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# ------------------- HEADER -------------------
st.markdown("""
<div class="top-header">
    <div class="logo">
        AEROLÍNEAS<br><small>RAFAEL PABÓN</small>
    </div>
    <div class="nav-links">
        <a href="#">Book a flight</a>
        <a href="#">Stopover / Packages</a>
        <a href="#">Manage / Check in</a>
        <a href="#">Flight status</a>
    </div>
    <div class="user-area">
        <span>🌐 EN</span>
        <span class="login-btn">Log in | Sign up</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ------------------- HERO BANNER -------------------
st.markdown('<div class="hero-banner"></div>', unsafe_allow_html=True)

# ------------------- TARJETA DE BÚSQUEDA -------------------
# Abrimos el card
st.markdown('<div class="search-card">', unsafe_allow_html=True)

# Estado para la pestaña activa
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Return"

# Pestañas
col_t1, col_t2, col_t3 = st.columns([1, 1, 1])

with col_t1:
    if st.button("✈️ Return", key="tab_return", use_container_width=True):
        st.session_state.active_tab = "Return"
        st.rerun()
    if st.session_state.active_tab == "Return":
        st.markdown('<div style="height:3px; background:#6B0F1E; margin-top:-10px; border-radius:3px;"></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="height:3px; margin-top:-10px;"></div>', unsafe_allow_html=True)

with col_t2:
    if st.button("🔄 One way", key="tab_oneway", use_container_width=True):
        st.session_state.active_tab = "One way"
        st.rerun()

with col_t3:
    if st.button("📍 Multi-city", key="tab_multicity", use_container_width=True):
        st.session_state.active_tab = "Multi-city"
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# Grid de búsqueda - 5 columnas
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown('<div class="field-label">FROM</div>', unsafe_allow_html=True)
    from_airport = st.text_input("", placeholder="City or airport", label_visibility="collapsed", key="from_input")

with col2:
    st.markdown('<div class="field-label">TO</div>', unsafe_allow_html=True)
    to_airport = st.text_input("", placeholder="City or airport", label_visibility="collapsed", key="to_input")

with col3:
    st.markdown('<div class="field-label">DEPARTURE</div>', unsafe_allow_html=True)
    depart_date = st.date_input("", datetime.now() + timedelta(days=30), label_visibility="collapsed", key="depart_date")

with col4:
    if st.session_state.active_tab == "Return":
        st.markdown('<div class="field-label">RETURN</div>', unsafe_allow_html=True)
        return_date = st.date_input("", datetime.now() + timedelta(days=37), label_visibility="collapsed", key="return_date")
    else:
        return_date = None
        st.markdown('<div class="field-label">&nbsp;</div>', unsafe_allow_html=True)
        st.empty()

with col5:
    st.markdown('<div class="field-label">PASSENGERS/CLASS</div>', unsafe_allow_html=True)
    passengers = st.selectbox("", ["1 Passenger", "2 Passengers", "3 Passengers", "4 Passengers"], label_visibility="collapsed", key="passengers")
    class_type = st.selectbox("", ["Economy", "Business", "First"], label_visibility="collapsed", key="class_type")

# Opciones adicionales
col_check, col_promo, col_btn = st.columns([1.2, 2, 1.2])

with col_check:
    use_avios = st.checkbox("Book using Avios")

with col_promo:
    promo = st.text_input("", placeholder="+ Add promo code", label_visibility="collapsed")

with col_btn:
    if st.button("🔍 Search flights", key="search_btn", use_container_width=True):
        if from_airport and to_airport:
            st.session_state.search_params = {
                "origin": from_airport.upper(),
                "destination": to_airport.upper(),
                "departure": depart_date.strftime("%Y-%m-%d"),
                "return": return_date.strftime("%Y-%m-%d") if return_date else None,
                "passengers": passengers,
                "class": class_type
            }
            st.switch_page("pages/1_buscar_vuelo.py")
        else:
            st.warning("Please enter origin and destination")

# Cerramos el card
st.markdown('</div>', unsafe_allow_html=True)

# ------------------- SECCIÓN DE DESTINOS -------------------
st.markdown('<div class="section-title">🌍 Places we think you\'ll love</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">From selected departure cities</div>', unsafe_allow_html=True)

destinos = [
    {"ciudad": "Paris", "codigo": "CDG", "fecha_ida": "27 May 2026", "fecha_vuelta": "02 Jun 2026", "precio": "USD 365", "img": "https://images.unsplash.com/photo-1502602898652-3b9b2934c6e3?w=400&h=180&fit=crop"},
    {"ciudad": "London", "codigo": "LHR", "fecha_ida": "15 Jun 2026", "fecha_vuelta": "20 Jun 2026", "precio": "USD 420", "img": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=400&h=180&fit=crop"},
    {"ciudad": "Tokyo", "codigo": "TYO", "fecha_ida": "10 Jul 2026", "fecha_vuelta": "25 Jul 2026", "precio": "USD 890", "img": "https://images.unsplash.com/photo-1536098561742-ca998e48cbcc?w=400&h=180&fit=crop"},
    {"ciudad": "New York", "codigo": "NYC", "fecha_ida": "05 Aug 2026", "fecha_vuelta": "12 Aug 2026", "precio": "USD 550", "img": "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=400&h=180&fit=crop"},
    {"ciudad": "Dubai", "codigo": "DXB", "fecha_ida": "20 Sep 2026", "fecha_vuelta": "28 Sep 2026", "precio": "USD 680", "img": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=400&h=180&fit=crop"},
    {"ciudad": "Sydney", "codigo": "SYD", "fecha_ida": "04 Jun 2026", "fecha_vuelta": "04 Jul 2026", "precio": "USD 890", "img": "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?w=400&h=180&fit=crop"},
]

cols = st.columns(3)
for idx, destino in enumerate(destinos):
    with cols[idx % 3]:
        st.markdown(f"""
        <div class="destino-card">
            <div class="destino-img" style="background-image: url('{destino['img']}');"></div>
            <div class="destino-info">
                <div class="destino-ciudad">{destino['ciudad']} ({destino['codigo']})</div>
                <div class="destino-fechas">{destino['fecha_ida']} - {destino['fecha_vuelta']}</div>
                <div class="destino-precio">{destino['precio']}</div>
                <div class="destino-clase">Economy</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ------------------- FOOTER -------------------
st.markdown("""
<div class="footer">
    <div class="footer-links">
        <a href="#">Download app</a>
        <a href="#">Follow us on X</a>
        <a href="#">Instagram</a>
        <a href="#">Facebook</a>
        <a href="#">Help Center</a>
    </div>
    <p>✈️ Aerolíneas Rafael Pabón | Sistema distribuido de reservas · 3 nodos · Relojes Vectoriales</p>
</div>
""", unsafe_allow_html=True)

# ------------------- SIDEBAR -------------------
with st.sidebar:
    st.markdown("### 🌍 Select your region")
    
    if os.path.exists('/.dockerenv'):
        node_urls = {
            "Europe (Frankfurt)": "http://nodo1:8001",
            "Asia (Tokyo)": "http://nodo2:8002",
            "South America (La Paz)": "http://nodo3:8003"
        }
    else:
        node_urls = {
            "Europe (Frankfurt)": "http://localhost:8001",
            "Asia (Tokyo)": "http://localhost:8002",
            "South America (La Paz)": "http://localhost:8003"
        }
    
    selected_region = st.radio("Connection region:", list(node_urls.keys()), index=0)
    
    st.session_state.node_url = node_urls[selected_region]
    st.session_state.node_id = selected_region[:10]
    
    st.markdown("---")
    st.markdown("### ℹ️ System Status")
    
    for region, url in node_urls.items():
        try:
            response = requests.get(f"{url}/flights", timeout=2)
            if response.status_code == 200:
                st.success(f"✅ {region}")
            else:
                st.warning(f"⚠️ {region}")
        except:
            st.error(f"❌ {region}")