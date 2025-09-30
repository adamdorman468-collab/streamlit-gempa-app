# Pusat Informasi Gempa Bumi Real-time Indonesia

**LIVE DEMO APLIKASI:** [https://adamdorman-gempa.streamlit.app/](https://adamdorman-gempa.streamlit.app/)

![Screenshot Aplikasi Gempa](link_ke_screenshot_aplikasi_anda.jpg)
*(Ganti link ini dengan URL screenshot aplikasi Anda yang di-upload ke GitHub)*

---

## 📖 Deskripsi Proyek

Pusat Informasi Gempa Bumi adalah aplikasi web interaktif yang menyajikan data gempa bumi terkini di wilayah Indonesia secara *real-time*. Proyek ini dibangun sebagai portofolio untuk menunjukkan kemampuan dalam pengembangan aplikasi data, mulai dari pengambilan data melalui API, pengolahan, visualisasi, hingga deployment aplikasi.

Aplikasi ini terhubung langsung ke **API publik dari Badan Meteorologi, Klimatologi, dan Geofisika (BMKG)**, memastikan data yang ditampilkan selalu akurat dan terbaru.

## ✨ Fitur-Fitur Utama

- **Sumber Data Dinamis:** Pengguna dapat memilih untuk menampilkan data dari 3 sumber resmi BMKG:
  - **Gempa Dirasakan:** Daftar 15 gempa terakhir yang dirasakan oleh manusia, umumnya dengan data paling lengkap.
  - **Gempa Terbaru M 5.0+:** Daftar 15 gempa terakhir dengan kekuatan magnitudo 5.0 atau lebih.
  - **Gempa Real-time:** Data gempa tunggal yang paling baru terdeteksi oleh sistem otomatis BMKG.

- **Jam & Tanggal Real-time:** Menampilkan jam digital yang terus bergerak dalam zona waktu **WIB** dan **UTC**, beserta tanggal lengkap dalam format Bahasa Indonesia.

- **Filter Interaktif:**
  - **Filter Rentang Magnitudo:** Slider untuk menyaring data gempa berdasarkan rentang magnitudo tertentu.
  - **Filter Cepat (≥ 5.0):** Checkbox untuk dengan cepat menampilkan gempa berkekuatan signifikan.
  - **Tombol Reset:** Mengembalikan filter ke kondisi awal.

- **Visualisasi Peta Cerdas:**
  - **Peta Interaktif:** Peta persebaran gempa menggunakan Folium yang dapat di-zoom dan di-klik.
  - **Marker Dinamis:** Warna penanda (marker) di peta berubah sesuai kekuatan magnitudo (Hijau < 4.0, Oranye 4.0-5.9, Merah ≥ 6.0).
  - **Clustering:** Mengelompokkan gempa yang berdekatan untuk menjaga performa dan kejelasan peta.
  - **Popup Detail:** Menampilkan informasi lengkap (Wilayah, Magnitudo, Kedalaman, Skala MMI) saat marker di-klik.

- **Detail & Statistik:**
  - **Informasi Gempa Terkini:** Menampilkan detail lengkap dari gempa terbaru, termasuk **indikator potensi tsunami** dan **gambar Peta Guncangan (Shakemap)** jika tersedia.
  - **Ringkasan Statistik:** Memberikan ringkasan cepat mengenai jumlah gempa yang ditampilkan, magnitudo terkuat, dan gempa terdangkal.

- **Desain Responsif & Profesional:** Didesain dengan Streamlit untuk tampilan yang bersih dan mudah digunakan di berbagai perangkat.

## 🛠️ Teknologi yang Digunakan

- **Bahasa Pemrograman:** Python
- **Framework Web:** Streamlit
- **Library Pengolahan Data:** Pandas
- **Library Visualisasi Peta:** Folium, Streamlit-Folium
- **Library Koneksi API:** Requests

## 🚀 Cara Menjalankan Aplikasi Secara Lokal

1.  **Clone Repository:**
    ```bash
    git clone [https://github.com/adamdorman468-collab/nama-repository-anda.git](https://github.com/adamdorman468-collab/nama-repository-anda.git)
    cd nama-repository-anda
    ```

2.  **Buat Virtual Environment (Direkomendasikan):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Untuk Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Pastikan Anda sudah memiliki file `requirements.txt` yang berisi:*
    ```
    streamlit
    pandas
    requests
    folium
    streamlit-folium
    ```

4.  **Jalankan Aplikasi:**
    ```bash
    streamlit run app.py
    ```

## 👤 Author

- **Nama:** Adam Dorman
- **Institusi:** Mahasiswa S1 Sistem Informasi, UPN Veteran Jakarta (Angkatan 2024)
- **LinkedIn:** [https://www.linkedin.com/in/adamdorman68/](https://www.linkedin.com/in/adamdorman68/)
- **GitHub:** [https://github.com/adamdorman468-collab](https://github.com/adamdorman468-collab)
