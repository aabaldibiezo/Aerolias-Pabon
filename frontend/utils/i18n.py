# =============================================
# AEROLÍNEAS RAFAEL PABON
# utils/i18n.py — Internacionalización (ES / EN)
#
# Uso:
#   from utils.i18n import t, set_lang, get_lang
#   st.session_state.lang = "en"   # o "es"
#   label = t("search_flight")
# =============================================

import streamlit as st

TRANSLATIONS: dict[str, dict[str, str]] = {

    # ── Navegación / general ──
    "app_title":            {"es": "Aerolíneas Rafael Pabón", "en": "Rafael Pabón Airlines"},
    "app_subtitle":         {"es": "Sistema distribuido de reservas · 3 nodos · Relojes Vectoriales",
                             "en": "Distributed reservation system · 3 nodes · Vector Clocks"},
    "lang_selector":        {"es": "Idioma", "en": "Language"},
    "select_region":        {"es": "Seleccione su región de conexión",
                             "en": "Select your connection region"},
    "region_caption":       {"es": "Cada región conecta a un nodo diferente del sistema distribuido.",
                             "en": "Each region connects to a different node of the distributed system."},
    "check_connection":     {"es": "Verificar conexión", "en": "Check connection"},
    "connected":            {"es": "Conectado", "en": "Connected"},
    "clock":                {"es": "Reloj", "en": "Clock"},
    "seats_in_refund":      {"es": "asiento(s) en devolución pendiente",
                             "en": "seat(s) pending refund"},
    "no_connection":        {"es": "Sin conexión al nodo", "en": "No connection to node"},
    "system_status":        {"es": "Estado del sistema distribuido",
                             "en": "Distributed system status"},
    "online":               {"es": "Online", "en": "Online"},
    "offline":              {"es": "Offline", "en": "Offline"},
    "what_to_do":           {"es": "¿Qué desea hacer?", "en": "What would you like to do?"},
    "footer":               {"es": "Sistema distribuido · Relojes Vectoriales · Dijkstra · SQL Server × 2 + MongoDB × 1 · Docker Compose",
                             "en": "Distributed system · Vector Clocks · Dijkstra · SQL Server × 2 + MongoDB × 1 · Docker Compose"},

    # ── Búsqueda de vuelos ──
    "search_flight":        {"es": "Buscar vuelo", "en": "Search flight"},
    "search_caption":       {"es": "Busca vuelos por origen, destino y fecha",
                             "en": "Search flights by origin, destination and date"},
    "origin":               {"es": "Origen (IATA)", "en": "Origin (IATA)"},
    "destination":          {"es": "Destino (IATA)", "en": "Destination (IATA)"},
    "date":                 {"es": "Fecha", "en": "Date"},
    "search":               {"es": "Buscar", "en": "Search"},
    "results":              {"es": "Resultados", "en": "Results"},
    "no_flights":           {"es": "No se encontraron vuelos", "en": "No flights found"},
    "flight":               {"es": "Vuelo", "en": "Flight"},
    "departure":            {"es": "Salida", "en": "Departure"},
    "arrival":              {"es": "Llegada", "en": "Arrival"},
    "aircraft":             {"es": "Aeronave", "en": "Aircraft"},
    "capacity":             {"es": "Capacidad", "en": "Capacity"},
    "select_flight":        {"es": "Seleccionar vuelo", "en": "Select flight"},

    # ── Mapa de asientos ──
    "seat_map":             {"es": "Mapa de asientos", "en": "Seat map"},
    "seat_map_caption":     {"es": "Selecciona un vuelo primero", "en": "Select a flight first"},
    "seat":                 {"es": "Asiento", "en": "Seat"},
    "class":                {"es": "Clase", "en": "Class"},
    "state":                {"es": "Estado", "en": "State"},
    "passport":             {"es": "Pasaporte", "en": "Passport"},
    "name":                 {"es": "Nombre", "en": "Name"},
    "email":                {"es": "Email", "en": "Email"},
    "reason":               {"es": "Motivo", "en": "Reason"},
    "reserve":              {"es": "Reservar", "en": "Reserve"},
    "sell":                 {"es": "Vender", "en": "Sell"},
    "return":               {"es": "Devolver", "en": "Return"},
    "price":                {"es": "Precio", "en": "Price"},
    "free":                 {"es": "Libre", "en": "Free"},
    "reserved":             {"es": "Reservado", "en": "Reserved"},
    "sold":                 {"es": "Vendido", "en": "Sold"},
    "returned":             {"es": "En devolución", "en": "Returned"},

    # ── Boarding pass ──
    "boarding_pass":        {"es": "Boarding Pass", "en": "Boarding Pass"},
    "boarding_caption":     {"es": "Ver tu boarding pass", "en": "View your boarding pass"},
    "download_pdf":         {"es": "Descargar PDF", "en": "Download PDF"},
    "flight_id":            {"es": "ID Vuelo", "en": "Flight ID"},
    "seat_number":          {"es": "Asiento", "en": "Seat"},

    # ── Dashboards ──
    "dashboard_flight":     {"es": "Dashboard por Vuelo", "en": "Flight Dashboard"},
    "dashboard_global":     {"es": "Dashboard Global", "en": "Global Dashboard"},
    "occupancy":            {"es": "Ocupación", "en": "Occupancy"},
    "revenue":              {"es": "Ingresos", "en": "Revenue"},
    "total_flights":        {"es": "Vuelos totales", "en": "Total flights"},
    "total_seats":          {"es": "Asientos totales", "en": "Total seats"},
    "by_state":             {"es": "Por estado", "en": "By state"},
    "by_class":             {"es": "Por clase", "en": "By class"},
    "primera":              {"es": "Primera Clase", "en": "First Class"},
    "business":             {"es": "Business", "en": "Business"},
    "economica":            {"es": "Económica", "en": "Economy"},
    "load_dashboard":       {"es": "Cargar dashboard", "en": "Load dashboard"},
    "select_flight_id":     {"es": "ID del vuelo", "en": "Flight ID"},

    # ── Nodos / regiones ──
    "nodo1_label":          {"es": "🌍  Nodo 1 — Europa / Frankfurt  (SQL Server)",
                             "en": "🌍  Node 1 — Europe / Frankfurt  (SQL Server)"},
    "nodo2_label":          {"es": "🌏  Nodo 2 — Asia / Tokio  (SQL Server)",
                             "en": "🌏  Node 2 — Asia / Tokyo  (SQL Server)"},
    "nodo3_label":          {"es": "🌎  Nodo 3 — Sudamérica / La Paz  (MongoDB)",
                             "en": "🌎  Node 3 — South America / La Paz  (MongoDB)"},
    "node":                 {"es": "Nodo", "en": "Node"},
    "engine":               {"es": "Motor", "en": "Engine"},
    "url":                  {"es": "URL", "en": "URL"},
}


def get_lang() -> str:
    """Retorna el idioma actual de la sesión ('es' por defecto)."""
    return st.session_state.get("lang", "es")


def set_lang(lang: str) -> None:
    """Establece el idioma de la sesión."""
    if lang in ("es", "en"):
        st.session_state.lang = lang


def t(key: str, lang: str | None = None) -> str:
    """
    Retorna la traducción para `key` en el idioma activo (o `lang` si se especifica).
    Si la clave no existe, retorna la clave misma.
    """
    lang = lang or get_lang()
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(lang, entry.get("es", key))
