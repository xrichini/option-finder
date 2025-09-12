# dashboard.py
import streamlit as st
import plotly.express as px
import pandas as pd
from data.screener_logic import OptionsScreener
from utils.config import Config
from data.async_tradier import AsyncTradierClient
import asyncio
import nest_asyncio


class OptionsDashboard:
    def __init__(self):
        self.screener = OptionsScreener()
        self.tradier = AsyncTradierClient()
        self._init_session_state()

    def _init_session_state(self):
        """Initialise les variables de session"""
        if "raw_symbols" not in st.session_state:
            st.session_state.raw_symbols = []

        if "optionable_symbols" not in st.session_state:
            st.session_state.optionable_symbols = []

        # Paramètres scanner
        if "max_dte" not in st.session_state:
            st.session_state.max_dte = Config.DEFAULT_DTE

        if "min_volume" not in st.session_state:
            st.session_state.min_volume = Config.MIN_VOLUME_THRESHOLD

        if "min_oi" not in st.session_state:
            st.session_state.min_oi = Config.MIN_OPEN_INTEREST_THRESHOLD

        if "min_whale_score" not in st.session_state:
            st.session_state.min_whale_score = Config.MIN_WHALE_SCORE

    def run(self):
        st.set_page_config(
            page_title="🐋 Options Whale Screener",
            page_icon="🐋",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        # Header avec style
        st.markdown(
            """
            <div style='text-align: center; padding: 1rem; margin-bottom: 2rem;
                background: linear-gradient(90deg, #1f4e79, #2e7d32); 
                border-radius: 10px;'>
                <h1 style='color: white; margin: 0;'>
                    🐋 Options Whale Screener
                </h1>
                <p style='color: #e8f5e8; margin: 0.5rem 0 0 0;'>
                    Détection des Big Calls & Puts Buying avec HighShortInterest.com
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Sidebar configuration
        self.render_sidebar()

        # Onglets principaux
        tab1, tab2 = st.tabs(["📈 Big Calls", "📉 Big Puts"])

        # Détermine quel onglet est actif et affiche son contenu
        with tab1:
            st.session_state.active_tab = "calls"
            self.render_options_tab("calls")

        with tab2:
            st.session_state.active_tab = "puts"
            self.render_options_tab("puts")

    def render_sidebar(self):
        """Affiche et gère la barre latérale"""
        st.sidebar.markdown("## ⚙️ Configuration")
        self._render_symbol_section()
        self._render_scanner_params()
        self.render_sidebar_buttons()

    def _render_scanner_params(self):
        """Affiche les paramètres de scan dans la sidebar"""
        st.sidebar.markdown("### 🔍 Paramètres du scanner")

        # Paramètres de scan
        st.session_state.min_volume = st.sidebar.number_input(
            "Volume minimum",
            min_value=0,
            max_value=10000,
            value=int(Config.MIN_VOLUME_THRESHOLD),
            step=100,
        )

        st.session_state.min_oi = st.sidebar.number_input(
            "Open Interest minimum",
            min_value=0,
            max_value=10000,
            value=int(Config.MIN_OPEN_INTEREST_THRESHOLD),
            step=100,
        )

        st.session_state.max_dte = st.sidebar.slider(
            "DTE maximum",
            min_value=1,
            max_value=30,
            value=int(Config.DEFAULT_DTE),
            step=1,
        )

        st.session_state.min_whale_score = st.sidebar.slider(
            "Score Whale minimum",
            min_value=50,
            max_value=100,
            value=int(Config.MIN_WHALE_SCORE),
            step=5,
        )

    def _render_symbol_section(self):
        """Affiche et gère la section des symboles"""
        st.sidebar.markdown("### 📋 Liste des symboles")

        # Symboles par défaut
        default_symbols = ""

        # Utilise les symboles filtrés s'ils existent, sinon les symboles bruts
        if "optionable_symbols" in st.session_state:
            current_symbols = st.session_state.optionable_symbols
        else:
            current_symbols = st.session_state.get("raw_symbols", [])

        current_text = (
            "\n".join(current_symbols) if current_symbols else default_symbols
        )

        symbols_input = st.sidebar.text_area(
            "Symboles (un par ligne)",
            value=current_text,
            height=120,
        )

        # Met à jour la session si nécessaire
        if symbols_input != current_text:
            raw_symbols = [
                s.strip().upper() for s in symbols_input.split("\n") if s.strip()
            ]
            st.session_state.raw_symbols = raw_symbols
            if "optionable_symbols" in st.session_state:
                del st.session_state.optionable_symbols

            # Vérifie les options disponibles pour les nouveaux symboles
            if raw_symbols:
                self._check_optionable_symbols()

        # Vérifie les options si pas encore fait
        elif "optionable_symbols" not in st.session_state and current_symbols:
            self._check_optionable_symbols()

    async def _async_check_symbols(self, symbols):
        """Vérifie les symboles de manière asynchrone"""
        return await self.tradier.filter_optionable_symbols(symbols)

    def _check_optionable_symbols(self):
        """Vérifie et affiche les symboles avec options disponibles"""
        if not hasattr(st.session_state, "raw_symbols"):
            return

        progress_text = st.sidebar.empty()
        progress_text.text("Vérification des options disponibles...")

        raw_symbols = st.session_state.raw_symbols
        if not raw_symbols:
            progress_text.warning("⚠️ Aucun symbole à vérifier")
            return

        # Vérifie les options disponibles
        optionable = asyncio.run(self._async_check_symbols(raw_symbols))

        # Met à jour la session avec les symboles filtrés
        st.session_state.optionable_symbols = optionable

        # Affiche le résultat
        message = (
            f"✅ {len(optionable)} symboles avec options sur "
            f"{len(raw_symbols)} total"
        )
        progress_text.success(message)

    def render_sidebar_buttons(self):
        """Affiche les boutons de scan et clear"""
        st.sidebar.markdown("### 🔄 Actions")
        col1, col2 = st.sidebar.columns(2)

        with col1:
            scan_button = st.button(
                "🔄 SCANNER", type="primary", width="stretch", key="scan_main"
            )

        with col2:
            if st.button("🧹 Clear", width="stretch", key="clear_main"):
                # Nettoie les résultats
                if "calls_results" in st.session_state:
                    del st.session_state.calls_results
                if "puts_results" in st.session_state:
                    del st.session_state.puts_results
                st.rerun()

        if scan_button:
            tab_id = st.session_state.get("active_tab", "calls")
            st.session_state.trigger_scan = tab_id
            st.rerun()

    def render_options_tab(self, option_type: str):
        """Affiche les opportunités d'options (calls ou puts)"""
        emoji = "📈" if option_type == "calls" else "📉"
        title = f"{emoji} Big {option_type.title()} Buying Opportunities"
        st.markdown(f"### {title}")

        # Enregistre l'onglet actif
        st.session_state.active_tab = option_type

        # Vérifier si un scan est demandé pour cet onglet
        has_trigger = st.session_state.get("trigger_scan") == option_type
        should_scan = has_trigger

        if should_scan:
            if (
                not hasattr(st.session_state, "optionable_symbols")
                or not st.session_state.optionable_symbols
            ):
                st.warning("⚠️ Aucun symbole avec options disponible")
                st.session_state.trigger_scan = False
                return

            progress_text = st.empty()
            progress_text.text("🔍 Initialisation du scan...")

            try:
                # Sélectionne la méthode de scan appropriée
                screen_method = (
                    self.screener.screen_big_calls
                    if option_type == "calls"
                    else self.screener.screen_big_puts
                )

                results = screen_method(
                    symbols=st.session_state.optionable_symbols,
                    max_dte=st.session_state.max_dte,
                    min_volume=st.session_state.min_volume,
                    min_oi=st.session_state.min_oi,
                    min_whale_score=st.session_state.min_whale_score,
                )

                if results:
                    progress_text.success("✅ Scan terminé avec succès!")
                    # Stocke les résultats dans la variable appropriée
                    results_key = f"{option_type}_results"
                    st.session_state[results_key] = results
                else:
                    progress_text.warning("⚠️ Aucune opportunité trouvée")

            except Exception as e:
                progress_text.error(f"❌ Erreur pendant le scan: {str(e)}")
                results_key = f"{option_type}_results"
                st.session_state[results_key] = []
            finally:
                st.session_state.trigger_scan = False

        # Affiche les résultats
        results_key = f"{option_type}_results"
        if results_key in st.session_state:
            results = st.session_state[results_key]

            if results:
                st.success(f"🎉 {len(results)} opportunités détectées !")

                # Créer le DataFrame avec les colonnes exactes demandées
                df_display = pd.DataFrame(
                    [
                        {
                            "Symbol": result.symbol,
                            "Side": result.side.title(),
                            "Strike": f"${result.strike:.0f}",
                            "Volume 1J": result.volume_1d,
                            "Vol/OI": (
                                f"{result.volume_1d/result.open_interest:.1f}"
                                if result.open_interest > 0
                                else "N/A"
                            ),
                            "Delta": f"{result.delta:.2f}",
                            "DTE": result.dte,
                            "Whale Score": result.whale_score,
                        }
                        for result in results
                    ]
                )

                # Tableau des résultats
                st.dataframe(df_display, width="stretch")

                # Graphiques en 2 colonnes
                col1, col2 = st.columns(2)

                with col1:
                    # Top 10 par Whale Score
                    fig1 = px.bar(
                        df_display.head(10),
                        x="Symbol",
                        y="Whale Score",
                        title="🏆 Top 10 par Whale Score",
                        color="Whale Score",
                        color_continuous_scale="Viridis",
                    )
                    fig1.update_layout(showlegend=False)
                    st.plotly_chart(fig1, width="stretch")

                with col2:
                    # Distribution par DTE
                    dte_counts = (
                        pd.DataFrame(results)[["dte"]].value_counts().reset_index()
                    )
                    dte_counts.columns = ["DTE", "Count"]

                    fig2 = px.pie(
                        dte_counts,
                        values="Count",
                        names="DTE",
                        title="📅 Distribution par DTE",
                    )
                    st.plotly_chart(fig2, width="stretch")

                # Métriques en bas
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    scores = [r.whale_score for r in results]
                    avg_whale_score = sum(scores) / len(scores)
                    st.metric("Score Whale Moyen", f"{avg_whale_score:.1f}")

                with col2:
                    total_volume = sum(r.volume_1d for r in results)
                    st.metric("Volume Total (1J)", f"{total_volume:,}")

                with col3:
                    total_oi = sum(r.open_interest for r in results)
                    st.metric("Open Interest Total", f"{total_oi:,}")

                with col4:
                    avg_dte = sum(r.dte for r in results) / len(results)
                    st.metric("DTE Moyen", f"{avg_dte:.1f}")

            else:
                message = (
                    "🔍 Aucune opportunité détectée. "
                    "Essayez d'ajuster les paramètres."
                )
                st.info(message)
        else:
            st.info("👆 Configurez et cliquez sur SCANNER pour commencer")
