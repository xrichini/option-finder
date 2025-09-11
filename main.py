# main.py
import streamlit as st
from ui.dashboard import OptionsDashboard
from utils.config import Config


def main():
    """Point d'entrée principal de l'application"""

    # Vérification de la configuration
    if not Config.TRADIER_API_KEY and not st.session_state.get("api_configured"):
        st.error("🔑 Clé API Tradier requise !")
        st.markdown(
            """
        ### Configuration requise

        1. **Clé API Tradier** - Obtenez votre clé sur 
           [tradier.com](https://tradier.com)
        2. **Créez un fichier `.env`** avec :
        ```
        TRADIER_API_KEY=votre_clé_ici
        OPENAI_API_KEY=votre_clé_openai (optionnel)
        PERPLEXITY_API_KEY=votre_clé_perplexity (optionnel)
        ```

        Ou configurez via `st.secrets` pour le déploiement Streamlit Cloud.
        """
        )

        # Permet de configurer temporairement pour test
        with st.expander("🧪 Configuration temporaire (test)"):
            temp_key = st.text_input("Clé API Tradier (temporaire)", type="password")
            if st.button("Utiliser cette clé"):
                st.session_state.api_configured = True
                st.session_state.temp_api_key = temp_key
                st.rerun()
        return

    # Lancer le dashboard
    dashboard = OptionsDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
