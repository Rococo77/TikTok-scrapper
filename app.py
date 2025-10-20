import streamlit as st
import os
import io
from scraper import scrape_tiktok_account

st.title("TikTok Scraper")

account_url = st.text_input("URL du compte TikTok", "https://www.tiktok.com/@hugodecrypte")
num_videos = st.number_input("Nombre de vidéos à scraper", min_value=1, max_value=200, value=50)

# initialisation session_state
if "df" not in st.session_state:
    st.session_state["df"] = None
if "last_path" not in st.session_state:
    st.session_state["last_path"] = ""

if st.button("Lancer le scraping"):
    with st.spinner("Scraping en cours... (ça peut prendre du temps)..."):
        df = scrape_tiktok_account(account_url, num_videos)
        st.session_state["df"] = df
        os.makedirs('output', exist_ok=True)
        out_path = os.path.join('output', 'tiktok_videos.csv')
        df.to_csv(out_path, index=False, encoding='utf-8')
        st.session_state["last_path"] = out_path
    st.success("Scraping terminé !")

# Affichage du DataFrame si disponible
if st.session_state["df"] is not None:
    st.subheader("Données recueillies")
    st.dataframe(st.session_state["df"])

    # Préparer le CSV pour téléchargement
    csv_bytes = st.session_state["df"].to_csv(index=False, encoding='utf-8').encode('utf-8')

    col1, col2 = st.columns([1,1])
    with col1:
        st.download_button(
            label="Télécharger le CSV",
            data=csv_bytes,
            file_name="tiktok_videos.csv",
            mime="text/csv"
        )
    with col2:
        if st.session_state["last_path"]:
            st.write("CSV sauvegardé dans:")
            st.code(st.session_state["last_path"])
else:
    st.info("Lancez un scraping pour afficher et exporter les résultats.")