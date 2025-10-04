# ======================================================================================
# PUSAT INFORMASI GEMPA BUMI - Versi 8.1 (Clock & UI Tweak)
# Dibuat oleh: Adam Dorman (Mahasiswa S1 Sistem Informasi UPNVJ)
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
# Bagian 1: Konfigurasi & Konstanta
# ---------------------------------------------------------------------
st.set_page_config(page_title="Pusat Informasi Gempa Indonesia", page_icon="🌋", layout="wide")
try:
    locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
except locale.Error:
    pass

BMKG_API_BASE_URL = "https://data.bmkg.go.id/DataMKG/TEWS/"
DATA_SOURCES = {
    "Gempa Dirasakan (Lengkap)": "gempadirasakan.json",
    "Gempa Terbaru M 5.0+": "gempaterkini.json",
    "Gempa Real-time (Otomatis)": "autogempa.json"
}
APP_VERSION = "8.1"

# ---------------------------------------------------------------------
# Bagian 2: Fungsi Bantu
# ---------------------------------------------------------------------
def get_color_from_magnitude(magnitude):
    try:
        m = float(magnitude)
        if m < 4.0: return 'green'
        if m < 6.0: return 'orange'
        return 'red'
    except (ValueError, TypeError):
        return 'gray'

def display_realtime_clock():
    html_code = """
        <div id="clock-container" style="display: flex; justify-content: space-between; font-family: 'Segoe UI', 'Roboto', 'sans-serif';">
            <div style="text-align: center;">
                <span style="font-size: 1rem; color: #A0A0A0;">WIB</span>
                <h2 id="wib-time" style="margin: 0; color: #FFFFFF; font-size: 2.5rem; font-weight: 700;">--:--:--</h2>
            </div>
            <div style="text-align: center;">
                <span style="font-size: 1rem; color: #A0A0A0;">UTC</span>
                <h2 id="utc-time" style="margin: 0; color: #FFFFFF; font-size: 2.5rem; font-weight: 700;">--:--:--</h2>
            </div>
        </div>
        <script>
            function updateTime() {
                const wibTimeElement = document.getElementById('wib-time');
                const utcTimeElement = document.getElementById('utc-time');
                if (!wibTimeElement || !utcTimeElement) return;
                const wibDate = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Jakarta' }));
                const wibHours = String(wibDate.getHours()).padStart(2, '0');
                const wibMinutes = String(wibDate.getMinutes()).padStart(2, '0');
                const wibSeconds = String(wibDate.getSeconds()).padStart(2, '0');
                const utcDate = new Date();
                const utcHours = String(utcDate.getUTCHours()).padStart(2, '0');
                const utcMinutes = String(utcDate.getUTCMinutes()).padStart(2, '0');
                const utcSeconds = String(utcDate.getUTCSeconds()).padStart(2, '0');
                wibTimeElement.innerHTML = `${wibHours}:${wibMinutes}:${wibSeconds}`;
                utcTimeElement.innerHTML = `${utcHours}:${utcMinutes}:${utcSeconds}`;
            }
            setInterval(updateTime, 1000);
            updateTime();
        </script>
    """
    components.html(html_code, height=75)

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

        df['DateTime'] = pd.to_datetime(df.get('DateTime'), errors='coerce')
        if 'Coordinates' in df.columns:
            coords = df['Coordinates'].str.split(',', expand=True)
            df['Latitude'] = pd.to_numeric(coords.get(0), errors='coerce')
            df['Longitude'] = pd.to_numeric(coords.get(1), errors='coerce')
        
        df['Magnitude'] = pd.to_numeric(df.get('Magnitude'), errors='coerce')
        if 'Kedalaman' in df.columns:
            df['KedalamanValue'] = pd.to_numeric(df['Kedalaman'].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
        else:
            df['KedalamanValue'] = 0

        if 'Shakemap' in df.columns:
            df['ShakemapURL'] = df['Shakemap'].apply(lambda x: f"https://data.bmkg.go.id/DataMKG/TEWS/{x}" if isinstance(x, str) and x.endswith('.jpg') else None)
        
        df.dropna(subset=['DateTime', 'Latitude', 'Longitude', 'Magnitude'], inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

# ---------------------------------------------------------------------
# Bagian 3: Sidebar & Kontrol State
# ---------------------------------------------------------------------
with st.sidebar:
    st.title("👨‍💻 Tentang Author")
    st.image("adam_dorman_profile.jpg", use_column_width=True, caption="Adam Dorman")
    st.markdown("""
    - [LinkedIn](https://www.linkedin.com/in/adamdorman68/) 
    - [GitHub](https://github.com/adamdorman468-collab)
    - [Instagram](https://www.instagram.com/adam_abu_umar?igsh=OGQ5ZDc2ODk2ZA==)
    """)
    st.divider()
    st.title("⚙️ Kontrol & Pengaturan")
    
    selected_data_name = st.selectbox("Pilih Sumber Data:", list(DATA_SOURCES.keys()))
    selected_file_name = DATA_SOURCES[selected_data_name]

    if 'last_data_source' not in st.session_state or st.session_state.last_data_source != selected_file_name:
        st.session_state.last_data_source = selected_file_name
        keys_to_clear = ['mag_filter', 'depth_filter']
        for key in keys_to_clear:
            st.session_state.pop(key, None)
        st.rerun()

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    df_for_filters = get_data_gempa(selected_file_name)
    
    st.divider()
    sort_by = st.selectbox("Urutkan Data:", ("Waktu Terbaru", "Magnitudo Terkuat", "Paling Dangkal"))
    
    if not df_for_filters.empty:
        min_mag, max_mag = float(df_for_filters['Magnitude'].min()), float(df_for_filters['Magnitude'].max())
        if min_mag < max_mag:
            st.session_state.mag_filter = st.slider("Filter Magnitudo", min_mag, max_mag, st.session_state.get('mag_filter', (min_mag, max_mag)), 0.1)
        else:
            st.session_state.mag_filter = (min_mag, max_mag)

        if 'KedalamanValue' in df_for_filters.columns and df_for_filters['KedalamanValue'].notna().any():
            min_d, max_d = int(df_for_filters['KedalamanValue'].min()), int(df_for_filters['KedalamanValue'].max())
            if min_d < max_d:
                st.session_state.depth_filter = st.slider("Filter Kedalaman (km)", min_d, max_d, st.session_state.get('depth_filter', (min_d, max_d)))
            else:
                 st.session_state.depth_filter = (min_d, max_d)
        else:
            st.session_state.depth_filter = (0, 700)
    else: 
        st.slider("Filter Magnitudo", 0.0, 10.0, (0.0, 10.0), 0.1, disabled=True)
        st.slider("Filter Kedalaman (km)", 0, 700, (0, 700), disabled=True)

    if st.button("Reset Semua Filter", use_container_width=True):
        keys_to_clear = ['mag_filter', 'depth_filter']
        for key in keys_to_clear:
            st.session_state.pop(key, None)
        st.rerun()

    st.divider()
    st.markdown("#### Opsi Peta")
    use_clustering = st.checkbox("Kelompokkan gempa (clustering)", value=True)
    show_heatmap = st.checkbox("Tampilkan Heatmap", value=False)
    show_shakemap = st.checkbox("Tampilkan Shakemap BMKG", value=False)
    
    st.divider()
    st.markdown(f"**🌋 Versi Aplikasi: {APP_VERSION}**")

# ---------------------------------------------------------------------
# Bagian 4: Tampilan Utama
# ---------------------------------------------------------------------
header_col1, header_col2 = st.columns([2, 1])
with header_col1:
    st.title("🌋 Pusat Informasi Gempa Indonesia")
    st.caption(f"Menampilkan: **{selected_data_name}** | Sumber: [API Publik BMKG](https://data.bmkg.go.id/)")
with header_col2:
    display_realtime_clock() # Jam otomatis dikembalikan
st.divider()

df_gempa = get_data_gempa(selected_file_name)

if df_gempa.empty:
    st.error("Gagal memuat data dari BMKG atau tidak ada data saat ini. Silakan coba refresh.")
else:
    mag_filter_range = st.session_state.get('mag_filter', (df_gempa['Magnitude'].min(), df_gempa['Magnitude'].max()))
    depth_filter_range = st.session_state.get('depth_filter', (df_gempa['KedalamanValue'].min(), df_gempa['KedalamanValue'].max()))

    df_filtered = df_gempa[
        (df_gempa['Magnitude'].between(*mag_filter_range)) &
        (df_gempa['KedalamanValue'].between(*depth_filter_range))
    ].copy()

    if sort_by == "Magnitudo Terkuat": df_filtered.sort_values(by='Magnitude', ascending=False, inplace=True)
    elif sort_by == "Paling Dangkal": df_filtered.sort_values(by='KedalamanValue', ascending=True, inplace=True)
    else: df_filtered.sort_values(by='DateTime', ascending=False, inplace=True)

    if df_filtered.empty:
        st.warning("Tidak ada data gempa yang sesuai dengan kriteria filter Anda.")
    else:
        stat_cols = st.columns(4)
        stat_cols[0].metric("Total Gempa (Filter)", len(df_filtered))
        stat_cols[1].metric("Magnitudo Tertinggi", f"{df_filtered['Magnitude'].max():.1f} M")
        stat_cols[2].metric("Magnitudo Rata-rata", f"{df_filtered['Magnitude'].mean():.2f} M")
        stat_cols[3].metric("Kedalaman Terdangkal", f"{int(df_filtered['KedalamanValue'].min())} km")
        
        tab1, tab2, tab3 = st.tabs(["📍 Peta Interaktif", "📑 Tabel Data Rinci", "📈 Analisis Statistik"])

        with tab1:
            map_center = [df_filtered['Latitude'].mean(), df_filtered['Longitude'].mean()]
            m = folium.Map(location=map_center, zoom_start=5, tiles="CartoDB positron") # Tema peta di-set ke Light
            
            marker_group = folium.FeatureGroup(name="Gempa").add_to(m)
            heat_group = folium.FeatureGroup(name="Heatmap", show=False).add_to(m)
            shake_group = folium.FeatureGroup(name="Shakemap BMKG", show=False).add_to(m)
            
            marker_target = MarkerCluster().add_to(marker_group) if use_clustering else marker_group
            for _, row in df_filtered.iterrows():
                popup_html = f"<b>{row['Wilayah']}</b><br>M: {row['Magnitude']}<br>Kedalaman: {row.get('Kedalaman', 'N/A')}"
                folium.Marker(
                    location=[row['Latitude'], row['Longitude']],
                    popup=popup_html, tooltip=f"M{row['Magnitude']}",
                    icon=folium.Icon(color=get_color_from_magnitude(row['Magnitude']), icon='info-sign')
                ).add_to(marker_target)

            if show_heatmap:
                heat_data = [[row['Latitude'], row['Longitude']] for _, row in df_filtered.iterrows()]
                HeatMap(heat_data).add_to(heat_group)

            if show_shakemap and 'ShakemapURL' in df_filtered.columns:
                shakemap_quake = df_filtered.sort_values(by='Magnitude', ascending=False)[df_filtered['ShakemapURL'].notna()].iloc[0] if not df_filtered[df_filtered['ShakemapURL'].notna()].empty else None
                if shakemap_quake is not None:
                    lat, lon, mag = shakemap_quake['Latitude'], shakemap_quake['Longitude'], shakemap_quake['Magnitude']
                    delta = 0.1 * (1.8 ** mag) / 2 
                    bounds = [[lat - delta, lon - delta], [lat + delta, lon + delta]]
                    folium.raster_layers.ImageOverlay(image=shakemap_quake['ShakemapURL'], bounds=bounds, opacity=0.7).add_to(shake_group)
            
            folium.LayerControl().add_to(m)
            st_folium(m, width="100%", height=600, returned_objects=[])

        with tab2:
            st.dataframe(df_filtered[['DateTime', 'Magnitude', 'Kedalaman', 'Wilayah']], use_container_width=True)

        with tab3:
            st.subheader("Analisis Statistik Gempa (Hasil Filter)")
            c1, c2 = st.columns(2)
            c1.markdown("#### Distribusi Magnitudo")
            mag_counts = pd.cut(df_filtered['Magnitude'], bins=[0, 4, 6, 10], labels=["< 4.0", "4.0 - 5.9", "≥ 6.0"], right=False).value_counts().sort_index()
            st.bar_chart(mag_counts)
            
            c2.markdown("#### Distribusi Kedalaman (km)")
            depth_counts = pd.cut(df_filtered['KedalamanValue'], bins=[-1, 70, 300, 800], labels=["Dangkal (< 70)", "Menengah (70-300)", "Dalam (> 300)"]).value_counts().sort_index()
            st.bar_chart(depth_counts)
