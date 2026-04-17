import json
from html.parser import interesting_normal

import streamlit as st
from pathlib import Path
import logging
import sys
from datetime import datetime, time
import os
from dotenv import load_dotenv

load_dotenv()


# Percorsi
BASE_DIR = Path(__file__).resolve().parent
SERVER_DIR = BASE_DIR.parent / "server"
sys.path.append(str(SERVER_DIR))

BASE_DIR = Path(__file__).resolve().parent
SHARED_DIR = BASE_DIR.parent / "shared"
sys.path.append(str(SHARED_DIR))

# Logging
logging.basicConfig(level=logging.INFO)

# Importazioni moduli locali
from trascrizione import carica_modello_whisper, elabora_file_audio
from LLM import processa_report_clinico, create_client
from dizionari import (
    SINTOMI_COSCIENZA,
    SINTOMI_CUTE,
    SINTOMI_RESPIRO,
    SINTOMI_APERTURA_OCCHI,
    SINTOMI_RISPOSTA_VERBALE,
    SINTOMI_RISPOSTA_MOTORIA,
    COLORI_TO_CODICE,
    NUMERI_TO_CODICE
)

# Directory di lavoro
REPORTS_DIR = SERVER_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_FOLDER = SERVER_DIR / "audio"
TRANSCRIPTS_FOLDER = SERVER_DIR / "transcripts"
IMG_FOLDER = SERVER_DIR / "img"

# Funzione che inizializza il client per un modello LLM
def init_llm_client():
    API_KEY = os.getenv("API_KEY")

    try:
        # Cerca di creare un client a partire dall'API_KEY
        return create_client(API_KEY)
    # In caso di errore stampa a video il messaggio
    except Exception as e:
        logging.error(f"Errore nell'inizializzazione del client LLM: {e}")
        st.toast("Errore nel collegamento con il modello LLM.", icon="🚨")
        return None

# Funzione che trascrive il file audio, salva i risultati e li inserisce nel DB
def processa_audio(audio_path: Path):
    # Nel caso in path non esista si genera un errore
    if not audio_path.exists():
        st.toast("File audio non trovato.", icon="🚨")
        logging.error(f"File audio non trovato: {audio_path}")
        return

    try:
        # Caricamento modello Whisper
        logging.info("Caricamento modello Whisper...")
        modello = carica_modello_whisper("base")
    except Exception as e:
        # In caso di eccezione mostra l'errore
        logging.error(f"Errore nel caricamento del modello: {e}")
        st.toast("Errore nel caricamento del modello Whisper.", icon="🚨")
        return

    # Conversione dell'audio in testo
    logging.info("Inizio trascrizione...")
    trascrizione = elabora_file_audio(modello, audio_path)
    # In caso di errore
    if not trascrizione:
        st.toast("Errore durante la trascrizione audio.", icon="🚨")
        return
    else:
        logging.info("Trascrizione completata. Avvio analisi NLP...")

    # Inizializza client LLM
    client = init_llm_client()

    # In caso di errore si ritorna
    if not client:
        return

    # Estrazione dati clinici tramite LLM
    try:
        risultato_json = processa_report_clinico(client, trascrizione)
    except Exception as e:
        logging.error(f"Errore NLP: {e}")
        st.toast("Errore durante l'elaborazione NLP.", icon="🚨")
        return

    # Se il campo error nell'oggetto di ritorno non è vuoto o risultato_json è vuoto,
    # si stampa un messaggio
    if not risultato_json or "error" in risultato_json:
        errore = risultato_json.get("error", "Errore sconosciuto.")
        logging.error(f"Errore LLM: {errore}")
        st.toast("Errore LLM: " + str(errore), icon="🚨")
        return

    # Salvataggio risultato NLP
    output_report = REPORTS_DIR / "report_finale.json"
    try:
        # Scrittura dell'oggetto ottenuto dal modello in report_finale.json
        with open(output_report, "w", encoding="utf-8") as f:
            json.dump(risultato_json, f, indent=2, ensure_ascii=False)
        logging.info(f"Dati NLP salvati in {output_report}")
    except Exception as e:
        # In caso di eccezione stampa un errore
        logging.error(f"Errore nel salvataggio del report: {e}")
        st.toast("Errore nel salvataggio del report.", icon="🚨")
        return

# Funzione che rimuove gli spazi esterni in caso il campo non sia vuoto o diverso dal tipo stringa
def safe_strip(x):
    if not x or not isinstance(x, str):
        return ""
    return x.strip()

# Funzione per la gestione del tempo da passare all'oggetto st.time_input()
def parse_time(val):
    # In caso di assenza di valore non ritorna nulla
    if not val:
        return None
    # Se l'oggetto è già di tipo time
    if isinstance(val, time):
        return val
    # Cerca di convertire l'oggetto stringa in time
    try:
        return datetime.strptime(val, "%H:%M").time()
    except ValueError:
        return None

# Funzione che ricerca nella lista l'indice che ha quel valore
def safe_index(lista, valore):
    try:
        return lista.index(valore)
    except ValueError:
        return 0

# Funzione converte un valore prima in float e poi intero
def safe_int(val, default=0):
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return default

# Funzione per gestire il percentuale
def safe_parse_percent(val, default=0.0):
    # Se il valore è vuoto restituisce quello di default
    if val is None:
        return default
    # Verifica che il tipo sia intero o float e lo restituisce
    if isinstance(val, (int, float)):
        return val
    # In caso sia una stringa
    if isinstance(val, str):
        # Si rimuovono spazi e simboli di percentuale
        val = val.strip().replace('%', '')
        # Cerca di fare il casting altrimenti ritorna il valore di default
        try:
            return float(val)
        except ValueError:
            return default
    return default

# Funzione che converte i float
def safe_float(val, default=0.0):
    # Se il valore è nullo restituisce quello di default
    if val is None:
        return default
    # Se è intero o float restituisce il valore come float
    if isinstance(val, (int, float)):
        return float(val)
    # Se è una stringa
    if isinstance(val, str):
        # Si rimuovono spazi e caratteri non numerici
        val = val.strip().replace('%', '').replace(',', '.')
        # Cerca di fare il casting altrimenti restituisce il valore di default
        try:
            return float(val)
        except ValueError:
            return default
    return default

from datetime import datetime, date

def parse_date(val):
    if not val:
        return None
    
    if isinstance(val, date):
        return val
    
    if isinstance(val, str):
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()  # formato ISO
        except ValueError:
            return None
    
    return None

# Funzione per la visualizzazione dei risultati su streamlit
def mostra_editor_ui(option):
    dati = st.session_state.get("dati_json", {})

    # Si recupera il dizionario paziente
    paziente = dati.get("paziente", {})

    # Paziente
    if option == "Paziente":

        # Sesso con opzioni M e F
        sesso_opzioni = {"M": "M", "F": "F"}
        valore_iniziale = paziente.get("sesso", "M")
        sesso_selezionato = st.selectbox("Sesso",list(sesso_opzioni.keys()),index=list(sesso_opzioni.keys()).index(valore_iniziale) if valore_iniziale in sesso_opzioni else 0)
        sesso_valore = sesso_opzioni[sesso_selezionato]
        data_nascita = parse_date(paziente.get("data_nascita"))

        # Session_state con i dati del paziente
        st.session_state["dati_json"]["paziente"] = {
            "nome": st.text_input("Nome", paziente.get("nome", "")),
            "cognome": st.text_input("Cognome", paziente.get("cognome", "")),
            "sesso": sesso_valore,
            "data_nascita": st.date_input("Data di nascita", data_nascita).isoformat() if data_nascita else "",            "luogo_nascita": st.text_input("Luogo di nascita", paziente.get("luogo_nascita", "")),
            "codice_fiscale": st.text_input("Codice fiscale", paziente.get("codice_fiscale", "")),
            "telefono": st.text_input("Telefono", paziente.get("telefono", "")),
            "via": st.text_input("Via", paziente.get("via", "")),
            "numero_civico": st.text_input("Numero civico", paziente.get("numero_civico", "")),
            "citta": st.text_input("Città", paziente.get("citta", "")),
            "provincia": st.text_input("Provincia", paziente.get("provincia", "")),
            "cap": st.text_input("CAP", paziente.get("cap", "")),
            "patologie_note": st.text_input("Patologie note", paziente.get("patologie_note", ""))
        }

    # Intervento
    if option == "Intervento":
        # Si recuperano il dizionario intervento
        intervento = dati.get("intervento",{})

        scelte_uscita = list(COLORI_TO_CODICE.keys())
        scelte_rientro = list(NUMERI_TO_CODICE.keys())

        # Recupero le informazioni relative a codice uscita e rientro
        uscita_corrente = str(intervento.get("codici", {}).get("uscita") or "").strip().capitalize()
        rientro_corrente = str(intervento.get("codici", {}).get("rientro") or "").strip().capitalize()

        # Se non è nella lista, si usa la prima opzione come default
        default_uscita = uscita_corrente if uscita_corrente in scelte_uscita else scelte_uscita[0]
        default_rientro = rientro_corrente if rientro_corrente in scelte_rientro else scelte_rientro[0]
        chi_firma = st.radio("Chi firma?", ["Medico", "Interessato"], horizontal=True)

        if chi_firma == "Medico":
            # Prendi il nome del medico da personale_equipaggio, non input
            personale = dati.get("personale_equipaggio", {})
            firma = personale.get("medico", "")
            st.text("Firma medico: " + firma)  # Mostriamo come testo, non modificabile
        else:
            firma = paziente.get("nome", "") + " " + paziente.get("cognome", "")
            st.text("Firma interessato: " + firma)  # visualizzo solo il testo
        intervento["chi_firma"] = firma

        ora_chiamata = parse_time(intervento.get("ora_chiamata"))
        ora_partenza_mezzo = parse_time(intervento.get("ora_partenza_mezzo"))
        ora_arrivo_sul_posto = parse_time(intervento.get("ora_arrivo_sul_posto"))
        ora_partenza_dal_posto = parse_time(intervento.get("ora_partenza_dal_posto"))
        ora_arrivo_destinazione = parse_time(intervento.get("ora_arrivo_destinazione"))
        ora_decesso = parse_time(intervento.get("ora_decesso"))

        # Session state intervento
        st.session_state["dati_json"]["intervento"] = {
            "data_intervento": st.date_input("Data intervento", intervento.get("data_intervento")).isoformat() if intervento.get("data_intervento") else "",
            "luogo_intervento": st.text_input("Luogo intervento", intervento.get("luogo_intervento", "")),
            "motivo_chiamata": st.text_input("Motivo chiamata", intervento.get("motivo_chiamata", "")),
            "modalita_richiesta": st.text_input("Modalità richiesta", intervento.get("modalita_richiesta", "")),
            "ora_chiamata": st.time_input("Ora chiamata", ora_chiamata).strftime('%H:%M') if ora_chiamata else "",
            "ora_partenza_mezzo": st.time_input("Ora partenza mezzo", ora_partenza_mezzo).strftime('%H:%M') if ora_partenza_mezzo else "",
            "ora_arrivo_sul_posto": st.time_input("Ora arrivo sul posto", ora_arrivo_sul_posto).strftime('%H:%M') if ora_arrivo_sul_posto else "",
            "ora_partenza_dal_posto": st.time_input("Ora partenza dal posto", ora_partenza_dal_posto).strftime('%H:%M') if ora_partenza_dal_posto else "",
            "ora_arrivo_destinazione": st.time_input("Ora arrivo destinazione", ora_arrivo_destinazione).strftime('%H:%M') if ora_arrivo_destinazione else "",
            "ora_decesso": st.time_input("Ora decesso", ora_decesso).strftime('%H:%M') if ora_decesso else "",
            "destinazione_trasporto": st.text_input("Destinazione trasporto",intervento.get("trasporto", {}).get("destinazione", "")),
            "tipo_mezzo": st.text_input("Tipo mezzo", intervento.get("trasporto", {}).get("tipo_mezzo", "")),
            "codice_uscita": st.radio("Codice uscita", options=scelte_uscita, index=scelte_uscita.index(default_uscita),horizontal=True),
            "codice_rientro": st.radio("Codice rientro", options=scelte_rientro,index=scelte_rientro.index(default_rientro), horizontal=True),
            "firma_medico": firma if chi_firma == "Medico" else "",
            "firma_interessato": firma if chi_firma == "Interessato" else "",
            "chi_firma": chi_firma,
            "firma_valore": firma,
        }

    # Rilevazioni
    if option == "Rilevazioni":
        rilevazione = dati.get("rilevazioni", {})

        # Lista delle opzioni a partire dai dizionari precedenteente definiti (da usare nelle selectbox)
        opzioni_coscienza = [""] + list(SINTOMI_COSCIENZA.values())
        opzione_cute = [""] + list(SINTOMI_CUTE.values())
        opzione_respiro = [""] + list(SINTOMI_RESPIRO.values())
        opzioni_apertura_occhi = [""] + list(SINTOMI_APERTURA_OCCHI.values())
        opzioni_risposta_verbale = [""] + list(SINTOMI_RISPOSTA_VERBALE.values())
        opzioni_risposta_motoria = [""] + list(SINTOMI_RISPOSTA_MOTORIA.values())

        # Session state rilevazioni
        st.session_state["dati_json"]["rilevazioni"] = {
            "coscienza_t1": st.selectbox("Coscienza T1", opzioni_coscienza, index=safe_index(opzioni_coscienza, rilevazione.get("coscienza_t1", " "))),
            "coscienza_t2": st.selectbox("Coscienza T2", opzioni_coscienza, index=safe_index(opzioni_coscienza, rilevazione.get("coscienza_t2", " "))),
            "coscienza_t3": st.selectbox("Coscienza T3", opzioni_coscienza,index=safe_index(opzioni_coscienza, rilevazione.get("coscienza_t3", " "))),
            "cute_t1": st.selectbox("Cute T1", opzione_cute, index=safe_index(opzione_cute, rilevazione.get("cute_t1", " "))),
            "cute_t2": st.selectbox("Cute T2", opzione_cute,index=safe_index(opzione_cute, rilevazione.get("cute_t2", " "))),
            "cute_t3": st.selectbox("Cute T3", opzione_cute,index=safe_index(opzione_cute, rilevazione.get("cute_t3", " "))),
            "respiro_t1": st.selectbox("Respiro T1", opzione_respiro,index=safe_index(opzione_respiro, rilevazione.get("respiro_t1", " "))),
            "respiro_t2": st.selectbox("Respiro T2", opzione_respiro,index=safe_index(opzione_respiro, rilevazione.get("respiro_t2", " "))),
            "respiro_t3": st.selectbox("Respiro T3", opzione_respiro,index=safe_index(opzione_respiro, rilevazione.get("respiro_t3", " "))),
            "pressione_t1": st.text_input("Pressione T1", value=rilevazione.get("pressione_t1", "")),
            "pressione_t2": st.text_input("Pressione T2", value=rilevazione.get("pressione_t2", "")),
            "pressione_t3": st.text_input("Pressione T3", value=rilevazione.get("pressione_t3", "")),
            "frequenza_cardiaca_t1": safe_int(rilevazione.get("frequenza_cardiaca_t1", 0)),
            "frequenza_cardiaca_t2": safe_int(rilevazione.get("frequenza_cardiaca_t2", 0)),
            "frequenza_cardiaca_t3": safe_int(rilevazione.get("frequenza_cardiaca_t3", 0)),
            "saturazione_t1": st.number_input("Saturazione T1",value=safe_parse_percent(rilevazione.get("saturazione_t1", 0))),
            "saturazione_t2": st.number_input("Saturazione T2",value=safe_parse_percent(rilevazione.get("saturazione_t2", 0))),
            "saturazione_t3": st.number_input("Saturazione T3",value=safe_parse_percent(rilevazione.get("saturazione_t3", 0))),
            "glicemia_t1": st.number_input("Glicemia T1", value=safe_float(rilevazione.get("glicemia_t1", 0))),
            "glicemia_t2": st.number_input("Glicemia T2", value=safe_float(rilevazione.get("glicemia_t2", 0))),
            "glicemia_t3": st.number_input("Glicemia T3", value=safe_float(rilevazione.get("glicemia_t3", 0))),
            "temperatura_t1": st.number_input("Temperatura T1", value=safe_float(rilevazione.get("temperatura_t1", 0))),
            "temperatura_t2": st.number_input("Temperatura T2", value=safe_float(rilevazione.get("temperatura_t2", 0))),
            "temperatura_t3": st.number_input("Temperatura T3", value=safe_float(rilevazione.get("temperatura_t3", 0))),
            "apertura_occhi_t1": st.selectbox("Apertura Occhi T1", opzioni_apertura_occhi, index=safe_index(opzioni_apertura_occhi,rilevazione.get("apertura_occhi_t1", " "))),
            "apertura_occhi_t2": st.selectbox("Apertura Occhi T2", opzioni_apertura_occhi,index=safe_index(opzioni_apertura_occhi,rilevazione.get("apertura_occhi_t2", " "))),
            "apertura_occhi_t3": st.selectbox("Apertura Occhi T3", opzioni_apertura_occhi,index=safe_index(opzioni_apertura_occhi,rilevazione.get("apertura_occhi_t3", " "))),
            "risposta_verbale_t1": st.selectbox("Risposta Verbale T1", opzioni_risposta_verbale,index=safe_index(opzioni_risposta_verbale,rilevazione.get("risposta_verbale_t1", " "))),
            "risposta_verbale_t2": st.selectbox("Risposta Verbale T2", opzioni_risposta_verbale,index=safe_index(opzioni_risposta_verbale,rilevazione.get("risposta_verbale_t2", " "))),
            "risposta_verbale_t3": st.selectbox("Risposta Verbale T3", opzioni_risposta_verbale,index=safe_index(opzioni_risposta_verbale,rilevazione.get("risposta_verbale_t3", " "))),
            "risposta_motoria_t1": st.selectbox("Risposta Motoria T1", opzioni_risposta_motoria,index=safe_index(opzioni_risposta_motoria,rilevazione.get("risposta_motoria_t1", " "))),
            "risposta_motoria_t2": st.selectbox("Risposta Motoria T2", opzioni_risposta_motoria,index=safe_index(opzioni_risposta_motoria,rilevazione.get("risposta_motoria_t2", " "))),
            "risposta_motoria_t3": st.selectbox("Risposta Motoria T3", opzioni_risposta_motoria,index=safe_index(opzioni_risposta_motoria,rilevazione.get("risposta_motoria_t3", " "))),
        }

    # Trasporto non effettuato
    if option == "Trasporto non effettuato":
        trasporto = dati.get("trasporto_non_effettuato", {})

        # Session state trasporto non effettuato
        st.session_state["dati_json"]["trasporto_non_effettuato"] = {
            "Effettuato da altra ambulanza": st.checkbox("Effettuato da altra ambulanza",trasporto.get("Effettuato da altra ambulanza", False)),
            "Effettuato da elisoccorso": st.checkbox("Effettuato da elisoccorso",trasporto.get("Effettuato da elisoccorso", False)),
            "Non necessita": st.checkbox("Non necessita", trasporto.get("Non necessita", False)),
            "Trattato sul posto": st.checkbox("Trattato sul posto", trasporto.get("Trattato sul posto", False)),
            "Sospeso da centrale": st.checkbox("Sospeso da centrale", trasporto.get("Sospeso da centrale", False)),
            "Non reperito": st.checkbox("Non reperito", trasporto.get("Non reperito", False)),
            "Scherzo": st.checkbox("Scherzo", trasporto.get("Scherzo", False)),
        }

    # Parametri Vitali
    if option == "Parametri Vitali":
        parametri = dati.get("parametri_vitali", {})
        lesioni = parametri.get("lesioni", {})

        # Session state parametri vitali
        st.session_state["dati_json"]["parametri_vitali"] = {
            "Pupille Reagenti": st.checkbox("Pupille Reagenti", value=parametri.get("Pupille Reagenti", False)),
            "Pupille Non Reagenti": st.checkbox("Pupille Non Reagenti",value=parametri.get("Pupille Non Reagenti", False)),
            "Pupille Anisocorie": st.checkbox("Pupille Anisocorie", value=parametri.get("Pupille Anisocorie", False)),
            "Pupille Non Anisocorie": st.checkbox("Pupille Non Anisocorie",value=parametri.get("Pupille Non Anisocorie", False)),
            "diametro_DX_pupilla": st.number_input("Diametro DX Pupilla",value=float(parametri.get("diametro_DX_pupilla", 0)), format="%.2f",step=0.01),
            "diametro_SX_pupilla": st.number_input("Diametro SX Pupilla",value=float(parametri.get("diametro_SX_pupilla", 0)), format="%.2f",step=0.01),
            "lesioni": {
                "amputazione": st.checkbox("Amputazione", value=lesioni.get("amputazione", False)),
                "deformità": st.checkbox("Deformità", value=lesioni.get("deformità", False)),
                "dolore": st.checkbox("Dolore", value=lesioni.get("dolore", False)),
                "emorragia": st.checkbox("Emorragia", value=lesioni.get("emorragia", False)),
                "ferita_profonda": st.checkbox("Ferita Profonda", value=lesioni.get("ferita_profonda", False)),
                "ferita_superficiale": st.checkbox("Ferita Superficiale",value=lesioni.get("ferita_superficiale", False)),
                "trauma_chiuso": st.checkbox("Trauma Chiuso", value=lesioni.get("trauma_chiuso", False)),
                "ustione": st.checkbox("Ustione", value=lesioni.get("ustione", False)),
                "obiett_motorio": st.checkbox("Obiettivo Motorio", value=lesioni.get("obiett_motorio", False)),
                "sensibilità_assente": st.checkbox("Sensibilità Assente",value=lesioni.get("sensibilità_assente", False)),
                "frattura_sosp": st.checkbox("Frattura Sospetta", value=lesioni.get("frattura_sosp", False)),
                "lussazione": st.checkbox("Lussazione", value=lesioni.get("lussazione", False)),
            }
        }

    # Trattamenti e Interventi
    if option == "Trattamenti e Interventi":
        tratt = dati.get("trattamenti_e_interventi", {})
        respiratori = tratt.get("respiratori", {})
        circolatori = tratt.get("circolatori", {})
        immobil = tratt.get("immobilizzazione", {})
        altro = tratt.get("altro", {})
        farmaci_str_default = ", ".join(circolatori.get("infusione_farmaci", []))

        # Session state trattamenti e interventi
        st.session_state["dati_json"]["trattamenti_e_interventi"] = {
            "respiratori": {
                "ossigenoterapia_l_min": st.number_input("Ossigenoterapia (L/min)",value=respiratori.get("ossigenoterapia_l_min", 0)),
                "ventilazione_assistita": st.checkbox("Ventilazione assistita",respiratori.get("ventilazione_assistita", False)),
                "aspirazione": st.checkbox("Aspirazione", respiratori.get("aspirazione", False)),
                "intubazione": st.checkbox("Intubazione", respiratori.get("intubazione", False)),
                "cannula_orofaringea": st.checkbox("Cannula Orofaringea", respiratori.get("cannula_orofaringea", False))
            },
            "circolatori": {
                "emostasi": st.checkbox("Emostasi", circolatori.get("emostasi", False)),
                "MCE_min": st.checkbox("MCE", circolatori.get("MCE_min", False)),
                "DAE_N°_Shock": st.checkbox("DAE Shock", circolatori.get("DAE_N°_Shock", False)),
                "accesso_venoso": st.checkbox("Accesso venoso", circolatori.get("accesso_venoso", False)),
                "infusione_farmaci" : [safe_strip(f) for f in st.text_area("Infusione farmaci (separati da virgola)", farmaci_str_default).split(",") if safe_strip(f)],
                "monitoraggio_ecg": st.checkbox("Monitoraggio ECG", circolatori.get("monitoraggio_ecg", False)),
                "monitoraggio_spo2": st.checkbox("Monitoraggio SpO2", circolatori.get("monitoraggio_spo2", False)),
                "monitoraggio_nibp": st.checkbox("Monitoraggio NiBP", circolatori.get("monitoraggio_nibp", False))
            },
            "immobilizzazione": {
                "collare_cervicale": st.checkbox("Collare cervicale", immobil.get("collare_cervicale", False)),
                "tavola_spinale": st.checkbox("Tavola spinale", immobil.get("tavola_spinale", False)),
                "ked": st.checkbox("KED", immobil.get("ked", False)),
                "barella_cucchiaio": st.checkbox("Barella Cucchiaio", immobil.get("barella_cucchiaio", False)),
                "steccobenda": st.checkbox("Steccobenda", immobil.get("steccobenda", False)),
                "materassino_decompressione": st.checkbox("Materassino decompressione",immobil.get("materassino_decompressione", False))
            },
            "altro": {
                "coperta_isotermica": st.checkbox("Coperta isotermica", altro.get("coperta_isotermica", False)),
                "medicazione": st.checkbox("Medicazione", altro.get("medicazione", False)),
                "ghiaccio": st.checkbox("Ghiaccio", altro.get("ghiaccio", False)),
                "osservazione": st.checkbox("Osservazione", altro.get("osservazione", False)),
            }
        }

    # Personale Equipaggio
    if option == "Personale Equipaggio":
        personale = dati.get("personale_equipaggio", {})

        # Session state personale equipaggio
        st.session_state["dati_json"]["personale_equipaggio"] = {
            "autista": st.text_input("Autista", personale.get("autista", "")),
            "medico": st.text_input("Medico", personale.get("medico", "")),
            "infermiere": st.text_input("Infermiere", personale.get("infermiere", "")),
            "soccorritori": [safe_strip(s) for s in (st.text_area("Soccorritori (separati da virgola)", ", ".join(
                personale.get("soccorritori", []))) or "").split(",") if safe_strip(s)]        }

    # Autorità
    if option == "Presenza Autorità":
        autorita = dati.get("presenza_autorita", {})

        st.session_state["dati_json"]["presenza_autorita"] = {
            "carabinieri": st.checkbox("Carabinieri", autorita.get("carabinieri", False)),
            "polizia_stradale": st.checkbox("Polizia Stradale", autorita.get("polizia_stradale", False)),
            "polizia_municipale": st.checkbox("Polizia Municipale", autorita.get("polizia_municipale", False)),
            "vigili_del_fuoco": st.checkbox("Vigili del Fuoco", autorita.get("vigili_del_fuoco", False)),
            "guardia_medica": st.checkbox("Guardia Medica", autorita.get("guardia_medica", False)),
            "altra_ambulanza": st.checkbox("Altra ambulanza", autorita.get("altra_ambulanza", False)),
            "automedica": st.checkbox("Automedica", autorita.get("automedica", False)),
            "elisoccorso": st.checkbox("Elisoccorso", autorita.get("elisoccorso", False)),
            "altro": st.text_input("Altro (specificare)", autorita.get("altro", ""))
        }

    # Restituisce la session state con i dati aggiornati
    return st.session_state["dati_json"]