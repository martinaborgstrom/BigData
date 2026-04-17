# Librerie
import sys
from pathlib import Path
import streamlit as st
from datetime import date, datetime

# Setup dei path
BASE_DIR = Path(__file__).resolve().parent
CLIENT_DIR = BASE_DIR.parent / "client"
sys.path.append(str(CLIENT_DIR))

# Import delle funzioni
from database import get_nome_cognome, ricerca_paziente, get_codici_fiscali

# Layout della pagina
st.set_page_config(
    page_title="Ricerca Pazienti",
    layout="wide",
    page_icon="🔎",
    initial_sidebar_state="collapsed"
)

st.markdown("<h1 style='text-align:center'>Ricerca Pazienti</h1>",unsafe_allow_html = True)

# Inizializzazione variabili
nome, cognome = None, None
risultati = ""

# Form che contiene i campi per il filtraggio
with st.form("Filtra paziente"):
    col_a, col_b = st.columns(2)
    # Si richiamano le funzioni di get_nome_cognome e get_codici_fiscali direttamente dal database
    # in modo da permettere all'utente di non inserire valori errati
    with col_a:
        nome_cognome = st.selectbox("Seleziona *nome* e *cognome*", [""] + get_nome_cognome(), index=0)
    with col_b:
        cf = st.selectbox("Seleziona *codice fiscale*", [""] + get_codici_fiscali(), index=0)

    # Si effettua un filtraggio simile per la data. Il medico infatti può definire l'intervallo di
    # tempo in cui è stato effettuato l'intervento (non necessariamente definendo entrambi i campi).
    col_c, col_d = st.columns(2)
    with col_c:
        data_intervento_da = st.date_input("Data inizio intervento", value=None)
    with col_d:
        data_intervento_a = st.date_input("Data fine intervento", value=None)

    # Nel caso in cui il campo non sia vuoto (è stato selezionato un valore), ricava i campi
    # nome e cognome
    if nome_cognome != "":
        nome, cognome = nome_cognome.split(" ")

    col1, col2, col3 = st.columns([5, 1, 5])
    with col2:
        submitted = st.form_submit_button("🔎 Ricerca")

        # Se viene premuto il bottone del form si avvia la ricerca
        if submitted:
            # Si convertono le date in stringa nel formato usato nel DB (YYYY-MM-DD)
            da_str = data_intervento_da.strftime("%Y-%m-%d") if data_intervento_da else None
            a_str = data_intervento_a.strftime("%Y-%m-%d") if data_intervento_a else None

            # Si invoca la funzione di ricerca
            risultati = ricerca_paziente(nome, cognome, cf, da_str, a_str)

# In caso di risultati stampa a video il messaggio
if risultati:
    st.toast(f"\n Risultati trovati: **{len(risultati)}**\n", icon="ℹ️")

    # Separazione per sesso
    donne = []
    uomini = []

    # Si scorrono i risultati per dividerli per sesso e aggiungerli ai vettori
    for p in risultati:
        sesso = p["paziente"].get("sesso")
        if sesso == "F":
            donne.append(p)
        else:
            uomini.append(p)

    col_1, col_2 = st.columns(2)

    # Si definisce una funzione per il calcolo dell'età
    def calcola_eta(data_nascita_str):
        # Se il campo non è vuoto
        if data_nascita_str:
            # Verifica che il campo sia una stringa
            if isinstance(data_nascita_str, str):
                # Lo si converte in data
                data_nascita = datetime.strptime(data_nascita_str, "%Y-%m-%d").date()
            else:
                # In caso sia già una data
                data_nascita = data_nascita_str
            # Si considera la data odierna
            oggi = date.today()

            # Ritorna l'età: in caso di compleanno non ancora passato si sottrae 1
            return oggi.year - data_nascita.year - ((oggi.month, oggi.day) < (data_nascita.month, data_nascita.day))
        return 0

    # Funzione che seleziona l'emoji in base all'età e al sesso
    def seleziona_emoji(eta, sesso):
        if eta <= 17:
            return "👧🏽" if sesso == "F" else "👦🏽"
        elif eta <= 64:
            return "👩🏼" if sesso == "F" else "👨🏼"
        else:
            return "👵🏾" if sesso == "F" else "👴🏾"

    # Colonna Donne
    with col_1:
        if donne:
            st.markdown("<h2 style='text-align:center'> Donne </h2>",unsafe_allow_html=True)
            # Per ogni paziente stampa le informazioni più rilevanti quali: nome, cognome, codice fiscale, età e sesso
            for p in donne:
                paz = p["paziente"]
                eta = calcola_eta(paz.get("data_nascita"))
                emoji = seleziona_emoji(eta, "F")
                with st.expander(f"{emoji} {paz.get('cognome')} {paz.get('nome')}", expanded=False):
                    st.markdown(f"🔹 **Paziente**: {paz.get('cognome')} {paz.get('nome')}")
                    st.markdown(f"🔹 **Codice Fiscale**: {paz.get('codice_fiscale')}")
                    st.markdown(f"🔹 **Età**: {eta}")
                    st.markdown(f"🔹 **Sesso**: {paz.get('sesso')}")

                    # In caso il paziente abbia subito interventi
                    interventi = p["intervento"]
                    if interventi:
                        # Per ogni intervento stampa: data intervento, motivo chiamata, operatore e destinazione trasporto
                        for i, intervento in enumerate(interventi, 1):
                            with st.expander(f"Intervento {i}", expanded=False):
                                st.markdown(f"🔹 **Data intervento**: {intervento.get('data_intervento', 'N/D')}")
                                st.markdown(f"🔹 **Motivo chiamata**: {intervento.get('motivo_chiamata', 'N/D')}")
                                st.markdown(f"🔹 **Operatore**: {intervento.get('operatore', 'N/D')}")
                                st.markdown(f"🔹 **Destinazione trasporto**: {intervento.get('destinazione_trasporto', 'N/D')}")
                                st.markdown(f"🔹 **Ora chiamata**: {intervento.get('ora_chiamata', 'N/D')}")
                    else:
                        st.info("Nessun intervento disponibile.")

    # Colonna Uomini
    with col_2:
        if uomini:
            st.markdown("<h2 style='text-align:center'> Uomini </h2>",unsafe_allow_html=True)
            # Per ogni paziente stampa le informazioni più rilevanti quali: nome, cognome, codice fiscale, età e sesso
            for p in uomini:
                paz = p["paziente"]
                eta = calcola_eta(paz.get("data_nascita"))
                emoji = seleziona_emoji(eta, "M")
                with st.expander(f"{emoji} {paz.get('cognome')} {paz.get('nome')}", expanded=False):
                    st.markdown(f"🔹 **Paziente**: {paz.get('cognome')} {paz.get('nome')}")
                    st.markdown(f"🔹 **Codice Fiscale**: {paz.get('codice_fiscale')}")
                    st.markdown(f"🔹 **Età**: {eta}")
                    st.markdown(f"🔹 **Sesso**: {paz.get('sesso')}")

                    # In caso il paziente abbia subito interventi
                    interventi = p["intervento"]
                    if interventi:
                        # Per ogni intervento stampa: data intervento, motivo chiamata, operatore e destinazione trasporto
                        for i, intervento in enumerate(interventi, 1):
                            with st.expander(f"Intervento {i}", expanded=False):
                                st.markdown(f"🔹 **Data intervento**: {intervento.get('data_intervento', 'N/D')}")
                                st.markdown(f"🔹 **Motivo chiamata**: {intervento.get('motivo_chiamata', 'N/D')}")
                                st.markdown(f"🔹 **Operatore**: {intervento.get('operatore', 'N/D')}")
                                st.markdown(f"🔹 **Destinazione trasporto**: {intervento.get('destinazione_trasporto', 'N/D')}")
                                st.markdown(f"🔹 **Ora chiamata**: {intervento.get('ora_chiamata', 'N/D')}")
                    else:
                        st.info("Nessun intervento disponibile.")


# In caso di assegna di risultati o bottone non premuto si stampa il seguente messaggio
elif risultati == "" and submitted != True:
    st.info("Si prega di selezionare un paziente da ricercare")
# In caso di bottone premuto e assenza di risultati si stampa il seguente messaggio
else:
    st.warning("❌ Nessun paziente trovato con i criteri specificati.")