# Librerie
from datetime import datetime
import json
import logging
from traceback import print_tb
from typing import Dict, Any, Callable
import re
from database import genera_codice,get_provincia_cap
import requests
from dizionari import COLORI_TO_CODICE, NUMERI_TO_CODICE


# Crea un client remoto verso l'API di Google AI Studio.
def create_client(api_key: str) -> str:
    if not api_key:
        raise EnvironmentError(
            "Impossibile inizializzare il client: API key mancante. "
            "Imposta la variabile d'ambiente GEMINI_API_KEY oppure passa api_key esplicitamente."
        )

    logging.info("Client inizializzato correttamente con API key fornita.")
    return api_key

# ----------------------------------------------------------------------------------------------------------------------
# Funzione che controlla i dati clinici
def validate_clinical_report_data(data):
    errors = {}
    report = []

    # Validità del tempo
    def is_valid_time(s):
        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                datetime.strptime(s, fmt)
                return True
            except ValueError:
                continue
        return False

    # Validità della data
    def is_valid_date(s):
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return True
        except:
            return False

    # Verifica la presenza e il formato dell'orario
    def check_time_field(field):
        value = data.get(field)
        if not value:
            errors[field] = "Campo orario mancante"
            report.append(f"{field}: MANCANTE")
        elif not isinstance(value, str) or not is_valid_time(value):
            errors[field] = "Formato orario non valido (HH:MM o HH:MM:SS)"
            report.append(f"{field}: FORMATO NON VALIDO")
        else:
            report.append(f"{field}: OK")

    # Verifica che il campo non sia vuoto
    def check_non_empty(field):
        value = data.get(field)
        if not value or not str(value).strip():
            errors[field] = "Campo obbligatorio mancante"
            report.append(f"{field}: MANCANTE")
        else:
            report.append(f"{field}: OK")

    # Verifica del campo - dati enumerativi
    def check_enum(field, valid_values):
        value = data.get(field)
        if value and value not in valid_values:
            errors[field] = f"Valore non valido: {value}"
            report.append(f"{field}: VALORE NON VALIDO")
        else:
            report.append(f"{field}: OK")

    # Verifica il range di valori
    def check_range(field, min_val, max_val):
        val = data.get(field)
        # Se non presente ritorna
        if val is None:
            return
        try:
            val = float(val)
            # Se il valore non è nel range
            if not (min_val <= val <= max_val):
                errors[field] = f"Valore fuori range: {val} (atteso tra {min_val} e {max_val})"
                report.append(f"{field}: FUORI RANGE")
            else:
                report.append(f"{field}: OK")
        except:
            # In caso non si riesca a fare il casting
            errors[field] = "Valore non numerico"
            report.append(f"{field}: NON NUMERICO")

    # Verifica i campi temporali
    for field in [
        "H_chiamata", "H_arrivo", "H_partenza", "H_arrivo_destinazione",
        "H_partenza_posto", "H_in_PS", "H_libero_operativo"
    ]: check_time_field(field)

    # Verifica i codici
    check_enum("codice_uscita", list(COLORI_TO_CODICE.values()))
    check_enum("codice_rientro", list(NUMERI_TO_CODICE.values()))

    # Verifica l'anagrafica
    for f in ["cognome", "nome", "sesso", "luogo_nascita"]:
        check_non_empty(f)

    # Verifica la data
    if not is_valid_date(data.get("data_nascita", "")):
        errors["data_nascita"] = "Formato data non valido (YYYY-MM-DD)"
        report.append("data_nascita: FORMATO NON VALIDO")
    else:
        report.append("data_nascita: OK")

    # Controllo dei parametri vitali
    check_range("pressione_sistolica", 60, 250)
    check_range("pressione_diastolica", 30, 150)
    check_range("frequenza_cardiaca", 30, 200)
    check_range("frequenza_respiratoria", 5, 60)
    check_range("saturazione", 50, 100)
    check_range("temperatura", 30, 43)
    check_range("dolore_VAS", 0, 10)

    # Provvedimenti da applicare
    provvedimenti_validi = {
        "respiro": ["aspirazione", "cannula", "monitor SpO2", "ossigeno", "ventilazione", "intubazione",
                    "ossigeno al 100%"],
        "circolo": ["emostasi", "accesso venoso", "monitor ECG", "D.A.E", "shock", "infusione Ringer lattato",
                    "due accessi venosi"],
        "immobilizzazione": ["collare cervicale", "KED", "tavola spinale", "materassino depressione",
                             "immobilizzazione arto inferiore sinistro", "barella cucchiaio", "steccobenda"],
        "altro": ["coperta isotermica", "copertura termica", "osservazione", "medicazione", "monitoraggio continuo",
                  "comunicazione con C.O."]
    }

    # Si itera il dizionario
    for sezione, validi in provvedimenti_validi.items():
        valori = data.get("provvedimenti", {}).get(sezione, [])
        # In caso di assenza di elemento nella lista
        if not isinstance(valori, list):
            errors[f"provvedimenti_{sezione}"] = "Deve essere una lista"
            report.append(f"{sezione}: NON È LISTA")
        else:
            # In caso di campo non valido
            invalidi = [v for v in valori if v.lower() not in map(str.lower, validi)]
            if invalidi:
                errors[f"provvedimenti_{sezione}"] = f"Valori non riconosciuti: {', '.join(invalidi)}"
                report.append(f"{sezione}: VALORI NON RICONOSCIUTI")
            else:
                report.append(f"{sezione}: OK")

    # Cause mancato trasporto
    motivi = ["rifiuto_interessato", "trattato_sul_posto", "non_necessita", "decesso"]

    # Se non esiste nessun elemento tra quei motivi
    if not any(data.get(m) for m in motivi):
        errors["causa_non_trasporto"] = "Nessuna causa selezionata"
        report.append("causa_non_trasporto: MANCANTE")
    else:
        report.append("causa_non_trasporto: OK")

    # Lesioni
    lesioni_validi = ["amputazione", "deformità", "dolore", "ferita", "ferita profonda", "frattura", "trauma chiuso",
                      "trauma cranico", "ematoma frontale", "ferita lacero-contusa"]
    lesioni = data.get("lesioni", [])

    # Si verifica sia una lista
    if isinstance(lesioni, list):
        invalidi = [l for l in lesioni if l.lower() not in map(str.lower, lesioni_validi)]
        if invalidi:
            # Se il campo è invalido
            errors["lesioni"] = f"Lesioni non riconosciute: {', '.join(invalidi)}"
            report.append("lesioni: VALORI NON RICONOSCIUTI")
        else:
            report.append("lesioni: OK")

    # Autorità
    autorita_validi = ["carabinieri", "polizia", "vigili", "vvf", "118", "elisoccorso", "polizia municipale"]
    autorita = data.get("autorità_presenti", [])

    # Se il campo esiste
    if autorita:
        # E non è tra quelle valide
        invalidi = [a for a in autorita if a.lower() not in map(str.lower, autorita_validi)]
        if invalidi:
            errors["autorità_presenti"] = f"Autorità non riconosciute: {', '.join(invalidi)}"
            report.append("autorità_presenti: VALORI NON RICONOSCIUTI")
        else:
            report.append("autorità_presenti: OK")

    # Esito
    check_enum("esito", ["ricovero", "dimissione", "rifiuto", "decesso", "non necessario", "altro",
                         "trasporto in PS con codice rosso"])

    return {"report": report, "errors": errors}

# ----------------------------------------------------------------------------------------------------------------------

# Funzione che richiama il modello
def chiama_modello(prompt: str, api_key: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    response = requests.post(url, headers=headers, json=payload)

    # In caso di errore
    if response.status_code != 200:
        return f"Errore HTTP {response.status_code}: {response.text}"

    # Estrae la risposta
    try:
        testo = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return "Errore: risposta modello inattesa"

    # Restituisce il testo senza spazi
    return testo.strip()

# ----------------------------------------------------------------------------------------------------------------------

# Funzione che controlla la trascrizione medica
def correggi_trascrizione_medica(testo_grezzo: str, api_key: str, temperatura: float = 0.2) -> str:
    # Correzione trascrizione medica
    prompt_correzione = f"""
        Correggi solo gli errori di trascrizione causati da rumori, termini medici errati o sigle sbagliate.
        Non aggiungere né modificare informazioni originali. Controlla e correggi eventuali errori di ortografia 
        o grammatica. Non modificare termini medici, abbreviazioni o contenuti clinici. Modifica l'orario se in 
        formato diverso da HH:MM e fai lo stesso per la data YYYY-MM-DD

        Testo da correggere:
        \"\"\"
        {testo_grezzo}
        \"\"\"
    """

    # Si richiama il modello
    testo_corretto = chiama_modello(prompt_correzione, api_key)

    if testo_corretto.startswith("Errore"):
        # Se il controllo fallisce, restituisce None
        return None

    return testo_corretto

# ----------------------------------------------------------------------------------------------------------------------

# Funzione che invia il testo al modello Gemini per estrarre informazioni cliniche salienti in formato JSON conforme
# alla struttura dettagliata fornita e deserializza il JSON in dict.
def estrai_info_cliniche_da_testo(testo: str, api_key: str) -> dict:
    # Struttura del file JSON
    struttura_json = {
        "paziente": {
            "nome": "",
            "cognome": "",
            "sesso": "",
            "data_nascita": "%Y-%m-%d",
            "luogo_nascita": "",
            "codice_fiscale": "",
            "telefono": "",
            "via": "",
            "numero_civico": "",
            "citta": "",
            "provincia": "",
            "cap": "",
            "patologie_note": ""
        },
        "intervento": {
            "data_intervento": "%Y-%m-%d",
            "luogo_intervento": "",
            "motivo_chiamata": "",
            "modalita_richiesta": "",
            "ora_chiamata": "",
            "ora_partenza_mezzo": "",
            "ora_arrivo_sul_posto": "",
            "ora_partenza_dal_posto": "",
            "ora_arrivo_destinazione": "",
            "destinazione_trasporto": "",
            "tipo_mezzo": "",
            "codice_uscita": "",
            "codice_rientro": "",
            "ora_decesso": "",
            "firma_medico": "",
            "firma_interessato": ""
        },
        "trasporto_non_effettuato": {
            "Effettuato da altra ambulanza": False,
            "Effettuato da elisoccorso": False,
            "Non necessita": False,
            "Trattato sul posto": False,
            "Sospeso da centrale": False,
            "Non reperito": False,
            "Scherzo": False,
        },
        "rilevazioni": {
            "coscienza_t1": "",
            "coscienza_t2": "",
            "coscienza_t3": "",
            "cute_t1": "",
            "cute_t2": "",
            "cute_t3": "",
            "respiro_t1": "",
            "respiro_t2": "",
            "respiro_t3": "",
            "pressione_t1": "",
            "pressione_t2": "",
            "pressione_t3": "",
            "frequenza_cardiaca_t1": "",
            "frequenza_cardiaca_t2": "",
            "frequenza_cardiaca_t3": "",
            "saturazione_t1": "",
            "saturazione_t2": "",
            "saturazione_t3": "",
            "glicemia_t1": "",
            "glicemia_t2": "",
            "glicemia_t3": "",
            "temperatura_t1": "",
            "temperatura_t2": "",
            "temperatura_t3": "",
            "apertura_occhi_t1": "",
            "apertura_occhi_t2": "",
            "apertura_occhi_t3": "",
            "risposta_verbale_t1": "",
            "risposta_verbale_t2": "",
            "risposta_verbale_t3": "",
            "risposta_motoria_t1": "",
            "risposta_motoria_t2": "",
            "risposta_motoria_t3": "",
        },
        "parametri_vitali": {
            "Pupille Reagenti": False,
            "Pupille Non Reagenti": False,
            "Pupille Anisocorie": False,
            "Pupille Non Anisocorie": False,
            "diametro_DX_pupilla": "",
            "diametro_SX_pupilla": "",
            "lesioni": {
                "amputazione": False,
                "deformità": False,
                "dolore": False,
                "emorragia": False,
                "ferita_profonda": False,
                "ferita_superficiale": False,
                "trauma_chiuso": False,
                "ustione": False,
                "obiett_motorio": False,
                "sensibilità_assente": False,
                "frattura_sosp": False,
                "lussazione": False
            }
        },
        "trattamenti_e_interventi": {
            "respiratori": {
                "ossigenoterapia_l_min": None,
                "ventilazione_assistita": False,
                "aspirazione": False,
                "intubazione": False,
                "cannula_orofaringea": False
            },
            "circolatori": {
                "MCE_min": False,
                "DAE_N°_Shock": False,
                "emostasi": False,
                "accesso_venoso": False,
                "infusione_farmaci": [],
                "monitoraggio_ecg": False,
                "monitoraggio_spo2": False,
                "monitoraggio_nibp": False
            },
            "immobilizzazione": {
                "collare_cervicale": False,
                "tavola_spinale": False,
                "ked": False,
                "barella_cucchiaio": False,
                "steccobenda": False,
                "materassino_decompressione": False
            },
            "altro": {
                "coperta_isotermica": False,
                "medicazione": False,
                "ghiaccio": False,
                "osservazione": False
            }
        },
        "personale_equipaggio": {
            "autista": "",
            "medico": "",
            "infermiere": "",
            "soccorritori": []
        },
        "presenza_autorita": {
            "carabinieri": False,
            "polizia_stradale": False,
            "polizia_municipale": False,
            "vigili_del_fuoco": False,
            "guardia_medica": False,
            "altra_ambulanza": False,
            "automedica": False,
            "elisoccorso": False
        },
    }

    prompt = f"""
        Sei un assistente medico esperto in estrazione dati clinici. Analizza il testo fornito e restituisci SOLO un 
        JSON conforme a questa struttura, senza aggiungere o modificare dati e senza fornire spiegazioni aggiuntive:

        {json.dumps(struttura_json, indent=2)}

        Testo clinico:
        \"\"\"
        {testo}
        \"\"\"
    """

    # Si richiama il modello con il prompt definito
    risposta_testo = chiama_modello(prompt, api_key)

    try:
        # Dopo aver ripulito i dati, ricava dal testo il file JSON
        dati_clinici = estrai_json_da_testo(risposta_testo)
    except Exception as e:
        raise Exception(f"Errore di parsing JSON: {e}")

    return dati_clinici

# ----------------------------------------------------------------------------------------------------------------------

# Funzione che trasforma il testo in JSON
def estrai_json_da_testo(testo: str) -> dict:

    stack = []
    inizio = None

    # Per ogni elemento nel testo
    for i, char in enumerate(testo):
        # Se viene trovata parentesi aperta, essa rappresenterà l'inizio
        if char == '{':
            if not stack:
                inizio = i
            stack.append('{')

        # Nel caso di parentesi chiusa, essa rappresenterà la fine
        elif char == '}':
            if stack:
                stack.pop()
                if not stack and inizio is not None:
                    # Si estrae il blocco da "{" a "}"
                    blocco = testo[inizio:i + 1]
                    try:
                        # Lo carica come JSON
                        return json.loads(blocco)
                    except json.JSONDecodeError:
                        continue

    # Se nessun blocco JSON è stato trovato o valido, solleva un'eccezione
    raise ValueError("Nessun blocco JSON valido trovato.")

# ----------------------------------------------------------------------------------------------------------------------

# Funzione che normalizza i dati
def normalizza_dati_medici(dati: dict) -> dict:
    # Funzioni di normalizzazione stringa
    def norm_str(val):
        if isinstance(val, str):
            return val.strip().title()
        elif val is None:
            return ""
        else:
            return str(val).strip().title()

    # Converte i valori testuali/booleani in Tree e false
    def norm_bool(val):
        if isinstance(val, str): val = val.lower()
        return val in ["sì", "si", "true", "1", True]

    # Normalizzazione del numero
    def norm_num(val, tipo=int):
        try:
            return tipo(val)
        except:
            return None

    def norm_sesso(field):
        valore = str(field).strip().lower()
        if valore in ["femminile", "femmina"]:
            return "F"
        elif valore in ["maschile", "maschio"]:
            return "M"
        return field

    def norm_value(val):
        # Dizionario con equivalenti di null
        NULL_EQUIVALENTS = {"n.d.", "n.d", "non rilevato", "non rilevata", "-", "N.D.", "N.D", "nd", "ND"}

        # In assenza di valore
        if val is None:
            return ""

        # Se il valore è una srtinga
        if isinstance(val, str):
            # Si pulisce e si rende minuscolo
            raw_val = val.strip().lower()
            # Se è contenuto nel fizionario o è "" ritorna ""
            if raw_val in NULL_EQUIVALENTS or raw_val == "":
                return ""

            # Sostituisco la virgola con il punto per i decimali
            val_mod = raw_val.replace(',', '.')

            # Se contiene lettere o simboli (es. "120/80 mmHg"), si restituisce com'è
            if re.search(r'[a-zA-Z/]', val):
                return val.strip()

            # Si converte in float
            try:
                num = float(val_mod)
                return str(int(num)) if num.is_integer() else str(num)
            # In caso di eccezione si stampa un errore
            except ValueError:
                return val.strip()

        # Se il valore è intero o float lo rende stringa
        if isinstance(val, (int, float)):
            return str(int(val)) if float(val).is_integer() else str(val)

        # Se è una lista si restituisce una stringa con elementi separati dalla virgola
        if isinstance(val, list):
            return ", ".join(norm_value(v) for v in val if norm_value(v) != "")

        return str(val)

    # Normalizza una lista
    def norm_list(valori):
        # Se è una lista, normalizza ogni elemento
        if isinstance(valori, list):
            return [norm_value(v) for v in valori if norm_value(v) != ""]
        # Se è una stringa, normalizza il singolo valore
        elif isinstance(valori, str):
            v_norm = norm_value(valori)
            return [v_norm] if v_norm != "" else []
        else:
            return []

    # Funzione per verificare o generare CF
    def verifica_o_calcola_cf(paziente: dict) -> str:
        # Si ricavano i campi
        cf = norm_str(paziente.get("codice_fiscale", ""))
        nome = norm_str(paziente.get("nome", ""))
        cognome = norm_str(paziente.get("cognome", ""))
        sesso = norm_str(paziente.get("sesso", ""))
        data_nascita = norm_str(paziente.get("data_nascita", ""))
        luogo_nascita = norm_str(paziente.get("luogo_nascita", ""))
        ris = norm_str(genera_codice(nome, cognome, sesso, data_nascita, luogo_nascita))

        # Se il campo CF non esiste si ricava da quello generato
        if not cf:
            cf = ris
        else:
            # Se esiste ma è diverso si associa quello corretto
            if cf != ris:
                cf = ris

        return cf.strip().upper()

    # Funzione che calcola provincia e cap
    def verifica_o_calcola_provincia_cap(paziente: dict) -> tuple[str, str]:
        # Si ricavano i campi
        citta = norm_str(paziente.get("citta", ""))
        provincia_corrente = norm_str(paziente.get("provincia", ""))
        cap_corrente = norm_str(paziente.get("cap", ""))

        # Si ottiene da città provincia e cap
        provincia_attesa, cap_atteso = get_provincia_cap(citta)

        # Se il campo non esiste si associa
        if not provincia_corrente or not cap_corrente:
            return provincia_attesa, cap_atteso
        # Se esiste ma è diverso si associa quello corretto
        else:
            if provincia_corrente != provincia_attesa or cap_corrente != cap_atteso:
                return provincia_attesa, cap_atteso

        return provincia_corrente, cap_corrente

    # Normalizzazione del paziente
    if "paziente" in dati:
        paziente = dati["paziente"]
        citta_norm = norm_str(paziente.get("citta", ""))
        provincia, cap = verifica_o_calcola_provincia_cap(paziente)
        paziente.update({
            "nome": norm_str(paziente.get("nome", "")),
            "cognome": norm_str(paziente.get("cognome", "")),
            "sesso": norm_sesso(paziente.get("sesso", "")),
            "luogo_nascita": norm_str(paziente.get("luogo_nascita", "")),
            "codice_fiscale": verifica_o_calcola_cf(paziente),
            "telefono": norm_str(paziente.get("telefono", "")),
            "patologie_note": norm_str(paziente.get("patologie_note", "")),
            "via": norm_str(paziente.get("via", "")),
            "numero_civico": norm_str(str(paziente.get("numero_civico", ""))),
            "citta": citta_norm,
            "provincia": provincia,
            "cap": cap
        })

    # Rilevazioni
    if "rilevazioni" in dati:
        rilevazione = dati["rilevazioni"]

        # Normalizzazione campi singoli e liste
        rilevazione.update({
            "coscienza_t1": norm_str(rilevazione.get("coscienza_t1", "")),
            "coscienza_t2": norm_str(rilevazione.get("coscienza_t2", "")),
            "coscienza_t3": norm_str(rilevazione.get("coscienza_t3", "")),
            "cute_t1": norm_str(rilevazione.get("cute_t1", "")),
            "cute_t2": norm_str(rilevazione.get("cute_t2", "")),
            "cute_t3": norm_str(rilevazione.get("cute_t3", "")),
            "respiro_t1": norm_str(rilevazione.get("respiro_t1", "")),
            "respiro_t2": norm_str(rilevazione.get("respiro_t2", "")),
            "respiro_t3": norm_str(rilevazione.get("respiro_t3", "")),
            "pressione_t1": norm_value(rilevazione.get("pressione_t1", "")),
            "pressione_t2": norm_value(rilevazione.get("pressione_t2", "")),
            "pressione_t3": norm_value(rilevazione.get("pressione_t3", "")),
            "frequenza_cardiaca_t1": norm_value(rilevazione.get("frequenza_cardiaca_t1", "")),
            "frequenza_cardiaca_t2": norm_value(rilevazione.get("frequenza_cardiaca_t2", "")),
            "frequenza_cardiaca_t3": norm_value(rilevazione.get("frequenza_cardiaca_t3", "")),
            "saturazione_t1": norm_value(rilevazione.get("saturazione_t1", "")),
            "saturazione_t2": norm_value(rilevazione.get("saturazione_t2", "")),
            "saturazione_t3": norm_value(rilevazione.get("saturazione_t3", "")),
            "glicemia_t1": norm_value(rilevazione.get("glicemia_t1", "")),
            "glicemia_t2": norm_value(rilevazione.get("glicemia_t2", "")),
            "glicemia_t3": norm_value(rilevazione.get("glicemia_t3", "")),
            "temperatura_t1": norm_value(rilevazione.get("temperatura_t1", "")),
            "temperatura_t2": norm_value(rilevazione.get("temperatura_t2", "")),
            "temperatura_t3": norm_value(rilevazione.get("temperatura_t3", "")),
            "apertura_occhi_t1": norm_str(rilevazione.get("apertura_occhi_t1", "")),
            "apertura_occhi_t2": norm_str(rilevazione.get("apertura_occhi_t2", "")),
            "apertura_occhi_t3": norm_str(rilevazione.get("apertura_occhi_t3", "")),
            "risposta_verbale_t1": norm_str(rilevazione.get("risposta_verbale_t1", "")),
            "risposta_verbale_t2": norm_str(rilevazione.get("risposta_verbale_t2", "")),
            "risposta_verbale_t3": norm_str(rilevazione.get("risposta_verbale_t3", "")),
            "risposta_motoria_t1": norm_str(rilevazione.get("risposta_motoria_t1", "")),
            "risposta_motoria_t2": norm_str(rilevazione.get("risposta_motoria_t2", "")),
            "risposta_motoria_t3": norm_str(rilevazione.get("risposta_motoria_t3", "")),
        })

    # Intervento
    if "intervento" in dati:
        intervento = dati["intervento"]
        # Pulizia orari
        for campo in ["data_intervento", "ora_chiamata", "ora_partenza_mezzo",
                      "ora_arrivo_sul_posto", "ora_partenza_dal_posto", "ora_arrivo_destinazione", "ora_decesso"]:
            intervento[campo] = norm_str(intervento.get(campo, ""))
        # Stringhe
        for campo in ["luogo_intervento", "motivo_chiamata", "modalita_richiesta",
                      "destinazione_trasporto", "tipo_mezzo", "codice_uscita", "codice_rientro", "firma_medico",
                      "firma_interessato"]:
            intervento[campo] = norm_str(intervento.get(campo, ""))

    # Trasporto non effettuato
    if "trasporto_non_effettuato" in dati:
        trasporto = dati["trasporto_non_effettuato"]
        trasporto["Effettuato da altra ambulanza"] = norm_bool(trasporto.get("Effettuato da altra ambulanza", False))
        trasporto["Effettuato da elisoccorso"] = norm_bool(trasporto.get("Effettuato da elisoccorso", False))
        trasporto["Non necessita"] = norm_bool(trasporto.get("Non necessita", False))
        trasporto["Trattato sul posto"] = norm_bool(trasporto.get("Trattato sul posto", False))
        trasporto["Sospeso da centrale"] = norm_bool(trasporto.get("Sospeso da centrale", False))
        trasporto["Non reperito"] = norm_bool(trasporto.get("Non reperito", False))
        trasporto["Scherzo"] = norm_bool(trasporto.get("Scherzo", False))

    # Parametri vitali
    if "parametri_vitali" in dati:
        # Pupille
        parametri = dati["parametri_vitali"]
        parametri["Pupille Reagenti"] = norm_bool(parametri.get("Pupille Reagenti", False))
        parametri["Pupille Non Reagenti"] = norm_bool(parametri.get("Pupille Non Reagenti", False))
        parametri["Pupille Anisocorie"] = norm_bool(parametri.get("Pupille Anisocorie", False))
        parametri["Pupille Non Anisocorie"] = norm_bool(parametri.get("Pupille Non Anisocorie", False))
        parametri["diametro_DX_pupilla"] = parametri.get("diametro_DX_pupilla", "")
        parametri["diametro_SX_pupilla"] = parametri.get("diametro_SX_pupilla", "")
        # Lesioni
        if "lesioni" in parametri:
            lesioni = parametri["lesioni"]
            lesioni["amputazione"] = norm_bool(parametri.get("amputazione", False))
            lesioni["deformità"] = norm_bool(parametri.get("deformità", False))
            lesioni["dolore"] = norm_bool(parametri.get("dolore", False))
            lesioni["emorragia"] = norm_bool(parametri.get("emorragia", False))
            lesioni["ferita_profonda"] = norm_bool(parametri.get("ferita_profonda", False))
            lesioni["ferita_superficiale"] = norm_bool(parametri.get("ferita_superficiale", False))
            lesioni["trauma_chiuso"] = norm_bool(parametri.get("trauma_chiuso", False))
            lesioni["ustione"] = norm_bool(parametri.get("ustione", False))
            lesioni["obiett_motorio"] = norm_bool(parametri.get("obiett_motorio", False))
            lesioni["sensibilità_assente"] = norm_bool(parametri.get("sensibilità_assente", False))
            lesioni["frattura_sosp"] = norm_bool(parametri.get("frattura_sosp", False))
            lesioni["lussazione"] = norm_bool(parametri.get("lussazione", False))

    # Trattamenti e interventi eseguiti
    if "trattamenti_e_interventi" in dati:
        tr = dati["trattamenti_e_interventi"]
        if "respiratori" in tr:
            resp = tr["respiratori"]
            resp["ossigenoterapia_l_min"] = norm_num(resp.get("ossigenoterapia_l_min"), float)
            resp["ventilazione_assistita"] = norm_bool(resp.get("ventilazione_assistita", False))
            resp["aspirazione"] = norm_bool(resp.get("aspirazione", False))
            resp["intubazione"] = norm_bool(resp.get("intubazione", False))
            resp["cannula_orofaringea"] = norm_bool(resp.get("cannula_orofaringea", False))
        if "circolatori" in tr:
            circ = tr["circolatori"]
            circ["emostasi"] = norm_bool(circ.get("emostasi", False))
            circ["MCE_min"] = norm_str(circ.get("MCE_min", False))
            circ["DAE_N°_Shock"] = norm_str(circ.get("DAE_N°_Shock", False))
            circ["accesso_venoso"] = norm_bool(circ.get("accesso_venoso", False))
            circ["infusione_farmaci"] = norm_list(circ.get("infusione_farmaci", []))
            circ["monitoraggio_ecg"] = norm_bool(circ.get("monitoraggio_ecg", False))
            circ["monitoraggio_spo2"] = norm_bool(circ.get("monitoraggio_spo2", False))
            circ["monitoraggio_nibp"] = norm_bool(circ.get("monitoraggio_nibp", False))
        if "immobilizzazione" in tr:
            imm = tr["immobilizzazione"]
            imm["collare_cervicale"] = norm_bool(imm.get("collare_cervicale", False))
            imm["tavola_spinale"] = norm_bool(imm.get("tavola_spinale", False))
            imm["ked"] = norm_bool(imm.get("ked", False))
            imm["barella_cucchiaio"] = norm_bool(imm.get("barella_cucchiaio", False))
            imm["steccobenda"] = norm_bool(imm.get("steccobenda", False))
            imm["materassino_decompressione"] = norm_bool(imm.get("materassino_decompressione", False))
        if "altro" in tr:
            altro = tr["altro"]
            altro["coperta_isotermica"] = norm_bool(altro.get("coperta_isotermica", False))
            altro["medicazione"] = norm_bool(altro.get("medicazione", False))
            altro["ghiaccio"] = norm_bool(altro.get("ghiaccio", False))

    # Personale equipaggio
    if "personale_equipaggio" in dati:
        pers = dati["personale_equipaggio"]
        pers["autista"] = norm_str(pers.get("autista", ""))
        pers["medico"] = norm_str(pers.get("medico", ""))
        pers["infermiere"] = norm_str(pers.get("infermiere", ""))
        pers["soccorritori"] = norm_list(pers.get("soccorritori", []))

    # Presenza autorità
    if "presenza_autorita" in dati:
        pres = dati["presenza_autorita"]
        pres["carabinieri"] = norm_bool(pres.get("carabinieri", False))
        pres["polizia_stradale"] = norm_bool(pres.get("polizia_stradale", False))
        pres["polizia_municipale"] = norm_bool(pres.get("polizia_municipale", False))
        pres["vigili_del_fuoco"] = norm_bool(pres.get("vigili_del_fuoco", False))
        pres["guardia_medica"] = norm_bool(pres.get("guardia_medica", False))
        pres["altra_ambulanza"] = norm_bool(pres.get("altra_ambulanza", False))
        pres["automedica"] = norm_bool(pres.get("automedica", False))
        pres["elisoccorso"] = norm_bool(pres.get("elisoccorso", False))

    return dati

# ----------------------------------------------------------------------------------------------------------------------

# Ogni funzione (contenuta nella pipeline) riceve e restituisce il dizionario dati
def processa_report_clinico(api_key: str, testo_report: str, *, temperatura: float = 0.1, max_token: int = 2048) -> \
Dict[str, Any]:
    # Funzione per la correzione dei dati
    def step_correggi(dati):
        logging.info("Correzione trascrizione...")
        dati["testo"] = correggi_trascrizione_medica(dati["testo"], api_key, temperatura=temperatura)
        return dati

    # Funzione per l'estrazione
    def step_estrai(dati):
        logging.info("Estrazione dati clinici...")
        estratti = estrai_info_cliniche_da_testo(dati["testo"], api_key)
        if "error" in estratti:
            dati["error"] = estratti["error"]
        else:
            dati["estratti"] = estratti
        return dati

    # Funzione per la validazione
    def step_valida(dati):
        if "error" in dati:
            return dati
        logging.info("Validazione dati...")
        dati["validazione"] = validate_clinical_report_data(dati["estratti"])
        return dati

    # Funzione per la normalizzazione
    def step_normalizza(dati):
        if "error" in dati:
            return dati
        logging.info("Normalizzazione dati...")
        dati["normalizzati"] = normalizza_dati_medici(dati["estratti"])
        return dati

    # Pipeline che contiene gli step
    pipeline: list[Callable[[Dict[str, Any]], Dict[str, Any]]] = [
        step_correggi,
        step_estrai,
        step_valida,
        step_normalizza
    ]

    # Si inizializza il dizionario con il testo originale del report
    dati: Dict[str, Any] = {"testo": testo_report}

    # Si eseguono i passi della pipeline
    for fn in pipeline:
        dati = fn(dati)
        if "error" in dati:
            # In caso di errore l'intero processo è blocato
            logging.error(f"Errore rilevato: {dati['error']}")
            return {"error": dati["error"]}

    # Restituisce solo il JSON normalizzato
    return dati.get("normalizzati")