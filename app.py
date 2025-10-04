# ======================================================================================
# PUSAT INFORMASI GEMPA BUMI - Versi 7.0 (PRO UPGRADE)
# Dibuat oleh: Adam Dorman (Mahasiswa S1 Sistem Informasi UPNVJ)
# Fitur utama: single-dashboard stats, BMKG shakemap overlay, heatmap, dark/light tiles,
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
import math

# ---------------------------------------------------------------------
# Konfigurasi & Konstanta
# ---------------------------------------------------------------------
st.set_page_config(page_title="Pusat Informasi Gempa Indonesia", page_icon="🌋", layout="wide")
try:
    locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
except locale.Error:
    # Jangan crash - beri warning ringan
    st.sidebar.warning("Lokal 'id_ID' tidak ditemukan. Tanggal akan ditampilkan standar.")

BMKG_API_BASE_URL = "https://data.bmkg.go.id/DataMKG/TEWS/"
DATA_SOURCES = {
    "Gempa Dirasakan (Lengkap)": "gempadirasakan.json",
    "Gempa Terbaru M 5.0+": "gempaterkini.json",
    "Gempa Real-time (Otomatis)": "autogempa.json"
}
APP_VERSION = "7.0"

# ---------------------------------------------------------------------
# Fungsi bantu
# ---------------------------------------------------------------------
def get_color_from_magnitude(magnitude):
    try:
        m = float(magnitude)
    except Exception:
        return 'gray'
    if m < 4.0: return 'green'
    if m < 6.0: return 'orange'
    return 'red'

def small_toast_js(message, level='info', duration=4500):
    """Microinteraction: toast notification (JS/CSS)"""
    escaped = message.replace("'", "\\'")
    html = f"""
    <div id="toast-root" style="position:fixed;top:1rem;right:1rem;z-index:99999;"></div>
    <script>
    (function() {{
      const root = document.getElementById('toast-root');
      const toast = document.createElement('div');
      toast.innerText = '{escaped}';
      toast.style = "background:rgba(30,30,30,0.9);color:white;padding:12px 18px;border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,0.25);font-family:Inter,Segoe UI,Roboto,sans-serif;opacity:0;transform:translateY(-10px);transition:all 350ms;";
      root.appendChild(toast);
      requestAnimationFrame(()=>{{ toast.style.opacity=1; toast.style.transform='translateY(0)'; }});
      setTimeout(()=>{{ toast.style.opacity=0; toast.style.transform='translateY(-10px)'; setTimeout(()=>toast.remove(), 350); }}, {duration});
    }})();
    </script>
    """
    components.html(html, height=0)

def create_stat_cards_html(stats: dict):
    """Return HTML block with responsive stat cards (no st.columns)."""
    # stats = {'Total': 10, 'Max M': '6.2', ...}
    cards_html = """
    <style>
      .dash-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(180px,1fr)); gap:12px; margin-bottom:10px; }
      .card { background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)); 
              padding:14px; border-radius:12px; box-shadow:0 6px 20px rgba(2,6,23,0.35); color:#fff; font-family:Inter,Segoe UI,Roboto,sans-serif; min-height:72px;
              transition: transform .18s ease, box-shadow .18s ease;}
      .card:hover { transform: translateY(-6px); box-shadow:0 10px 30px rgba(2,6,23,0.55); }
      .card .label { font-size:0.85rem; color:#cbd5e1; }
      .card .value { font-size:1.35rem; font-weight:700; margin-top:6px; }
    </style>
    <div class="dash-grid">
    """
    for k, v in stats.items():
        cards_html += f"""
        <div class="card">
            <div class="label">{k}</div>
            <div class="value">{v}</div>
        </div>
        """
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
        data_for_df = [gempa_data_raw] if isinstance(gempa_data_raw, dict) else gempa_data_raw
        if not data_for_df:
            return pd.DataFrame()
        df = pd.DataFrame(data_for_df)
        # pastikan kolom
        cols_needed = ['DateTime','Coordinates','Latitude','Longitude','Magnitude','Kedalaman','Wilayah','Potensi','Dirasakan','Shakemap','Tanggal','Jam']
        for c in cols_needed:
            if c not in df.columns:
                df[c] = pd.NA
        df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
        # Coordinates kadang string 'lat,lon' - kalau tidak, gunakan kolom Latitude/Longitude
        if df['Coordinates'].notna().any():
            try:
                df[['Latitude','Longitude']] = df['Coordinates'].str.split(',', expand=True, n=1).astype(float)
            except Exception:
                # fallback: try using existing Latitude/Longitude if numeric
                pass
        # Convert magnitude & kedalaman
        df['Magnitude'] = pd.to_numeric(df['Magnitude'], errors='coerce')
        df['KedalamanValue'] = pd.to_numeric(df['Kedalaman'].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
        # Ensure Tanggal/Jam/Waktu Kejadian
        df['Tanggal'] = df['DateTime'].dt.strftime('%Y-%m-%d')
        df['Jam'] = df['DateTime'].dt.strftime('%H:%M:%S WIB')
        df['Waktu Kejadian'] = df['DateTime'].dt.strftime('%Y-%m-%d %H:%M:%S')
        # Drop rows missing essentials
        df.dropna(subset=['DateTime','Latitude','Longitude','Magnitude'], inplace=True)
        # Normalize Shakemap field (bisa dict/url/empty)
        def extract_shakemap(val):
            if isinstance(val, dict):
                # BMKG kadang kirim dict {'image':'url', ...}
                return val.get('image') or val.get('shakemap') or None
            if isinstance(val, str) and val.strip():
                return val.strip()
            return None
        df['ShakemapURL'] = df['Shakemap'].apply(extract_shakemap) if 'Shakemap' in df.columns else None
        return df
    except Exception:
        return pd.DataFrame()

# ---------------------------------------------------------------------
# Sidebar modern: kontrol dan filter (dengan auto-reset saat ganti source)
# ---------------------------------------------------------------------
with st.sidebar:
    st.title("👨‍💻 Tentang Author")
    st.image("adam_dorman_profile.jpg", use_container_width=True, caption="Adam Dorman")
    st.markdown("""
    **Adam Dorman**  
    S1 Sistem Informasi - UPNVJ  
    [LinkedIn](https://www.linkedin.com/in/adamdorman68/) | [GitHub](https://github.com/adamdorman468-collab)
    """)
    st.markdown("---")
    st.header("Kontrol Aplikasi")
    selected_data_name = st.selectbox("Pilih Sumber Data", options=list(DATA_SOURCES.keys()))
    selected_file_name = DATA_SOURCES[selected_data_name]

    # Auto-reset state when data source changes
    if 'last_data_source' not in st.session_state or st.session_state['last_data_source'] != selected_file_name:
        st.session_state['last_data_source'] = selected_file_name
        # reset filters
        st.session_state.pop('mag_filter', None)
        st.session_state.pop('depth_filter', None)

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.experimental_rerun()

    st.info(f"Versi: {APP_VERSION} • Last fetch: {datetime.now(timezone(timedelta(hours=7))).strftime('%H:%M:%S WIB')}")

    # get data for initializing filter controls
    df_filters = get_data_gempa(selected_file_name)

    # Magnitude filter - safe defaults
    if not df_filters.empty:
        try:
            min_mag = float(df_filters['Magnitude'].min())
            max_mag = float(df_filters['Magnitude'].max())
        except Exception:
            min_mag, max_mag = 0.0, 10.0
    else:
        min_mag, max_mag = 0.0, 10.0

    if 'mag_filter' not in st.session_state:
        st.session_state.mag_filter = (min_mag, max_mag)
    mag_filter = st.slider("Filter Magnitudo", min_value=min_mag, max_value=max_mag, value=st.session_state.mag_filter, step=0.1)
    st.session_state.mag_filter = mag_filter

    # Depth filter
    if not df_filters.empty and df_filters['KedalamanValue'].notna().any():
        min_depth = int(df_filters['KedalamanValue'].min())
        max_depth = int(df_filters['KedalamanValue'].max())
        if min_depth == max_depth:
            depth_filter = (min_depth, max_depth)
            st.info(f"Semua data kedalaman = {min_depth} km")
        else:
            if 'depth_filter' not in st.session_state:
                st.session_state.depth_filter = (min_depth, max_depth)
            depth_filter = st.slider("Filter Kedalaman (km)", min_value=min_depth, max_value=max_depth, value=st.session_state.depth_filter)
            st.session_state.depth_filter = depth_filter
    else:
        depth_filter = (0, 700)  # safe fallback
        st.caption("Data kedalaman tidak tersedia — menggunakan default 0–700 km")

    # Map & view options
    st.markdown("---")
    tile_mode = st.selectbox("Tema Peta", options=["Light (default)","Dark (kontras tinggi)"])
    use_clustering = st.checkbox("Gunakan Clustering untuk marker", value=True)
    show_heatmap = st.checkbox("Tampilkan Heatmap (point-based)", value=True)
    show_shakemap_overlay = st.checkbox("Overlay Shakemap BMKG (jika tersedia)", value=True)
    alert_threshold = st.number_input("Alert jika M ≥", min_value=0.0, max_value=10.0, value=6.0, step=0.1, format="%.1f")
    st.markdown("---")
    st.caption("Hint: fitur shakemap membutuhkan URL image dari API BMKG. Jika CORS/akses dibatasi, overlay bisa gagal di browser — lihat logs / proxy jika perlu.")
    st.markdown("---")
    st.write(f"Versi Aplikasi: **{APP_VERSION}**")

# ---------------------------------------------------------------------
# Main UI (container + tabs) — modern layout, satu layar statistik ringkas
# ---------------------------------------------------------------------
header = st.container()
with header:
    st.markdown("## 🌋 Pusat Informasi Gempa Indonesia")
    st.markdown(f"**{datetime.now(timezone(timedelta(hours=7))).strftime('%A, %d %B %Y')}**")
    st.caption(f"Sumber: API Publik BMKG • Menampilkan: **{selected_data_name}**")

# fetch main data
df_gempa = get_data_gempa(selected_file_name)

if df_gempa.empty:
    st.error("Gagal memuat data gempa dari BMKG (kosong). Coba refresh atau pilih sumber lain.")
else:
    # Terapkan filter mag & depth
    df_filtered = df_gempa[
        (df_gempa['Magnitude'] >= mag_filter[0]) &
        (df_gempa['Magnitude'] <= mag_filter[1]) &
        (df_gempa['KedalamanValue'] >= depth_filter[0]) &
        (df_gempa['KedalamanValue'] <= depth_filter[1])
    ].copy()

    # sorting logika (lebih intuitif naming)
    # gunakan nilai string input 'sort' dari sidebar? gunakan default: terbaru
    # Keep default: urut berdasarkan DateTime terbaru
    df_filtered.sort_values(by='DateTime', ascending=False, inplace=True)
    if df_filtered.empty:
        st.warning("Tidak ada gempa sesuai filter.")
    else:
        # Ringkasan statistik (di satu layar) - buat HTML cards
        stats = {
            "Total Gempa": len(df_filtered),
            "Magnitudo Tertinggi": f"{df_filtered['Magnitude'].max():.1f}",
            "Magnitudo Rata-rata": f"{df_filtered['Magnitude'].mean():.2f}",
            "Kedalaman Terdangkal": f"{int(df_filtered['KedalamanValue'].min())} km",
            "Kedalaman Terdalam": f"{int(df_filtered['KedalamanValue'].max())} km",
            "Gempa Terbaru": df_filtered.iloc[0]['Waktu Kejadian']
        }
        st.markdown(create_stat_cards_html(stats), unsafe_allow_html=True)

        # Jika ada gempa M >= alert_threshold -> tampilkan toast microinteraction
        if df_filtered['Magnitude'].max() >= alert_threshold:
            top = df_filtered.sort_values(by='Magnitude', ascending=False).iloc[0]
            msg = f"ALERT: Gempa M {top['Magnitude']} - {top['Wilayah']} ({top['Waktu Kejadian']})"
            small_toast_js(msg, duration=6500)

        # Tabs: Map + Table + Detail
        tabs = st.tabs(["📍 Peta Interaktif", "📑 Tabel Data", "🔎 Detail Gempa Terbaru"])
        # Peta
        with tabs[0]:
            # prepare map tiles
            if tile_mode.startswith("Dark"):
                base_tiles = "CartoDB dark_matter"
            else:
                base_tiles = "CartoDB positron"

            latest = df_filtered.iloc[0]
            center = [latest['Latitude'], latest['Longitude']]
            folium_map = folium.Map(location=center, zoom_start=5, tiles=None)
            # add tile layers for Light & Dark to allow switching
            folium.TileLayer("CartoDB positron", name="Light").add_to(folium_map)
            folium.TileLayer("CartoDB dark_matter", name="Dark").add_to(folium_map)
            # add optional additional tiles (OSM)
            folium.TileLayer("OpenStreetMap", name="OSM").add_to(folium_map)

            # Layers: marker cluster
            marker_layer = folium.FeatureGroup(name="Markers", show=True)
            if use_clustering:
                mc = MarkerCluster(name="Cluster").add_to(folium_map)
                target = mc
            else:
                target = marker_layer

            # Add markers
            for _, r in df_filtered.iterrows():
                popup = folium.Popup(f"<b>{r['Wilayah']}</b><br/>M: {r['Magnitude']} • Kedalaman: {r['Kedalaman']}<br/>{r.get('Dirasakan','')}", max_width=320)
                folium.Marker(
                    location=[r['Latitude'], r['Longitude']],
                    popup=popup,
                    tooltip=f"M{r['Magnitude']} - {r['Wilayah']}",
                    icon=folium.Icon(color=get_color_from_magnitude(r['Magnitude']), icon='info-sign')
                ).add_to(target)

            # Add marker layer if not using cluster
            if not use_clustering:
                marker_layer.add_to(folium_map)

            # Heatmap (point-based) layer
            if show_heatmap:
                heat_layer = folium.FeatureGroup(name="Heatmap (points)", show=False)
                heat_data = [[row['Latitude'], row['Longitude'], max(0.5, float(row['Magnitude']))] for _, row in df_filtered.iterrows()]
                HeatMap(heat_data, radius=20, blur=15, min_opacity=0.2).add_to(heat_layer)
                heat_layer.add_to(folium_map)

            # Shakemap image overlay integration if requested
            if show_shakemap_overlay:
                # Try to find first available shakemap URL in filtered set
                candidate = None
                if 'ShakemapURL' in df_filtered.columns:
                    candidate_rows = df_filtered[df_filtered['ShakemapURL'].notna() & (df_filtered['ShakemapURL'] != '')]
                    if not candidate_rows.empty:
                        candidate = candidate_rows.iloc[0]
                # If candidate found, attempt overlay
                if candidate is not None:
                    img_url = candidate['ShakemapURL']
                    # Compute bounds heuristically: create a square around epicenter proportional to magnitude
                    lat0, lon0 = float(candidate['Latitude']), float(candidate['Longitude'])
                    # scale factor: bigger magnitude -> larger shakemap image area (heuristic)
                    mag = float(candidate['Magnitude']) if not pd.isna(candidate['Magnitude']) else 5.0
                    # 1 degree ~ 111 km; choose delta deg such that magnitude 6 -> ~1.0 deg (≈111km), magnitude 4 -> 0.25 deg
                    delta = max(0.1, min(5.0, 10 ** ( (mag - 4.0) / 4.0 ) * 0.25 ))
                    bounds = [[lat0 - delta, lon0 - delta], [lat0 + delta, lon0 + delta]]
                    try:
                        folium.raster_layers.ImageOverlay(
                            name="Shakemap BMKG",
                            image=img_url,
                            bounds=bounds,
                            opacity=0.65,
                            interactive=True,
                            cross_origin=False,
                            zindex=2
                        ).add_to(folium_map)
                        # add note popup near epicenter
                        folium.map.Marker(
                            [lat0, lon0],
                            icon=folium.DivIcon(html=f"""<div style="font-size:12px;background:rgba(255,255,255,0.85);padding:4px 8px;border-radius:6px;">Shakemap (BMKG)</div>""")
                        ).add_to(folium_map)
                    except Exception as ex:
                        # overlay failed (often due to CORS). Show informational marker
                        folium.map.Marker(
                            [lat0, lon0],
                            icon=folium.DivIcon(html=f"""<div style="font-size:12px;background:rgba(255,255,0,0.95);padding:4px 8px;border-radius:6px;">Shakemap tersedia (overlay gagal - CORS?)</div>""")
                        ).add_to(folium_map)

            # Layer control & fullscreen
            folium.LayerControl(collapsed=False).add_to(folium_map)
            folium_map.add_child(folium.map.LayerControl())

            # Show map
            st_folium(folium_map, width="100%", height=650)

        # Tabel data (tab 2)
        with tabs[1]:
            st.markdown("### Data Gempa (hasil filter)")
            # show dataframe nicely; user can sort client-side
            display_df = df_filtered[['Waktu Kejadian','Magnitude','Kedalaman','Wilayah','ShakemapURL']].rename(columns={
                'Waktu Kejadian':'Waktu',
                'Kedalaman':'Kedalaman (raw)',
                'ShakemapURL':'Shakemap URL'
            })
            st.dataframe(display_df, use_container_width=True, height=420)

        # Detail Gempa Terbaru (tab 3)
        with tabs[2]:
            top = df_filtered.iloc[0]
            st.markdown("### Detail Gempa Terbaru")
            # custom HTML card for latest
            latest_html = f"""
            <style>
              .latest-card {{ background: linear-gradient(90deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)); padding:14px;border-radius:12px;color:#fff; }}
              .row {{ display:flex; gap:18px; align-items:center; flex-wrap:wrap; }}
              .big {{ font-size:2.2rem; font-weight:800; }}
              .muted {{ color:#cbd5e1; }}
            </style>
            <div class="latest-card">
              <div class="row">
                <div><div class="muted">Wilayah</div><div style="font-size:1.25rem;font-weight:700">{top['Wilayah']}</div></div>
                <div><div class="muted">Magnitudo</div><div class="big">{top['Magnitude']:.1f}</div></div>
                <div><div class="muted">Kedalaman</div><div style="font-weight:700">{top['Kedalaman']}</div></div>
                <div><div class="muted">Waktu</div><div style="font-weight:700">{top['Waktu Kejadian']}</div></div>
              </div>
              <div style="margin-top:12px;">
                <div class="muted">Dirasakan (MMI / laporan)</div>
                <div style="margin-top:6px;">{top.get('Dirasakan','-')}</div>
              </div>
            </div>
            """
            st.markdown(latest_html, unsafe_allow_html=True)
            if pd.notna(top.get('ShakemapURL')):
                st.markdown("**Shakemap (Preview)**")
                st.image(top['ShakemapURL'], use_column_width=True, clamp=True)

# End of app
