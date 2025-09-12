# dashboard.py
import streamlit as st
import plotly.express as px
import pandas as pd
from data.screener_logic import OptionsScreener
from utils.config import Config
from data.async_tradier import AsyncTradierClient
from utils.async_utils import (
    run_async_in_streamlit, 
    safe_async_run_with_fallback,
    cleanup_session_async_resources
)
import asyncio
import time
import atexit
from typing import Optional


class OptionsDashboard:
    def __init__(self):
        self.screener = OptionsScreener()
        self.tradier = self._get_or_create_async_client()
        self._init_session_state()
        
        # Register cleanup for graceful shutdown
        atexit.register(self._cleanup_async_resources)
    
    def _get_or_create_async_client(self) -> AsyncTradierClient:
        """Get existing async client or create new one with proper session management"""
        if 'async_tradier_client' not in st.session_state:
            st.session_state.async_tradier_client = AsyncTradierClient()
        return st.session_state.async_tradier_client
    
    def _cleanup_async_resources(self):
        """Clean up async resources gracefully"""
        try:
            # Use the centralized cleanup utility
            cleanup_session_async_resources()
        except Exception as e:
            print(f"Warning: Error cleaning up async resources: {e}")

    def _init_session_state(self):
        """Initialise les variables de session sans écraser les valeurs existantes"""
        # Initialize symbols lists only if they don't exist
        if "raw_symbols" not in st.session_state:
            st.session_state.raw_symbols = []

        if "optionable_symbols" not in st.session_state:
            st.session_state.optionable_symbols = []

        # Paramètres scanner - utiliser setdefault pour éviter d'écraser
        st.session_state.setdefault("max_dte", Config.DEFAULT_DTE)
        st.session_state.setdefault("min_volume", Config.MIN_VOLUME_THRESHOLD)
        st.session_state.setdefault("min_oi", Config.MIN_OPEN_INTEREST_THRESHOLD)
        st.session_state.setdefault("min_whale_score", Config.MIN_WHALE_SCORE)
        
        # Initialize other necessary state variables
        st.session_state.setdefault("enable_prefiltering", True)
        st.session_state.setdefault("min_market_cap", 100_000_000)
        st.session_state.setdefault("min_stock_volume", 500_000)

    def run(self):
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
        
        # Main controls section
        self.render_main_controls()

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
        """Affiche et gère la barre latérale simplifiée"""
        st.sidebar.markdown("## ⚙️ Configuration")
        self._render_scanner_params()
        self.render_sidebar_buttons()

    def _render_scanner_params(self):
        """Affiche les paramètres essentiels du scanner"""
        st.sidebar.markdown("### 🔍 Paramètres")
        
        # Market filtering parameters
        st.sidebar.markdown("**Filtrage des symboles**")
        st.session_state.min_market_cap = st.sidebar.selectbox(
            "Capitalisation minimum",
            options=[50_000_000, 100_000_000, 500_000_000, 1_000_000_000],
            index=1,
            format_func=lambda x: f"{x/1_000_000:,.0f}M $"
        )
        
        st.session_state.min_stock_volume = st.sidebar.selectbox(
            "Volume stock minimum",
            options=[100_000, 500_000, 1_000_000, 2_000_000],
            index=1,
            format_func=lambda x: f"{x/1_000:,.0f}K"
        )
        
        # Set prefiltering to always True
        st.session_state.enable_prefiltering = True
        
        st.sidebar.markdown("**Options scanning**")
        # Essential options scanning parameters
        st.session_state.min_volume = st.sidebar.number_input(
            "📈 Volume option minimum",
            min_value=500,
            max_value=10000,
            value=int(Config.MIN_VOLUME_THRESHOLD),
            step=100,
            help="Volume minimum requis pour détecter une option"
        )

        st.session_state.min_whale_score = st.sidebar.slider(
            "🐋 Score Whale minimum",
            min_value=60,
            max_value=95,
            value=int(Config.MIN_WHALE_SCORE),
            step=5,
            help="Score minimum pour considérer une option comme 'whale activity'"
        )
        
        # Additional scanning parameters (now directly in main section, not in expander)
        st.session_state.min_oi = Config.MIN_OPEN_INTEREST_THRESHOLD
        st.session_state.max_dte = Config.DEFAULT_DTE


    def render_sidebar_buttons(self):
        """Affiche seulement l'état et les paramètres dans la sidebar"""
        # Informations sur l'état actuel
        optionable_symbols = st.session_state.get('optionable_symbols', [])
        
        if optionable_symbols:
            st.sidebar.success(
                f"✅ **{len(optionable_symbols)}** symboles chargés\n\n"
                "📈 Utilisez les contrôles de la page principale"
            )
            
            # Debug info in collapsible expander
            with st.sidebar.expander("🔍 Debug Info", expanded=False):
                raw_symbols = st.session_state.get('raw_symbols', [])
                st.write(f"Raw: {len(raw_symbols)}, Optionable: {len(optionable_symbols)}")
                st.write(f"Samples: {optionable_symbols[:3] if optionable_symbols else 'None'}")
        else:
            st.sidebar.info(
                "📝 **Configuration uniquement**\n\n"
                "Les contrôles principaux sont sur la page principale"
            )
    
    def render_main_controls(self):
        """Affiche les contrôles principaux sur la page principale"""
        st.markdown("## 🎯 Contrôles")
        
        # Status and load section
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Display current status
            optionable_symbols = st.session_state.get('optionable_symbols', [])
            if optionable_symbols:
                st.success(f"✅ **{len(optionable_symbols)} symboles** prêts pour le screening")
            else:
                st.info("💭 Chargez des symboles depuis HighShortInterest.com")
        
        with col2:
            # Load symbols button
            if st.button("🚀 Charger Symboles", type="primary", use_container_width=True, key="main_load_btn"):
                self._load_symbols_main()
        
        with col3:
            # Clear all button
            if st.button("🧹 Clear All", use_container_width=True, key="main_clear_btn"):
                self._clear_all_data()
        
        st.divider()
    
    def _load_symbols_main(self):
        """Charge les symboles depuis la page principale"""
        from utils.helpers import get_high_short_interest_symbols
        
        # Get parameters
        enable_prefiltering = st.session_state.get('enable_prefiltering', True)
        min_market_cap = st.session_state.get('min_market_cap', 100_000_000)
        min_stock_volume = st.session_state.get('min_stock_volume', 500_000)
        
        try:
            # Show loading message
            with st.spinner("📡 Chargement des symboles depuis HighShortInterest.com..."):
                # Load symbols
                symbols = get_high_short_interest_symbols(
                    enable_prefiltering=enable_prefiltering,
                    min_market_cap=min_market_cap,
                    min_avg_volume=min_stock_volume
                )
            
            if symbols:
                # Save to session state
                st.session_state.raw_symbols = symbols
                st.session_state.optionable_symbols = symbols
                st.session_state.symbols_loaded = True
                st.session_state.symbols_count = len(symbols)
                st.session_state.last_load_time = time.time()
                
                st.success(f"✅ **{len(symbols)} symboles** chargés avec succès!")
                st.rerun()
            else:
                st.error("❌ Aucun symbole trouvé - la fonction a retourné une liste vide")
                
        except Exception as e:
            st.error(f"❌ Erreur lors du chargement: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    def _clear_all_data(self):
        """Efface toutes les données"""
        # Clear symbols
        cleanup_keys = [
            "raw_symbols", "optionable_symbols", "symbols_loaded", 
            "symbols_count", "last_load_time",
            "calls_results", "puts_results",
            "trigger_scan", "is_scanning", "stop_scanning"
        ]
        
        for key in cleanup_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        st.success("✅ Toutes les données ont été effacées")
        st.rerun()

    def render_options_tab(self, option_type: str):
        """Affiche les opportunités d'options (calls ou puts)"""
        emoji = "📈" if option_type == "calls" else "📉"
        title = f"{emoji} Big {option_type.title()} Buying Opportunities"
        st.markdown(f"### {title}")

        # Enregistre l'onglet actif
        st.session_state.active_tab = option_type

        # Vérifier si un scan est demandé pour cet onglet spécifique
        has_trigger = st.session_state.get("trigger_scan") == option_type
        is_scanning = st.session_state.get("is_scanning", False)
        scan_requested_tab = st.session_state.get("scan_requested_tab")
        current_scan_type = st.session_state.get("scan_option_type")
        
        # Only this tab should handle scanning if:
        # 1. It was triggered for this option type AND not already scanning
        # 2. OR it's currently scanning for this option type
        should_scan = has_trigger and not is_scanning
        is_my_scan = is_scanning and current_scan_type == option_type

        # Only show scanning progress if this tab is handling the scan
        if is_scanning and current_scan_type == option_type:
            self._render_scanning_progress(option_type)
            return
        elif is_scanning and current_scan_type != option_type:
            # Different tab is scanning, just show a message
            st.info(f"🔍 Un scan {current_scan_type} est en cours dans l'autre onglet...")
            self._render_results_section(option_type)
            return

        if should_scan:
            if (
                not hasattr(st.session_state, "optionable_symbols")
                or not st.session_state.optionable_symbols
            ):
                st.warning("⚠️ Aucun symbole avec options disponible")
                st.session_state.trigger_scan = None  # Reset the trigger
                # Continue to render results section even if no symbols
                self._render_results_section(option_type)
                return

            # Interface de progression améliorée
            progress_container = st.container()
            
            with progress_container:
                st.markdown("### 🔍 Scan en cours...")
                
                # Barre de progression principale
                main_progress = st.progress(0)
                status_text = st.empty()
                
                # Métriques en temps réel avec containers
                col1, col2, col3 = st.columns(3)
                with col1:
                    symbols_container = st.empty()
                with col2:
                    options_container = st.empty()
                with col3:
                    time_container = st.empty()
                
                # Initialisation des métriques
                symbols_container.metric("Symboles analysés", "0")
                options_container.metric("Options trouvées", "0")
                time_container.metric("Temps écoulé", "0s")
                
                # Container pour les détails de progression
                details_expander = st.expander("🔍 Détails du scan", expanded=True)
                details_text = details_expander.empty()
                
                # Bouton d'interruption
                col_stop1, col_stop2, col_stop3 = st.columns([1, 1, 1])
                with col_stop2:
                    stop_button = st.button("🛑 Interrompre le scan", type="secondary", use_container_width=True)
                    if stop_button:
                        st.session_state.stop_scanning = True

            # Variables pour le suivi
            symbols_to_process = st.session_state.optionable_symbols
            total_symbols = len(symbols_to_process)
            start_time = time.time()
            processed_symbols = 0
            total_options_found = 0
            last_update_time = 0
            update_interval = 0.5  # Mise à jour toutes les 500ms minimum
            
            def update_progress(symbol_idx, symbol_name, options_found, current_details=""):
                nonlocal processed_symbols, total_options_found, last_update_time
                processed_symbols = symbol_idx + 1
                total_options_found += options_found
                
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # Throttling: ne pas mettre à jour trop souvent
                should_update = (
                    current_time - last_update_time >= update_interval or
                    processed_symbols == 1 or  # Première mise à jour
                    processed_symbols == total_symbols  # Dernière mise à jour
                )
                
                if should_update:
                    # Calcul du progrès
                    progress = processed_symbols / total_symbols
                    
                    # Mise à jour des éléments UI avec force refresh
                    main_progress.progress(progress)
                    status_text.text(f"Analyse {symbol_name}... ({processed_symbols}/{total_symbols})")
                    
                    # Mise à jour des métriques
                    symbols_container.metric("Symboles analysés", f"{processed_symbols}/{total_symbols}")
                    options_container.metric("Options trouvées", str(total_options_found))
                    time_container.metric("Temps écoulé", f"{elapsed_time:.1f}s")
                    
                    last_update_time = current_time
                
                # Détails actuels (mis à jour plus fréquemment pour le feedback)
                if current_details:
                    details_text.text(f"[{symbol_idx+1}/{total_symbols}] {current_details}")
                    
                # Stocker l'état dans session_state pour le débug
                st.session_state.debug_progress = {
                    'processed': processed_symbols,
                    'total': total_symbols,
                    'options_found': total_options_found,
                    'current_symbol': symbol_name,
                    'details': current_details,
                    'elapsed': elapsed_time
                }

            try:
                # Initialiser le scanning par chunks
                st.session_state.is_scanning = True
                st.session_state.scan_option_type = option_type
                st.session_state.symbols_to_scan = symbols_to_process
                st.session_state.current_scan_index = 0
                st.session_state.scan_results = []
                st.session_state.scan_start_time = time.time()
                st.session_state.stop_scanning = False
                st.session_state.trigger_scan = None  # Reset trigger after starting scan
                
                status_text.text("🚀 Initialisation du scan...")
                st.rerun()  # Relancer pour démarrer la progression

            except Exception as e:
                st.error(f"❌ Erreur pendant l'initialisation du scan: {str(e)}")
                st.session_state.is_scanning = False
                st.session_state.trigger_scan = None
                st.session_state.pop('scan_option_type', None)
        
        # Render results section when not scanning or not my scan or not starting scan
        if not should_scan and (not is_scanning or current_scan_type != option_type):
            self._render_results_section(option_type)
    
    def _run_enhanced_screening(self, option_type, symbols, progress_callback=None):
        """Exécute le screening avec progression en temps réel"""
        all_results = []
        
        for idx, symbol in enumerate(symbols):
            # Vérifier si l'utilisateur a demandé l'interruption
            if st.session_state.get('stop_scanning', False):
                if progress_callback:
                    progress_callback(idx, symbol, 0, "⚠️ Scan interrompu par l'utilisateur")
                break
                
            try:
                # Callback de progression
                if progress_callback:
                    progress_callback(
                        idx, 
                        symbol, 
                        0,  # Pas encore d'options trouvées
                        f"🔍 Analyse {symbol}..."
                    )
                
                # Obtenir les expirations
                expirations = self.screener.client.get_option_expirations(symbol)
                if not expirations:
                    if progress_callback:
                        progress_callback(idx, symbol, 0, f"⚠️ {symbol}: Pas d'expirations")
                    continue
                
                # Filtrer par DTE
                filtered_exps = self.screener.client.filter_expirations_by_dte(
                    expirations, st.session_state.max_dte
                )
                
                if not filtered_exps:
                    if progress_callback:
                        progress_callback(
                            idx, symbol, 0, 
                            f"⚠️ {symbol}: Pas d'expirations < {st.session_state.max_dte} DTE"
                        )
                    continue
                
                if progress_callback:
                    progress_callback(
                        idx, symbol, 0,
                        f"📅 {symbol}: Analyse de {len(filtered_exps)} expirations..."
                    )
                
                symbol_results = []
                
                # Analyser chaque expiration
                for exp_idx, expiration in enumerate(filtered_exps):
                    try:
                        if progress_callback:
                            progress_callback(
                                idx, symbol, len(symbol_results),
                                f"📅 {symbol}: Expiration {exp_idx+1}/{len(filtered_exps)} ({expiration})"
                            )
                        
                        # Récupérer les chaînes d'options
                        chain_data = self.screener.client.get_option_chains(symbol, expiration)
                        if not chain_data:
                            continue
                        
                        # Filtrer les options
                        options = [
                            opt for opt in chain_data
                            if (opt["option_type"].lower() == option_type
                                and opt["volume"] >= st.session_state.min_volume
                                and opt["open_interest"] >= st.session_state.min_oi)
                        ]
                        
                        if progress_callback:
                            progress_callback(
                                idx, symbol, len(symbol_results),
                                f"⚙️ {symbol}: {len(options)} options qualifiées pour {expiration}"
                            )
                        
                        # Analyser chaque option
                        for opt in options:
                            try:
                                result = self.screener._process_option(
                                    opt, symbol, option_type, st.session_state.min_whale_score
                                )
                                if result:
                                    symbol_results.append(result)
                                    
                                    if progress_callback:
                                        progress_callback(
                                            idx, symbol, len(symbol_results),
                                            f"✅ {symbol}: Option qualifiée! Score: {result.whale_score:.0f}"
                                        )
                            
                            except Exception as e:
                                if progress_callback:
                                    progress_callback(
                                        idx, symbol, len(symbol_results),
                                        f"❌ {symbol}: Erreur option - {str(e)[:50]}..."
                                    )
                                continue
                                
                    except Exception as e:
                        if progress_callback:
                            progress_callback(
                                idx, symbol, len(symbol_results),
                                f"❌ {symbol}: Erreur expiration - {str(e)[:50]}..."
                            )
                        continue
                
                # Ajouter les résultats du symbole
                if symbol_results:
                    all_results.extend(symbol_results)
                    if progress_callback:
                        progress_callback(
                            idx, symbol, len(symbol_results),
                            f"✨ {symbol}: {len(symbol_results)} options ajoutées (Total: {len(all_results)})"
                        )
                else:
                    if progress_callback:
                        progress_callback(
                            idx, symbol, 0,
                            f"🚫 {symbol}: Aucune option qualifiée"
                        )
                        
            except Exception as e:
                if progress_callback:
                    progress_callback(
                        idx, symbol, 0,
                        f"❌ {symbol}: Erreur générale - {str(e)[:50]}..."
                    )
                continue
        
        # Trier par whale score
        return sorted(all_results, key=lambda x: x.whale_score, reverse=True)
    
    def _render_scanning_progress(self, option_type: str):
        """Affiche la progression du scan en cours et traite le prochain chunk"""
        if not st.session_state.get('is_scanning', False):
            return
            
        # Récupérer l'état du scan
        symbols_to_scan = st.session_state.get('symbols_to_scan', [])
        current_index = st.session_state.get('current_scan_index', 0)
        scan_results = st.session_state.get('scan_results', [])
        start_time = st.session_state.get('scan_start_time', time.time())
        
        total_symbols = len(symbols_to_scan)
        
        # Interface de progression
        st.markdown("### 🔍 Scan en cours...")
        
        # Barre de progression
        progress = current_index / total_symbols if total_symbols > 0 else 0
        main_progress = st.progress(progress)
        
        # Métriques
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Symboles analysés", f"{current_index}/{total_symbols}")
        with col2:
            st.metric("Options trouvées", str(len(scan_results)))
        with col3:
            elapsed = time.time() - start_time
            st.metric("Temps écoulé", f"{elapsed:.1f}s")
        
        # Bouton d'interruption
        col_stop1, col_stop2, col_stop3 = st.columns([1, 1, 1])
        with col_stop2:
            if st.button("🛑 Interrompre le scan", type="secondary", use_container_width=True):
                # Arrêter complètement le scan
                st.session_state.stop_scanning = True
                st.session_state.is_scanning = False
                st.session_state.trigger_scan = False
                
                # Nettoyer immédiatement les variables de scan
                cleanup_keys = ['symbols_to_scan', 'current_scan_index', 'scan_results', 
                               'scan_start_time', 'scan_option_type', 'stop_scanning']
                for key in cleanup_keys:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.warning("⚠️ Scan interrompu par l'utilisateur")
                st.rerun()
        
        # Vérifier si le scan est terminé ou interrompu
        if current_index >= total_symbols or st.session_state.get('stop_scanning', False):
            # Scan terminé
            st.session_state.is_scanning = False
            st.session_state.trigger_scan = False
            
            final_time = time.time() - start_time
            
            # Sauvegarder les résultats seulement si le scan n'a pas été interrompu
            if not st.session_state.get('stop_scanning', False):
                results_key = f"{option_type}_results"
                st.session_state[results_key] = scan_results
                
                if scan_results:
                    st.success(f"✅ Scan terminé! {len(scan_results)} opportunités trouvées en {final_time:.1f}s")
                else:
                    st.warning(f"⚠️ Aucune opportunité trouvée (scan terminé en {final_time:.1f}s)")
            
            # Nettoyer les variables de session
            cleanup_keys = ['symbols_to_scan', 'current_scan_index', 'scan_results', 
                           'scan_start_time', 'scan_option_type', 'stop_scanning']
            for key in cleanup_keys:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.rerun()
            return
        
        # Traiter le prochain symbole
        if current_index < total_symbols:
            current_symbol = symbols_to_scan[current_index]
            st.text(f"Analyse {current_symbol}... ({current_index + 1}/{total_symbols})")
            
            # Détails en temps réel
            with st.expander("🔍 Détails", expanded=True):
                detail_placeholder = st.empty()
                detail_placeholder.text(f"🔍 Analyse {current_symbol} en cours...")
            
            # Traiter ce symbole
            try:
                symbol_results = self._process_single_symbol(
                    current_symbol, 
                    option_type, 
                    detail_placeholder
                )
                
                if symbol_results:
                    scan_results.extend(symbol_results)
                    st.session_state.scan_results = scan_results
                    detail_placeholder.success(f"✅ {current_symbol}: {len(symbol_results)} options ajoutées")
                else:
                    detail_placeholder.info(f"🚫 {current_symbol}: Aucune option qualifiée")
                    
            except Exception as e:
                detail_placeholder.error(f"❌ {current_symbol}: Erreur - {str(e)[:100]}...")
            
            # Passer au symbole suivant
            st.session_state.current_scan_index = current_index + 1
            
            # Vérifier si l'arrêt a été demandé pendant le traitement
            if st.session_state.get('stop_scanning', False) or not st.session_state.get('is_scanning', False):
                return  # Ne pas continuer si arrêt demandé
            
            # Petit délai pour permettre à l'utilisateur de voir la progression
            time.sleep(0.1)
            
            # Relancer pour le prochain symbole seulement si le scan est toujours actif
            if st.session_state.get('is_scanning', False):
                st.rerun()
    
    def _process_single_symbol(self, symbol: str, option_type: str, detail_placeholder=None):
        """Traite un seul symbole et retourne les résultats"""
        try:
            if detail_placeholder:
                detail_placeholder.text(f"📅 {symbol}: Récupération des expirations...")
            
            # Obtenir les expirations
            expirations = self.screener.client.get_option_expirations(symbol)
            if not expirations:
                return []
                
            # Filtrer par DTE
            filtered_exps = self.screener.client.filter_expirations_by_dte(
                expirations, st.session_state.max_dte
            )
            
            if not filtered_exps:
                return []
            
            if detail_placeholder:
                detail_placeholder.text(f"📅 {symbol}: Analyse de {len(filtered_exps)} expirations...")
            
            symbol_results = []
            
            # Analyser chaque expiration
            for exp_idx, expiration in enumerate(filtered_exps):
                try:
                    if detail_placeholder:
                        detail_placeholder.text(f"⚙️ {symbol}: Expiration {exp_idx+1}/{len(filtered_exps)} ({expiration})")
                    
                    # Récupérer les chaînes d'options
                    chain_data = self.screener.client.get_option_chains(symbol, expiration)
                    if not chain_data:
                        continue
                    
                    # Filtrer les options
                    options = [
                        opt for opt in chain_data
                        if (opt["option_type"].lower() == option_type
                            and opt["volume"] >= st.session_state.min_volume
                            and opt["open_interest"] >= st.session_state.min_oi)
                    ]
                    
                    if detail_placeholder:
                        detail_placeholder.text(f"⚙️ {symbol}: {len(options)} options qualifiées pour {expiration}")
                    
                    # Analyser chaque option
                    for opt in options:
                        try:
                            result = self.screener._process_option(
                                opt, symbol, option_type, st.session_state.min_whale_score
                            )
                            if result:
                                symbol_results.append(result)
                        except Exception:
                            continue
                            
                except Exception:
                    continue
                    
            return symbol_results
            
        except Exception:
            return []
    
    def _render_results_section(self, option_type: str):
        """Affiche la section des résultats avec workflow amélioré"""
        results_key = f"{option_type}_results"
        
        # Interface de contrôle contextuelle
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"### 📋 Résultats {option_type.title()}")
        
        with col2:
            # Bouton scanner contextuel avec clé unique
            scan_label = f"🔄 Scanner {option_type.title()}"
            scan_key = f"scan_{option_type}_btn"
            if st.button(scan_label, type="primary", use_container_width=True, key=scan_key):
                # Vérifier que les symboles sont disponibles
                optionable_symbols = st.session_state.get('optionable_symbols', [])
                if not optionable_symbols:
                    st.warning("⚠️ Chargez d'abord des symboles avec le bouton '🚀 Charger Symboles' ci-dessus")
                else:
                    st.info(f"🚀 Démarrage du scan {option_type.title()} avec {len(optionable_symbols)} symboles...")
                    # Démarrer le scan pour ce type d'option spécifique
                    st.session_state.trigger_scan = option_type
                    st.session_state.scan_requested_tab = option_type  # Track which tab requested the scan
                    st.rerun()
        
        with col3:
            # Bouton clear des résultats avec clé unique
            clear_key = f"clear_{option_type}_btn"
            if st.button(f"🧹 Clear {option_type.title()}", use_container_width=True, key=clear_key):
                if results_key in st.session_state:
                    del st.session_state[results_key]
                st.rerun()
        
        # Afficher les résultats s'ils existent
        if results_key in st.session_state:
            results = st.session_state[results_key]

            if results:
                # Badge du nombre de résultats
                st.success(f"🎉 {len(results)} opportunités détectées pour {option_type}!")

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
