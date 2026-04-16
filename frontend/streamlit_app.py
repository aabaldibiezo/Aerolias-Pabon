import streamlit as st
import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Aerolíneas Rafael Pabón | Qatar Style",
    page_icon="✈️",
    layout="wide"
)

# 2. ESTILOS CSS PERSONALIZADOS (LOOK & FEEL QATAR AIRWAYS)
def apply_custom_styles():
    st.markdown("""
        <style>
        /* Importar fuentes de lujo */
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@300;400;600&display=swap');

        /* Configuración global */
        .main { background-color: #f9f9f9; }
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

        /* Títulos Serif Estilo Qatar */
        h1, h2, h3, .qatar-title {
            font-family: 'Playfair Display', serif !important;
            color: #662046 !important;
        }

        /* Hero Section */
        .hero-container {
            position: relative;
            background-image: linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)), 
                              url('https://www.oneair.es/wp-content/uploads/2023/06/turbulencias-en-avion-todo-lo-que-necesitas-saber.jpeg?q=80&w=2069&auto=format&fit=crop');
            background-size: cover;
            background-position: center;
            height: 450px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            color: white;
            border-radius: 20px;
            margin-bottom: 20px;
        }

        /* Buscador Flotante */
        .search-widget {
            background-color: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            margin-top: -80px;
            position: relative;
            z-index: 10;
            border-bottom: 4px solid #662046;
        }

        /* Botones Personalizados */
        div.stButton > button {
            background-color: #662046 !important;
            color: white !important;
            border-radius: 5px !important;
            border: none !important;
            padding: 10px 25px !important;
            font-weight: 600 !important;
            width: 100%;
            transition: 0.3s;
        }
        div.stButton > button:hover {
            background-color: #4a1732 !important;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 32, 70, 0.3);
        }

        /* Tarjetas de Destino */
        .dest-card {
            border-radius: 15px;
            overflow: hidden;
            background: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            transition: 0.3s;
        }
        .dest-card:hover { transform: scale(1.02); }

        /* Tarjetas de Nodo */
        .node-card {
            background-color: #fff;
            padding: 20px;
            border-radius: 12px;
            border-left: 5px solid #662046;
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)

def main():
    apply_custom_styles()

    # --- HEADER ---
    col_logo, col_lang = st.columns([4, 1])
    with col_logo:
        st.markdown("<h2 style='margin:0; color:#662046;'>AEROLÍNEAS <b>RAFAEL PABÓN</b></h2>", unsafe_allow_html=True)
    with col_lang:
        st.selectbox("🌐 Idioma", ["Español", "English"], label_visibility="collapsed")

    # --- HERO SECTION ---
    st.markdown("""
        <div class="hero-container">
            <h1 style="color: white !important; font-size: 3.5rem; margin-bottom: 0;">Vaya más allá</h1>
            <p style="font-size: 1.4rem; font-weight: 300;">Experiencia premium en cada nodo de nuestra red.</p>
        </div>
    """, unsafe_allow_html=True)

    # --- BUSCADOR DE VUELOS (WIDGET FLOTANTE) ---
    with st.container():
        st.markdown('<div class="search-widget">', unsafe_allow_html=True)
        st.markdown("<h4 style='margin-top:0; color:#662046;'>Reserva tu próximo viaje</h4>", unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        with c1:
            st.selectbox("Desde", ["LAX - Los Ángeles", "FRA - Frankfurt", "LPB - La Paz", "TYO - Tokio", "MAD - Madrid"])
        with c2:
            st.selectbox("Hacia", ["DXB - Dubái", "PEK - Pekín", "AMS - Ámsterdam", "LON - Londres", "SAO - São Paulo"])
        with c3:
            st.date_input("Fecha de salida", datetime.date.today())
        with c4:
            st.write("<div style='height:28px;'></div>", unsafe_allow_html=True)
            if st.button("BUSCAR"):
                st.info("Redirigiendo al sistema de búsqueda...")
                # st.switch_page("pages/1_buscar_vuelo.py")
        st.markdown('</div>', unsafe_allow_html=True)

    st.write(" ")
    st.write(" ")

    # --- SECCIÓN: PLACES WE THINK YOU'LL LOVE ---
    st.markdown("<h3>Places we think you'll love</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666;'>Ofertas exclusivas seleccionadas para usted.</p>", unsafe_allow_html=True)
    
    d1, d2, d3 = st.columns(3)
    
    destinos = [
        {"nombre": "Dubái, EAU", "img": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?q=80&w=500", "tag": "LUJO", "precio": "850"},
        {"nombre": "Tokio, Japón", "img": "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?q=80&w=500", "tag": "POPULAR", "precio": "1,120"},
        {"nombre": "París, Francia", "img": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?q=80&w=500", "tag": "CULTURA", "precio": "740"}
    ]

    cols = [d1, d2, d3]
    for i, dest in enumerate(destinos):
        with cols[i]:
            st.markdown(f"""
                <div class="dest-card">
                    <img src="{dest['img']}" style="width:100%; height:200px; object-fit:cover;">
                    <div style="padding: 15px;">
                        <small style="color: #662046; font-weight: bold;">{dest['tag']}</small>
                        <h4 style="margin: 5px 0;">{dest['nombre']}</h4>
                        <p style="color: #555;">Desde <b>${dest['precio']} USD</b></p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"Explorar {dest['nombre'].split(',')[0]}", key=f"btn_{i}"):
                pass

    st.write(" ")
    st.write("---")

    # --- SECCIÓN: ESTADO DE NODOS ---
    st.markdown("<h3 style='text-align:center;'>Seleccione su Región de Acceso</h3>", unsafe_allow_html=True)
    
    n1, n2, n3 = st.columns(3)
    
    regiones = [
        {"id": 1, "nombre": "Europa", "ciudad": "Frankfurt", "db": "SQL Server", "emoji": "🇪🇺"},
        {"id": 2, "nombre": "Asia", "ciudad": "Tokio", "db": "SQL Server", "emoji": "🇯🇵"},
        {"id": 3, "nombre": "Sudamérica", "ciudad": "La Paz", "db": "MongoDB", "emoji": "🇧🇴"}
    ]

    node_cols = [n1, n2, n3]
    for i, reg in enumerate(regiones):
        with node_cols[i]:
            st.markdown(f"""
                <div class="node-card">
                    <span style="font-size: 30px;">{reg['emoji']}</span>
                    <h4>{reg['nombre']}</h4>
                    <p style="color: #28a745; font-size: 0.8rem;">● Nodo Operativo</p>
                    <p style="font-size: 0.85rem; color: #666;">{reg['ciudad']} | {reg['db']}</p>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"CONECTAR NODO {reg['id']}", key=f"node_{reg['id']}"):
                st.session_state['selected_node'] = reg['id']
                st.success(f"Conectado a {reg['ciudad']}")

    # --- FOOTER ---
    st.markdown("""
        <div style="text-align: center; padding: 40px; color: #999; font-size: 0.8rem; margin-top: 50px; border-top: 1px solid #eee;">
            © 2026 Aerolíneas Rafael Pabón. Inspirado en la excelencia. <br>
            Sistema Distribuido con Consistencia Eventual y Relojes de Lamport.
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()