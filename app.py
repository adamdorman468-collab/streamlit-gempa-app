# ======================================================================================
# PUSAT INFORMASI GEMPA BUMI - Versi 5.2 (Stabil & Ditingkatkan)
# Dibuat oleh: Adam Dorman (Mahasiswa S1 Sistem Informasi UPNVJ)
# ======================================================================================

import streamlit as st
import pandas as pd
import requests
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from datetime import datetime, timezone, timedelta
import locale
import streamlit.components.v1 as components

# ---------------------------------------------------------------------
# Konfigurasi Halaman
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
    "Gempa Dirasakan (Paling Lengkap)": "gempadirasakan.json",
    "Gempa Terbaru M 5.0+": "gempaterkini.json",
    "Gempa Real-time (Otomatis)": "autogempa.json"
}
ALL_COLUMNS = ['DateTime', 'Coordinates', 'Latitude', 'Longitude', 'Magnitude',
               'Kedalaman', 'Wilayah', 'Potensi', 'Dirasakan', 'Shakemap',
               'Tanggal', 'Jam']

# ---------------------------------------------------------------------
# Fungsi Bantuan
# ---------------------------------------------------------------------
def get_color_from_magnitude(magnitude):
    if not isinstance(magnitude, (int, float)):
        return 'gray'
    if magnitude < 4.0:
        return 'green'
    elif magnitude < 6.0:
        return 'orange'
    else:
        return 'red'

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

# ---------------------------------------------------------------------
# Data BMKG
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
        if not data_for_df:
            return pd.DataFrame()

        df = pd.DataFrame(data_for_df)

        # Tambah kolom kosong jika tidak ada
        for col in ALL_COLUMNS:
            if col not in df.columns:
                df[col] = pd.NA

        # Parsing data
        df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
        if 'Coordinates' in df.columns:
            coords = df['Coordinates'].str.split(',', expand=True)
            if coords.shape[1] == 2:
                df['Latitude'] = pd.to_numeric(coords[0], errors='coerce')
                df['Longitude'] = pd.to_numeric(coords[1], errors='coerce')

        df['Magnitude'] = pd.to_numeric(df['Magnitude'], errors='coerce')
        df['KedalamanValue'] = pd.to_numeric(
            df['Kedalaman'].astype(str).str.extract(r'(\d+)')[0], errors='coerce'
        )

        df['Waktu Kejadian'] = df['DateTime'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df.dropna(subset=['DateTime', 'Latitude', 'Longitude', 'Magnitude'], inplace=True)
        return df

    except Exception:
        return pd.DataFrame()

# ---------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------
with st.sidebar:
    st.title("👨‍💻 Tentang Author")
    st.image("adam_dorman_profile.jpg", use_container_width=True, caption="Adam Dorman")
    st.markdown("""
    *Adam Dorman*  
    Mahasiswa S1 Sistem Informasi, UPN Veteran Jakarta  

    [LinkedIn](https://www.linkedin.com/in/adamdorman68/) | 
    [Instagram](https://www.instagram.com/adam_abu_umar) | 
    [GitHub](https://github.com/adamdorman468-collab)
    """)
    st.divider()

    st.title("⚙ Kontrol & Pengaturan")
    selected_data_name = st.selectbox("Pilih Sumber Data:", options=list(DATA_SOURCES.keys()))
    selected_file_name = DATA_SOURCES[selected_data_name]

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.info(f"Data terakhir diperbarui: {datetime.now(timezone(timedelta(hours=7))).strftime('%H:%M:%S WIB')}")

    df_for_filters = get_data_gempa(selected_file_name)

    st.divider()
    sort_by = st.selectbox("Urutkan Data:", ("Waktu Terbaru", "Magnitudo Terkuat", "Paling Dangkal"))

    # Filter kedalaman
    if not df_for_filters.empty:
        min_depth = int(df_for_filters['KedalamanValue'].min())
        max_depth = int(df_for_filters['KedalamanValue'].max())
        if min_depth == max_depth:
            min_depth -= 1; max_depth += 1
        depth_filter_values = st.slider("Kedalaman (km):", min_value=min_depth, max_value=max_depth,
                                        value=(min_depth, max_depth))
    else:
        depth_filter_values = (0, 700)

    use_clustering = st.checkbox("Cluster gempa di peta", value=True)

# ---------------------------------------------------------------------
# Main Page
# ---------------------------------------------------------------------
col1, col2 = st.columns([3, 2])
with col1:
    st.title("🌋 Pusat Informasi Gempa Indonesia")
    st.markdown(f"{datetime.now(timezone(timedelta(hours=7))).strftime('%A, %d %B %Y')}")
with col2:
    display_realtime_clock()

st.markdown(f"Menampilkan: *{selected_data_name}* | Sumber: [API BMKG](https://data.bmkg.go.id/)")
st.divider()

df_gempa = get_data_gempa(selected_file_name)

if not df_gempa.empty:
    df_tampil = df_gempa.copy()

    # Magnitudo filter
    min_mag, max_mag = float(df_tampil['Magnitude'].min()), float(df_tampil['Magnitude'].max())
    if min_mag == max_mag:
        min_mag -= 0.1; max_mag += 0.1

    mag_filter_values = st.slider("Magnitudo:", min_value=min_mag, max_value=max_mag,
                                  value=(min_mag, max_mag))

    df_filtered = df_tampil[
        (df_tampil['Magnitude'].between(*mag_filter_values)) &
        (df_tampil['KedalamanValue'].between(*depth_filter_values))
    ]

    # Sorting
    if sort_by == "Magnitudo Terkuat":
        df_filtered = df_filtered.sort_values(by='Magnitude', ascending=False)
    elif sort_by == "Paling Dangkal":
        df_filtered = df_filtered.sort_values(by='KedalamanValue', ascending=True)
    else:
        df_filtered = df_filtered.sort_values(by='DateTime', ascending=False)

    # Output
    if not df_filtered.empty:
        gempa_terbaru = df_filtered.iloc[0]

        map_col, data_col = st.columns([2, 1])
        with map_col:
            st.subheader("Peta Persebaran Gempa")
            map_center = [gempa_terbaru['Latitude'], gempa_terbaru['Longitude']]
            m = folium.Map(location=map_center, zoom_start=5)
            target_map = MarkerCluster().add_to(m) if use_clustering else m

            for _, row in df_filtered.iterrows():
                popup_text = f"""<b>{row.get('Wilayah')}</b><br>
                                 Magnitudo: {row.get('Magnitude')}<br>
                                 Kedalaman: {row.get('Kedalaman')}<br><hr>
                                 Dirasakan: {row.get('Dirasakan')}"""
                folium.Marker(
                    location=[row['Latitude'], row['Longitude']],
                    popup=popup_text,
                    tooltip=f"Mag {row.get('Magnitude')} - {row.get('Wilayah')}",
                    icon=folium.Icon(color=get_color_from_magnitude(row['Magnitude']))
                ).add_to(target_map)

            st_folium(m, width='100%', height=500, returned_objects=[])

        with data_col:
            st.subheader("Data Detail")
            df_display = df_filtered.copy()
            df_display['Waktu Kejadian'] = df_display['DateTime'].dt.strftime('%d-%b %H:%M:%S')
            st.dataframe(df_display[['Waktu Kejadian', 'Magnitude', 'Kedalaman', 'Wilayah']])
    else:
        st.warning("⚠️ Tidak ada data sesuai filter Anda.")
else:
    st.error("❌ Gagal memuat data dari BMKG. Coba refresh atau pilih sumber lain.")
