import os
import re
import json
import subprocess
import streamlit as st
import yt_dlp
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai

st.set_page_config(page_title="Auto FYP Clipper AI", page_icon="⚡", layout="centered")

st.title("⚡ Auto FYP Clipper (Powered by Gemini & YouTube API)")
st.write("Masukkan link video YouTube untuk dipotong adegan paling viralnya secara otomatis!")

# Mengambil kedua API Key dari Streamlit Secrets secara aman
gemini_api_key = st.secrets.get("GEMINI_API_KEY")
youtube_api_key = st.secrets.get("YOUTUBE_API_KEY")

# Form Input Link & Durasi
url = st.text_input("URL Video YouTube:", placeholder="https://www.youtube.com/watch?v=...")
duration_target = st.slider("Target Durasi Klip (Detik):", min_value=10, max_value=60, value=30)

temp_raw_file = "raw_video.mp4"
output_file = "output_clip.mp4"

def get_youtube_id(url):
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_video_info_from_api(video_id, api_key):
    """Mengambil judul & deskripsi resmi dari YouTube Data API v3"""
    try:
        youtube = build("youtube", "v3", developerKey=api_key)
        request = youtube.videos().list(part="snippet", id=video_id)
        response = request.execute()
        if response.get("items"):
            snippet = response["items"][0]["snippet"]
            return snippet.get("title", ""), snippet.get("description", "")
    except Exception as e:
        st.warning(f"YouTube API Warning: {e}")
    return "", ""

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
    except Exception:
        return None

if st.button("🚀 Analisis AI & Potong Otomatis", use_container_width=True):
    if not gemini_api_key or not youtube_api_key:
        st.error("🔑 API Key Gemini atau YouTube belum dipasang lengkap di Streamlit Secrets!")
    elif not url:
        st.warning("Silakan masukkan URL Video terlebih dahulu!")
    else:
        # Bersihkan file lama
        for f in [temp_raw_file, output_file]:
            if os.path.exists(f):
                os.remove(f)

        with st.spinner("⏳ Menganalisis metadata & transkrip video menggunakan Gemini AI..."):
            try:
                video_id = get_youtube_id(url)
                if not video_id:
                    st.error("URL YouTube tidak valid!")
                    st.stop()

                # 1. Panggil YouTube Data API v3 untuk mengambil metadata resmi
                title, description = get_video_info_from_api(video_id, youtube_api_key)
                if title:
                    st.info(f"📌 **Judul Video:** {title}")

                # 2. Ambil Transkrip Subtitle
                transcript_data = get_transcript_text(video_id)
                start_time = 0

                # 3. Analisis Gemini AI
                client = genai.Client(api_key=gemini_api_key)
                
                content_to_analyze = ""
                if transcript_data:
                    content_to_analyze = f"Transkrip:\n{transcript_data[:10000]}"
                    st.info("📜 Subtitle/Transkrip ditemukan! Gemini AI sedang mencari detik adegan paling seru...")
                else:
                    content_to_analyze = f"Judul: {title}\nDeskripsi: {description}"
                    st.warning("⚠️ Transkrip tidak tersedia. Menggunakan perkiraan bagian tengah video berdasarkan info judul/deskripsi...")

                prompt = f"""
                Berikut adalah data video YouTube.
                Tugasmu adalah menganalisis teks ini dan menentukan 1 adegan paling menarik, memicu rasa penasaran (hook), atau dramatis yang cocok untuk video pendek (TikTok/Reels/Shorts) dengan target durasi sekitar {duration_target} detik.
                Jika hanya ada Judul dan Deskripsi tanpa transkrip, berikan perkiraan estimasi detik mulai (misalnya detik ke-30 atau ke-60) yang potensial menarik.

                {content_to_analyze}

                Kembalikan HANYA format JSON valid berikut tanpa teks tambahan/markdown lain:
                {{"start_seconds": 30, "reason": "Penjelasan singkat alasan bagian ini menarik"}}
                """

                # Menggunakan nama model resmi: gemini-1.5-flash
                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=prompt,
                )
                
                clean_res = response.text.replace("```json", "").replace("```", "").strip()
                ai_result = json.loads(clean_res)
                
                start_time = ai_result.get("start_seconds", 0)
                reason = ai_result.get("reason", "Adegan pilihan AI")
                st.success(f"🎯 **AI Highlight:** {reason} (Mulai detik ke-{start_time})")

                # 4. Pengunduhan & Pemotongan Video
                st.info("⚡ Mengunduh & memotong klip video...")
                
                ydl_opts = {
                    'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
                    'outtmpl': temp_raw_file,
                    'quiet': True,
                    'no_warnings': True,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android', 'ios', 'web'],
                            'skip': ['dash', 'hls']
                        }
                    },
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    }
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                if not os.path.exists(temp_raw_file):
                    st.error("Gagal mengunduh file video.")
                else:
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
                if os.path.exists(temp_raw_file):
                    os.remove(temp_raw_file)
