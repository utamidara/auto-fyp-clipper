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
st.write("Masukkan link video TikTok / YouTube untuk dipotong adegan paling viralnya secara otomatis!")

# Mengambil API Key dari Streamlit Secrets
api_key = st.secrets.get("GEMINI_API_KEY")

# Form Input Link & Durasi
url = st.text_input("URL Video (YouTube / TikTok):", placeholder="https://www.youtube.com/watch?v=...")
duration_target = st.slider("Target Durasi Klip (Detik):", min_value=10, max_value=60, value=30)

temp_raw_file = "raw_video.mp4"
output_file = "output_clip.mp4"

def get_youtube_id(url):
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_transcript_text(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['id', 'en'])
        full_text_with_time = []
        for item in transcript:
            start = int(item['start'])
            text = item['text']
            full_text_with_time.append(f"[{start}s] {text}")
        return "\n".join(full_text_with_time)
    except Exception:
        return None

if st.button("🚀 Analisis AI & Potong Otomatis", use_container_width=True):
    if not api_key:
        st.error("🔑 API Key belum dipasang di Streamlit Secrets!")
    elif not url:
        st.warning("Silakan masukkan URL Video terlebih dahulu!")
    else:
        # Pembersihan file lama
        for f in [temp_raw_file, output_file]:
            if os.path.exists(f):
                os.remove(f)

        with st.spinner("⏳ Menganalisis transkrip video menggunakan Gemini AI..."):
            try:
                video_id = get_youtube_id(url)
                transcript_data = None
                if video_id:
                    transcript_data = get_transcript_text(video_id)

                start_time = 0

                if transcript_data:
                    st.info("📜 Transkrip ditemukan! Gemini AI sedang menganalisis adegan paling seru...")
                    
                    client = genai.Client(api_key=api_key)
                    
                    prompt = f"""
                    Berikut adalah transkrip video beserta timestamp detik.
                    Tugasmu adalah menganalisis teks ini dan menemukan 1 adegan paling menarik, memicu rasa penasaran (hook), lucu, atau dramatis yang cocok untuk video pendek (TikTok/Reels/Shorts) dengan target durasi sekitar {duration_target} detik.

                    Transkrip:
                    {transcript_data[:10000]}

                    Kembalikan HANYA format JSON valid berikut tanpa teks tambahan/markdown lain:
                    {{"start_seconds": 12, "reason": "Penjelasan singkat alasan bagian ini menarik"}}
                    """

                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                    )
                    
                    clean_res = response.text.replace("```json", "").replace("```", "").strip()
                    ai_result = json.loads(clean_res)
                    
                    start_time = ai_result.get("start_seconds", 0)
                    reason = ai_result.get("reason", "Adegan pilihan AI")
                    st.success(f"🎯 **AI Highlight:** {reason} (Mulai detik ke-{start_time})")
                else:
                    st.warning("⚠️ Transkrip teks tidak ditemukan pada video ini. Menggunakan pemotongan dari awal video.")

                st.info("⚡ Mengunduh video ke server lokal...")
                
                user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                
                # Opsi yt-dlp untuk mendownload langsung ke file lokal di server
                ydl_opts = {
                    'format': 'best[ext=mp4]/best',
                    'outtmpl': temp_raw_file,
                    'quiet': True,
                    'no_warnings': True,
                    'user_agent': user_agent,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                if not os.path.exists(temp_raw_file):
                    st.error("Gagal mengunduh file video dari URL tersebut.")
                else:
                    st.info("✂️ Memotong video lokal dengan FFmpeg...")
                    
                    # Potong dari file video yang sudah terunduh di server lokal
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-y',
                        '-ss', str(start_time),
                        '-i', temp_raw_file,
                        '-t', str(duration_target),
                        '-c', 'copy',
                        output_file
                    ]

                    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                    if result.returncode == 0 and os.path.exists(output_file):
                        st.success("🎉 Video adegan viral berhasil dipotong oleh AI!")
                        
                        st.video(output_file)
                        
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
            finally:
                # Bersihkan file video mentah agar memori server hemat
                if os.path.exists(temp_raw_file):
                    os.remove(temp_raw_file)
