# Librerie
import streamlit as st
import altair as alt
import pandas as pd
import folium
from folium.plugins import HeatMap
from geopy.geocoders import Nominatim
import streamlit.components.v1 as components
import time
from database import analitica_1,analitica_2,analitica_3, analitica_4, analitica_5, get_patologie

# Configurazione pagina
st.set_page_config(page_title="Analitiche", page_icon="📈",layout="wide")

st.markdown("<h1 style='text-align:center'>📊 Analitiche 📊</h1>",unsafe_allow_html = True)

# Creazione di 5 tab per le analitiche
tab1, tab2, tab3, tab4, tab5 = st.tabs(["\# Pazienti per patologia", "% Interventi per sesso","Provenienza dei pazienti","Motivi chiamata per fascia d'età","Interventi per fascia oraria"])

# TAB 1: # Pazienti affetti da una o più patologie
with tab1:
    st.markdown("<h3 style='text-align:center'>Numero di pazienti affetti da una o più patologia</h3>", unsafe_allow_html=True)

    # Ricerca nel db di patologie presenti
    patologie_disponibili = get_patologie()

    # Selezione delle patologie sulla base di quelle trovate
    patologie_scelte = st.multiselect("Seleziona una o più patologie", options=patologie_disponibili, default=[])

    # In caso di risultati
    if patologie_scelte:
        # Si invoca la analitica 1. Tale funzione calcola per ogni patologia, il # di pazienti che presenta
        # quella patologia e la loro età media
        risultati = analitica_1(patologie_scelte)

        # Se ritornano risultati
        if risultati:
            # Si preparano i dati per il dataframe
            data = []
            for r in risultati:
                data.append({
                    "Patologia": r['_id'],
                    "Numero pazienti": r['numero_pazienti'],
                    "Età media": r['eta_media']
                })

            # Creazione del df a partire dai dati ricavati
            df = pd.DataFrame(data)

            # Bar chart con Altair
            chart = alt.Chart(df).mark_bar().encode(
                x=alt.X("Numero pazienti:Q", title="Numero di pazienti"),
                y=alt.Y("Patologia:N", sort='-x', title="Patologia"),
                color=alt.Color("Età media:Q", scale=alt.Scale(scheme='blues'), legend=alt.Legend(title="Età media")),
                tooltip=[
                    alt.Tooltip("Patologia", title="Patologia"),
                    alt.Tooltip("Numero pazienti", title="Numero pazienti"),
                    alt.Tooltip("Età media", title="Età media", format=".1f")
                ]
            ).properties(
                width=700,
                height=400,
                title="Numero di pazienti per patologia"
            )

            # Visualizzazione
            st.altair_chart(chart, use_container_width=True)
        else:
            # In caso di assenza di risultati
            st.warning("⚠️ Nessun paziente trovato con le patologie selezionate.")
    else:
        # In caso non sia stato ancora selezionato niente
        st.info("Seleziona almeno una patologia per visualizzare i risultati.")

# TAB 2: Percentuale di interventi per sesso in base al periodo di osservazione
with tab2:
    st.markdown("<h3 style='text-align:center'>Percentuale interventi per sesso</h3>", unsafe_allow_html=True)

    # Si seleziona il periodo di osservazione
    scelta = st.radio("", ["Oggi", "Ultimo mese", "Ultimo anno"], horizontal=True)

    # Si richiama l'analitica 2. Tale funzione restituisce per ogni intervento sesso e numero di interventi effettuati
    # nel periodo di tempo considerato
    risultati = analitica_2(scelta)

    # Se ci sono risultati
    if risultati:
        # Si ricava un dataframe a partire dai risultati
        df = pd.DataFrame(risultati)

        # Si rinomina _id in Sesso e numero_interventi in Totale Interventi
        df = df.rename(columns={'_id': 'Sesso', 'numero_interventi': 'Totale Interventi'})

        # Si calca il totale interventi per tutti i sessi (per il calcolo delle percentuali)
        totale_interventi = df['Totale Interventi'].sum()
        if totale_interventi > 0:
            df['Percentuale'] = (df['Totale Interventi'] / totale_interventi) * 100
        else:
            df['Percentuale'] = 0

        # Creazione del grafico a torta con Altair
        chart = alt.Chart(df).mark_arc().encode(
            theta=alt.Theta(field='Percentuale', type='quantitative'),
            color=alt.Color('Sesso:N',
                            scale=alt.Scale(domain=['F', 'M'], range=['#ff69b4', '#4169e1']),
                            legend=alt.Legend(title="Sesso")),
            tooltip=['Sesso', 'Totale Interventi', alt.Tooltip('Percentuale', format=".2f")]
        ).properties(
            width=700,
            height=400,
            title="Percentuale di interventi per sesso"
        )

        # Visualizzazione del risultato
        st.altair_chart(chart, use_container_width=True)
    else:
        # In caso di nessun valore
        st.warning("Nessun risultato ottenuto.")

# TAB 3: Provenienza pazienti
with tab3:
    st.markdown("<h3 style='text-align:center'>Provenienza dei pazienti</h3>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    # Analitica 3: funzione che calcola per ogni paziente la provenienza
    risultati = analitica_3()

    if risultati:
        # Geocoding delle città (con cache in session_state per evitare troppe richieste)
        if "heatmap_data" not in st.session_state:
            geolocator = Nominatim(user_agent="ospedale_app")
            heat_data = []
            # Per ciascun risultato si ricavano città e numero di pazienti
            for r in risultati:
                citta = r["_id"]
                numero = r["numero_pazienti"]
                try:
                    # Attraverso l'API che ricava le coordinante a partire dalla città
                    location = geolocator.geocode(f"{citta}, Italia", timeout=10)
                    # In caso di risultati, li salva nella lista
                    if location:
                        heat_data.append([location.latitude, location.longitude, numero])
                    time.sleep(1)  # per rispettare limiti API
                # In caso di eccezioni mostra un errore
                except Exception as e:
                    st.error(f"Errore geocoding per {citta}: {e}")
            # Aggiorna la session_state
            st.session_state.heatmap_data = heat_data
        else:
            # In caso di dati già presenti li carica
            heat_data = st.session_state.heatmap_data

        # Se esistono dati
        if heat_data:
            # Crea mappa centrata sull'Italia
            m = folium.Map(location=[42.5, 12.5], zoom_start=6, tiles="CartoDB positron")
            HeatMap(heat_data, radius=25, blur=15, max_zoom=10).add_to(m)

            # Si salva la mappa in HTML e la si visualizza in Streamlit
            m.save("temp_heatmap.html")
            with open("temp_heatmap.html", 'r', encoding='utf-8') as f:
                html_data = f.read()

            # Nella colonna di sx si mostra la mappa, mentre in quella di dx la tabella con nome di città e numero di
            # pazienti per ciascuna città. Si mostrano le prima 10
            with col1:
                components.html(html_data, height=600)
            with col2:
                # Creazione df
                df = pd.DataFrame(risultati)

                # Ridenominazione delle colonne
                df = df.rename(columns={'_id': 'Città', 'numero_pazienti': 'Numero di Pazienti'})

                # Si prendono le prime 10 righe
                df = df.head(10)

                # Si cambia l'indice incrementandolo di 1
                df.index = range(1, len(df) + 1)

                # Si mostra la tabella
                st.table(df)
        else:
            # Se non vi è alcun dato
            st.warning("Nessun dato valido per generare la mappa di calore.")

    else:
        # In caso di campo risultati vuoto
        st.warning("Nessun risultato ottenuto dalla query.")

# TAB 4: Motivi di chiamata per fascia d'età
with tab4:
    st.markdown("<h3 style='text-align:center'>Distribuzione motivi chiamata per fascia d'età</h3>", unsafe_allow_html=True)

    # Si richiama l'analitica_4. Tale funzione calcola per ogni fascia d'età la percentuale di motivi di chiamata
    risultati = analitica_4()

    # In caso di risultati
    if risultati:
        # Si prepara un DataFrame salvando fascia d'età, motivo chiamata e conteggio
        rows = []
        for fascia_eta, motivi in risultati.items():
            for motivo, count in motivi.items():
                rows.append({
                    "Fascia d'età": fascia_eta,
                    "Motivo chiamata": motivo,
                    "Conteggio": count
                })

        # Si crea il df dall'array precedentemente popolato
        df = pd.DataFrame(rows)

        # Selezione fascia d'età da menu a discesa
        fascia_scelta = st.radio("Seleziona fascia d'età", options=sorted(df["Fascia d'età"].unique()), horizontal=True)

        # Filtro per fascia scelta
        df_filtrato = df[df["Fascia d'età"] == fascia_scelta]

        # Se il DataFrame filtrato ha dati
        if not df_filtrato.empty:
            chart = alt.Chart(df_filtrato).mark_bar().encode(
                x=alt.X("Conteggio:Q", title="Numero di chiamate"),
                y=alt.Y("Motivo chiamata:N", sort='-x', title="Motivo della chiamata"),
                color=alt.Color("Motivo chiamata:N", legend=None),
                tooltip=["Motivo chiamata", "Conteggio"]
            ).properties(
                width=700,
                height=400,
                title=f"Motivi chiamata per fascia d'età: {fascia_scelta}"
            )

            # Visualizzazione
            st.altair_chart(chart, use_container_width=True)
        else:
            # In caso non ci siano dati per fascia d'età
            st.warning(f"Nessun dato disponibile per la fascia d'età '{fascia_scelta}'.")
    else:
        # In caso non ci siano risultati
        st.info("Nessun dato disponibile per questa analitica.")

with tab5:
    st.markdown("<h3 style='text-align:center'>Distribuzione degli interventi tra ore diurne e notturne</h3>", unsafe_allow_html=True)

    risultati = analitica_5()

    if risultati:
        # Converto in DataFrame
        df = pd.DataFrame(risultati)
        df = df.rename(columns={"_id": "Fascia oraria", "count": "Numero interventi"})

        # Calcolo le percentuali manualmente per visualizzazione interna
        totale = df["Numero interventi"].sum()
        df["Percentuale"] = (df["Numero interventi"] / totale * 100).round(2)

        # Creo il grafico a torta
        chart = alt.Chart(df).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="Numero interventi", type="quantitative"),
            color=alt.Color(field="Fascia oraria", type="nominal"),
            tooltip=[
                alt.Tooltip("Fascia oraria:N", title="Fascia oraria"),
                alt.Tooltip("Numero interventi:Q", title="Numero interventi"),
                alt.Tooltip("Percentuale:Q", title="Percentuale (%)")
            ]
        ).properties(
            title="Distribuzione temporale degli interventi (Giorno vs Notte)",
            width=400,
            height=400
        )

        st.altair_chart(chart, use_container_width=True)
    else:
        st.warning("Nessun dato disponibile per questa analitica.")


############################### ANALITICA LUOGO NASCITA PAZIENTI OPPURE LUOGO INTERVENTO

