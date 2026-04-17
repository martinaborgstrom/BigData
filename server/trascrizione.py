# Librerie
import whisper
import logging
from pathlib import Path
from datetime import datetime
import json
import sounddevice as sd
from scipy.io.wavfile import write

# Definizione delle directory base per i file audio e le trascrizioni. In caso non esistano, verranno create
BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "audio"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
AUDIO_DIR.mkdir(exist_ok=True)
TRANSCRIPTS_DIR.mkdir(exist_ok=True)

# Configurazione del logging per stampare informazioni a console
logging.basicConfig(level=logging.INFO)

# Funzione per caricare il modello Whisper specificando la dimensione (es. "base", "small", "medium", "large")
def carica_modello_whisper(tipo_modello="base"):
    logging.info(f"Inizializzo modello Whisper: {tipo_modello}")
    return whisper.load_model(tipo_modello)

# Funzione per trascrivere il contenuto di un file audio usando Whisper
def trascrivi_audio(modello, percorso_file: Path):
    logging.info(f"Trascrivo file: {percorso_file}")

    start = datetime.now()
    risultato = modello.transcribe(str(percorso_file),fp16=False)      # trascrizione

    tempo = datetime.now() - start
    testo = risultato["text"].strip().replace("...", "")    # pulizia del testo trascritto

    logging.info(f"Trascrizione completata in {tempo.total_seconds():.2f} secondi")
    return testo

# Funzione per salvare la trascrizione in un file JSON
def salva_trascrizione(testo, file_output: Path):
    dati = {
        "trascrizione": testo,
        "generato_il": datetime.now().isoformat()   # timestamp
    }

    with open(file_output, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=2) # salvataggio in formato JSON

    logging.info(f"Trascrizione salvata in: {file_output}")

# Funzione per elaborare (verificare, trascrivere e salvare) un file audio
def elabora_file_audio(modello, percorso_file: Path):
    # Si verifica se l'estensione del file è supportata
    if not percorso_file.suffix.lower() in (".mp3", ".wav", ".m4a"):
        logging.warning(f"Formato non supportato: {percorso_file.name}")
        return None

    # Si verifica l'esistenza del file
    if not percorso_file.exists():
        logging.error(f"File non trovato: {percorso_file}")
        return None

    # Si trascrive il file audio
    testo_trascritto = trascrivi_audio(modello, percorso_file)

    # Salvataggio file
    file_json = TRANSCRIPTS_DIR / f"{percorso_file.stem}.json"
    salva_trascrizione(testo_trascritto, file_json)


    return {
        "trascrizione": testo_trascritto,
        "json": str(file_json)
    }