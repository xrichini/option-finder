import streamlit as st
from utils.helpers import get_high_short_interest_symbols


def main():
    st.title("Test de la fonction de scraping")
    st.write("Chargement des symboles...")
    symbols = get_high_short_interest_symbols()
    st.write(f"📈 {len(symbols)} symboles trouvés.")
    st.write("Test terminé!")


if __name__ == "__main__":
    main()
