import os
import re
import json
import subprocess
import streamlit as st
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai

st.set_page_config(page_title="Auto FYP Clipper AI", page_icon="⚡", layout="centered")

st.title("⚡ Auto FYP Clipper (Powered by Gemini AI)")
st.write("Cari adegan paling seru/viral secara otomatis menggunakan AI!")

# Input API Key & URL
api_key = st.text_input("🔑 Masukkan Gemini API Key Kamu:", type="password")
url = st.text_input("URL Video (YouTube / TikTok):", placeholder="https://www.youtube.com/watch?v=...")

# Option Durasi Target
duration_target = st.slider("Target Durasi Klip (Detik):", min_value=10, max_value=60, value=30)

output_file = "output_clip.mp4"

def get_youtube_id(url):
    """Mengekstrak Video ID dari URL YouTube"""
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_transcript_text(video_id):
    """Mengambil transkrip teks beserta timestamp-nya"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['id', 'en'])
        full_text_with_time = []
        for item in transcript:
            start = int(item['start'])
            text = item['text']
            full_text_with_time.append(f"[{start}s] {text}")
        return "\n".join(full_text_with_time)
    except Exception as e:
        return None

if st.button("🚀 Analisis AI & Potong Otomatis", use_container_width=True):
    if not api_key:
        st.warning("Silakan masukkan Gemini API Key kamu terlebih dahulu!")
    elif not url:
        st.warning("Silakan masukkan URL Video terlebih dahulu!")
    else:
        # Hapus file lama jika ada
        if os.path.exists(output_file):
            os.remove(output_file)

        with st.spinner("⏳ Menganalisis transkrip video menggunakan Gemini AI..."):
            try:
                video_id = get_youtube_id(url)
                transcript_data = None
                if video_id:
                    transcript_data = get_transcript_text(video_id)

                start_time = 0

                # Jika transkrip ditemukan, minta Gemini AI cari detik paling viral
                if transcript_data:
                    st.info("📜 Transkrip ditemukan! Gemini AI sedang mencari adegan paling seru/viral...")
                    
                    client = genai.Client(api_key=api_key)
                    
                    prompt = f"""
                    Berikut adalah transkrip video beserta timestamp detik.
                    Tugasmu adalah menganalisis teks ini dan menemukan 1 adegan paling menarik, memicu rasa penasaran (hook), lucu, atau dramatis yang cocok untuk video pendek (TikTok/Reels/Shorts) dengan target durasi sekitar {duration_target} detik.

                    Transkrip:
                    {transcript_data[:10000]}  # Batasi 10rb karakter pertama

                    Kembalikan HANYA format JSON valid berikut tanpa teks tambahan/markdown lain:
                    {{"start_seconds": 12, "reason": "Penjelasan singkat alasan bagian ini menarik"}}
                    """

                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                    )
                    
                    # Bersihkan response jika ada penanda markdown json
                    clean_res = response.text.replace("```json", "").replace("```", "").strip()
                    ai_result = json.loads(clean_res)
                    
                    start_time = ai_result.get("start_seconds", 0)
                    reason = ai_result.get("reason", "Adegan pilihan AI")
                    st.success(f"🎯 **AI Highlight:** {reason} (Mulai detik ke-{start_time})")
                else:
                    st.warning("⚠️ Transkrip teks tidak ditemukan pada video ini. Menggunakan pemotongan dari awal video.")

                # Mengambil direct URL media via yt-dlp
                st.info("⚡ Memproses pengunduhan dan pemotongan video...")
                ydl_opts = {
                    'format': 'best[ext=mp4]/best',
                    'quiet': True,
                    'no_warnings': True,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                }
                
                direct_url = None
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if 'url' in info:
                        direct_url = info['url']
                    elif 'requested_formats' in info:
                        direct_url = info['requested_formats'][0]['url']

                if not direct_url:
                    st.error("Gagal mendapatkan link media dari URL yang diberikan.")
                else:
                    # Potong dengan FFmpeg berdasarkan timestamp hasil AI
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-y',
                        '-ss', str(start_time),
                        '-i', direct_url,
                        '-t', str(duration_target),
                        '-c', 'copy',
                        output_file
                    ]

                    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                    if result.returncode == 0 and os.path.exists(output_file):
                        st.success("🎉 Video adegan viral berhasil dipotong oleh AI!")
                        
                        # Tampilkan Video
                        st.video(output_file)
                        
                        # Tombol Download
                        with open(output_file, "rb") as file:
                            st.download_button(
                                label="📥 Download Hasil Klip AI",
                                data=file,
                                file_name="klip_fyp_ai.mp4",
                                mime="video/mp4",
                                use_container_width=True
                            )
                    else:
                        st.error(f"Gagal memotong video via FFmpeg: {result.stderr}")

            except Exception as e:
                st.error(f"Terjadi kesalahan: {str(e)}")
