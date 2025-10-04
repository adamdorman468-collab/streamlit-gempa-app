# ======================================================================================
# PUSAT INFORMASI GEMPA BUMI - Versi 10.0 (Definitif)
# Dibuat oleh: Adam Dorman (Mahasiswa S1 Sistem Informasi UPNVJ)
# Arsitektur: Container-based layout, centralized state management, modular functions.
# Fitur: Advanced filtering, global reset, interactive layer control, all features retained.
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
APP_VERSION = "10.0"

# ---------------------------------------------------------------------
# Bagian 2: Fungsi Bantu
# ---------------------------------------------------------------------
@st.cache_data(ttl=60)
def get_data_gempa(file_name: str) -> pd.DataFrame:
    """Mengambil dan memproses data gempa dari API BMKG dengan penanganan error yang kuat."""
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
        df['KedalamanValue'] = pd.to_numeric(df.get('Kedalaman', '0').astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)

        if 'Shakemap' in df.columns:
            df['ShakemapURL'] = df['Shakemap'].apply(lambda x: f"https://data.bmkg.go.id/DataMKG/TEWS/{x}" if isinstance(x, str) and x.endswith('.jpg') else None)
        
        df.dropna(subset=['DateTime', 'Latitude', 'Longitude', 'Magnitude'], inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

def create_folium_map(df: pd.DataFrame, options: dict) -> folium.Map:
    """Membuat objek peta Folium dengan semua layer dan kontrolnya."""
    map_center = [df['Latitude'].mean(), df['Longitude'].mean()]
    m = folium.Map(location=map_center, zoom_start=5, tiles=options['tiles'])

    # Layer 1: Marker (dengan atau tanpa clustering)
    marker_group = folium.FeatureGroup(name="Gempa (Markers)", show=True).add_to(m)
    marker_target = MarkerCluster().add_to(marker_group) if options['use_clustering'] else marker_group
    for _, row in df.iterrows():
        color = 'red' if row['Magnitude'] >= 6.0 else 'orange' if row['Magnitude'] >= 4.0 else 'green'
        popup_html = f"<b>{row['Wilayah']}</b><br>M: {row['Magnitude']}<br>Kedalaman: {row.get('Kedalaman', 'N/A')}"
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=popup_html, tooltip=f"M{row['Magnitude']}",
            icon=folium.Icon(color=color, icon='info-sign')
        ).add_to(marker_target)

    # Layer 2: Heatmap (jika diaktifkan)
    if options['show_heatmap']:
        heat_group = folium.FeatureGroup(name="Heatmap", show=False).add_to(m)
        heat_data = [[row['Latitude'], row['Longitude']] for _, row in df.iterrows()]
        HeatMap(heat_data).add_to(heat_group)

    # Layer 3: Shakemap (jika diaktifkan dan tersedia)
    if options['show_shakemap'] and 'ShakemapURL' in df.columns:
        shake_group = folium.FeatureGroup(name="Shakemap BMKG", show=False).add_to(m)
        shakemap_quake = df.sort_values(by='Magnitude', ascending=False)[df['ShakemapURL'].notna()].iloc[0] if not df[df['ShakemapURL'].notna()].empty else None
        if shakemap_quake is not None:
            lat, lon, mag = shakemap_quake['Latitude'], shakemap_quake['Longitude'], shakemap_quake['Magnitude']
            delta = 0.1 * (1.8 ** mag) / 2 
            bounds = [[lat - delta, lon - delta], [lat + delta, lon + delta]]
            folium.raster_layers.ImageOverlay(image=shakemap_quake['ShakemapURL'], bounds=bounds, opacity=0.7).add_to(shake_group)
    
    folium.LayerControl().add_to(m)
    return m

# ---------------------------------------------------------------------
# Bagian 3: Sidebar
# ---------------------------------------------------------------------
with st.sidebar:
    st.title("👨‍💻 Tentang Author")
    st.image("adam_dorman_profile.jpg", use_column_width=True, caption="Adam Dorman")
    st.markdown("- [LinkedIn](https://www.linkedin.com/in/adamdorman68/)\n- [GitHub](https://github.com/adamdorman468-collab)\n- [Instagram](https://www.instagram.com/adam_abu_umar?igsh=OGQ5ZDc2ODk2ZA==)")
    st.divider()
    st.title("⚙️ Pengaturan Data")
    
    selected_data_name = st.selectbox("Pilih Sumber Data:", list(DATA_SOURCES.keys()))
    selected_file_name = DATA_SOURCES[selected_data_name]

    if 'last_data_source' not in st.session_state or st.session_state.last_data_source != selected_file_name:
        st.session_state.last_data_source = selected_file_name
        keys_to_clear = ['mag_filter', 'depth_filter']
        for key in keys_to_clear: st.session_state.pop(key, None)
        st.rerun()

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    st.markdown("#### Opsi Peta")
    tile_theme = st.selectbox("Tema Peta:", ("Light", "Dark"))
    use_clustering = st.checkbox("Kelompokkan gempa (clustering)", value=True)
    show_heatmap = st.checkbox("Aktifkan layer Heatmap", value=False)
    show_shakemap = st.checkbox("Aktifkan layer Shakemap", value=False)
    
    st.divider()
    st.markdown(f"**🌋 Versi Aplikasi: {APP_VERSION}**")

# ---------------------------------------------------------------------
# Bagian 4: Tampilan Utama
# ---------------------------------------------------------------------
header_container = st.container()
with header_container:
    col1, col2 = st.columns([2,1])
    with col1:
        st.title("🌋 Pusat Informasi Gempa Indonesia")
        st.markdown(f"**{datetime.now(timezone(timedelta(hours=7))).strftime('%A, %d %B %Y')}**")
    with col2:
        components.html(f"""<div style="font-family: 'Segoe UI', 'Roboto', 'sans-serif'; text-align: right;"><span style="font-size: 1rem; color: #A0A0A0;">WIB</span><h2 id="wib-time" style="margin: 0; color: #FFFFFF; font-size: 2.5rem; font-weight: 700;">{datetime.now(timezone(timedelta(hours=7))).strftime('%H:%M:%S')}</h2></div>""", height=75)

st.caption(f"Menampilkan: **{selected_data_name}** | Sumber: [API Publik BMKG](https://data.bmkg.go.id/)")
st.divider()

df_gempa = get_data_gempa(selected_file_name)

if df_gempa.empty:
    st.error("Gagal memuat data dari BMKG. Silakan coba refresh atau pilih sumber data lain.")
else:
    # --- Kontainer untuk Filter ---
    filter_container = st.expander("Buka/Tutup Panel Filter & Pengurutan", expanded=True)
    with filter_container:
        fc1, fc2, fc3 = st.columns([2, 2, 1])
        with fc1:
            if not df_gempa.empty:
                min_mag, max_mag = float(df_gempa['Magnitude'].min()), float(df_gempa['Magnitude'].max())
                if min_mag < max_mag:
                    st.session_state.mag_filter = st.slider("Filter Magnitudo", min_mag, max_mag, st.session_state.get('mag_filter', (min_mag, max_mag)), 0.1)
                else: st.session_state.mag_filter = (min_mag, max_mag)
            else: st.slider("Filter Magnitudo", 0.0, 10.0, (0.0, 10.0), 0.1, disabled=True)
        with fc2:
            if not df_gempa.empty:
                min_d, max_d = int(df_gempa['KedalamanValue'].min()), int(df_gempa['KedalamanValue'].max())
                if min_d < max_d:
                    st.session_state.depth_filter = st.slider("Filter Kedalaman (km)", min_d, max_d, st.session_state.get('depth_filter', (min_d, max_d)))
                else: st.session_state.depth_filter = (min_d, max_d)
            else: st.slider("Filter Kedalaman (km)", 0, 700, (0, 700), disabled=True)
        with fc3:
            sort_by = st.selectbox("Urutkan:", ("Waktu Terbaru", "Magnitudo Terkuat", "Paling Dangkal"), label_visibility="collapsed")
            if st.button("Reset Filter", use_container_width=True):
                keys_to_clear = ['mag_filter', 'depth_filter']
                for key in keys_to_clear: st.session_state.pop(key, None)
                st.rerun()

    # Terapkan filter dan sorting
    mag_filter = st.session_state.get('mag_filter', (0.0, 10.0))
    depth_filter = st.session_state.get('depth_filter', (0, 700))
    df_filtered = df_gempa[(df_gempa['Magnitude'].between(*mag_filter)) & (df_gempa['KedalamanValue'].between(*depth_filter))].copy()
    if sort_by == "Magnitudo Terkuat": df_filtered.sort_values(by='Magnitude', ascending=False, inplace=True)
    elif sort_by == "Paling Dangkal": df_filtered.sort_values(by='KedalamanValue', ascending=True, inplace=True)
    else: df_filtered.sort_values(by='DateTime', ascending=False, inplace=True)

    if df_filtered.empty:
        st.warning("Tidak ada data yang sesuai dengan kriteria filter Anda.")
    else:
        # --- Kontainer Statistik ---
        stats_container = st.container()
        with stats_container:
            stat_cols = st.columns(4)
            stat_cols[0].metric("Total Gempa (Filter)", len(df_filtered))
            stat_cols[1].metric("Magnitudo Tertinggi", f"{df_filtered['Magnitude'].max():.1f} M")
            stat_cols[2].metric("Magnitudo Rata-rata", f"{df_filtered['Magnitude'].mean():.2f} M")
            stat_cols[3].metric("Kedalaman Terdangkal", f"{int(df_filtered['KedalamanValue'].min())} km")
        
        if df_filtered['Magnitude'].max() >= 6.0:
            toast_js(f"PERINGATAN: Terdeteksi gempa M {df_filtered['Magnitude'].max():.1f}")

        # --- Kontainer Konten Utama (Tabs) ---
        main_content_container = st.container()
        with main_content_container:
            tab1, tab2, tab3 = st.tabs(["📍 Peta Interaktif", "📑 Tabel Data Rinci", "📈 Analisis Statistik"])
            with tab1:
                map_options = {
                    'tiles': 'CartoDB dark_matter' if tile_theme == "Dark" else 'CartoDB positron',
                    'use_clustering': use_clustering,
                    'show_heatmap': show_heatmap,
                    'show_shakemap': show_shakemap
                }
                folium_map = create_folium_map(df_filtered, map_options)
                st_folium(folium_map, width="100%", height=600, returned_objects=[])

            with tab2:
                st.dataframe(df_filtered[['DateTime', 'Magnitude', 'Kedalaman', 'Wilayah']], use_container_width=True)

            with tab3:
                st.subheader("Analisis Statistik Gempa (Hasil Filter)")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### Distribusi Magnitudo")
                    mag_counts = pd.cut(df_filtered['Magnitude'], bins=[0, 4, 6, 10], labels=["< 4.0", "4.0 - 5.9", "≥ 6.0"], right=False).value_counts().sort_index()
                    st.bar_chart(mag_counts)
                with c2:
                    st.markdown("#### Distribusi Kedalaman (km)")
                    depth_counts = pd.cut(df_filtered['KedalamanValue'], bins=[-1, 70, 300, 800], labels=["Dangkal (<70)", "Menengah (70-300)", "Dalam (>300)"]).value_counts().sort_index()
                    st.bar_chart(depth_counts)
