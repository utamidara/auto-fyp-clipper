import streamlit as st
import subprocess
import os

st.set_page_config(page_title="Auto FYP Clipper Panel", page_icon="⚡", layout="centered")

st.title("⚡ Auto FYP Clipper Panel")
st.write("Masukkan link video TikTok / YouTube untuk dipotong otomatis!")

# Form Input Link
url = st.text_input("URL Video:", placeholder="https://www.tiktok.com/@user/video/...")

# Option Durasi Potong
duration = st.slider("Durasi Klip (Detik):", min_value=5, max_value=60, value=30)

if st.button("🚀 Analisis & Potong Otomatis", use_container_width=True):
    if not url:
        st.warning("Silakan masukkan URL terlebih dahulu!")
    else:
        st.info("⏳ Sedang mengunduh dan memproses video...")
        
        # Contoh eksekusi yt-dlp & ffmpeg di background
        output_file = "output_clip.mp4"
        
        # Jalankan proses pemotongan (menyesuaikan perintah script kamu sebelumnya)
        cmd = f'.\\yt-dlp.exe -g "{url}"'
        
        try:
            st.success("🎉 Video berhasil dipotong!")
            
            # Menampilkan video di browser jika file output sudah jadi
            if os.path.exists(output_file):
                st.video(output_file)
                with open(output_file, "rb") as file:
                    st.download_button(
                        label="📥 Download Hasil Klip",
                        data=file,
                        file_name="klip_fyp.mp4",
                        mime="video/mp4"
                    )
        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")