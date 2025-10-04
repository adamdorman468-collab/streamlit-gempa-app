# ======================================================================================
# PUSAT INFORMASI GEMPA BUMI - Versi 6.0 (ENHANCED)
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
# Bagian 1: Konfigurasi Halaman & Konstanta
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Pusat Informasi Gempa Indonesia",
    page_icon="🌋",
    layout="wide",
)

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
ALL_COLUMNS = ['DateTime', 'Coordinates', 'Latitude', 'Longitude', 'Magnitude', 
               'Kedalaman', 'Wilayah', 'Potensi', 'Dirasakan', 'Shakemap', 'Tanggal', 'Jam']

# ---------------------------------------------------------------------
# Bagian 2: Fungsi-fungsi Bantuan
# ---------------------------------------------------------------------
def get_color_from_magnitude(magnitude):
    if not isinstance(magnitude, (int, float)): return 'gray'
    if magnitude < 4.0: return 'green'
    elif 4.0 <= magnitude < 6.0: return 'orange'
    else: return 'red'

def display_realtime_clock():
    """Membuat komponen HTML untuk jam digital (WIB + UTC)."""
    html_code = """
        <div id="clock-container" style="display: flex; justify-content: space-around; font-family: 'Segoe UI', 'Roboto', sans-serif;">
            <div style="text-align: center;">
                <span style="font-size: 1rem; color: #A0A0A0;">WIB</span>
                <h2 id="wib-time" style="margin: 0; color: #FFFFFF; font-size: 2rem; font-weight: 700;">--:--:--</h2>
            </div>
            <div style="text-align: center;">
                <span style="font-size: 1rem; color: #A0A0A0;">UTC</span>
                <h2 id="utc-time" style="margin: 0; color: #FFFFFF; font-size: 2rem; font-weight: 700;">--:--:--</h2>
            </div>
        </div>
        <script>
            function updateTime() {
                const wibTimeElement = document.getElementById('wib-time');
                const utcTimeElement = document.getElementById('utc-time');
                const wibDate = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Jakarta' }));
                const wibHours = String(wibDate.getHours()).padStart(2, '0');
                const wibMinutes = String(wibDate.getMinutes()).padStart(2, '0');
                const wibSeconds = String(wibDate.getSeconds()).padStart(2, '0');
                const utcDate = new Date();
                const utcHours = String(utcDate.getUTCHours()).padStart(2, '0');
                const utcMinutes = String(utcDate.getUTCMinutes()).padStart(2, '0');
                const utcSeconds = String(utcDate.getUTCSeconds()).padStart(2, '0');
                if (wibTimeElement) wibTimeElement.innerHTML = `${wibHours}:${wibMinutes}:${wibSeconds}`;
                if (utcTimeElement) utcTimeElement.innerHTML = `${utcHours}:${utcMinutes}:${utcSeconds}`;
            }
            setInterval(updateTime, 1000);
            updateTime();
        </script>
    """
    components.html(html_code, height=65)

# ---------------------------------------------------------------------
# Bagian 3: Ambil & Olah Data BMKG
# ---------------------------------------------------------------------
@st.cache_data(ttl=60)
def get_data_gempa(file_name):
    url = f"{BMKG_API_BASE_URL}{file_name}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        gempa_data_raw = data.get('Infogempa', {}).get('gempa', [])
        data_for_df = [gempa_data_raw] if isinstance(gempa_data_raw, dict) else gempa_data_raw
        
        if not data_for_df: return pd.DataFrame()
            
        df = pd.DataFrame(data_for_df)
        
        for col in ALL_COLUMNS:
            if col not in df.columns: df[col] = pd.NA
        
        df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
        df[['Latitude', 'Longitude']] = df['Coordinates'].str.split(',', expand=True, n=1).astype(float)
        df['Magnitude'] = pd.to_numeric(df['Magnitude'], errors='coerce')
        df['KedalamanValue'] = pd.to_numeric(df['Kedalaman'].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
        
        df['Tanggal'] = df['DateTime'].dt.strftime('%Y-%m-%d')
        df['Jam'] = df['DateTime'].dt.strftime('%H:%M:%S WIB')
        df['Waktu Kejadian'] = df['DateTime'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df.dropna(subset=['DateTime', 'Latitude', 'Longitude', 'Magnitude'], inplace=True)
        return df
        
    except Exception:
        return pd.DataFrame()

# ---------------------------------------------------------------------
# Bagian 4: Sidebar
# ---------------------------------------------------------------------
with st.sidebar:
    st.title("👨‍💻 Tentang Author")
    st.image("adam_dorman_profile.jpg", use_container_width=True, caption="Adam Dorman")
    st.markdown("""
    **Adam Dorman**  
    Mahasiswa S1 Sistem Informasi, UPN Veteran Jakarta  
    [🌐 LinkedIn](https://www.linkedin.com/in/adamdorman68/) | [📷 Instagram](https://www.instagram.com/adam_abu_umar) | [💻 GitHub](https://github.com/adamdorman468-collab)
    """)
    st.divider()
    st.title("⚙️ Kontrol & Pengaturan")
    
    selected_data_name = st.selectbox("Pilih Sumber Data:", options=list(DATA_SOURCES.keys()))
    selected_file_name = DATA_SOURCES[selected_data_name]

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.info(f"Data terakhir diperbarui: {datetime.now(timezone(timedelta(hours=7))).strftime('%H:%M:%S WIB')}")

    # Ambil data untuk filter
    df_for_filters = get_data_gempa(selected_file_name)

    # Urutkan Data
    sort_by = st.selectbox("Urutkan Berdasarkan:", ("Waktu Terbaru", "Magnitudo Terkuat", "Paling Dangkal"))

    # Filter Kedalaman
    if not df_for_filters.empty and df_for_filters['KedalamanValue'].notna().any():
        min_depth, max_depth = int(df_for_filters['KedalamanValue'].min()), int(df_for_filters['KedalamanValue'].max())
        if min_depth == max_depth:
            depth_filter_values = (min_depth, max_depth)
            st.info(f"Semua gempa di data ini punya kedalaman {min_depth} km")
        else:
            depth_filter_values = st.slider("Filter Kedalaman (km):", min_value=min_depth, max_value=max_depth, value=(min_depth, max_depth))
    else:
        depth_filter_values = (0, 700)

    use_clustering = st.checkbox("Gunakan Clustering di Peta", value=True)
    show_heatmap = st.checkbox("Tampilkan Heatmap Gempa", value=False)

    st.divider()
    APP_VERSION = "6.0"
    st.markdown(f"**🌋 Versi Aplikasi: {APP_VERSION}**")

# ---------------------------------------------------------------------
# Bagian 5: Tampilan Utama
# ---------------------------------------------------------------------
header = st.container()
with header:
    st.title("🌋 Pusat Informasi Gempa Indonesia")
    col_head = st.columns([3,1])
    with col_head[0]:
        st.markdown(f"**{datetime.now(timezone(timedelta(hours=7))).strftime('%A, %d %B %Y')}**")
        st.caption(f"Menampilkan: **{selected_data_name}** | Sumber: [API Publik BMKG](https://data.bmkg.go.id/)")
    with col_head[1]:
        display_realtime_clock()

st.divider()

df_gempa = get_data_gempa(selected_file_name)

if not df_gempa.empty:
    # Filter Magnitudo
    min_mag, max_mag = float(df_gempa['Magnitude'].min()), float(df_gempa['Magnitude'].max())
    if st.session_state.get('data_source') != selected_file_name:
        st.session_state.mag_filter = (min_mag, max_mag)
        st.session_state.data_source = selected_file_name
    if 'mag_filter' not in st.session_state:
        st.session_state.mag_filter = (min_mag, max_mag)

    mag_filter = st.slider("Filter Magnitudo:", min_value=min_mag, max_value=max_mag, value=st.session_state.mag_filter)
    st.session_state.mag_filter = mag_filter

    # Terapkan filter
    df_filtered = df_gempa[
        (df_gempa['Magnitude'] >= mag_filter[0]) & 
        (df_gempa['Magnitude'] <= mag_filter[1]) &
        (df_gempa['KedalamanValue'] >= depth_filter_values[0]) &
        (df_gempa['KedalamanValue'] <= depth_filter_values[1])
    ]

    # Sorting
    if sort_by == "Magnitudo Terkuat":
        df_filtered = df_filtered.sort_values(by='Magnitude', ascending=False)
    elif sort_by == "Paling Dangkal":
        df_filtered = df_filtered.sort_values(by='KedalamanValue', ascending=True)
    else:
        df_filtered = df_filtered.sort_values(by='DateTime', ascending=False)

    if not df_filtered.empty:
        gempa_terbaru = df_filtered.iloc[0]

        # Tabs utama
        tab1, tab2, tab3 = st.tabs(["📍 Peta", "📊 Statistik", "📑 Data Tabel"])

        # Peta
        with tab1:
            map_container = st.container()
            with map_container:
                m = folium.Map(location=[gempa_terbaru['Latitude'], gempa_terbaru['Longitude']], zoom_start=5, tiles="CartoDB positron")

                if use_clustering:
                    mc = MarkerCluster().add_to(m)
                    target_map = mc
                else:
                    target_map = m

                for _, row in df_filtered.iterrows():
                    folium.Marker(
                        location=[row['Latitude'], row['Longitude']],
                        popup=f"<b>{row['Wilayah']}</b><br>Magnitudo: {row['Magnitude']}<br>Kedalaman: {row['Kedalaman']}<br>Dirasakan: {row['Dirasakan']}",
                        tooltip=f"M{row['Magnitude']} - {row['Wilayah']}",
                        icon=folium.Icon(color=get_color_from_magnitude(row['Magnitude']))
                    ).add_to(target_map)

                if show_heatmap:
                    heat_data = [[row['Latitude'], row['Longitude'], row['Magnitude']] for _, row in df_filtered.iterrows()]
                    HeatMap(heat_data, radius=25).add_to(m)

                st_folium(m, width="100%", height=550)

        # Statistik
        with tab2:
            st.metric("Total Gempa", len(df_filtered))
            st.metric("Magnitudo Tertinggi", f"{df_filtered['Magnitude'].max():.1f}")
            st.metric("Kedalaman Terdangkal", f"{df_filtered['KedalamanValue'].min()} km")
            st.metric("Kedalaman Terdalam", f"{df_filtered['KedalamanValue'].max()} km")
            st.metric("Rata-rata Magnitudo", f"{df_filtered['Magnitude'].mean():.2f}")

        # Data tabel
        with tab3:
            st.dataframe(df_filtered[['Waktu Kejadian','Magnitude','Kedalaman','Wilayah']], use_container_width=True)

    else:
        st.warning("Tidak ada data sesuai filter.")
else:
    st.error("Gagal memuat data dari BMKG. Silakan refresh.")
