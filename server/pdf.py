from playwright.sync_api import sync_playwright
import os
from bs4 import BeautifulSoup
import re
import logging
import pdfkit
from processa import SERVER_DIR
from dizionari import ( SINTOMI_COSCIENZA, SINTOMI_CUTE, SINTOMI_RESPIRO, SINTOMI_APERTURA_OCCHI,
    SINTOMI_RISPOSTA_VERBALE, SINTOMI_RISPOSTA_MOTORIA, COLORI_TO_CODICE, NUMERI_TO_CODICE)

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

html_path = SERVER_DIR / "file_html_CRI.html"

# Funzione per la lettura del file HTML
def carica_html(percorso_file):
    try:
        # Lettura del file
        with open(percorso_file, 'r', encoding='utf-8') as file:
            return file.read()
    # In caso il file non esista
    except FileNotFoundError:
        logging.error(f"Errore: il file '{percorso_file}' non è stato trovato.")
        return None
    # In caso non sia possibile leggere il file
    except Exception as e:
        logging.error(f"Errore durante la lettura del file: {e}")
        return None

# ----------------------------------------------------------------------------------------------------------------------

# Funzione per mappare il JSON nel file HTML
def mappa_campi_json_a_html(dati_json: dict) -> dict:
    # Creazione del dizionario
    mapping = {}

    # Estrazione dei sotto-dizionari
    paziente = dati_json.get("paziente", {})
    intervento = dati_json.get("intervento", {})
    parametri_vitali = dati_json.get("parametri_vitali", {})
    personale_equipaggio = dati_json.get("personale_equipaggio", {})
    trasporto_non_effettuato = dati_json.get("trasporto_non_effettuato", {})
    autorita = dati_json.get("presenza_autorita", {})
    trattamenti_interventi = dati_json.get("trattamenti_e_interventi", {})
    rilevazioni = dati_json.get("rilevazioni", {})

    # Funzione che restituisce "" in caso il valore non sia una stringa, altrimenti la sua versione senza spazi
    def normalize(value):
        if not isinstance(value, str):
            return ""
        return value.strip() 

    # Funzione per ricercare un valore da un dizionario, dopo averlo normalizzato
    def map_single(value, mapping_dict):
        return mapping_dict.get(normalize(value), '')

    # Estrazione e mappatura dei vari campi
    raw_uscita_t1 = rilevazioni.get('apertura_occhi_t1', '')
    raw_uscita_t2 = rilevazioni.get('apertura_occhi_t2', '')
    raw_uscita_t3 = rilevazioni.get('apertura_occhi_t3', '')

    mapping['apertura_occhi_t1'] = map_single(raw_uscita_t1, SINTOMI_APERTURA_OCCHI)
    mapping['apertura_occhi_t2'] = map_single(raw_uscita_t2, SINTOMI_APERTURA_OCCHI)
    mapping['apertura_occhi_t3'] = map_single(raw_uscita_t3, SINTOMI_APERTURA_OCCHI)

    raw_uscita_t1 = rilevazioni.get('risposta_verbale_t1', '')
    raw_uscita_t2 = rilevazioni.get('risposta_verbale_t2', '')
    raw_uscita_t3 = rilevazioni.get('risposta_verbale_t3', '')

    mapping['risposta_verbale_t1'] = map_single(raw_uscita_t1, SINTOMI_RISPOSTA_VERBALE)
    mapping['risposta_verbale_t2'] = map_single(raw_uscita_t2, SINTOMI_RISPOSTA_VERBALE)
    mapping['risposta_verbale_t3'] = map_single(raw_uscita_t3, SINTOMI_RISPOSTA_VERBALE)

    raw_uscita_t1 = rilevazioni.get('risposta_motoria_t1', '')
    raw_uscita_t2 = rilevazioni.get('risposta_motoria_t2', '')
    raw_uscita_t3 = rilevazioni.get('risposta_motoria_t3', '')

    mapping['risposta_motoria_t1'] = map_single(raw_uscita_t1, SINTOMI_RISPOSTA_MOTORIA)
    mapping['risposta_motoria_t2'] = map_single(raw_uscita_t2, SINTOMI_RISPOSTA_MOTORIA)
    mapping['risposta_motoria_t3'] = map_single(raw_uscita_t3, SINTOMI_RISPOSTA_MOTORIA)

    raw_uscita_t1 = rilevazioni.get('coscienza_t1', '')
    raw_uscita_t2 = rilevazioni.get('coscienza_t2', '')
    raw_uscita_t3 = rilevazioni.get('coscienza_t3', '')

    mapping['coscienza_t1'] = map_single(raw_uscita_t1, SINTOMI_COSCIENZA)
    mapping['coscienza_t2'] = map_single(raw_uscita_t2, SINTOMI_COSCIENZA)
    mapping['coscienza_t3'] = map_single(raw_uscita_t3, SINTOMI_COSCIENZA)

    raw_uscita_t1 = rilevazioni.get('cute_t1', '')
    raw_uscita_t2 = rilevazioni.get('cute_t2', '')
    raw_uscita_t3 = rilevazioni.get('cute_t3', '')

    mapping['cute_t1'] = map_single(raw_uscita_t1, SINTOMI_CUTE)
    mapping['cute_t2'] = map_single(raw_uscita_t2, SINTOMI_CUTE)
    mapping['cute_t3'] = map_single(raw_uscita_t3, SINTOMI_CUTE)

    raw_uscita_t1 = rilevazioni.get('respiro_t1', '')
    raw_uscita_t2 = rilevazioni.get('respiro_t2', '')
    raw_uscita_t3 = rilevazioni.get('respiro_t3', '')

    mapping['respiro_t1'] = map_single(raw_uscita_t1, SINTOMI_RESPIRO)
    mapping['respiro_t2'] = map_single(raw_uscita_t2, SINTOMI_RESPIRO)
    mapping['respiro_t3'] = map_single(raw_uscita_t3, SINTOMI_RESPIRO)

    # Funzione per la normalizzazione dei valori numerici
    def normalize_number(value):
        # Se il valore è intero o float restituisce tale valore come float
        if isinstance(value, (int, float)):
            return float(value)
        # Se non è ina stringa la restituisce come ''
        if not isinstance(value, str):
            return ''
        # Se quindi è una stringa, elimina spazi e converte "," con "."
        value = value.strip()
        value = value.replace(',', '.')

        # Ricerca il primo numero intero o decimale presente in value
        match = re.search(r'\d+(\.\d+)?', value)
        if match:
            try:
                # Se trovato si cerca di fare il casting
                return float(match.group())
            except ValueError:
                # Altrimenti si restituisce un a stringa ''
                return ''
        return ''

    # Estrazione valori numerici
    mapping['saturazione_t1'] = normalize_number(rilevazioni.get('saturazione_t1', ''))
    mapping['saturazione_t2'] = normalize_number(rilevazioni.get('saturazione_t2', ''))
    mapping['saturazione_t3'] = normalize_number(rilevazioni.get('saturazione_t3', ''))

    mapping['frequenza_cardiaca_t1'] = normalize_number(rilevazioni.get('frequenza_cardiaca_t1', ''))
    mapping['frequenza_cardiaca_t2'] = normalize_number(rilevazioni.get('frequenza_cardiaca_t2', ''))
    mapping['frequenza_cardiaca_t3'] = normalize_number(rilevazioni.get('frequenza_cardiaca_t3', ''))

    mapping['pressione_t1'] = normalize_number(rilevazioni.get('pressione_t1', ''))
    mapping['pressione_t2'] = normalize_number(rilevazioni.get('pressione_t2', ''))
    mapping['pressione_t3'] = normalize_number(rilevazioni.get('pressione_t3', ''))

    mapping['glicemia_t1'] = normalize_number(rilevazioni.get('glicemia_t1', ''))
    mapping['glicemia_t2'] = normalize_number(rilevazioni.get('glicemia_t2', ''))
    mapping['glicemia_t3'] = normalize_number(rilevazioni.get('glicemia_t3', ''))

    mapping['temperatura_t1'] = normalize_number(rilevazioni.get('temperatura_t1', ''))
    mapping['temperatura_t2'] = normalize_number(rilevazioni.get('temperatura_t2', ''))
    mapping['temperatura_t3'] = normalize_number(rilevazioni.get('temperatura_t3', ''))

    # Dati anagrafici del paziente
    mapping['cognome_nome'] = f"{paziente.get('cognome', '')} {paziente.get('nome', '')}".strip()
    mapping['nato_il'] = paziente.get('data_nascita', '')
    mapping['nato_a'] = paziente.get('luogo_nascita', '')
    mapping['via'] = paziente.get('via', '')
    mapping['numero_civico'] = paziente.get('numero_civico', '')
    mapping['cap'] = paziente.get('cap', '')
    mapping['residente_a'] = paziente.get('citta', '')
    mapping['provincia_residenza'] = paziente.get('provincia', '')
    mapping['telefono'] = paziente.get('telefono', '')
    mapping['altro_dati'] = "Documento" if paziente.get('codice_fiscale') else ''
    mapping['codice_fiscale'] = paziente.get('codice_fiscale', '')
    mapping['annotazioni'] = paziente.get('patologie_note', '')
    
    sesso_del_paziente = (paziente.get('sesso') or '').strip().upper()

    if sesso_del_paziente in ('M', 'F'):
        mapping['sesso'] = sesso_del_paziente

    # Intervento
    mapping['data'] = intervento.get('data_intervento', '')
    mapping['h_chiamata'] = intervento.get('ora_chiamata', '')
    mapping['h_partenza'] = intervento.get('ora_partenza_mezzo', '')
    mapping['h_sul_posto'] = intervento.get('ora_arrivo_sul_posto', '')
    mapping['h_partenza_posto'] = intervento.get('ora_partenza_dal_posto', '')
    mapping['h_ps'] = intervento.get('ora_arrivo_destinazione', '')
    mapping['h_libero_operativo'] = ''
    mapping['luogo_intervento'] = intervento.get('luogo_intervento', '')
    chi_firma = intervento.get("chi_firma", "Medico")
    firma_valore = intervento.get("firma_valore", "")

    mapping['firma_medico'] = ""
    mapping['firma_interessato'] = ""

    if chi_firma == "Medico":
        mapping['firma_medico'] = firma_valore  # nome medico
    elif chi_firma == "Interessato":
        mapping['firma_interessato'] = firma_valore  # nome paziente

    mapping['ora_decesso'] = intervento.get('ora_decesso', '')
    mapping['condizione_riferita'] = intervento.get('motivo_chiamata', '')
    mapping['recapito_telefonico'] = paziente.get('telefono', '')
    mapping['cri'] = intervento.get('tipo_mezzo', '')
    mapping['sel'] = ''  # da mappare se esiste

    raw_uscita = intervento.get('codice_uscita', '').strip().capitalize()  # es. "Bianco"
    mapping['codice_uscita'] = COLORI_TO_CODICE.get(raw_uscita, '')  # restituisce "B" se esiste, altrimenti ""

    raw_rientro = intervento.get('codice_rientro', '').strip().capitalize()  # es. "Annullato", "Rosso"
    mapping['codice_rientro'] = NUMERI_TO_CODICE.get(raw_rientro, '')  # restituisce "0", "4", ecc.

    # Equipaggio
    mapping['aut'] = personale_equipaggio.get("autista", "")
    mapping['medico'] = personale_equipaggio.get("medico", "")
    mapping['ip'] = personale_equipaggio.get("infermiere", "")

    # Soccorritori, massimo 3, se meno si riempie con stringa vuota
    socc_list = personale_equipaggio.get("soccorritori", [])
    for i in range(3):
        mapping[f'socc_{i + 1}'] = socc_list[i] if i < len(socc_list) else ""

    # Autorità presenti
    autorita_map = {
        "carabinieri": "Carabinieri",
        "polizia_stradale": "Polizia Stradale",
        "polizia_municipale": "Polizia Municipale",
        "vigili_del_fuoco": "Vigili del Fuoco",
        "guardia_medica": "Guardia Medica",
        "altra_ambulanza": "Altra ambulanza",
        "automedica": "Automedica",
        "elisoccorso": "Elisoccorso"
    }

    mapping['autorita_presenti'] = [
        label for key, label in autorita_map.items()
        if autorita.get(key)
    ]

    # Trasporto non effettuato
    motivi_trasporto_map = {
        "Effettuato da altra ambulanza": "Effettuato da altra ambulanza",
        "Effettuato da elisoccorso": "Effettuato da elisoccorso",
        "Non necessita": "Non necessita",
        "Trattato sul posto": "Trattato sul posto",
        "Sospeso da centrale": "Sospeso da centrale",
        "Non reperito": "Non reperito",
        "Scherzo": "Scherzo"
    }

    mapping["trasporto_non_effettuato"] = [
        label for key, label in motivi_trasporto_map.items()
        if trasporto_non_effettuato.get(key)
    ]

    # Parametri vitali
    parametri_map = {
        "Pupille Reagenti": "Pupille Reagenti",
        "Pupille Non Reagenti": "Pupille Non Reagenti",
        "Pupille Anisocorie": "Pupille Anisocorie",
        "Pupille Non Anisocorie": "Pupille Non Anisocorie"
    }

    mapping["parametri_vitali"] = [
        label for key, label in parametri_map.items()
        if parametri_vitali.get(key, False)
    ]

    # Funzione che arrotonda un valore ad un numero specificato di cifre decimali (in questo caso 2 di default)
    def safe_round(value, digits=2):
        try:
            return round(float(value), digits)
        except (TypeError, ValueError):
            return 0.0

    mapping["diametro_DX_pupilla"] = safe_round(parametri_vitali.get("diametro_DX_pupilla", 0), 2)
    mapping["diametro_SX_pupilla"] = safe_round(parametri_vitali.get("diametro_SX_pupilla", 0), 2)

    # Definizione delle opzioni relative alle lesioni
    lesioni_options = [
        ("amputazione", "Amputazione"),
        ("deformità", "Deformità"),
        ("dolore", "Dolore"),
        ("emorragia", "Emorragia"),
        ("ferita_profonda", "Ferita Profonda"),
        ("ferita_superficiale", "Ferita Superficiale"),
        ("trauma_chiuso", "Trauma Chiuso"),
        ("ustione", "Ustione"),
        ("obiett_motorio", "Obiettivo Motorio"),
        ("sensibilità_assente", "Sensibilità Assente"),
        ("frattura_sosp", "Frattura Sospetta"),
        ("lussazione", "Lussazione"),
    ]

    # Lettura dati esistenti
    lesioni = parametri_vitali.get("lesioni", {})

    mapping['lesioni_riscontrate'] = [
        label for key, label in lesioni_options if lesioni.get(key, False)
    ]

    # Provvedimenti respiro
    mapping['provvedimenti_respiro'] = []

    resp = trattamenti_interventi.get('respiratori', {})

    # Inserimento dei campi in base al valore presente
    if resp.get('aspirazione'):
        mapping['provvedimenti_respiro'].append('Aspirazione')
    if resp.get('cannula_orofaringea'):
        mapping['provvedimenti_respiro'].append('Cannula orofaringea')
    if resp.get('monitoraggio_spo2'):
        mapping['provvedimenti_respiro'].append('Monitor SpO₂')

    # Si ripete per ossigenoterapia_l_min
    oss_val = resp.get('ossigenoterapia_l_min')
    if oss_val not in [None, '', 0]:
        mapping['provvedimenti_respiro'].append(f"O₂ l/min: {oss_val}")
    if resp.get('ventilazione_assistita'):
        mapping['provvedimenti_respiro'].append('Ventilazione')
    if resp.get('intubazione'):
        mapping['provvedimenti_respiro'].append(f"Intubazione")

    # Si ripete per circolatori
    circ = trattamenti_interventi.get("circolatori", {})
    mapping['provvedimenti_circolo'] = []

    if circ.get('emostasi'):
        mapping['provvedimenti_circolo'].append('Emostasi')
    if circ.get('accesso_venoso'):
        mapping['provvedimenti_circolo'].append('Accesso venoso')
    if circ.get('monitoraggio_ecg'):
        mapping['provvedimenti_circolo'].append('Monitor ECG')
    if circ.get('monitoraggio_spo2'):
        mapping['provvedimenti_circolo'].append('Monitor SpO₂')
    if circ.get('MCE_min'):
        mapping['provvedimenti_circolo'].append('MCE')
    if circ.get('DAE_N°_Shock'):
        mapping['provvedimenti_circolo'].append('DAE')

    # Immobilizzazione
    mapping['provvedimenti_immobilizzazione'] = []
    imm = trattamenti_interventi.get('immobilizzazione', {})

    if imm.get('collare_cervicale'):
        mapping['provvedimenti_immobilizzazione'].append('Collare cervicale')
    if imm.get('ked'):
        mapping['provvedimenti_immobilizzazione'].append('KED')
    if imm.get('barella_cucchiaio'):
        mapping['provvedimenti_immobilizzazione'].append('Barella cucchiaio')
    if imm.get('tavola_spinale'):
        mapping['provvedimenti_immobilizzazione'].append('Tavola spinale')
    if imm.get('steccobenda'):
        mapping['provvedimenti_immobilizzazione'].append('Steccobenda')
    if imm.get('materassino_decompressione'):
        mapping['provvedimenti_immobilizzazione'].append('Materassino decompressione')

    # Mapping dati da JSON a lista checkbox da visualizzare
    mapping['provvedimenti_altro'] = []
    alt = trattamenti_interventi.get('altro', {})
    if alt.get('coperta_isotermica'):
        mapping['provvedimenti_altro'].append('Coperta isotermica')
    if alt.get('medicazione'):
        mapping['provvedimenti_altro'].append('Medicazione')
    if alt.get('ghiaccio'):
        mapping['provvedimenti_altro'].append('Ghiaccio')
    if alt.get('osservazione'):
        mapping['provvedimenti_altro'].append('Osservazione')

    return mapping

# ----------------------------------------------------------------------------------------------------------------------

# Funzione per inserire i campi ricavati da un dizionario in un template HTML
def renderizza_html_da_mappa(mapping: dict, html_template: str) -> str:

    # Si crea il contenuto HTML per poterlo manipolare
    soup = BeautifulSoup(html_template, 'html.parser')

    # Si itera tu tutti gli "<input>"
    for input_tag in soup.find_all('input'):
        # Per ogni input si estraggono: nome, tipo e valore
        name = input_tag.get('name')
        input_type = input_tag.get('type', '').lower()
        value = input_tag.get('value', '')

        # Se il campo non è presente continua
        if not name:
            continue

        # Ricerca il valore nel dizionario
        mapped_value = mapping.get(name)

        # Se non presente o non termina con _raw (possibile variante)
        if mapped_value is None and not name.endswith('_raw'):
            # Ulteriore ricerca considerano name_raw
            mapped_value = mapping.get(f"{name}_raw")

        # Se il tipo di input è uno dei seguenti
        if input_type in ['text', 'date', 'time']:
            # Se il valore è una stringa, un intero o un float
            if isinstance(mapped_value, (str, int, float)):
                # Imposta il valore come stringa
                input_tag['value'] = str(mapped_value)
        # Se di tipo checkbox
        elif input_type == 'checkbox':
            # Se è una lista
            if isinstance(mapped_value, list):
                # Se il valore è nella lista
                if value in mapped_value:
                    # "Checka" il campo
                    input_tag['checked'] = 'checked'
            # Se è una stringa e i valori coincidono
            elif isinstance(mapped_value, str) and value == mapped_value:
                input_tag['checked'] = 'checked'
            # Se il valore è booleano
            elif isinstance(mapped_value, bool) and mapped_value:
                input_tag['checked'] = 'checked'
        # Se di tipo radio
        elif input_type == 'radio':
            # Se il valore è una stringa
            if isinstance(mapped_value, str) and value == mapped_value:
                input_tag['checked'] = 'checked'

    return str(soup)

# ----------------------------------------------------------------------------------------------------------------------

# Funzione che converte il file HTML in PDF
def stampa_html_in_pdf(html_path, output_pdf):
    # In caso non esista il path genera un eccezione
    if not os.path.exists(html_path):
        logging.error(f"File HTML non trovato: {html_path}")
        raise FileNotFoundError(f"File HTML non trovato: {html_path}")

    try:
        config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

        # Stylesheet
        options = {
            'page-size': 'A4',
            'margin-top': '20mm',
            'margin-bottom': '20mm',
            'margin-left': '20mm',
            'margin-right': '20mm',
            'print-media-type': True,
            'enable-local-file-access': True
        }

        # Funzione che converte HTML in PDF secondo il formato CSS fornito
        pdfkit.from_file(html_path, output_pdf, options=options, configuration=config)
        logging.info(f"PDF generato con successo: {output_pdf} --")
    except Exception as e:
        # In caso di errore
        logging.error(f"Errore nella generazione del PDF: {e} --")
        raise

# ----------------------------------------------------------------------------------------------------------------------

# Funzione che carica il file HTML, mappa i dati del JSON e compila il template con i dati ricavati,
# infine genera un file JSON
def compila_e_stampa_scheda_cri(dati_json: dict, percorso_template_html: str, percorso_output_html: str,
        percorso_output_pdf: str ) -> None:

    # Funzione di caricamento del file HTML
    logger.info("Caricamento del template HTML...")
    html_template = carica_html(percorso_template_html)

    # Funzione che mappa i campi del JSON nel file HTML
    logger.info("Mappatura dei campi del JSON in quelli del form...")
    mappa_html = mappa_campi_json_a_html(dati_json)

    # Funzione che compila il file HTML
    logger.info("Compilazione del template con BeautifulSoup...")
    html_compilato = renderizza_html_da_mappa(mappa_html, html_template)

    # Salvataggio dei risultati
    logger.info(f"Salvataggio del file HTML compilato in: {percorso_output_html}")
    try:
        with open(percorso_output_html, 'w', encoding='utf-8') as f:
            f.write(html_compilato)
    except Exception as e:
        logger.error(f"Errore nel salvataggio del file HTML: {e}")
        return

    # Generazione del PDF a partire dal file HTML
    logger.info("Generazione del PDF...")
    try:
        stampa_html_in_pdf(percorso_output_html, percorso_output_pdf)
    except Exception as e:
        logger.error(f"Errore nella generazione del PDF: {e}")