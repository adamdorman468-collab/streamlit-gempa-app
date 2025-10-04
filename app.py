# ======================================================================================
# PUSAT INFORMASI GEMPA BUMI - Versi 6.1 (Filter Reset Fix + Full Reset)
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
st.set_page_config(page_title="Pusat Informasi Gempa Indonesia", page_icon="🌋", layout="wide")

try:
    locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
except locale.Error:
    st.sidebar.warning("Lokal 'id_ID' tidak ditemukan.")

BMKG_API_BASE_URL = "https://data.bmkg.go.id/DataMKG/TEWS/"
DATA_SOURCES = {
    "Gempa Dirasakan (Paling Lengkap)": "gempadirasakan.json",
    "Gempa Terbaru M 5.0+": "gempaterkini.json",
    "Gempa Real-time (Otomatis)": "autogempa.json"
}
APP_VERSION = "6.1"

# ---------------------------------------------------------------------
# Bagian 2: Fungsi Bantuan
# ---------------------------------------------------------------------
def get_color_from_magnitude(magnitude):
    if not isinstance(magnitude, (int, float)): return 'gray'
    if magnitude < 4.0: return 'green'
    elif 4.0 <= magnitude < 6.0: return 'orange'
    else: return 'red'

def display_realtime_clock():
    html_code = """
        <div id="clock-container" style="display: flex; justify-content: space-between; font-family: 'Segoe UI', 'Roboto', 'sans-serif';">
            <div style="text-align: center;"><span style="font-size: 1rem; color: #A0A0A0;">WIB</span><h2 id="wib-time" style="margin: 0; color: #FFFFFF; font-size: 2.5rem; font-weight: 700;">--:--:--</h2></div>
            <div style="text-align: center;"><span style="font-size: 1rem; color: #A0A0A0;">UTC</span><h2 id="utc-time" style="margin: 0; color: #FFFFFF; font-size: 2.5rem; font-weight: 700;">--:--:--</h2></div>
        </div>
        <script>
            function updateTime() {
                const wibTimeElement = document.getElementById('wib-time');
                const utcTimeElement = document.getElementById('utc-time');
                if (!wibTimeElement || !utcTimeElement) return;
                const wibDate = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Jakarta' }));
                const utcDate = new Date();
                wibTimeElement.innerHTML = wibDate.toTimeString().split(' ')[0];
                utcTimeElement.innerHTML = utcDate.toISOString().split('T')[1].split('.')[0];
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
            df['Latitude'] = pd.to_numeric(coords[0], errors='coerce')
            df['Longitude'] = pd.to_numeric(coords[1], errors='coerce')

        df['Magnitude'] = pd.to_numeric(df.get('Magnitude'), errors='coerce')
        df['KedalamanValue'] = pd.to_numeric(df.get('Kedalaman', '').astype(str).str.extract(r'(\d+)')[0], errors='coerce')
        df['ShakemapURL'] = df.get('Shakemap', '').apply(lambda x: f"https://data.bmkg.go.id/DataMKG/TEWS/{x}" if isinstance(x, str) and x.endswith('.jpg') else None)
        df['Waktu Kejadian'] = df['DateTime'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df.dropna(subset=['DateTime', 'Latitude', 'Longitude', 'Magnitude'], inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

# ---------------------------------------------------------------------
# Bagian 3: Sidebar
# ---------------------------------------------------------------------
with st.sidebar:
    st.title("👨‍💻 Tentang Author")
    st.caption("Mahasiswa S1 Sistem Informasi UPNVJ Angkatan 2024")
    st.image("adam_dorman_profile.jpg", use_container_width=True, caption="Adam Dorman - 2025")
    st.markdown("""
    - [LinkedIn](https://www.linkedin.com/in/adamdorman68/) 
    - [GitHub](https://github.com/adamdorman468-collab)
    - [Instagram](https://www.instagram.com/adam_abu_umar?igsh=OGQ5ZDc2ODk2ZA==)
    """)
    st.divider()

    st.title("⚙️ Kontrol & Pengaturan")
    selected_data_name = st.selectbox("Pilih Sumber Data:", options=list(DATA_SOURCES.keys()))
    selected_file_name = DATA_SOURCES[selected_data_name]

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.info(f"Data terakhir diperbarui: {datetime.now(timezone(timedelta(hours=7))).strftime('%H:%M:%S WIB')}")

    df_for_filters = get_data_gempa(selected_file_name)
    st.divider()

    sort_by = st.selectbox("Urutkan Data:", ("Waktu Terbaru", "Magnitudo Terkuat", "Paling Dangkal"))

    # Simpan nilai default filter kedalaman
    if not df_for_filters.empty and 'KedalamanValue' in df_for_filters.columns:
        min_depth, max_depth = int(df_for_filters['KedalamanValue'].min()), int(df_for_filters['KedalamanValue'].max())
    else:
        min_depth, max_depth = 0, 700

    if "depth_filter" not in st.session_state:
        st.session_state.depth_filter = (min_depth, max_depth)

    depth_filter_values = st.slider(
        "Saring berdasarkan kedalaman (km):",
        min_value=min_depth,
        max_value=max_depth,
        value=st.session_state.depth_filter,
        key="depth_slider"
    )
    st.session_state.depth_filter = depth_filter_values

    st.divider()
    st.markdown("#### Opsi Peta")
    use_clustering = st.checkbox("Kelompokkan gempa (clustering)", value=True)
    show_heatmap = st.checkbox("Tampilkan Heatmap", value=False)
    show_shakemap = st.checkbox("Tampilkan Shakemap BMKG (jika ada)", value=False)
    st.divider()

    if st.button("🔁 Reset Semua Filter"):
        st.session_state.mag_filter = None
        st.session_state.depth_filter = (min_depth, max_depth)
        st.rerun()

    st.markdown("---")
    st.markdown("*Legenda Warna:*")
    st.markdown("<span style='color:green'>🟢</span> M < 4.0", unsafe_allow_html=True)
    st.markdown("<span style='color:orange'>🟠</span> 4.0 ≤ M < 6.0", unsafe_allow_html=True)
    st.markdown("<span style='color:red'>🔴</span> M ≥ 6.0", unsafe_allow_html=True)
    st.divider()
    st.markdown(f"🌋 Versi Aplikasi: {APP_VERSION}")

# ---------------------------------------------------------------------
# Bagian 4: Tampilan Utama
# ---------------------------------------------------------------------
col1, col2 = st.columns([3, 2])
with col1:
    st.title("🌋 Pusat Informasi Gempa Indonesia")
    st.markdown(f"{datetime.now(timezone(timedelta(hours=7))).strftime('%A, %d %B %Y')}")
with col2:
    display_realtime_clock()

st.markdown(f"Menampilkan: *{selected_data_name}* | Sumber: [API Publik BMKG](https://data.bmkg.go.id/)")
st.divider()

df_gempa = get_data_gempa(selected_file_name)

if not df_gempa.empty:
    df_tampil = df_gempa.copy()
    min_mag, max_mag = float(df_tampil['Magnitude'].min()), float(df_tampil['Magnitude'].max())

    # Inisialisasi session state magnitudo
    if "mag_filter" not in st.session_state or st.session_state.mag_filter is None:
        st.session_state.mag_filter = (min_mag, max_mag)

    filter_col1, filter_col2 = st.columns([3, 1])
    with filter_col1:
        mag_filter_values = st.slider(
            "Saring berdasarkan Magnitudo:",
            min_value=min_mag,
            max_value=max_mag,
            value=st.session_state.mag_filter,
            key="mag_slider"
        )
    with filter_col2:
        st.write("")
        if st.button("Reset Filter Magnitudo"):
            st.session_state.mag_filter = (min_mag, max_mag)
            st.rerun()

    st.session_state.mag_filter = mag_filter_values

    df_filtered = df_tampil[
        (df_tampil['Magnitude'].between(*st.session_state.mag_filter)) &
        (df_tampil['KedalamanValue'].between(*st.session_state.depth_filter))
    ]

    if sort_by == "Magnitudo Terkuat":
        df_filtered = df_filtered.sort_values(by='Magnitude', ascending=False)
    elif sort_by == "Paling Dangkal":
        df_filtered = df_filtered.sort_values(by='KedalamanValue', ascending=True)
    else:
        df_filtered = df_filtered.sort_values(by='DateTime', ascending=False)

    if not df_filtered.empty:
        gempa_terbaru = df_filtered.iloc[0]
        map_col, data_col = st.columns([2, 1])

        with map_col:
            st.subheader("🗺️ Peta Persebaran Gempa")
            m = folium.Map(location=[gempa_terbaru['Latitude'], gempa_terbaru['Longitude']], zoom_start=5)

            # Marker utama
            marker_layer = MarkerCluster(name="Gempa (Cluster)") if use_clustering else folium.FeatureGroup(name="Gempa")
            marker_layer.add_to(m)

            for _, row in df_filtered.iterrows():
                popup = f"<b>{row['Wilayah']}</b><br>M: {row['Magnitude']}<br>Kedalaman: {row['Kedalaman']}"
                folium.Marker(
                    location=[row['Latitude'], row['Longitude']],
                    popup=popup,
                    tooltip=f"M {row['Magnitude']} - {row['Wilayah']}",
                    icon=folium.Icon(color=get_color_from_magnitude(row['Magnitude']))
                ).add_to(marker_layer)

            if show_heatmap:
                heat_data = [[r['Latitude'], r['Longitude']] for _, r in df_filtered.iterrows()]
                HeatMap(heat_data, name="Heatmap Kepadatan").add_to(m)

            if show_shakemap:
                candidate = df_filtered[df_filtered['ShakemapURL'].notna()]
                if not candidate.empty:
                    r = candidate.iloc[0]
                    delta = 0.1 * (1.8 ** r['Magnitude']) / 2
                    bounds = [[r['Latitude'] - delta, r['Longitude'] - delta], [r['Latitude'] + delta, r['Longitude'] + delta]]
                    folium.raster_layers.ImageOverlay(
                        name="Shakemap BMKG", image=r['ShakemapURL'], bounds=bounds, opacity=0.7
                    ).add_to(m)

            folium.LayerControl().add_to(m)
            st_folium(m, width="100%", height=500)

        with data_col:
            st.subheader("📊 Data Detail Gempa")
            df_display = df_filtered.copy()
            df_display['Waktu Kejadian'] = df_display['DateTime'].dt.strftime('%d-%b %H:%M:%S')
            st.dataframe(df_display[['Waktu Kejadian', 'Magnitude', 'Kedalaman', 'Wilayah']])
    else:
        st.warning("Tidak ada data sesuai filter.")
else:
    st.error("Gagal memuat data dari BMKG. Coba refresh atau pilih sumber lain.")
