# ======================================================================================
# PUSAT INFORMASI GEMPA BUMI - Versi 6.0 (Heatmap & Shakemap Integration)
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
    "Gempa Dirasakan (Paling Lengkap)": "gempadirasakan.json",
    "Gempa Terbaru M 5.0+": "gempaterkini.json",
    "Gempa Real-time (Otomatis)": "autogempa.json"
}
APP_VERSION = "6.0"

# ---------------------------------------------------------------------
# Bagian 2: Fungsi-fungsi Bantuan
# ---------------------------------------------------------------------
def get_color_from_magnitude(magnitude):
    if not isinstance(magnitude, (int, float)): return 'gray'
    if magnitude < 4.0: return 'green'
    elif 4.0 <= magnitude < 6.0: return 'orange'
    else: return 'red'

def display_realtime_clock():
    # ... (Fungsi ini tidak berubah)
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
        df = pd.DataFrame([gempa_data_raw] if isinstance(gempa_data_raw, dict) else gempa_data_raw)
        if df.empty: return pd.DataFrame()

        # Data Cleaning yang lebih tangguh
        df['DateTime'] = pd.to_datetime(df.get('DateTime'), errors='coerce')
        if 'Coordinates' in df.columns:
            coords = df['Coordinates'].str.split(',', expand=True)
            df['Latitude'] = pd.to_numeric(coords[0], errors='coerce')
            df['Longitude'] = pd.to_numeric(coords[1], errors='coerce')
        
        df['Magnitude'] = pd.to_numeric(df.get('Magnitude'), errors='coerce')
        if 'Kedalaman' in df.columns:
            df['KedalamanValue'] = pd.to_numeric(df['Kedalaman'].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
        else:
            df['KedalamanValue'] = 0

        # --- FITUR BARU: Parsing URL Shakemap ---
        if 'Shakemap' in df.columns:
            df['ShakemapURL'] = df['Shakemap'].apply(lambda x: f"https://data.bmkg.go.id/DataMKG/TEWS/{x}" if isinstance(x, str) and x.endswith('.jpg') else None)
        else:
            df['ShakemapURL'] = None
            
        df['Waktu Kejadian'] = df['DateTime'].dt.strftime('%Y-%m-%d %H:%M:%S')
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
    st.markdown("[LinkedIn](https://www.linkedin.com/in/adamdorman68/) | [GitHub](https://github.com/adamdorman468-collab)")
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
    sort_by = st.selectbox( "Urutkan Data Tabel Berdasarkan:", ("Waktu Terbaru", "Magnitudo Terkuat", "Paling Dangkal"))

    if not df_for_filters.empty and 'KedalamanValue' in df_for_filters.columns and df_for_filters['KedalamanValue'].notna().any():
        min_depth, max_depth = int(df_for_filters['KedalamanValue'].min()), int(df_for_filters['KedalamanValue'].max())
        if min_depth >= max_depth:
             depth_filter_values = (min_depth, max_depth)
        else:
            depth_filter_values = st.slider("Saring berdasarkan kedalaman (km):", min_value=min_depth, max_value=max_depth, value=(min_depth, max_depth))
    else:
        depth_filter_values = (0, 700) 

    st.divider()
    st.markdown("#### Opsi Peta")
    use_clustering = st.checkbox("Kelompokkan gempa (clustering)", value=True)
    # --- FITUR BARU: Kontrol Heatmap & Shakemap ---
    show_heatmap = st.checkbox("Tampilkan Heatmap", value=False)
    show_shakemap = st.checkbox("Tampilkan Shakemap BMKG (jika ada)", value=False)
    
    st.divider()
    st.markdown("#### Informasi Tambahan")
    st.markdown("- **[Info Gempa BMKG](https://www.bmkg.go.id/gempabumi/gempabumi-dirasakan.bmkg)**")
    st.markdown("- **[Skala MMI](https://www.bmkg.go.id/gempabumi/skala-mmi.bmkg)**") # <-- FITUR BARU
    st.markdown("---")
    st.markdown("**Legenda Warna Peta:**")
    st.markdown("<span style='color:green'>🟢</span> M < 4.0", unsafe_allow_html=True)
    st.markdown("<span style='color:orange'>🟠</span> 4.0 ≤ M < 6.0", unsafe_allow_html=True)
    st.markdown("<span style='color:red'>🔴</span> M ≥ 6.0", unsafe_allow_html=True)

    st.divider()
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

if not df_gempa.empty:
    df_tampil = df_gempa.copy()
    
    min_mag, max_mag = float(df_tampil['Magnitude'].min()), float(df_tampil['Magnitude'].max())
    
    if min_mag >= max_mag:
        mag_filter_values = (min_mag, max_mag)
    else:
        if st.session_state.get('data_source') != selected_file_name: st.session_state.pop('mag_filter', None)
        st.session_state.data_source = selected_file_name
        current_filter_value = st.session_state.get('mag_filter', (min_mag, max_mag))
        if not (min_mag <= current_filter_value[0] <= max_mag and min_mag <= current_filter_value[1] <= max_mag):
            current_filter_value = (min_mag, max_mag)
        
        filter_col1, filter_col2 = st.columns([3, 1])
        with filter_col1:
            mag_filter_values = st.slider("Saring berdasarkan Magnitudo:", min_value=min_mag, max_value=max_mag, value=current_filter_value)
            st.session_state.mag_filter = mag_filter_values
        with filter_col2:
            st.write(""); 
            if st.button("Reset Filter"): st.session_state.mag_filter = (min_mag, max_mag); st.rerun()

    df_filtered = df_tampil[
        (df_tampil['Magnitude'].between(*mag_filter_values)) &
        (df_tampil['KedalamanValue'].between(*depth_filter_values))
    ]

    if sort_by == "Magnitudo Terkuat": df_filtered = df_filtered.sort_values(by='Magnitude', ascending=False)
    elif sort_by == "Paling Dangkal": df_filtered = df_filtered.sort_values(by='KedalamanValue', ascending=True)
    else: df_filtered = df_filtered.sort_values(by='DateTime', ascending=False)

    if not df_filtered.empty:
        gempa_terbaru = df_filtered.iloc[0]
        
        map_col, data_col = st.columns([2, 1])
        with map_col:
            st.subheader("Peta Persebaran Gempa")
            map_center = [gempa_terbaru['Latitude'], gempa_terbaru['Longitude']]
            m = folium.Map(location=map_center, zoom_start=5)
            
            # --- FITUR BARU: Logika Layer Peta ---
            
            # 1. Layer Marker (tetap ada)
            if use_clustering:
                marker_layer = MarkerCluster(name="Gempa (Cluster)").add_to(m)
            else:
                marker_layer = folium.FeatureGroup(name="Gempa").add_to(m)

            for _, row in df_filtered.iterrows():
                popup_text = f"<b>{row.get('Wilayah')}</b><br>M: {row.get('Magnitude')}<br>Kedalaman: {row.get('Kedalaman')}"
                folium.Marker(
                    location=[row['Latitude'], row['Longitude']],
                    popup=popup_text,
                    tooltip=f"M: {row.get('Magnitude')} - {row.get('Wilayah')}",
                    icon=folium.Icon(color=get_color_from_magnitude(row['Magnitude']))
                ).add_to(marker_layer)
            
            # 2. Layer Heatmap (jika diaktifkan)
            if show_heatmap:
                heat_data = [[row['Latitude'], row['Longitude']] for _, row in df_filtered.iterrows()]
                HeatMap(heat_data, name="Heatmap Kepadatan").add_to(m)

            # 3. Layer Shakemap (jika diaktifkan & tersedia)
            if show_shakemap:
                shakemap_candidate = df_filtered[df_filtered['ShakemapURL'].notna()].iloc[0] if not df_filtered[df_filtered['ShakemapURL'].notna()].empty else None
                if shakemap_candidate is not None:
                    lat, lon, mag = shakemap_candidate['Latitude'], shakemap_candidate['Longitude'], shakemap_candidate['Magnitude']
                    # Heuristik bounds yang simpel
                    delta = 0.1 * (1.8 ** mag) / 2
                    bounds = [[lat - delta, lon - delta], [lat + delta, lon + delta]]
                    try:
                        folium.raster_layers.ImageOverlay(
                            name="Shakemap BMKG", image=shakemap_candidate['ShakemapURL'],
                            bounds=bounds, opacity=0.7, interactive=True, cross_origin=False
                        ).add_to(m)
                    except Exception as e:
                        st.warning(f"Gagal menampilkan overlay Shakemap: {e}")

            # Selalu tambahkan kontrol layer
            folium.LayerControl().add_to(m)
            
            st_folium(m, width='100%', height=500, returned_objects=[])

        with data_col:
            st.subheader("Data Detail Gempa")
            df_display = df_filtered.copy()
            df_display['Waktu Kejadian'] = df_display['DateTime'].dt.strftime('%d-%b, %H:%M:%S')
            st.dataframe(df_display[['Waktu Kejadian', 'Magnitude', 'Kedalaman', 'Wilayah']])
    else:
        st.warning("Tidak ada data yang sesuai dengan filter Anda.")
else:
    st.error("Gagal memuat data dari BMKG. Silakan coba refresh atau pilih sumber data lain.")
