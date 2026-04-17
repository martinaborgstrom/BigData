import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Percorso base
BASE_DIR = Path(__file__).parent

# Percorsi relativi
AUDIO_DIR = BASE_DIR / "audio"
TRASCRIZIONI_DIR = BASE_DIR / "transcripts"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
TRASCRIZIONI_DIR.mkdir(parents=True, exist_ok=True)

# Percorso a ffmpeg
FFMPEG_PATH = os.getenv("FFMPEG_PATH")
os.environ["PATH"] += os.pathsep + FFMPEG_PATH

# Verifica ffmpeg
if not any(Path(FFMPEG_PATH).glob("ffmpeg.exe")):
    logging.warning("Attenzione: FFmpeg non trovato nella directory specificata.")
