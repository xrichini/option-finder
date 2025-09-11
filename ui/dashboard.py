# dashboard.py
import streamlit as st
import plotly.express as px
import pandas as pd
from data.screener_logic import OptionsScreener
from utils.config import Config


class OptionsDashboard:
    def __init__(self):
        self.screener = OptionsScreener()

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
        <div style="text-align: center; padding: 1rem; background: linear-gradient(90deg, #1f4e79, #2e7d32); border-radius: 10px; margin-bottom: 2rem;">
            <h1 style="color: white; margin: 0;">🐋 Options Squeeze Screener</h1>
            <p style="color: #e8f5e8; margin: 0.5rem 0 0 0;">Détection de Big Call Buying & High Short Interest</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Sidebar configuration
        self.render_sidebar()

        # Onglets principaux
        tab1, tab2 = st.tabs(["🐋 Big Calls Scanner", "📊 Short Interest Analysis"])

        with tab1:
            self.render_big_calls_tab()

        with tab2:
            self.render_short_interest_tab()

    def render_sidebar(self):
        st.sidebar.markdown("## ⚙️ Configuration")

        # Symboles à analyser
        st.sidebar.markdown("### 📊 Symboles à analyser")
        symbols_input = st.sidebar.text_area(
            "Symboles (un par ligne)",
            value="AAPL\nTSLA\nNVDA\nAMD\nSPY\nQQQ\nIWM\nMSFT\nGOOGL",
            height=120,
        )

        symbols = [s.strip().upper() for s in symbols_input.split("\n") if s.strip()]
        st.session_state.symbols = symbols
        st.sidebar.success(f"✅ {len(symbols)} symboles configurés")

        # Paramètres de screening
        st.sidebar.markdown("### 🎯 Paramètres Big Calls")

        st.session_state.max_dte = st.sidebar.slider(
            "DTE Maximum",
            min_value=1,
            max_value=45,
            value=Config.DEFAULT_DTE,
            step=1,
            help="Days To Expiration - Plage de recherche des expirations",
        )

        st.session_state.min_volume = st.sidebar.number_input(
            "Volume minimum (1J)",
            min_value=100,
            max_value=10000,
            value=Config.MIN_VOLUME_THRESHOLD,
            step=100,
        )

        st.session_state.min_oi = st.sidebar.number_input(
            "Open Interest minimum",
            min_value=100,
            max_value=5000,
            value=Config.MIN_OPEN_INTEREST_THRESHOLD,
            step=100,
        )

        st.session_state.min_whale_score = st.sidebar.slider(
            "Score Whale minimum",
            min_value=50,
            max_value=95,
            value=Config.MIN_WHALE_SCORE,
            step=5,
            help="Score minimum pour détecter une activité de 'whale'",
        )

        # Paramètres Short Interest
        st.sidebar.markdown("### 📈 Paramètres Short Interest")
        st.session_state.min_short_interest = st.sidebar.slider(
            "Short Interest minimum (%)",
            min_value=10,
            max_value=80,
            value=int(Config.DEFAULT_SHORT_INTEREST_THRESHOLD),
            step=5,
        )

        # Bouton scan
        col1, col2 = st.sidebar.columns(2)
        with col1:
            scan_button = st.button(
                "🔄 SCANNER", type="primary", use_container_width=True
            )
        with col2:
            if st.button("🧹 Clear", use_container_width=True):
                if "scan_results" in st.session_state:
                    del st.session_state.scan_results
                if "short_results" in st.session_state:
                    del st.session_state.short_results
                st.rerun()

        if scan_button:
            st.session_state.trigger_scan = True
            st.rerun()

    def render_big_calls_tab(self):
        st.markdown("### 🎯 Big Call Buying Opportunities")

        # Vérifier si un scan est demandé
        if hasattr(st.session_state, "trigger_scan") and st.session_state.trigger_scan:
            with st.spinner("🔍 Scanning options chains..."):
                results = self.screener.screen_big_calls(
                    symbols=st.session_state.symbols,
                    max_dte=st.session_state.max_dte,
                    min_volume=st.session_state.min_volume,
                    min_oi=st.session_state.min_oi,
                    min_whale_score=st.session_state.min_whale_score,
                )
                st.session_state.scan_results = results
                st.session_state.trigger_scan = False

        # Afficher les résultats
        if hasattr(st.session_state, "scan_results"):
            results = st.session_state.scan_results

            if results:
                st.success(f"🎉 {len(results)} opportunités détectées !")

                # Créer le DataFrame avec les colonnes exactes demandées
                df_display = pd.DataFrame(
                    [
                        {
                            "Symbol": result.symbol,
                            "Side": result.side.title(),
                            "Strike": f"${result.strike:.0f}",
                            "Expiration": result.expiration,
                            "Delta": f"{result.delta:.3f}",
                            "Volume (1D)": f"{result.volume_1d:,}",
                            "Volume (7D)": f"{result.volume_7d:,}",
                            "Open Interest": f"{result.open_interest:,}",
                            "Whale Score": f"{result.whale_score:.0f}",
                            "DTE": result.dte,
                            "Last Price": f"${result.last_price:.2f}",
                            "IV": f"{result.implied_volatility*100:.1f}%",
                        }
                        for result in results
                    ]
                )

                # Tableau principal avec mise en forme
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Whale Score": st.column_config.ProgressColumn(
                            "Whale Score",
                            help="Score de probabilité d'activité whale",
                            min_value=0,
                            max_value=100,
                            format="%d",
                        ),
                        "Volume (1D)": st.column_config.NumberColumn(
                            "Volume (1D)", help="Volume du jour"
                        ),
                        "Volume (7D)": st.column_config.NumberColumn(
                            "Volume (7D)", help="Volume estimé 7 jours"
                        ),
                    },
                )

                # Graphiques
                col1, col2 = st.columns(2)

                with col1:
                    # Top 10 par volume
                    fig1 = px.bar(
                        df_display.head(10),
                        x="Symbol",
                        y=[
                            int(v.replace(",", ""))
                            for v in df_display.head(10)["Volume (1D)"]
                        ],
                        title="📊 Top 10 - Volume 1 Jour",
                        color=[float(s) for s in df_display.head(10)["Whale Score"]],
                        color_continuous_scale="Viridis",
                    )
                    fig1.update_layout(showlegend=False)
                    st.plotly_chart(fig1, use_container_width=True)

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
                    st.plotly_chart(fig2, use_container_width=True)

                # Métriques en bas
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    avg_whale_score = sum(r.whale_score for r in results) / len(results)
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
                st.info(
                    "🔍 Aucune opportunité détectée avec les critères actuels. Essayez d'ajuster les paramètres."
                )
        else:
            st.info(
                "👆 Configurez vos paramètres et cliquez sur **SCANNER** pour commencer"
            )

    def render_short_interest_tab(self):
        st.markdown("### 📈 High Short Interest Analysis")

        # Scan short interest si déjà fait un scan général
        if hasattr(st.session_state, "trigger_scan") or st.button(
            "🔍 Analyser Short Interest"
        ):
            with st.spinner("📊 Récupération des données short interest..."):
                short_data = self.screener.get_short_interest_data(
                    symbols=st.session_state.symbols,
                    min_short_interest=st.session_state.min_short_interest,
                )
                st.session_state.short_results = short_data

        if hasattr(st.session_state, "short_results"):
            short_data = st.session_state.short_results

            if short_data:
                st.success(f"📊 {len(short_data)} symboles avec high short interest !")

                # DataFrame pour affichage
                df_short = pd.DataFrame(short_data)
                df_short["Market Cap"] = df_short["market_cap"].apply(
                    lambda x: (
                        f"${x/1e9:.1f}B"
                        if x > 1e9
                        else f"${x/1e6:.0f}M" if x > 0 else "N/A"
                    )
                )
                df_short["Short %"] = df_short["short_percent"].apply(
                    lambda x: f"{x:.1f}%"
                )
                df_short["Short Ratio"] = df_short["short_ratio"].apply(
                    lambda x: f"{x:.1f}"
                )

                # Tableau
                display_cols = ["symbol", "Short %", "Short Ratio", "Market Cap"]
                st.dataframe(
                    df_short[display_cols].rename(
                        columns={
                            "symbol": "Symbol",
                            "Short %": "Short Interest %",
                            "Short Ratio": "Short Ratio (Days)",
                            "Market Cap": "Market Cap",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

                # Graphique
                if len(short_data) > 1:
                    fig = px.bar(
                        df_short,
                        x="symbol",
                        y="short_percent",
                        title="📊 Short Interest par Symbole",
                        labels={
                            "short_percent": "Short Interest %",
                            "symbol": "Symbol",
                        },
                        color="short_percent",
                        color_continuous_scale="Reds",
                    )
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

                # Alerte si combinaison call buying + short interest
                if hasattr(st.session_state, "scan_results"):
                    call_symbols = {r.symbol for r in st.session_state.scan_results}
                    short_symbols = {s["symbol"] for s in short_data}
                    combo_symbols = call_symbols.intersection(short_symbols)

                    if combo_symbols:
                        st.warning(
                            f"🚨 **ALERTE COMBO** - Symboles avec Big Calls ET High Short Interest: {', '.join(combo_symbols)}"
                        )
            else:
                st.info("📊 Aucun symbole avec short interest élevé trouvé")
