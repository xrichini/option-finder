# main.py
import streamlit as st
from ui.dashboard import OptionsDashboard
from utils.config import Config
from utils.async_utils import cleanup_session_async_resources
import atexit

# Register global cleanup for async resources


def main():
    """Point d'entrée principal de l'application"""
    
    # Configure Streamlit page settings for better WebSocket handling
    try:
        st.set_page_config(
            page_title="🐋 Options Whale Screener",
            page_icon="🐋",
            layout="wide",
            initial_sidebar_state="expanded",
            # Disable some features that can cause WebSocket issues
            menu_items={
                'Get Help': None,
                'Report a bug': None,
                'About': None
            }
        )
    except st.errors.StreamlitAPIException:
        # Page config already set, ignore
        pass

    # Clean up any stale async resources at start
    try:
        cleanup_session_async_resources()
    except Exception as e:
        print(f"Warning: Could not clean up resources on startup: {e}")

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

    # Lancer le dashboard avec gestion d'erreurs
    try:
        dashboard = OptionsDashboard()
        dashboard.run()
    except Exception as e:
        st.error(f"❌ Erreur de l'application: {str(e)}")
        st.info("💡 Essayez de rafraîchir la page (F5) pour résoudre les problèmes de connexion.")
        
        # Clean up resources on error
        try:
            cleanup_session_async_resources()
        except Exception:
            pass
            
        # Show debug info in expander
        with st.expander("🔍 Informations de débogage"):
            st.code(str(e))
            st.text("Si le problème persiste, vérifiez votre connexion internet et les clés API.")


if __name__ == "__main__":
    main()
