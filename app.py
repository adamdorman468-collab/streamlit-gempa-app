# ======================================================================================
# PUSAT INFORMASI GEMPA BUMI - Versi 4.1 
# ======================================================================================

import streamlit as st
import pandas as pd
import requests
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from datetime import datetime, timezone, timedelta
import time
import locale

# ---------------------------------------------------------------------
# Konfigurasi halaman
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Pusat Informasi Gempa Indonesia",
    page_icon="🌋",
    layout="wide",
)

try:
    locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
except locale.Error:
    st.sidebar.warning("Lokal 'id_ID' tidak ditemukan. (Melanjutkan tanpa locale id_ID)")

# ---------------------------------------------------------------------
# Konstanta & sumber data
# ---------------------------------------------------------------------
BMKG_API_BASE_URL = "https://data.bmkg.go.id/DataMKG/TEWS/"
DATA_SOURCES = {
    "Gempa Dirasakan": "gempadirasakan.json",
    "Gempa Terbaru M 5.0+": "gempaterkini.json",
    "Gempa Real-time": "autogempa.json"
}
ALL_COLUMNS = ['DateTime', 'Coordinates', 'Latitude', 'Longitude', 'Magnitude', 'Kedalaman', 'Wilayah', 'Potensi', 'Dirasakan', 'Shakemap', 'Tanggal', 'Jam']

# ---------------------------------------------------------------------
# Fungsi pembantu
# ---------------------------------------------------------------------
def get_color_from_magnitude(magnitude):
    try:
        mag = float(magnitude)
    except Exception:
        return 'gray'
    if mag < 4.0:
        return 'green'
    elif 4.0 <= mag < 6.0:
        return 'orange'
    else:
        return 'red'

@st.cache_data(ttl=60)
def get_data_gempa(file_name):
    url = f"{BMKG_API_BASE_URL}{file_name}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        # strukture response BMKG beberapa kali berbeda, robust parsing:
        gempa_data_raw = data.get('Infogempa', {}).get('gempa', [])
        data_for_df = [gempa_data_raw] if isinstance(gempa_data_raw, dict) else gempa_data_raw

        if not data_for_df:
            return pd.DataFrame()

        df = pd.DataFrame(data_for_df)

        # pastikan kolom ada
        for col in ALL_COLUMNS:
            if col not in df.columns:
                df[col] = pd.NA

        # DateTime
        df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')

        # Coordinates -> Latitude, Longitude (lebih aman)
        coords = df['Coordinates'].fillna('').astype(str).str.split(',', n=1, expand=True)
        df['Latitude'] = pd.to_numeric(coords[0], errors='coerce')
        df['Longitude'] = pd.to_numeric(coords[1], errors='coerce')

        # Magnitude dan kedalaman
        df['Magnitude'] = pd.to_numeric(df['Magnitude'], errors='coerce')
        df['KedalamanValue'] = pd.to_numeric(df['Kedalaman'].astype(str).str.extract(r'(\d+\.?\d*)')[0], errors='coerce')

        # Tanggal/Jam fallback
        if 'Tanggal' not in df.columns or df['Tanggal'].isna().all():
            df['Tanggal'] = df['DateTime'].dt.strftime('%Y-%m-%d')
        if 'Jam' not in df.columns or df['Jam'].isna().all():
            df['Jam'] = df['DateTime'].dt.strftime('%H:%M:%S WIB')

        df['Waktu Kejadian'] = df['DateTime'].dt.strftime('%Y-%m-%d %H:%M:%S')
        # buang baris tanpa info minimum
        df.dropna(subset=['DateTime', 'Latitude', 'Longitude', 'Magnitude'], inplace=True)

        # urutkan descending berdasarkan DateTime (paling baru di atas)
        df.sort_values('DateTime', ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    except Exception:
        return pd.DataFrame()

# ---------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------
with st.sidebar:
    st.title("👨‍💻 Tentang Author")
    # ganti path gambar sesuai environmentmu
    try:
        st.image("adam_dorman_profile.jpg", use_container_width=True, caption="Adam Dorman - 2025")
    except Exception:
        st.write("_Gambar profil tidak ditemukan (adam_dorman_profile.jpg)_")

    st.markdown("""
    **Adam Dorman**  
    Mahasiswa S1 Sistem Informasi, UPN Veteran Jakarta Angkatan 2024
    - [LinkedIn](https://www.linkedin.com/in/adamdorman68/) 
    - [Instagram](https://www.instagram.com/adam_abu_umar?igsh=OGQ5ZDc2ODk2ZA==)
    - [GitHub](https://github.com/adamdorman468-collab)
    """)
    st.divider()
    st.title("⚙️ Kontrol & Pengaturan")

    selected_data_name = st.selectbox("Pilih Sumber Data:", options=list(DATA_SOURCES.keys()))
    selected_file_name = DATA_SOURCES[selected_data_name]

    if st.button("🔄 Refresh Data"):
        try:
            # clear cached data
            st.cache_data.clear()
        except Exception:
            pass
        st.rerun()

    st.info(f"Data terakhir di-cache: {datetime.now(timezone(timedelta(hours=7))).strftime('%H:%M:%S WIB')}")

    st.divider()
    APP_VERSION = "4.2"
    st.markdown(f"**🌋 Versi Aplikasi: {APP_VERSION}**")

# ---------------------------------------------------------------------
# Tampilan Utama
# ---------------------------------------------------------------------
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.title("Pusat Informasi Gempa Indonesia")
    st.markdown(f"**{datetime.now(timezone(timedelta(hours=7))).strftime('%A, %d %B %Y')}**")
with col2:
    wib_placeholder = st.empty()
with col3:
    utc_placeholder = st.empty()

st.markdown(f"Menampilkan: **{selected_data_name}** | Sumber: [API Publik BMKG](https://data.bmkg.go.id/)")
st.divider()

# ambil data
df_gempa = get_data_gempa(selected_file_name)

if df_gempa.empty:
    st.error("Gagal memuat data dari BMKG atau data kosong. Coba refresh atau pilih sumber data lain di sidebar.")
else:
    # state management untuk source & filter
    min_mag = float(df_gempa['Magnitude'].min())
    max_mag = float(df_gempa['Magnitude'].max())

    # reset saat sumber berubah
    if st.session_state.get('data_source') != selected_file_name:
        # default filter = full range
        st.session_state.mag_filter = (min_mag, max_mag)
        st.session_state.data_source = selected_file_name

    if 'mag_filter' not in st.session_state:
        st.session_state.mag_filter = (min_mag, max_mag)

    # filter UI
    filter_col1, filter_col2 = st.columns([3, 1])
    with filter_col1:
        st.write("**Filter Magnitudo**")
        # checkbox quick filter >=5.0
        only_ge_5 = st.checkbox("Tampilkan hanya Magnitudo ≥ 5.0", value=False)

        # jika semua magnitudo sama (min==max), jangan buat slider yang error -> gunakan number_input
        if min_mag == max_mag:
            st.info(f"Hanya ditemukan satu nilai magnitudo: {min_mag:.1f}. Gunakan input untuk memilih nilai.")
            mag_val = st.number_input(
                "Magnitudo (satu nilai):",
                min_value=min_mag,
                max_value=max_mag,
                value=min_mag,
                format="%.1f"
            )
            # simpan sebagai tuple konsisten
            mag_filter_values = (float(mag_val), float(mag_val))
        else:
            # normal case: range slider
            # tentukan step sensibel (0.1)
            step = 0.1
            # ambil current safe value dari state
            current_filter_value = st.session_state.get('mag_filter', (min_mag, max_mag))
            # sanitize current value agar dalam rentang
            low = max(min(current_filter_value[0], max_mag), min_mag)
            high = max(min(current_filter_value[1], max_mag), min_mag)
            if low > high:
                low, high = min_mag, max_mag

            mag_filter_values = st.slider(
                "Saring berdasarkan Magnitudo (rentang):",
                min_value=min_mag,
                max_value=max_mag,
                value=(low, high),
                step=step
            )

        # jika user ingin hanya >=5.0, override filter
        if only_ge_5:
            mag_filter_values = (5.0, max_mag)

        # simpan ke session
        st.session_state.mag_filter = mag_filter_values

    with filter_col2:
        st.write("")
        if st.button("Reset Filter"):
            st.session_state.mag_filter = (min_mag, max_mag)
            st.rerun()

    # aplikasikan filter ke dataframe (toleransi float)
    low, high = st.session_state.mag_filter
    df_filtered = df_gempa[(df_gempa['Magnitude'] >= float(low) - 1e-9) & (df_gempa['Magnitude'] <= float(high) + 1e-9)]

    # show results
    if df_filtered.empty:
        st.warning("Tidak ada data yang sesuai filter.")
    else:
        gempa_terbaru = df_filtered.iloc[0]

        st.header(f"Guncangan Terkini: {gempa_terbaru.get('Wilayah', 'N/A')}")
        detail_col1, detail_col2 = st.columns(2)
        with detail_col1:
            st.metric("Waktu Kejadian (WIB)", gempa_terbaru['DateTime'].strftime('%H:%M:%S'))
            st.metric("Magnitudo", f"{gempa_terbaru.get('Magnitude')}")
            potensi = gempa_terbaru.get('Potensi')
            if pd.notna(potensi):
                if "tidak" in str(potensi).lower():
                    st.success(f"✅ {potensi}")
                else:
                    st.error(f"🚨 {potensi}")

        with detail_col2:
            st.metric("Tanggal", gempa_terbaru.get('Tanggal'))
            st.metric("Kedalaman", f"{gempa_terbaru.get('Kedalaman')}")

        shakemap = gempa_terbaru.get('Shakemap')
        if pd.notna(shakemap) and str(shakemap).strip():
            try:
                st.image(f"https://data.bmkg.go.id/DataMKG/TEWS/{shakemap}", caption="Peta Skala Intensitas Guncangan (MMI)", use_container_width='auto')
            except Exception:
                pass

        st.divider()

        st.subheader("Ringkasan Statistik")
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        stat_col1.metric("Jumlah Gempa Tampil", f"{len(df_filtered)} kejadian")
        stat_col2.metric("Magnitudo Terkuat", f"{df_filtered['Magnitude'].max():.1f}")
        if 'KedalamanValue' in df_filtered.columns and not df_filtered['KedalamanValue'].dropna().empty:
            stat_col3.metric("Gempa Terdangkal", f"{int(df_filtered['KedalamanValue'].min())} km")

        map_col, data_col = st.columns([2, 1])
        with map_col:
            st.subheader("Peta Persebaran Gempa")
            m = folium.Map(location=[gempa_terbaru['Latitude'], gempa_terbaru['Longitude']], zoom_start=6)
            mc = MarkerCluster().add_to(m)

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
                ).add_to(mc)
            st_folium(m, width='100%', height=500)

        with data_col:
            st.subheader("Data Detail")
            st.dataframe(df_filtered[['Waktu Kejadian', 'Magnitude', 'Kedalaman', 'Wilayah', 'Potensi']])

# ---------------------------------------------------------------------
# Waktu (tidak blocking)
# ---------------------------------------------------------------------
# Tampilkan waktu sekarang. Hindari while True yang mem-block Streamlit.
wib = timezone(timedelta(hours=7))
utc = timezone.utc
wib_placeholder.metric("WIB", datetime.now(wib).strftime("%H:%M:%S"))
utc_placeholder.metric("UTC", datetime.now(utc).strftime("%H:%M:%S"))
st.caption("Tekan tombol '🔄 Refresh Data' di sidebar untuk memperbarui data dan waktu.")
