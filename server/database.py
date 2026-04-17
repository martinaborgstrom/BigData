# Librerie
import json
from pymongo import MongoClient
import random
from faker import Faker
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Configurazione del logging per stampare informazioni a console
logging.basicConfig(level=logging.INFO)

# Funzione di connessione al database MongoDB
def connection_to_db():
    try:
        # Creazione del client
        DB_URI = os.getenv("DB_URI")
        client = MongoClient(DB_URI)

        # Accesso al database "hospital"
        db = client.hospital

        # Accesso alla collezione "patients"
        patients = db.patients

        logging.info("Connessione avvenuta")
        return patients
    except ConnectionRefusedError as e:
        logging.error(f"Errore in fase di connessione {e}")
        return None

# Dizionario codici catastali per città (per il calcolo del codice fiscale)
codici_catastali = {
    "Roma": "H501", "Milano": "F205", "Napoli": "F839", "Torino": "L219", "Palermo": "G273",
    "Genova": "D969", "Bari": "A662", "Firenze": "D612", "Bologna": "A944", "Venezia": "L736",
    "Verona": "L781", "Trieste": "L424", "Catania": "C351", "Padova": "G224", "Reggio Calabria": "H224",
    "Taranto": "L049", "Brescia": "B157", "Prato": "G999", "Parma": "G337", "Modena": "F257",
    "Reggio Emilia": "H223", "Perugia": "G478", "Livorno": "E625", "Ravenna": "H199", "Cagliari": "B354",
    "Foggia": "D643", "Salerno": "H703", "Forlì": "D704", "Pescara": "G482", "Monza": "F704",
    "Siracusa": "I754", "Latina": "E472", "Vicenza": "L840", "Terni": "L117", "Piacenza": "G535",
    "Alessandria": "A182", "La Spezia": "E463", "Pistoia": "G713", "Udine": "L483", "Trento": "L378",
    "Ancona": "A271", "Arezzo": "A390", "Lecce": "E506", "Pesaro": "G479", "Como": "C933",
    "Lucca": "E715", "Sassari": "I452", "Cosenza": "D086", "Massa": "F034", "Grosseto": "E202",
    "Treviso": "L407", "Rimini": "H294", "Ferrara": "D548", "Varese": "L682", "Asti": "A479",
    "Novara": "F952", "Caserta": "B963", "Cremona": "D150", "Campobasso": "B519", "Lodi": "E648",
    "Vercelli": "L750", "Benevento": "A783", "Matera": "E851", "Catanzaro": "C352"
}

# Dizionario info_città per la gestione di CAP e provincia
info_citta = {
    "Roma": ("RM", "00100"), "Milano": ("MI", "20100"), "Napoli": ("NA", "80100"),
    "Torino": ("TO", "10100"), "Palermo": ("PA", "90100"), "Genova": ("GE", "16100"),
    "Bari": ("BA", "70100"), "Firenze": ("FI", "50100"), "Bologna": ("BO", "40100"),
    "Venezia": ("VE", "30100"), "Verona": ("VR", "37121"), "Trieste": ("TS", "34100"),
    "Catania": ("CT", "95100"), "Padova": ("PD", "35100"), "Reggio Calabria": ("RC", "89100"),
    "Taranto": ("TA", "74100"), "Brescia": ("BS", "25100"), "Prato": ("PO", "59100"),
    "Parma": ("PR", "43100"), "Modena": ("MO", "41100"), "Reggio Emilia": ("RE", "42100"),
    "Perugia": ("PG", "06100"), "Livorno": ("LI", "57100"), "Ravenna": ("RA", "48100"),
    "Cagliari": ("CA", "09100"), "Foggia": ("FG", "71100"), "Salerno": ("SA", "84100"),
    "Forlì": ("FC", "47100"), "Pescara": ("PE", "65100"), "Monza": ("MB", "20900"),
    "Siracusa": ("SR", "96100"), "Latina": ("LT", "04100"), "Vicenza": ("VI", "36100"),
    "Terni": ("TR", "05100"), "Piacenza": ("PC", "29100"), "Alessandria": ("AL", "15100"),
    "La Spezia": ("SP", "19100"), "Pistoia": ("PT", "51100"), "Udine": ("UD", "33100"),
    "Trento": ("TN", "38100"), "Ancona": ("AN", "60100"), "Arezzo": ("AR", "52100"),
    "Lecce": ("LE", "73100"), "Pesaro": ("PU", "61100"), "Como": ("CO", "22100"),
    "Lucca": ("LU", "55100"), "Sassari": ("SS", "07100"), "Cosenza": ("CS", "87100"),
    "Massa": ("MS", "54100"), "Grosseto": ("GR", "58100"), "Treviso": ("TV", "31100"),
    "Rimini": ("RN", "47900"), "Ferrara": ("FE", "44100"), "Varese": ("VA", "21100"),
    "Asti": ("AT", "14100"), "Novara": ("NO", "28100"), "Caserta": ("CE", "81100"),
    "Cremona": ("CR", "26100"), "Campobasso": ("CB", "86100"), "Lodi": ("LO", "26900"),
    "Vercelli": ("VC", "13100"), "Benevento": ("BN", "82100"), "Matera": ("MT", "75100"),
    "Catanzaro": ("CZ", "88100")
}

# Dizionario per definire ospedali per ogni città
ospedali_per_citta = {
    "Roma": [
        "Policlinico Universitario Agostino Gemelli",
        "Policlinico Umberto I",
        "Ospedale San Camillo-Forlanini",
        "Ospedale San Giovanni Addolorata",
        "IRCCS San Raffaele Pisana",
        "IFO Regina Elena",
        "Ospedale Pediatrico Bambino Gesù"
    ],
    "Milano": [
        "Ospedale Niguarda Ca' Granda",
        "IRCCS Ospedale San Raffaele",
        "Policlinico di Milano",
        "Ospedale Buzzi",
        "Fatebenefratelli e Oftalmico",
        "Istituto Nazionale dei Tumori"
    ],
    "Napoli": [
        "Ospedale Antonio Cardarelli",
        "Ospedale del Mare",
        "AORN Monaldi",
        "Ospedale Pediatrico Santobono-Pausilipon",
        "AOU Federico II"
    ],
    "Torino": [
        "Città della Salute e della Scienza",
        "Ospedale CTO",
        "Ospedale Mauriziano",
        "Ospedale Maria Vittoria",
        "Ospedale Regina Margherita"
    ],
    "Palermo": [
        "Ospedale Civico Di Cristina Benfratelli",
        "Ospedale Villa Sofia Cervello",
        "Policlinico Paolo Giaccone"
    ],
    "Genova": [
        "Ospedale Policlinico San Martino",
        "Ospedale Galliera",
        "Ospedale Gaslini"
    ],
    "Bari": [
        "Policlinico di Bari",
        "Ospedale Di Venere",
        "Ospedale San Paolo"
    ],
    "Firenze": [
        "AOU Careggi",
        "Ospedale Santa Maria Nuova",
        "Ospedale Pediatrico Meyer"
    ],
    "Bologna": [
        "Policlinico Sant'Orsola-Malpighi",
        "Ospedale Maggiore Carlo Alberto Pizzardi",
        "Istituto Ortopedico Rizzoli"
    ],
    "Venezia": [
        "Ospedale SS. Giovanni e Paolo",
        "Ospedale dell'Angelo",
        "Ospedale Villa Salus"
    ],
    "Verona": [
        "Ospedale Borgo Trento",
        "Ospedale Borgo Roma",
        "Ospedale Sacro Cuore Don Calabria"
    ],
    "Trieste": [
        "Ospedale di Cattinara",
        "Ospedale Maggiore",
        "IRCCS Burlo Garofolo"
    ],
    "Catania": [
        "Ospedale Cannizzaro",
        "Ospedale Garibaldi",
        "Ospedale Vittorio Emanuele"
    ],
    "Padova": [
        "Azienda Ospedaliera di Padova",
        "Istituto Oncologico Veneto",
        "Ospedale Sant'Antonio"
    ],
    "Reggio Calabria": [
        "Grande Ospedale Metropolitano Bianchi-Melacrino-Morelli",
        "Ospedale Riuniti"
    ],
    "Taranto": [
        "Ospedale SS. Annunziata",
        "Presidio Ospedaliero Moscati"
    ],
    "Brescia": [
        "Spedali Civili di Brescia",
        "Fondazione Poliambulanza"
    ],
    "Prato": [
        "Ospedale Santo Stefano"
    ],
    "Parma": [
        "Azienda Ospedaliero-Universitaria di Parma"
    ],
    "Modena": [
        "Policlinico di Modena",
        "Ospedale Civile di Baggiovara"
    ],
    "Reggio Emilia": [
        "Arcispedale Santa Maria Nuova"
    ],
    "Perugia": [
        "Ospedale Santa Maria della Misericordia"
    ],
    "Livorno": [
        "Ospedale di Livorno"
    ],
    "Ravenna": [
        "Ospedale Santa Maria delle Croci"
    ],
    "Cagliari": [
        "Ospedale Brotzu",
        "Policlinico Universitario di Monserrato"
    ],
    "Foggia": [
        "Policlinico Riuniti di Foggia"
    ],
    "Salerno": [
        "Ospedale San Giovanni di Dio e Ruggi d'Aragona"
    ],
    "Forlì": [
        "Ospedale Morgagni-Pierantoni"
    ],
    "Pescara": [
        "Ospedale Santo Spirito"
    ],
    "Monza": [
        "Ospedale San Gerardo"
    ],
    "Siracusa": [
        "Ospedale Umberto I"
    ],
    "Latina": [
        "Ospedale Santa Maria Goretti"
    ],
    "Vicenza": [
        "Ospedale San Bortolo"
    ],
    "Terni": [
        "Azienda Ospedaliera Santa Maria di Terni"
    ],
    "Piacenza": [
        "Ospedale Guglielmo da Saliceto"
    ],
    "Alessandria": [
        "Ospedale SS. Antonio e Biagio e Cesare Arrigo"
    ],
    "La Spezia": [
        "Ospedale Sant’Andrea"
    ],
    "Pistoia": [
        "Ospedale San Jacopo"
    ],
    "Udine": [
        "Ospedale Santa Maria della Misericordia"
    ],
    "Trento": [
        "Ospedale Santa Chiara"
    ],
    "Ancona": [
        "Ospedali Riuniti di Ancona - Torrette"
    ],
    "Arezzo": [
        "Ospedale San Donato"
    ],
    "Lecce": [
        "Ospedale Vito Fazzi"
    ],
    "Pesaro": [
        "Ospedale San Salvatore"
    ],
    "Como": [
        "Ospedale Sant’Anna"
    ],
    "Lucca": [
        "Ospedale San Luca"
    ],
    "Sassari": [
        "AOU di Sassari"
    ],
    "Cosenza": [
        "Ospedale Annunziata"
    ],
    "Massa": [
        "Ospedale delle Apuane"
    ],
    "Grosseto": [
        "Ospedale Misericordia"
    ],
    "Treviso": [
        "Ospedale Ca' Foncello"
    ],
    "Rimini": [
        "Ospedale Infermi di Rimini"
    ],
    "Ferrara": [
        "Arcispedale Sant’Anna"
    ],
    "Varese": [
        "Ospedale di Circolo e Fondazione Macchi"
    ],
    "Asti": [
        "Ospedale Cardinal Massaia"
    ],
    "Novara": [
        "AOU Maggiore della Carità"
    ],
    "Caserta": [
        "AORN Sant'Anna e San Sebastiano"
    ],
    "Cremona": [
        "Ospedale di Cremona"
    ],
    "Campobasso": [
        "Ospedale Cardarelli di Campobasso"
    ],
    "Lodi": [
        "Ospedale Maggiore di Lodi"
    ],
    "Vercelli": [
        "Ospedale Sant’Andrea di Vercelli"
    ],
    "Benevento": [
        "Ospedale San Pio"
    ],
    "Matera": [
        "Ospedale Madonna delle Grazie"
    ],
    "Catanzaro": [
        "AOU Mater Domini",
        "Ospedale Pugliese-Ciaccio"
    ]
}

# Funzione che ricava provincia e CAP a partire dalla città
def get_provincia_cap(citta):
    # In caso la città sia presente nel dizionario
    if citta in info_citta:
        # Si ricavano capi provincia e cap
        provincia, cap = info_citta[citta]
        # Del CAP si prendono solo le prime 3 cifre
        base_cap = cap[:3]
        # Genera un valore randomico per le altre 2
        val = random.randint(1, 99)
        # Se necessario aggiunge uno 0
        val_str = f"{val:02d}"
        new_cap = base_cap + val_str
        # Restituisce i valori finali
        return provincia, new_cap
    else:
        # Non restituisce nulla
        return None, None

# Funzione che controlla l'ultimo carattere del codice fiscale
def calcola_codice_controllo(cf15):
    # Ad ogni carattere è associato un valore in base al fatto che si trovi nella posizione pari o dispari
    dispari = {
        '0': 1,  '1': 0,  '2': 5,  '3': 7,  '4': 9,  '5': 13, '6': 15, '7': 17, '8': 19, '9': 21,
        'A': 1,  'B': 0,  'C': 5,  'D': 7,  'E': 9,  'F': 13, 'G': 15, 'H': 17, 'I': 19, 'J': 21,
        'K': 2,  'L': 4,  'M': 18, 'N': 20,'O': 11, 'P': 3,  'Q': 6,  'R': 8,  'S': 12, 'T': 14,
        'U': 16, 'V': 10, 'W': 22, 'X': 25,'Y': 24, 'Z': 23
    }

    pari = {
        '0': 0,  '1': 1,  '2': 2,  '3': 3,  '4': 4,  '5': 5,  '6': 6,  '7': 7,  '8': 8,  '9': 9,
        'A': 0,  'B': 1,  'C': 2,  'D': 3,  'E': 4,  'F': 5,  'G': 6,  'H': 7,  'I': 8,  'J': 9,
        'K': 10, 'L': 11, 'M': 12, 'N': 13,'O': 14, 'P': 15, 'Q': 16,'R': 17,'S': 18, 'T': 19,
        'U': 20, 'V': 21, 'W': 22, 'X': 23,'Y': 24, 'Z': 25
    }

    # Caratteri ammessi
    caratteri = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    somma = 0

    # Si sommano i valori dei caratteri
    for i, c in enumerate(cf15):
        # Se la posizione è pari, si aggiunge alla tabella dispari e vic. (si consideri che la notazione parte da 0)
        if (i % 2) == 0:
            somma += dispari[c]
        else:
            somma += pari[c]

    # La somma si modula per 26 (numero di lettere dell'alfabeto)
    return caratteri[somma % 26]

# Funzione per la generazione del cf a partire da nome, cognome, sesso, data di nascita e luogo di nascita
def genera_codice(nome, cognome, sesso, data_nascita_str, luogo_nascita):
    # Converte la stringa data_nascita in un oggetto date
    data_nascita = datetime.strptime(data_nascita_str, "%Y-%m-%d").date()

    # Codifica nome
    def codifica_nome(nome):
        # Si considerano vocali e consonanti
        consonanti = ''.join([c for c in nome.upper() if c.isalpha() and c not in 'AEIOU'])
        vocali = ''.join([c for c in nome.upper() if c in 'AEIOU'])

        # Se la lunghezza è >= 4 si prendono quelle di posizione 0,2,3
        if len(consonanti) >= 4:
            return consonanti[0] + consonanti[2] + consonanti[3]
        # Altrimenti aggiunge fino a tre 'X'
        return (consonanti + vocali + 'XXX')[:3]

    # Codifica cognome
    def codifica_cognome(cognome):
        # Si distinguono sempre vocali e consonanti
        consonanti = ''.join([c for c in cognome.upper() if c.isalpha() and c not in 'AEIOU'])
        vocali = ''.join([c for c in cognome.upper() if c in 'AEIOU'])

        # Se non sono sufficienti si aggiungono fino a tre 'X'
        return (consonanti + vocali + 'XXX')[:3]

    # Codifica data e sesso
    def codifica_data(data_nascita, sesso):
        # Codifica mesi in lettere
        mesi = "ABCDEHLMPRST"

        # Prende le ultime 2 cifre dell'anno
        anno = str(data_nascita.year)[-2:]

        # Usa il numero del mese per trovare il carattere corrispondente
        mese = mesi[data_nascita.month - 1]

        # Se il sesso è M resta uguale il valore altrimenti si aggiunge 40
        giorno = data_nascita.day + (40 if sesso.upper() == "F" else 0)
        return f"{anno}{mese}{giorno:02d}"

    # Si ricavano i campi a partire dalle funzioni precedentemente definite
    cognome_cf = codifica_cognome(cognome)
    nome_cf = codifica_nome(nome)
    data_cf = codifica_data(data_nascita, sesso)
    codice_catastale = codici_catastali.get(luogo_nascita, "Z000")

    # Il codice fiscale si ottiene come concatenazione di questi valori
    cf15 = cognome_cf + nome_cf + data_cf + codice_catastale

    # Sedicesimo carattere
    check_char = calcola_codice_controllo(cf15)

    # Codice fiscale completo
    return (cf15 + check_char).upper()

# Funzione che verifica la validità degli orari
def check_orari(ora_chiamata=None):
    if not ora_chiamata:
        # Genera un orario base casuale nel formato HH:MM
        base_hour = random.randint(0, 22)  # fino alle 22 per lasciare spazio a +4 intervalli di max 1h
        base_minute = random.randint(0, 59)
        base_second = random.randint(0,59)
        ora_chiamata = datetime.strptime(f"{base_hour:02d}:{base_minute:02d}:{base_second:02d}", "%H:%M:%S")

    # Funzione per aggiungere un intervallo casuale fino a 60 minuti
    def next_time(prev_time):
        delta_minuti = random.randint(1, 60)  # almeno 1 minuto dopo, max 60
        return prev_time + timedelta(minutes=delta_minuti)

    # In modo da garantire che ora_partenza_mezzo < ora_arrivo_sul_posto < ora_partenza_dal_posto < ora_arrivo_destinazione
    ora_partenza_mezzo = next_time(ora_chiamata)
    ora_arrivo_sul_posto = next_time(ora_partenza_mezzo)
    ora_partenza_dal_posto = next_time(ora_arrivo_sul_posto)
    ora_arrivo_destinazione = next_time(ora_partenza_dal_posto)

    # Ritorna stringhe formattate
    return (ora_chiamata.strftime("%H:%M"), ora_partenza_mezzo.strftime("%H:%M"),
            ora_arrivo_sul_posto.strftime("%H:%M"), ora_partenza_dal_posto.strftime("%H:%M"),
            ora_arrivo_destinazione.strftime("%H:%M"))

# Funzione per la creazione dei pazienti nel DB
def generate_patients(n):
    # Si utilizza Faker
    fake = Faker('it_IT')
    patients = []

    # Vettore delle possibili diagnosi
    diagnosi_possibili = [
        'Ipertensione',
        'Diabete',
        'Asma',
        'Depressione',
        'Cardiopatia ischemica',
        'Broncopneumopatia cronica ostruttiva (BPCO)',
        'Insufficienza renale cronica',
        'Fibrillazione atriale',
        'Scompenso cardiaco',
        'Obesita',
        'Osteoartrite',
        'Ictus',
        'Epilessia',
        'Anemia',
        'Cancro al polmone',
        'Cancro al seno',
        'Alzheimer',
        'Morbo di Parkinson',
        'Ansia generalizzata',
        'Disturbo bipolare',
        'Infezione urinaria',
        'Polmonite',
        'Emicrania',
        'Gastrite',
        'Cirrosi epatica',
        'Pancreatite',
        'Covid-19',
        'Trombosi venosa profonda',
        'Celiachia',
        'Sclerosi multipla',
        'Morbo di Crohn',
        'Colite ulcerosa',
        'Dermatite atopica',
        'Psoriasi',
        'HIV/AIDS'
    ]


    # Vettore dei possibili motivi di chiamata
    motivi_chiamata = [
        'Dolore toracico',
        'Trauma',
        'Perdita di coscienza',
        'Difficolta respiratoria',
        'Emorragia',
        'Convulsioni',
        'Shock anafilattico',
        'Intossicazione',
        'Dolore addominale',
        'Ictus',
        'Ipotermia',
        'Febbre alta',
        'Frattura ossea',
        'Crisi ipertensiva',
        'Palpitazioni',
        'Infortunio sportivo',
        'Infortunio da caduta',
        'Allergia grave',
        'Avvelenamento',
        'Incidente stradale',
        'Soffocamento',
        'Arresto cardiaco',
    ]

    # Vettore che definisce le modalità di richiesta
    modalita_richiesta = [
        'Telefonata',
        'Richiesta diretta',
        'Allarme automatico',
        'Chiamata da operatore 118',
        'Segnalazione tramite app mobile',
        'Allarme da dispositivo medico',
        'Notifica da sistema di monitoraggio remoto',
        'Richiesta tramite centralino ospedaliero',
        'Allarme da sensori di caduta',
        'Segnalazione da passante',
        'Intervento da forze dell’ordine',
        'Richiesta da personale sanitario in loco',
    ]

    # Vettori mezzi di soccorso
    mezzi = [
        'Ambulanza BLS',
        'Ambulanza ALS',
        'Automedica',
        'Elisoccorso',
        'Auto infermieristica',
        'Veicolo di supporto logistico',
        'Ambulanza pediatrica',
        'Ambulanza per trasporto pazienti critici',
        'Ambulanza per emergenze ostetriche',
        'Unita mobile rianimazione',
        'Ambulanza di primo intervento',
        'Ambulanza con medico a bordo',
        'Ambulanza per trasporto neonatale',
    ]

    # Per ogni paziente
    for _ in range(n):
        # Si ricavano i seguenti campi
        data_nascita = str(fake.date_of_birth(minimum_age=1, maximum_age=100))
        sesso = random.choice(["M", "F"])
        nome = fake.first_name_male() if sesso == "M" else fake.first_name_female()
        cognome = fake.last_name()
        luogo_nascita = random.choice(list(codici_catastali.keys()))
        codice_fiscale = genera_codice(nome,cognome, sesso, data_nascita, luogo_nascita)

        intervento_presente = random.choice([True, False])
        codici = ['Giallo', 'Rosso', 'Verde','Bianco']
        medico = fake.first_name_male() if sesso == "M" else fake.first_name_female() + " " + fake.last_name()
        reagenti = random.choice([True, False])
        anisocorie = random.choice([True, False])
        diametro = str(random.randint(1,10))

        citta = random.choice(list(codici_catastali.keys()))
        provincia, cap = get_provincia_cap(citta)
        destinazione = random.choice(ospedali_per_citta.get(citta, ["Ospedale Generico"]))
        ora_chiamata, ora_partenza_mezzo, ora_arrivo_sul_posto, ora_partenza_dal_posto, ora_arrivo_destinazione = check_orari()

        # In caso di decesso avremo la firma del medico e l'ora del decesso
        if random.choice([True, False]):
            firma_medico = medico
            firma_interessato = None
            ora_decesso = fake.time()
        # In caso di mancato intervento per rifiuto, il campo firma interessato conterrà nome e cognome
        else:
            firma_medico = None
            firma_interessato = f"{nome} {cognome}"
            ora_decesso = None

        # Nel caso il campo non sia vuoto
        if intervento_presente:
            intervento = [{
                "data_intervento": str(fake.date_this_year()),
                "luogo_intervento": fake.address().replace("\n", ", "),
                "motivo_chiamata": random.choice(motivi_chiamata),
                "modalita_richiesta": random.choice(modalita_richiesta),
                "ora_chiamata": ora_chiamata,
                "ora_partenza_mezzo": ora_partenza_mezzo,
                "ora_arrivo_sul_posto": ora_arrivo_sul_posto,
                "ora_partenza_dal_posto": ora_partenza_dal_posto,
                "ora_arrivo_destinazione": ora_arrivo_destinazione,
                "destinazione_trasporto": destinazione,
                "tipo_mezzo": random.choice(mezzi),
                "codice_uscita": random.choice(codici),
                "codice_rientro": random.choice(codici),
                "ora_decesso": ora_decesso,
                "firma_medico": firma_medico,
                "firma_interessato": firma_interessato
            }]
        else:
            # Altrimenti lista vuota
            intervento = []

        # Definizione del paziente
        patient = {
            "paziente": {
                "nome": nome,
                "cognome": cognome,
                "sesso": sesso,
                "data_nascita": str(data_nascita),
                "luogo_nascita": luogo_nascita,
                "codice_fiscale": codice_fiscale.upper(),
                "telefono": fake.phone_number(),
                "via": fake.street_name(),
                "numero_civico": str(fake.building_number()),
                "citta": citta,
                "provincia": provincia,
                "cap": cap,
                "patologie_note": random.sample(diagnosi_possibili, k=random.randint(0, 2)),
            },
            # Lista di interventi
            "intervento": intervento,
            # Trasporto non effettuato
            "trasporto_non_effettuato": {
                "Effettuato da altra ambulanza": random.choice([True, False]),
                "Effettuato da elisoccorso": random.choice([True, False]),
                "Non necessita": random.choice([True, False]),
                "Trattato sul posto": random.choice([True, False]),
                "Sospeso da centrale": random.choice([True, False]),
                "Non reperito": random.choice([True, False]),
                "Scherzo": random.choice([True, False]),
            },
            # Rilevazioni
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
            # Parametri vitali
            "parametri_vitali": {
                "Pupille Reagenti": reagenti,
                "Pupille Non Reagenti": (not reagenti),
                "Pupille Anisocorie": anisocorie,
                "Pupille Non Anisocorie": (not anisocorie),
                "diametro_DX_pupilla": diametro,
                "diametro_SX_pupilla": diametro,
                "lesioni": {
                    "amputazione": random.choice([True, False]),
                    "deformita": random.choice([True, False]),
                    "dolore": random.choice([True, False]),
                    "emorragia": random.choice([True, False]),
                    "ferita_profonda": random.choice([True, False]),
                    "ferita_superficiale": random.choice([True, False]),
                    "trauma_chiuso": random.choice([True, False]),
                    "ustione": random.choice([True, False]),
                    "obiett_motorio": random.choice([True, False]),
                    "sensibilita_assente": random.choice([True, False]),
                    "frattura_sosp": random.choice([True, False]),
                    "lussazione": random.choice([True, False])
                }
            },
            # Trattamenti e interventi
            "trattamenti_e_interventi": {
                "respiratori": {
                    "ossigenoterapia_l_min": random.choice([0, 2, 5, 10]),
                    "ventilazione_assistita": random.choice([True, False]),
                    "aspirazione": random.choice([True, False]),
                    "intubazione": random.choice([True, False]),
                    "cannula_orofaringea": random.choice([True, False])
                },
                "circolatori": {
                    "MCE_min": "",
                    "DAE_N°_Shock": "",
                    "emostasi": random.choice([True, False]),
                    "accesso_venoso": random.choice([True, False]),
                    "infusione_farmaci": random.sample(["Soluzione fisiologica EV", "Paracetamolo 1000mg i.m.", "Adrenalina EV"], k=random.randint(0, 2)),
                    "monitoraggio_ecg": random.choice([True, False]),
                    "monitoraggio_spo2": random.choice([True, False]),
                    "monitoraggio_nibp": random.choice([True, False])
                },
                "immobilizzazione": {
                    "collare_cervicale": random.choice([True, False]),
                    "tavola_spinale": random.choice([True, False]),
                    "ked": random.choice([True, False]),
                    "barella_cucchiaio": random.choice([True, False]),
                    "steccobenda": random.choice([True, False]),
                    "materassino_decompressione": random.choice([True, False])
                },
                "altro": {
                    "coperta_isotermica": random.choice([True, False]),
                    "medicazione": random.choice([True, False]),
                    "ghiaccio": random.choice([True, False]),
                    "osservazione": random.choice([True, False]),
                    "annotazioni_intervento": random.choice([
                    "",
                    "Paziente collaborante durante l’intervento.",
                    "È stato necessario trasportare il paziente in posizione laterale di sicurezza.",
                    "Paziente ansioso, rassicurato verbalmente.",
                    "Presente ematoma al fianco destro, monitorato durante il trasporto.",
                    "Contatto con il medico di centrale operativa avvenuto regolarmente."])
                }
            },
            # Personale equipaggio
            "personale_equipaggio": {
                "autista": fake.name() + " " + fake.last_name(),
                "medico": medico,
                "infermiere": fake.name() + " " + fake.last_name(),
                "soccorritori": [fake.name() for _ in range(random.randint(1, 3))]
            },
            # Presenza autorità
            "presenza_autorita": {
                "carabinieri": random.choice([True, False]),
                "polizia_stradale": random.choice([True, False]),
                "polizia_municipale": random.choice([True, False]),
                "vigili_del_fuoco": random.choice([True, False]),
                "guardia_medica": random.choice([True, False]),
                "altra_ambulanza": random.choice([True, False]),
                "automedica": random.choice([True, False]),
                "elisoccorso": random.choice([True, False]),
                "altro": random.choice([
                    "118 presente sul posto",
                    "Presenza di volontari CRI",
                    "Supporto della Protezione Civile",
                    ""
                ])
            }
        }

        # Aggiungi alla lista il nuovo paziente
        patients.append(patient)

    # Restituisci tutti i pazienti
    return patients

# Funzione che carica tutti i pazienti
def load_patients(n):
    try:
        # Invoca la funzione di generazione dei pazienti
        patients = generate_patients(n)

        # Connessione al DB
        pats = connection_to_db()

        # Inserimento di tutti i pazienti nel db
        for i in range (0, len(patients)):
            pats.insert_one(patients[i])

        logging.info("Inserimento avvenuto con successo")

    except Exception as e:
        logging.error(f"Errore durante il caricamento: {e}")
        return

    return True

# Funzione per la rimozione di tutti i pazienti
def remove_all_patients():
    # Connessione al DB
    patients = connection_to_db()

    # In caso non ci siano pazienti ritorna
    if patients is None:
        return
    # Altrimenti li cancella tutti
    else:
        patients.delete_many({})
        print("Rimozione avvenuta con successo")

# Funzione per l'inserimento del paziente da file JSON
def new_patient(percorso_file_json):
        try:
            with open(percorso_file_json, "r", encoding="utf-8") as f:
                newPatient = json.load(f)

            # Se l'oggetto non è un dizionario
            if not isinstance(newPatient, dict):
                raise ValueError("Il contenuto JSON non è un oggetto valido (dict)")

            # Si estraggono le sottosezioni
            paziente = newPatient.get("paziente", {})
            intervento = newPatient.get("intervento")

            # Si controlla o genera il codice fiscale
            codice_fiscale = paziente.get("codice_fiscale", "").strip()
            if not codice_fiscale:
                nome = paziente.get("nome", "").strip()
                cognome = paziente.get("cognome", "").strip()
                sesso = paziente.get("sesso", "").strip()
                data_nascita = paziente.get("data_nascita", "").strip()
                luogo_nascita = paziente.get("luogo_nascita", "").strip()
                codice_fiscale = genera_codice(nome, cognome, sesso, data_nascita, luogo_nascita)
                paziente["codice_fiscale"] = codice_fiscale

            # Connessione al DB
            patients = connection_to_db()

            # Cerca se il paziente esiste
            existing_patient = patients.find_one({"paziente.codice_fiscale": codice_fiscale})

            if existing_patient:
                # Aggiorna: aggiungi intervento alla lista esistente (creata se non c'è)
                if "intervento" in existing_patient:
                    patients.update_one(
                        {"paziente.codice_fiscale": codice_fiscale},
                        {"$push": {"intervento": intervento}}
                    )
                else:
                    # Primo intervento → crea campo 'interventi'
                    patients.update_one(
                        {"paziente.codice_fiscale": codice_fiscale},
                        {"$set": {"intervento": [intervento]}}
                    )
                print(f"Intervento aggiunto al paziente {codice_fiscale}.")
            else:
                # Nuovo paziente → inserimento completo
                newPatient["intervento"] = [intervento]
                # newPatient.pop("intervento", None)  # Rimuove campo singolo intervento
                patients.insert_one(newPatient)
                print(f"Nuovo paziente {codice_fiscale} inserito.")

            return True

        # In caso di eccezione mostra un errore
        except Exception as e:
            print(f"Errore durante l'inserimento/aggiornamento del paziente: {e}")
        return False

# Funzione che calcola a partire dalle patologie selezionate, il numero di pazienti affetti e l'età media
def analitica_1(patologie_selezionate):
    # Connessione al DB
    patients = connection_to_db()


    pipeline = [
        {
            # Aggiunta del campo età come differenza tra data attuale e di nascita
            "$addFields": {
                "eta": {
                    "$dateDiff": {
                        "startDate": {"$dateFromString": {"dateString": "$paziente.data_nascita"}},
                        "endDate": datetime.today(),
                        "unit": "year"
                    }
                }
            }
        },
        # Filtro per pazienti che hanno almeno una delle patologie selezionate (gli altri sono scartati)
        {
            "$match": {
                "paziente.patologie_note": {"$in": patologie_selezionate}
            }
        },
        # Si decompone l'array patologie_note (da una lista si ottengono singoli elementi) per
        # raggruppare per singola patologia
        {
            "$unwind": "$paziente.patologie_note"
        },
        # Ulteriore filtraggio, per considerare solo le patologie scelte
        {
            "$match": {
                "paziente.patologie_note": {"$in": patologie_selezionate}
            }
        },
        # Raggruppamento per patologia (si considerano patologia, # di pazienti ed età media)
        {
            "$group": {
                "_id": "$paziente.patologie_note",
                "numero_pazienti": {"$sum": 1},
                "eta_media": {"$avg": "$eta"},
            }
        },
        # Ordina per numero pazienti decrescente
        {
            "$sort": {"numero_pazienti": -1}
        }
    ]

    # Si ottengono i risultati attraverso l'aggregazione
    results = list(patients.aggregate(pipeline))

    # In caso di risultati li restituisce altrimenti non restituisce nulla
    return results if results else None

# Funzione che seleziona in base al periodo di interesse il numero di interventi per sesso
def analitica_2(data_filter):
    # Connessione al DB
    patients = connection_to_db()

    # Variabili per il filtraggio (oggi, ultimo mese e ultimo anno)
    now = datetime.now()
    oggi_str = now.strftime("%Y-%m-%d")
    mese_str = now.strftime("%Y-%m")
    anno_str = now.strftime("%Y")

    # In base alla selezione si aggiorna la variabile di match
    if data_filter == "Oggi":
        match_date_filter = {"intervento.data_intervento": oggi_str}
    elif data_filter == "Ultimo mese":
        match_date_filter = {"intervento.data_intervento": {"$regex": f"^{mese_str}"}}
    else:
        match_date_filter = {"intervento.data_intervento": {"$regex": f"^{anno_str}"}}

    pipeline = [
        # Si separano gli interventi, in caso di assenza di interventi il campo viene preservato (non va perso)
        {"$unwind": {"path": "$intervento", "preserveNullAndEmptyArrays": True}},

        # Si considerano gli interventi con data valida (esistente e non nulla) e con data che
        # matchi la precedente calcolata
        {"$match": {
            "intervento.data_intervento": {"$exists": True, "$ne": None},
            **match_date_filter
        }},
        # Si raggruppa per sesso e si contano il numero di pazienti
        {"$group": {
            "_id": "$paziente.sesso",
            "numero_interventi": {"$sum": 1}
        }}
    ]

    # Si ottengono i risultati attraverso l'aggregazione
    result = list(patients.aggregate(pipeline))

    # Si restituiscono
    return  result

# Funzione che calcola il numero di pazienti per città di residenza
def analitica_3():
    # Connessione al DB
    patients = connection_to_db()

    pipeline = [
        # Raggruppamento per città e numero di pazienti
        {
            "$group": {
                "_id": "$paziente.citta",
                "numero_pazienti": {"$sum": 1}
            }
        },
        # Ordinamento per pazienti in modo decrescente
        {
            "$sort": {"numero_pazienti": -1}
        }
    ]

    # Si ottengono i risultati attraverso l'aggregazione
    return list(patients.aggregate(pipeline))

# Funzione che considera il numero di chiamate (motivi) per fasce d'età
def analitica_4():
    # Connessione al DB
    patients = connection_to_db()

    pipeline = [
        # Si trasforma la lista in modo da ottenere singoli elementi
        {"$unwind": "$intervento"},
        # Calcolo età come differenza tra la data di oggi e quella di nascita
        {
            "$addFields": {
                "eta": {
                    "$dateDiff": {
                        "startDate": {"$dateFromString": {"dateString": "$paziente.data_nascita"}},
                        "endDate": datetime.today(),
                        "unit": "year"
                    }
                }
            }
        },
        # Creazione del campo "fascia_eta"
        {"$addFields": {
            "fascia_eta": {
                # switch si usa per assegnare ad ogni documento una fascia
                "$switch": {
                    "branches": [
                        {"case": {"$lte": ["$eta", 17]}, "then": "0-17"},
                        {"case": {"$and": [{"$gte": ["$eta", 18]}, {"$lte": ["$eta", 64]}]}, "then": "18-64"},
                        {"case": {"$gte": ["$eta", 65]}, "then": "65+"}
                    ],
                    "default": "Non specificato"
                }
            }
        }},
        # Si raggruppa per fascia d'età e motivo di chiamata
        {"$group": {
            "_id": {
                "fascia_eta": "$fascia_eta",
                "motivo_chiamata": "$intervento.motivo_chiamata"
            },
            "count": {"$sum": 1}
        }},
        # Si ordinano per fascia e numero di chiamate
        {"$sort": {
            "_id.fascia_eta": 1,
            "count": -1
        }}
    ]

    # Si ottengono i risultati attraverso l'aggregazione
    risultati = patients.aggregate(pipeline)

    # Per la visualizzazione in streamlit in un formato leggibile:
    # {
    #   "0-17": {
    #     "Febbre alta": 12,
    #     "Trauma": 4
    #   },
    #   ...
    # }

    output = {}
    # Per ogni risultato
    for r in risultati:
        # Si calcolano fascia motivo e numero di chiamate
        fascia = r["_id"]["fascia_eta"]
        motivo = r["_id"]["motivo_chiamata"] or "Non specificato"
        count = r["count"]
        if fascia not in output:
            output[fascia] = {}
        output[fascia][motivo] = count

    # Restituisce l'output
    return output

# Funzione che calcola il # di interventi effettuati di giorno e di notte
def analitica_5():
    # Connessione al DB
    patients = connection_to_db()

    pipeline = [
        # Si divide la lista
        {"$unwind": "$intervento"},
        {   # Si aggiunge il campo ora_chiamata (tipo stringa)
            "$addFields": {
                "ora_chiamata_str": "$intervento.ora_chiamata"
            }
        },
        {   # Trasformazione in un oggetto date (es. "1970-01-01T14:30:00Z")
            "$project": {
                "ora_chiamata": {
                    "$dateFromString": {
                        "dateString": {
                            "$concat": ["1970-01-01T", "$ora_chiamata_str"]
                        },
                    }
                }
            }
        },
        # Raggruppamento per diurno e nottorno
        {
            "$group": {
                "_id": {
                    "$cond": [
                        {
                            "$and": [
                                # Attraverso hour si estra l'orario dall'oggetto Date
                                # Si considera notturna una chiamata tra le 00.00 e le 05.59
                                # altrimenti è diurna
                                {"$gte": [{"$hour": "$ora_chiamata"}, 0]},
                                {"$lt": [{"$hour": "$ora_chiamata"}, 6]}
                            ]
                        },
                        "notturna",
                        "diurna"
                    ]
                },
                "count": {"$sum": 1}
            }
        }
    ]

    # Si ottengono i risultati attraverso l'aggregazione
    result = list(patients.aggregate(pipeline))

    return result

# Funzione che restituisce nome e cognome dei pazienti nel db
def get_nome_cognome():
    # Connessione al DB
    patients = connection_to_db()

    # Si ricercano tutti i pazienti ("{}") e mostra solo nome e cognome
    risultati = patients.find({}, {"_id": 0, "paziente.nome": 1, "paziente.cognome": 1})

    # Creazione di una lista di pazienti. Si scorrono i risultati e si verifica se i campi non
    # sono vuoti, toglie spazi vuoti e rende maiuscola la prima lettera
    pazienti = [
        f"{r['paziente']['nome'].strip().title()} {r['paziente']['cognome'].strip().title()}"
        for r in risultati
        if "paziente" in r and "nome" in r["paziente"] and "cognome" in r["paziente"]
    ]

    # Rimozione duplicati
    pazienti_unici = sorted(set(pazienti))

    return pazienti_unici

# Funzione che restituisce tutti i CF presenti nel DB
def get_codici_fiscali():
    # Connessione al DB
    patients = connection_to_db()

    # Si ricercano tutti i pazienti e si estra solo il campo CF
    risultati = patients.find({}, {"_id": 0, "paziente.codice_fiscale": 1})

    # Si crea una lista nella quale si prendono tutti i CF non nulli e si rendono tutte le
    # lettere maiuscole
    codici_fiscali = [
        r['paziente']['codice_fiscale'].strip().upper()
        for r in risultati
        if "paziente" in r and "codice_fiscale" in r["paziente"] and r["paziente"]["codice_fiscale"]
    ]

    # Si rimuovono i duplicati
    codici_fiscali_unici = sorted(set(codici_fiscali))

    # Si restituiscono i cf
    return codici_fiscali_unici

# Funzione che restituisce tutte le patologie dei pazienti
def get_patologie():
    # Connessione al DB
    patients = connection_to_db()

    # Per ogni pazinte si estrae il campo patologie_note
    risultati = patients.find({}, {"_id": 0, "paziente.patologie_note": 1})

    # Si crea una lista vuota
    patologie = []

    # Per ogni elemento
    for r in risultati:
        # Verifica che il campo paziente sia nel documento e non vuoto
        if "paziente" in r and "patologie_note" in r["paziente"] and r["paziente"]["patologie_note"]:
            patologie_note = r["paziente"]["patologie_note"]
            # Si verifica sia una lista
            if isinstance(patologie_note, list):
                # Si verifica che ogni patologia sia una stringa
                for p in patologie_note:
                    if isinstance(p, str):
                        # Si aggiunge alla lista
                        patologie.append(p.strip())

    # Si rimuovono i duplicati
    patologie_uniche = sorted(set(patologie))

    # Restituisce le patologie uniche
    return patologie_uniche

# Funzione per ricercare paziente per nome, cognome, data_inizio e fine intervento
def ricerca_paziente(nome=None, cognome=None, cf=None, data_da=None, data_a=None):
    # Connessione al DB
    patients = connection_to_db()

    query = {}

    # In caso esista uno dei seguenti campi avviene un filtraggio (case in-sensitive)
    if nome:
        query['paziente.nome'] = {'$regex': f'^{nome}$', '$options': 'i'}
    if cognome:
        query['paziente.cognome'] = {'$regex': f'^{cognome}$', '$options': 'i'}
    if cf:
        query['paziente.codice_fiscale'] = {'$regex': f'^{cf}$', '$options': 'i'}

    # Ordinamento per nome
    risultati = patients.find(query).sort('paziente.cognome', 1)
    risultati_completi = []

    # Se uno dei campi data non è vuoto viene assegnato
    filtro_data_attivo = data_da is not None or data_a is not None

    # Per ogni paziente
    for paziente in risultati:
        # Si ricavano gli interventi
        interventi = paziente.get("intervento", [])

        # Se il campo non è vuoto
        if filtro_data_attivo:
            # Si ricavano i dati filtrati per data (data_da fino a data_a)
            interventi_filtrati = [
                i for i in interventi
                if (not data_da or i.get("data_intervento", "") >= data_da) and
                   (not data_a or i.get("data_intervento", "") <= data_a)
            ]
            # Si aggiunge paziente solo se ha almeno un intervento nel range di tempo selezionato
            if interventi_filtrati:
                risultati_completi.append({
                    "paziente": paziente.get("paziente", {}),
                    "intervento": interventi_filtrati
                })
        else:
            # In caso di nessun filtro data, si restituiscono tutti gli interventi (anche vuoti)
            risultati_completi.append({
                "paziente": paziente.get("paziente", {}),
                "intervento": interventi
            })

    return risultati_completi



# remove_all_patients()
# load_patients(100)
