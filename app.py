# ======================================================================================
# PUSAT INFORMASI GEMPA BUMI - Versi 7.1 (Refactored & Stabil)
# Dibuat oleh: Adam Dorman (Mahasiswa S1 Sistem Informasi UPNVJ)
# Fitur: single-dashboard stats, shakemap overlay, heatmap, dark/light tiles,
# microinteractions (toast), safe filters, auto-reset, modern containers & tabs.
# ======================================================================================

import streamlit as st
import pandas as pd
import requests
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import st_folium
from datetime import datetime, timezone, timedelta
import locale
import streamlit.components.v1 as components

# ---------------------------------------------------------------------
# Konfigurasi & Konstanta
# ---------------------------------------------------------------------
st.set_page_config(page_title="Pusat Informasi Gempa Indonesia", page_icon="🌋", layout="wide")
try:
    locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
except locale.Error:
    st.sidebar.warning("Lokal 'id_ID' tidak ditemukan.")

BMKG_API_BASE_URL = "https://data.bmkg.go.id/DataMKG/TEWS/"
DATA_SOURCES = {
    "Gempa Dirasakan (Lengkap)": "gempadirasakan.json",
    "Gempa Terbaru M 5.0+": "gempaterkini.json",
    "Gempa Real-time (Otomatis)": "autogempa.json"
}
APP_VERSION = "7.1"

# ---------------------------------------------------------------------
# Fungsi Bantu (Helper Functions)
# ---------------------------------------------------------------------
def get_color_from_magnitude(magnitude):
    try:
        m = float(magnitude)
        if m < 4.0: return 'green'
        if m < 6.0: return 'orange'
        return 'red'
    except (ValueError, TypeError):
        return 'gray'

def small_toast_js(message):
    escaped_message = message.replace("'", "\\'").replace("\n", "\\n")
    components.html(f"""
        <div id="toast-root" style="position:fixed; top:1rem; right:1rem; z-index:99999;"></div>
        <script>
        (function() {{
            const root = document.getElementById('toast-root');
            if (!root) return;
            const toast = document.createElement('div');
            toast.innerText = '{escaped_message}';
            toast.style = "background:rgba(220,38,38,0.9);color:white;padding:12px 18px;border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,0.25);font-family:sans-serif;opacity:0;transform:translateY(-10px);transition:all 350ms;";
            root.appendChild(toast);
            requestAnimationFrame(()=>{{ toast.style.opacity=1; toast.style.transform='translateY(0)'; }});
            setTimeout(()=>{{ toast.style.opacity=0; toast.style.transform='translateY(-10px)'; setTimeout(()=>toast.remove(), 350); }}, 6500);
        }})();
        </script>
    """, height=0)

def create_stat_cards_html(stats: dict):
    cards_html = """
    <style>
      .dash-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(180px,1fr)); gap:12px; margin-bottom:10px; }
      .card { background: rgba(30, 41, 59, 0.5); padding:16px; border-radius:12px; border: 1px solid rgba(255, 255, 255, 0.1); color:#fff; font-family:sans-serif; }
      .card .label { font-size:0.85rem; color:#cbd5e1; }
      .card .value { font-size:1.35rem; font-weight:700; margin-top:6px; }
    </style>
    <div class="dash-grid">
    """
    for label, value in stats.items():
        cards_html += f'<div class="card"><div class="label">{label}</div><div class="value">{value}</div></div>'
    cards_html += "</div>"
    return cards_html

@st.cache_data(ttl=60)
def get_data_gempa(file_name):
    url = f"{BMKG_API_BASE_URL}{file_name}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        gempa_data_raw = data.get('Infogempa', {}).get('gempa', [])
        df = pd.DataFrame([gempa_data_raw] if isinstance(gempa_data_raw, dict) else gempa_data_raw)
        if df.empty: return pd.DataFrame()

        # PERBAIKAN: Proses data dengan lebih aman
        df['DateTime'] = pd.to_datetime(df.get('DateTime'), errors='coerce')
        if 'Coordinates' in df.columns:
            coords = df['Coordinates'].str.split(',', expand=True)
            df['Latitude'] = pd.to_numeric(coords[0], errors='coerce')
            df['Longitude'] = pd.to_numeric(coords[1], errors='coerce')
        
        df['Magnitude'] = pd.to_numeric(df.get('Magnitude'), errors='coerce')
        if 'Kedalaman' in df.columns:
            df['KedalamanValue'] = pd.to_numeric(df['Kedalaman'].astype(str).str.extract(r'(\d+)')[0], errors='coerce')

        if 'Shakemap' in df.columns:
            df['ShakemapURL'] = df['Shakemap'].apply(lambda x: x if isinstance(x, str) and x.strip() else None)
        
        df.dropna(subset=['DateTime', 'Latitude', 'Longitude', 'Magnitude'], inplace=True)
        return df
    except Exception as e:
        st.sidebar.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# ---------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------
with st.sidebar:
    st.title("👨‍💻 Tentang Author")
    st.image("adam_dorman_profile.jpg", use_container_width=True, caption="Adam Dorman")
    st.markdown("[LinkedIn](https://www.linkedin.com/in/adamdorman68/) | [GitHub](https://github.com/adamdorman468-collab)")
    st.markdown("---")
    st.header("Kontrol Aplikasi")
    
    selected_data_name = st.selectbox("Pilih Sumber Data", list(DATA_SOURCES.keys()))
    selected_file_name = DATA_SOURCES[selected_data_name]

    if 'last_data_source' not in st.session_state or st.session_state.last_data_source != selected_file_name:
        st.session_state.last_data_source = selected_file_name
        st.session_state.pop('mag_filter', None)
        st.session_state.pop('depth_filter', None)
        if st.button("Tampilkan Data Baru"):
            st.rerun()

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun() # PERBAIKAN: Ganti st.experimental_rerun()
    
    df_filters = get_data_gempa(selected_file_name)

    # PERBAIKAN: Logika filter yang lebih aman dan rapi
    if not df_filters.empty:
        min_mag, max_mag = float(df_filters['Magnitude'].min()), float(df_filters['Magnitude'].max())
        st.session_state.mag_filter = st.slider("Filter Magnitudo", min_mag, max_mag, st.session_state.get('mag_filter', (min_mag, max_mag)), 0.1)
        
        if 'KedalamanValue' in df_filters.columns and df_filters['KedalamanValue'].notna().any():
            min_d, max_d = int(df_filters['KedalamanValue'].min()), int(df_filters['KedalamanValue'].max())
            st.session_state.depth_filter = st.slider("Filter Kedalaman (km)", min_d, max_d, st.session_state.get('depth_filter', (min_d, max_d)))
        else:
            st.session_state.depth_filter = (0, 700)
    else:
        st.session_state.mag_filter = (0.0, 10.0)
        st.session_state.depth_filter = (0, 700)

    # PERBAIKAN: Tambahkan kembali kontrol sorting
    sort_by = st.selectbox("Urutkan Data", ["Waktu Terbaru", "Magnitudo Terkuat", "Paling Dangkal"])
    
    st.markdown("---")
    st.header("Opsi Peta")
    tile_mode = st.selectbox("Tema Peta", ["Light", "Dark"])
    use_clustering = st.checkbox("Gunakan Clustering", value=True)
    show_heatmap = st.checkbox("Tampilkan Heatmap", value=False) # PERBAIKAN: Default False
    show_shakemap = st.checkbox("Overlay Shakemap", value=False) # PERBAIKAN: Default False
    
    st.markdown("---")
    alert_threshold = st.number_input("Alert jika M ≥", 0.0, 10.0, 6.0, 0.1, "%.1f")
    st.info(f"Versi Aplikasi: **{APP_VERSION}**")

# ---------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------
st.markdown(f"## 🌋 Pusat Informasi Gempa Indonesia")
st.caption(f"Sumber: API Publik BMKG • Menampilkan: **{selected_data_name}**")

df_gempa = get_data_gempa(selected_file_name)

if df_gempa.empty:
    st.error("Gagal memuat data gempa. Coba refresh atau pilih sumber lain.")
else:
    df_filtered = df_gempa[
        (df_gempa['Magnitude'].between(*st.session_state.mag_filter)) &
        (df_gempa.get('KedalamanValue', pd.Series(0)).between(*st.session_state.depth_filter))
    ].copy()

    # PERBAIKAN: Logika sorting yang terhubung ke UI
    if sort_by == "Magnitudo Terkuat":
        df_filtered.sort_values(by='Magnitude', ascending=False, inplace=True)
    elif sort_by == "Paling Dangkal" and 'KedalamanValue' in df_filtered.columns:
        df_filtered.sort_values(by='KedalamanValue', ascending=True, inplace=True)
    else: # Waktu Terbaru
        df_filtered.sort_values(by='DateTime', ascending=False, inplace=True)

    if df_filtered.empty:
        st.warning("Tidak ada gempa yang sesuai dengan kriteria filter Anda.")
    else:
        # Tampilkan statistik
        stats = {
            "Total Gempa (Filter)": len(df_filtered),
            "Magnitudo Tertinggi": f"{df_filtered['Magnitude'].max():.1f} M",
            "Kedalaman Terdangkal": f"{int(df_filtered['KedalamanValue'].min())} km" if 'KedalamanValue' in df_filtered.columns and df_filtered['KedalamanValue'].notna().any() else "N/A",
            "Gempa Terbaru": df_filtered.iloc[0]['DateTime'].strftime('%H:%M:%S WIB')
        }
        st.markdown(create_stat_cards_html(stats), unsafe_allow_html=True)

        if df_filtered['Magnitude'].max() >= alert_threshold:
            top_quake = df_filtered.iloc[0]
            alert_msg = f"ALERT: Gempa M {top_quake['Magnitude']:.1f} di {top_quake['Wilayah']}"
            small_toast_js(alert_msg)

        # Tabs untuk Peta dan Tabel
        tab1, tab2, tab3 = st.tabs(["📍 Peta Interaktif", "📑 Tabel Data", "🔎 Detail Terbaru"])

        with tab1: # Peta
            latest_quake = df_filtered.iloc[0]
            map_center = [latest_quake['Latitude'], latest_quake['Longitude']]
            
            tile_layer = "CartoDB dark_matter" if tile_mode == "Dark" else "CartoDB positron"
            m = folium.Map(location=map_center, zoom_start=5, tiles=tile_layer, attr="Stamen Terrain")
            
            # REFAKTOR: Logika layer yang lebih bersih
            # 1. Layer Marker (Cluster atau Normal)
            if use_clustering:
                marker_cluster = MarkerCluster().add_to(m)
                marker_target = marker_cluster
            else:
                marker_target = m

            for _, row in df_filtered.iterrows():
                popup_html = f"<b>{row['Wilayah']}</b><br>M: {row['Magnitude']}<br>Kedalaman: {row['Kedalaman']}"
                folium.Marker(
                    location=[row['Latitude'], row['Longitude']],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"M{row['Magnitude']} - {row['Wilayah']}",
                    icon=folium.Icon(color=get_color_from_magnitude(row['Magnitude']), icon='info-sign')
                ).add_to(marker_target)

            # 2. Layer Heatmap (opsional)
            if show_heatmap:
                heat_data = [[row['Latitude'], row['Longitude']] for _, row in df_filtered.iterrows()]
                HeatMap(heat_data).add_to(m)

            # 3. Layer Shakemap (opsional)
            if show_shakemap and 'ShakemapURL' in df_filtered.columns:
                shakemap_quake = df_filtered[df_filtered['ShakemapURL'].notna()].iloc[0] if not df_filtered[df_filtered['ShakemapURL'].notna()].empty else None
                if shakemap_quake is not None:
                    lat, lon, mag = shakemap_quake['Latitude'], shakemap_quake['Longitude'], shakemap_quake['Magnitude']
                    # PERBAIKAN: Rumus bounds yang lebih simpel
                    delta = 0.15 * (1.5 ** mag) / 2 
                    bounds = [[lat - delta, lon - delta], [lat + delta, lon + delta]]
                    folium.raster_layers.ImageOverlay(
                        name="Shakemap BMKG", image=shakemap_quake['ShakemapURL'],
                        bounds=bounds, opacity=0.6, interactive=True
                    ).add_to(m)
            
            st_folium(m, width="100%", height=600)

        with tab2: # Tabel
            st.dataframe(df_filtered[['DateTime', 'Magnitude', 'Kedalaman', 'Wilayah']], use_container_width=True)

        with tab3: # Detail
            st.subheader(f"Gempa Terbaru (Filter): {df_filtered.iloc[0]['Wilayah']}")
            latest = df_filtered.iloc[0]
            st.metric("Waktu Kejadian", latest['DateTime'].strftime('%d %b %Y, %H:%M:%S WIB'))
            c1, c2 = st.columns(2)
            c1.metric("Magnitudo", f"{latest['Magnitude']} M")
            c2.metric("Kedalaman", latest['Kedalaman'])
            if 'Dirasakan' in latest and pd.notna(latest['Dirasakan']):
                st.markdown("**Dirasakan:**")
                st.info(latest['Dirasakan'])
            if 'ShakemapURL' in latest and pd.notna(latest['ShakemapURL']):
                st.image(latest['ShakemapURL'])
