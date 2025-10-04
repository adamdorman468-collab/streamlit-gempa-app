# ======================================================================================
# PUSAT INFORMASI GEMPA BUMI - Versi 5.3 (Final & Stabil)
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
    "Gempa Dirasakan (Paling Lengkap)": "gempadirasakan.json",
    "Gempa Terbaru M 5.0+": "gempaterkini.json",
    "Gempa Real-time (Otomatis)": "autogempa.json"
}
ALL_COLUMNS = ['DateTime', 'Coordinates', 'Latitude', 'Longitude', 'Magnitude', 'Kedalaman', 'Wilayah', 'Potensi', 'Dirasakan', 'Shakemap', 'Tanggal', 'Jam']

# ---------------------------------------------------------------------
# Bagian 2: Fungsi-fungsi Bantuan
# ---------------------------------------------------------------------
def get_color_from_magnitude(magnitude):
    if not isinstance(magnitude, (int, float)): return 'gray'
    if magnitude < 4.0: return 'green'
    elif 4.0 <= magnitude < 6.0: return 'orange'
    else: return 'red'

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
# Bagian 3: "Mesin" Pengambilan & Pemrosesan Data
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
        if 'Coordinates' in df.columns:
            df[['Latitude', 'Longitude']] = df['Coordinates'].str.split(',', expand=True, n=1).astype(float)
        df['Magnitude'] = pd.to_numeric(df['Magnitude'], errors='coerce')
        if 'Kedalaman' in df.columns:
            df['KedalamanValue'] = pd.to_numeric(df['Kedalaman'].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
        
        df.dropna(subset=['DateTime', 'Latitude', 'Longitude', 'Magnitude'], inplace=True)
        return df
        
    except Exception:
        return pd.DataFrame()

# ---------------------------------------------------------------------
# Bagian 4: Tampilan Sidebar
# ---------------------------------------------------------------------
with st.sidebar:
    st.title("👨‍💻 Tentang Author")
    st.image("adam_dorman_profile.jpg", use_column_width=True, caption="Adam Dorman")
    st.markdown("""
    **Adam Dorman**
    Mahasiswa S1 Sistem Informasi, UPN Veteran Jakarta
    [LinkedIn](https://www.linkedin.com/in/adamdorman68/) | [GitHub](https://github.com/adamdorman468-collab)
    """)
    st.divider()
    st.title("⚙️ Kontrol & Pengaturan")
    
    selected_data_name = st.selectbox("Pilih Sumber Data:", options=list(DATA_SOURCES.keys()))
    selected_file_name = DATA_SOURCES[selected_data_name]

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.info(f"Data terakhir diperbarui: {datetime.now(timezone(timedelta(hours=7))).strftime('%H:%M:%S WIB')}")
    
    df_for_sidebar = get_data_gempa(selected_file_name)
    
    st.divider()
    sort_by = st.selectbox("Urutkan Data Tabel:", ("Waktu Terbaru", "Magnitudo Terkuat", "Paling Dangkal"))

    st.divider()
    st.write("**Filter Kedalaman (km)**")
    
    # Logika aman untuk slider kedalaman
    if not df_for_sidebar.empty and 'KedalamanValue' in df_for_sidebar.columns and not df_for_sidebar['KedalamanValue'].dropna().empty:
        min_depth = int(df_for_sidebar['KedalamanValue'].min())
        max_depth = int(df_for_sidebar['KedalamanValue'].max())
        depth_value = (min_depth, max_depth)
        slider_disabled = False
    else:
        min_depth, max_depth = 0, 700
        depth_value = (min_depth, max_depth)
        slider_disabled = True

    depth_filter_values = st.slider("Saring berdasarkan kedalaman:", min_value=min_depth, max_value=max_depth, value=depth_value, disabled=slider_disabled)
    
    st.divider()
    use_clustering = st.checkbox("Kelompokkan gempa di peta (clustering)", value=True)

    st.divider()
    st.markdown("#### Informasi Tambahan")
    st.markdown("- **[Info Gempa BMKG](https://www.bmkg.go.id/gempabumi/gempabumi-dirasakan.bmkg)**")
    st.markdown("---")
    st.markdown("**Legenda Warna Peta:**")
    st.markdown("<span style='color:green'>🟢</span> M < 4.0", unsafe_allow_html=True)
    st.markdown("<span style='color:orange'>🟠</span> 4.0 ≤ M < 6.0", unsafe_allow_html=True)
    st.markdown("<span style='color:red'>🔴</span> M ≥ 6.0", unsafe_allow_html=True)
    
    st.divider()
    APP_VERSION = "5.3"
    st.markdown(f"**🌋 Versi Aplikasi: {APP_VERSION}**")

# ---------------------------------------------------------------------
# Bagian 5: Tampilan Utama Aplikasi
# ---------------------------------------------------------------------
col1, col2 = st.columns([3, 2])
with col1:
    st.title("🌋 Pusat Informasi Gempa Indonesia")
    st.markdown(f"**{datetime.now(timezone(timedelta(hours=7))).strftime('%A, %d %B %Y')}**")
with col2:
    display_realtime_clock()

st.markdown(f"Menampilkan: **{selected_data_name}** | Sumber: [API Publik BMKG](https://data.bmkg.go.id/)")
st.divider()

df_gempa = get_data_gempa(selected_file_name)

if df_gempa.empty:
    st.error("Gagal memuat data dari BMKG atau tidak ada data gempa saat ini. Silakan coba refresh atau pilih sumber data lain.")
else:
    df_tampil = df_gempa.copy()
    
    # Filter Magnitudo
    min_mag, max_mag = float(df_tampil['Magnitude'].min()), float(df_tampil['Magnitude'].max())
    mag_filter_values = st.slider("Saring berdasarkan Magnitudo:", min_value=min_mag, max_value=max_mag, value=(min_mag, max_mag))
    
    # Terapkan semua filter
    filter_conditions = (
        (df_tampil['Magnitude'] >= mag_filter_values[0]) &
        (df_tampil['Magnitude'] <= mag_filter_values[1])
    )
    if 'KedalamanValue' in df_tampil.columns:
        filter_conditions &= (
            (df_tampil['KedalamanValue'] >= depth_filter_values[0]) &
            (df_tampil['KedalamanValue'] <= depth_filter_values[1])
        )
    
    df_filtered = df_tampil[filter_conditions]

    # Terapkan pengurutan
    if sort_by == "Magnitudo Terkuat":
        df_filtered = df_filtered.sort_values(by='Magnitude', ascending=False)
    elif sort_by == "Paling Dangkal" and 'KedalamanValue' in df_filtered.columns:
        df_filtered = df_filtered.sort_values(by='KedalamanValue', ascending=True)
    else: # Default "Waktu Terbaru"
        df_filtered = df_filtered.sort_values(by='DateTime', ascending=False)

    if df_filtered.empty:
        st.warning("Tidak ada data yang sesuai dengan filter Anda.")
    else:
        # Tampilkan Detail & Peta
        gempa_terbaru = df_filtered.iloc[0]
        
        st.subheader(f"Gempa Terbaru (Filter): {gempa_terbaru['Wilayah']}")
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Waktu Kejadian", gempa_terbaru['DateTime'].strftime('%H:%M:%S WIB'))
        k2.metric("Magnitudo", f"{gempa_terbaru['Magnitude']} M")
        if 'Kedalaman' in gempa_terbaru and pd.notna(gempa_terbaru['Kedalaman']):
            k3.metric("Kedalaman", gempa_terbaru['Kedalaman'])

        map_col, data_col = st.columns([2, 1])
        with map_col:
            st.subheader("Peta Persebaran Gempa")
            map_center = [gempa_terbaru['Latitude'], gempa_terbaru['Longitude']]
            m = folium.Map(location=map_center, zoom_start=5)
            
            target_map = MarkerCluster().add_to(m) if use_clustering else m

            for _, row in df_filtered.iterrows():
                popup_text = f"<b>{row.get('Wilayah')}</b><br>Mag: {row.get('Magnitude')}<br>Kedalaman: {row.get('Kedalaman', 'N/A')}"
                folium.Marker(
                    location=[row['Latitude'], row['Longitude']],
                    popup=popup_text,
                    tooltip=f"Mag: {row.get('Magnitude')} - {row.get('Wilayah')}",
                    icon=folium.Icon(color=get_color_from_magnitude(row['Magnitude']))
                ).add_to(target_map)
            
            st_folium(m, width='100%', height=500)

        with data_col:
            st.subheader("Data Detail (Filter)")
            display_cols = ['DateTime', 'Magnitude', 'Wilayah']
            if 'Kedalaman' in df_filtered.columns:
                display_cols.insert(2, 'Kedalaman')
            
            df_display = df_filtered[display_cols].copy()
            df_display['DateTime'] = df_display['DateTime'].dt.strftime('%d-%b-%Y %H:%M:%S')
            st.dataframe(df_display, use_container_width=True)
