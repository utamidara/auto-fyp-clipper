import os
import subprocess
import streamlit as st
import yt_dlp

st.set_page_config(page_title="Auto FYP Clipper Panel", page_icon="⚡", layout="centered")

st.title("⚡ Auto FYP Clipper Panel")
st.write("Masukkan link video TikTok / YouTube untuk dipotong otomatis!")

# Form Input Link
url = st.text_input("URL Video:", placeholder="https://www.youtube.com/watch?v=... atau TikTok")

# Option Durasi Potong
duration = st.slider("Durasi Klip (Detik):", min_value=5, max_value=60, value=30)

output_file = "output_clip.mp4"

if st.button("🚀 Analisis & Potong Otomatis", use_container_width=True):
    if not url:
        st.warning("Silakan masukkan URL terlebih dahulu!")
    else:
        # Hapus file lama jika ada
        if os.path.exists(output_file):
            os.remove(output_file)

        with st.spinner("⏳ Sedang mengambil URL video dan memproses pemotongan..."):
            try:
                # 1. Ambil direct URL video menggunakan yt_dlp
                ydl_opts = {
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'quiet': True,
                    'no_warnings': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    direct_url = info.get('url')

                if not direct_url:
                    st.error("Gagal mendapatkan link media dari URL yang diberikan.")
                else:
                    # 2. Potong video langsung menggunakan ffmpeg
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-y',                   # Timpa file jika sudah ada
                        '-ss', '00:00:00',      # Detik mulai (0)
                        '-i', direct_url,       # Input stream URL
                        '-t', str(duration),    # Durasi pemotongan
                        '-c', 'copy',           # Copy stream tanpa re-encode (proses sangat cepat)
                        output_file
                    ]

                    # Jalankan perintah ffmpeg
                    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                    if result.returncode == 0 and os.path.exists(output_file):
                        st.success("🎉 Video berhasil dipotong!")
                        
                        # 3. Tampilkan Video Player
                        st.video(output_file)
                        
                        # 4. Tombol Download
                        with open(output_file, "rb") as file:
                            st.download_button(
                                label="📥 Download Hasil Klip",
                                data=file,
                                file_name="klip_fyp.mp4",
                                mime="video/mp4",
                                use_container_width=True
                            )
                    else:
                        st.error(f"Gagal memotong video: {result.stderr}")

            except Exception as e:
                st.error(f"Terjadi kesalahan: {str(e)}")
