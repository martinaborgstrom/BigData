import json
import streamlit as st
import base64
from datetime import datetime, date, time
from processa import processa_audio, SERVER_DIR, AUDIO_FOLDER, REPORTS_DIR, mostra_editor_ui
from database import new_patient
from pdf import compila_e_stampa_scheda_cri

# Funzione per serializzare date/datetime in ISO format
def date_converter(obj):
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


# Configurazione pagina
st.set_page_config(page_title="Voice2Care ", page_icon="🚑", layout="wide")

st.markdown('<h1 style="text-align: center;">🚑 - Voice2Care - 🚑</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center;"><i>Il servizio che può salvarti la vita</i></p>', unsafe_allow_html=True)

# Selectbox usato per definire il metodo di acquisizione dell'audio
option = st.selectbox("Selezionare la modalità di acquisizione audio", ('', 'Registra un messaggio vocale', 'Carica file audio'))

audio_file = None
audio = None

# Selezione di diverso componente e percorso in base alla scelta precedentemente effettuata
if option == "Registra un messaggio vocale":
    audio = st.audio_input("Premi per registrare il messaggio vocale")
    audio_path = AUDIO_FOLDER / 'registrazione.mp3'
elif option == "Carica file audio":
    audio_file = st.file_uploader("Carica un file audio (mp3, wav, ogg, m4a)", type=["mp3", "wav", "ogg", "m4a"])
    audio_path = AUDIO_FOLDER / 'audio.mp3'

# Inizializzazione session_state
if "trascrizione" not in st.session_state:
    st.session_state.trascrizione = ""
if "dati_json" not in st.session_state:
    st.session_state.dati_json = {}
if "json_generato" not in st.session_state:
    st.session_state.json_generato = False
if "fase" not in st.session_state:
    st.session_state.fase = "start"
if "pdf_generato" not in st.session_state:
    st.session_state.pdf_generato = False

# Path per il file JSON contenente l'audio trascritto
report_path = REPORTS_DIR / "report_finale.json"

# Nel caso in cui il bottone sia premuto e sia stata selezionata una modalità di acquisizione audio, si procede
# con la trascrizione
if st.button("📝 Trascrivi audio") and (audio_file or audio):
    with st.spinner("Trascrizione in corso..."):
        # In caso di assenza di cartella questa è creata
        AUDIO_FOLDER.mkdir(parents=True, exist_ok=True)
        try:
            # Salvataggio del diverso file audio
            if audio_file:
                audio_path.write_bytes(audio_file.read())
            elif audio:
                audio_path.write_bytes(audio.getbuffer())
        # In caso di eccezione si stampa un messaggio
        except Exception as e:
            st.toast(f"Errore nel salvataggio dell'audio: {e}", icon="🚨")

        # Funzione che converte l'audio in testo
        processa_audio(audio_path)

        try:
            # Lettura del file (report_finale.json) e salvataggio nella variabile dati
            with open(report_path, "r", encoding="utf-8") as f:
                dati = json.load(f)

            # Session state
            st.session_state.dati_json = dati
            st.session_state.trascrizione = json.dumps(dati, indent=2, ensure_ascii=False, default=date_converter)
            st.session_state.json_generato = True
            st.session_state.fase = "editor"
            st.session_state.pdf_generato = False  # Reset PDF flag on new transcription

            # In assenza di errori viene stampato un messaggio
            st.toast("Trascrizione e analisi NLP completate!", icon="✅")

        # In caso di errore viene mostrata un'eccezione
        except Exception as e:
            st.toast(f"Errore durante il caricamento del report JSON: {e}", icon="🚨")
            st.session_state.fase = "errore_trascrizione"

# Nel caso in cui il JSON sia stato generato, si mostrano i dati estratti
if st.session_state.json_generato:
    st.markdown('<h2 style="text-align: center;"> 👤 Dati Estratti</h2>', unsafe_allow_html=True)
    option = st.selectbox("Selezionare i dati da mostrare:", (
    'Paziente', 'Trasporto non effettuato', 'Rilevazioni', 'Intervento', 'Parametri Vitali',
    'Trattamenti e Interventi', 'Personale Equipaggio', 'Presenza Autorità'))

    # Funzione che stampa i componenti streamlit sulla base della option selezionata precedentemente
    dati_modificati = mostra_editor_ui(option)

    # Una volta confermate le scelte, si procederà con la creazione di un nuovo paziente nel db e la generazione del PDF
    if st.button("💾 Conferma le scelte"):
        st.session_state.fase = "confermato"
        try:
            # In caso di dati modificati
            if dati_modificati:
                # Per ogni campo (dizionari)
                for key in ["paziente", "intervento", "trasporto_non_effettuato", "parametri_vitali", "rilevazioni",
                            "trattamenti_e_interventi",
                            "personale_equipaggio", "presenza_autorita"]:

                    # Si recuperano le informazioni passate e modificate
                    original_section = st.session_state.dati_json.get(key, {})
                    modified_section = dati_modificati.get(key, {})

                    # Si aggiornano i risultati e la session_state in caso di modifica
                    if isinstance(original_section, dict) and isinstance(modified_section, dict):
                        original_section.update(modified_section)
                        st.session_state.dati_json[key] = original_section
                    else:
                        st.session_state.dati_json[key] = modified_section

            # Si aggiora la session_state di trascrizione con in nuovi dati modificati e originali
            st.session_state.trascrizione = json.dumps(
                st.session_state.dati_json, indent=2, ensure_ascii=False, default=date_converter
            )

            # Si aggiorna il JSON con i dati modificati
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(st.session_state.dati_json, f, indent=2, ensure_ascii=False, default=date_converter)

            # Si crea un nuovo paziente
            if new_patient(report_path):
                st.toast("Paziente inserito nel database!", icon="✅")
            # In caso di errore si stampa un messaggio
            else:
                st.toast("Errore nell'inserimento del paziente nel database.", icon="🚨")
            st.session_state.pdf_generato = False  # Reset PDF flag dopo modifica dati
        except Exception as e:
            st.error(f"Errore nel salvataggio delle modifiche: {e}")

# Una volta aver confermato le scelte, compare il blocco genera PDF
if st.session_state.fase == "confermato":
    st.markdown('<h2 style="text-align: center;"> 📄 Generazione PDF</h2>', unsafe_allow_html=True)

    # Path dei file
    output_html_path = REPORTS_DIR / "scheda_compilata.html"
    output_pdf_path = REPORTS_DIR / "scheda_compilata.pdf"
    template_html_path = SERVER_DIR / "file_html_CRI.html"

    # In caso si prema il bottone
    if st.button("📤 Genera PDF"):
        try:
            # Funzione che compila il file HTML e crea il PDF a partire da un template
            compila_e_stampa_scheda_cri(
                dati_json=st.session_state.dati_json,
                percorso_template_html=str(template_html_path),
                percorso_output_html=str(output_html_path),
                percorso_output_pdf=str(output_pdf_path)
            )
            # In caso di assenza di errori si aggiorna session_state e si stampa un messaggio
            st.session_state.pdf_generato = True
            st.toast("PDF generato con successo!", icon="✅")
        # In caso di errore si genera un eccezione
        except Exception as e:
            st.error(f"Errore nella generazione del PDF: {e}")

    # In caso di PDF generato, si mostra
    if st.session_state.pdf_generato:
        # Se il file esiste
        if output_pdf_path.exists():
            # Si apre il file e si legge
            with open(output_pdf_path, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode("utf-8")

            # Dopo la lettura si stampa a video
            pdf_display = f'''
                <div style="display: flex; justify-content: center;">
                    <iframe src="data:application/pdf;base64,{base64_pdf}" 
                    width="65%" height="1000px" type="application/pdf"></iframe>
                </div>
            '''
            st.markdown(pdf_display, unsafe_allow_html=True)