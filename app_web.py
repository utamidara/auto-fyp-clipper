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

        with st.spinner("⏳ Sedang mengunduh dan memproses video..."):
            try:
                # Opsi yt-dlp yang kompatibel dengan Server Cloud
                ydl_opts = {
                    'format': 'best[ext=mp4]/best', # Ambil format mp4 langsung agar tidak gagal gabung
                    'quiet': True,
                    'no_warnings': True,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                }
                
                direct_url = None
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # Ambil URL media langsung
                    if 'url' in info:
                        direct_url = info['url']
                    elif 'requested_formats' in info:
                        direct_url = info['requested_formats'][0]['url']

                if not direct_url:
                    st.error("Gagal mengekstrak link media. Pastikan video publik dan link valid.")
                else:
                    # Potong langsung aliran video (stream) menggunakan FFmpeg
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-y',
                        '-ss', '00:00:00',
                        '-i', direct_url,
                        '-t', str(duration),
                        '-c', 'copy',
                        output_file
                    ]

                    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                    if result.returncode == 0 and os.path.exists(output_file):
                        st.success("🎉 Video berhasil dipotong!")
                        
                        # Tampilkan Video
                        st.video(output_file)
                        
                        # Tombol Download
                        with open(output_file, "rb") as file:
                            st.download_button(
                                label="📥 Download Hasil Klip",
                                data=file,
                                file_name="klip_fyp.mp4",
                                mime="video/mp4",
                                use_container_width=True
                            )
                    else:
                        st.error(f"Gagal memotong video via FFmpeg: {result.stderr}")

            except Exception as e:
                st.error(f"Terjadi kesalahan: {str(e)}")
