# ======================================================================================
# PUSAT INFORMASI GEMPA BUMI - Versi 5.1 (Dengan Perbaikan Stabilitas)
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
    """Membuat komponen HTML untuk jam digital yang berjalan di browser."""
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
        df[['Latitude', 'Longitude']] = df['Coordinates'].str.split(',', expand=True, n=1).astype(float)
        df['Magnitude'] = pd.to_numeric(df['Magnitude'], errors='coerce')
        df['KedalamanValue'] = pd.to_numeric(df['Kedalaman'].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
        
        if 'Tanggal' not in df.columns or df['Tanggal'].isna().all():
            df['Tanggal'] = df['DateTime'].dt.strftime('%Y-%m-%d')
        if 'Jam' not in df.columns or df['Jam'].isna().all():
            df['Jam'] = df['DateTime'].dt.strftime('%H:%M:%S WIB')
        
        df['Waktu Kejadian'] = df['DateTime'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df.dropna(subset=['DateTime', 'Latitude', 'Longitude', 'Magnitude'], inplace=True)
        return df
        
    except Exception:
        return pd.DataFrame()

# ---------------------------------------------------------------------
# Bagian 4: Tampilan Sidebar (Dengan Fitur Baru)
# ---------------------------------------------------------------------
with st.sidebar:
    st.title("👨‍💻 Tentang Author")
    st.image("adam_dorman_profile.jpg", use_column_width=True, caption="Adam Dorman")
    st.markdown("""
    **Adam Dorman**
    Mahasiswa S1 Sistem Informasi, UPN Veteran Jakarta
    [LinkedIn](https://www.linkedin.com/in/adamdorman68/) | [Instagram](https://www.instagram.com/adam_abu_umar?igsh=OGQ5ZDc2ODk2ZA==) | [GitHub](https://github.com/adamdorman468-collab)
    """)
    st.divider()
    st.title("⚙️ Kontrol & Pengaturan")
    
    selected_data_name = st.selectbox("Pilih Sumber Data:", options=list(DATA_SOURCES.keys()))
    selected_file_name = DATA_SOURCES[selected_data_name]

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.info(f"Data terakhir diperbarui: {datetime.now(timezone(timedelta(hours=7))).strftime('%H:%M:%S WIB')}")

    # --- FITUR BARU DI SIDEBAR ---
    df_for_filters = get_data_gempa(selected_file_name) # Ambil data untuk inisialisasi filter
    
    st.divider()
    sort_by = st.selectbox(
        "Urutkan Data Tabel Berdasarkan:",
        ("Waktu Terbaru", "Magnitudo Terkuat", "Paling Dangkal")
    )
    
       # --- PERBAIKAN FINAL UNTUK FILTER KEDALAMAN ---
    st.divider()
    st.write("**Filter Kedalaman (km)**")
    
    # Cek apakah data dan kolom 'KedalamanValue' ada dan berisi nilai valid
    if not df_for_filters.empty and 'KedalamanValue' in df_for_filters.columns and df_for_filters['KedalamanValue'].notna().any():
        min_depth = int(df_for_filters['KedalamanValue'].min())
        max_depth = int(df_for_filters['KedalamanValue'].max())
        
        # KASUS KRITIS: Jika semua data punya kedalaman yang sama
        if min_depth >= max_depth:
            st.info(f"Semua gempa memiliki kedalaman {min_depth} km. Filter nonaktif.")
            # Buat variabel agar tidak error, tapi jangan tampilkan slider
            depth_filter_values = (min_depth, max_depth)
        else:
            # Jika semua normal, tampilkan slider
            depth_filter_values = st.slider(
                "Saring berdasarkan kedalaman:",
                min_value=min_depth,
                max_value=max_depth,
                value=(min_depth, max_depth)
            )
    else:
        # KASUS JIKA DATA KOSONG ATAU TIDAK ADA INFO KEDALAMAN
        st.warning("Data kedalaman tidak tersedia untuk filter.")
        # Buat variabel default agar tidak error
        depth_filter_values = (0, 700)
    # --- PERBAIKAN SELESAI ---
    
    st.divider()
    use_clustering = st.checkbox("Kelompokkan gempa di peta (clustering)", value=True, help="Aktifkan untuk performa lebih baik saat data banyak.")

    st.divider()
    st.markdown("#### Informasi Tambahan")
    st.markdown("- **[Info Gempa BMKG](https://www.bmkg.go.id/gempabumi/gempabumi-dirasakan.bmkg)**")
    st.markdown("- **[Skala MMI](https://www.bmkg.go.id/gempabumi/skala-mmi.bmkg)**")
    st.markdown("---")
    st.markdown("**Legenda Warna Peta:**")
    st.markdown("<span style='color:green'>🟢</span> Magnitudo < 4.0", unsafe_allow_html=True)
    st.markdown("<span style='color:orange'>🟠</span> Magnitudo 4.0 - 5.9", unsafe_allow_html=True)
    st.markdown("<span style='color:red'>🔴</span> Magnitudo ≥ 6.0", unsafe_allow_html=True)

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

    # --- PERBAIKAN LOGIKA RESET FILTER MAGNITUDO ---
    # Cek apakah sumber data telah berubah
    if st.session_state.get('data_source') != selected_file_name:
        # Jika berubah, hapus nilai filter lama dan simpan sumber data baru
        st.session_state.pop('mag_filter', None)
        st.session_state.data_source = selected_file_name

    # Dapatkan nilai filter dari session state, atau gunakan rentang penuh jika tidak ada
    current_filter_value = st.session_state.get('mag_filter', (min_mag, max_mag))

    # Pastikan nilai filter lama valid untuk rentang baru, jika tidak, reset
    if not (min_mag <= current_filter_value[0] <= max_mag and min_mag <= current_filter_value[1] <= max_mag):
        current_filter_value = (min_mag, max_mag)
    # --- PERBAIKAN SELESAI ---

    filter_col1, filter_col2 = st.columns([3, 1])
    with filter_col1:
        # Buat slider dengan nilai yang sudah dijamin valid
        mag_filter_values = st.slider("Saring berdasarkan Magnitudo:", min_value=min_mag, max_value=max_mag, value=current_filter_value)
        # Simpan nilai slider terbaru ke session state
        st.session_state.mag_filter = mag_filter_values
    
    # Menerapkan semua filter
    df_filtered = df_tampil[
        (df_tampil['Magnitude'] >= mag_filter_values[0]) & 
        (df_tampil['Magnitude'] <= mag_filter_values[1]) &
        (df_tampil['KedalamanValue'] >= depth_filter_values[0]) &
        (df_tampil['KedalamanValue'] <= depth_filter_values[1])
    ]

    # Menerapkan pengurutan
    if sort_by == "Magnitudo Terkuat":
        df_filtered = df_filtered.sort_values(by='Magnitude', ascending=False)
    elif sort_by == "Paling Dangkal":
        df_filtered = df_filtered.sort_values(by='KedalamanValue', ascending=True)
    else: # Default "Waktu Terbaru"
        df_filtered = df_filtered.sort_values(by='DateTime', ascending=False)

    if not df_filtered.empty:
        gempa_terbaru = df_filtered.iloc[0]
        
        # ... (Sisa kode untuk detail, statistik, shakemap tetap sama) ...
        
        map_col, data_col = st.columns([2, 1])
        with map_col:
            st.subheader("Peta Persebaran Gempa")
            map_center = [gempa_terbaru['Latitude'], gempa_terbaru['Longitude']]
            m = folium.Map(location=map_center, zoom_start=5)
            
            # Logika untuk clustering on/off
            if use_clustering:
                mc = MarkerCluster().add_to(m)
                target_map = mc # Tambahkan marker ke cluster
            else:
                target_map = m # Tambahkan marker langsung ke peta

            for _, row in df_filtered.iterrows():
                popup_text = f"""<b>{row.get('Wilayah')}</b><br>
                                 Magnitudo: {row.get('Magnitude')}<br>
                                 Kedalaman: {row.get('Kedalaman')}<br><hr>
                                 Dirasakan (MMI):<br>{row.get('Dirasakan')}"""
                folium.Marker(
                    location=[row['Latitude'], row['Longitude']],
                    popup=popup_text,
                    tooltip=f"Mag: {row.get('Magnitude')} - {row.get('Wilayah')}",
                    icon=folium.Icon(color=get_color_from_magnitude(row['Magnitude']))
                ).add_to(target_map)
            
            st_folium(m, width='100%', height=500)

        with data_col:
            st.subheader("Data Detail")
            st.dataframe(df_filtered[['Waktu Kejadian', 'Magnitude', 'Kedalaman', 'Wilayah']])
    else:
        st.warning("Tidak ada data yang sesuai dengan filter Anda.")
else:
    st.error("Gagal memuat data dari BMKG. Silakan coba refresh atau pilih sumber data lain.")



