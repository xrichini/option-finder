#!/usr/bin/env python3
"""
Script de diagnostic à exécuter dans l'interface Streamlit
Ce script affiche l'état complet de la session pour identifier le problème
"""

import streamlit as st
from utils.config import Config

def main():
    st.title("🔍 Diagnostic État Streamlit")
    st.markdown("---")
    
    # 1. Configuration générale
    st.subheader("🔧 Configuration")
    
    config_info = {
        "Environnement": Config.get_tradier_environment(),
        "URL Base": Config.get_tradier_base_url(),
        "Mode Dev": Config.is_development_mode(),
        "Volume Min": Config.get_min_volume_threshold(),
        "OI Min": Config.get_min_open_interest_threshold(),
        "Whale Score Min": Config.get_min_whale_score(),
        "AI Capabilities": Config.has_ai_capabilities()
    }
    
    for key, value in config_info.items():
        st.write(f"**{key}:** {value}")
    
    # 2. État de la session
    st.subheader("📊 État Session")
    
    session_keys = [
        "optionable_symbols", "raw_symbols", "symbols_loaded", 
        "min_volume", "min_oi", "min_whale_score", "max_dte",
        "ai_enabled", "calls_results", "puts_results",
        "is_scanning", "trigger_scan", "active_tab"
    ]
    
    for key in session_keys:
        value = st.session_state.get(key, "❌ Non défini")
        if isinstance(value, list):
            st.write(f"**{key}:** {len(value)} éléments")
            if value and len(value) <= 10:
                st.write(f"  └─ {value}")
        else:
            st.write(f"**{key}:** {value}")
    
    # 3. Test de chargement de symboles
    st.subheader("📈 Test Chargement Symboles")
    
    if st.button("🚀 Charger Symboles Test"):
        try:
            # Force load symbols for test
            test_symbols = ['SPY', 'AAPL', 'TSLA']  # Test symbols
            st.session_state['optionable_symbols'] = test_symbols
            st.session_state['symbols_loaded'] = True
            st.success(f"✅ {len(test_symbols)} symboles chargés: {test_symbols}")
        except Exception as e:
            st.error(f"❌ Erreur chargement: {e}")
    
    # 4. Test de screening
    st.subheader("🔍 Test Screening Direct")
    
    if st.button("🎯 Test Screening CALLS") and st.session_state.get('optionable_symbols'):
        with st.spinner("Testing screening..."):
            try:
                from ui.dashboard import OptionsDashboard
                
                dashboard = OptionsDashboard()
                test_symbols = st.session_state.get('optionable_symbols', [])[:1]  # Just first symbol
                
                results = dashboard._run_enhanced_screening(
                    option_type='call',
                    symbols=test_symbols,
                    progress_callback=None
                )
                
                st.success(f"✅ {len(results)} options trouvées!")
                
                if results:
                    # Store results
                    st.session_state['calls_results'] = results
                    
                    # Show top results
                    sorted_results = sorted(results, key=lambda x: x.volume_1d, reverse=True)
                    
                    st.write("**Top 10 Options:**")
                    for i, result in enumerate(sorted_results[:10], 1):
                        st.write(f"{i}. {result.symbol} ${result.strike} - "
                                f"Vol: {result.volume_1d:,} | Score: {result.whale_score:.1f}")
                
            except Exception as e:
                st.error(f"❌ Erreur screening: {e}")
                st.code(str(e))
    
    # 5. Diagnostic des paramètres
    st.subheader("⚙️ Paramètres Actuels")
    
    current_params = {
        "max_dte": st.session_state.get('max_dte', 'N/A'),
        "min_volume": st.session_state.get('min_volume', 'N/A'),
        "min_oi": st.session_state.get('min_oi', 'N/A'),
        "min_whale_score": st.session_state.get('min_whale_score', 'N/A'),
        "ai_enabled": st.session_state.get('ai_enabled', 'N/A'),
    }
    
    for key, value in current_params.items():
        default_value = getattr(Config, f'get_{key.replace("max_", "default_" if "dte" in key else "")}', lambda: "N/A")()
        if callable(default_value):
            default_value = "N/A"
        
        st.write(f"**{key}:** {value} (défaut: {default_value})")
    
    # 6. Forcer réinitialisation
    st.subheader("🔄 Réinitialisation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🏗️ Réinitialiser Paramètres"):
            # Force reinit like in dashboard
            st.session_state.setdefault("max_dte", Config.DEFAULT_DTE)
            st.session_state.setdefault("min_volume", Config.get_min_volume_threshold())
            st.session_state.setdefault("min_oi", Config.get_min_open_interest_threshold())
            st.session_state.setdefault("min_whale_score", Config.get_min_whale_score())
            st.session_state.setdefault("ai_enabled", Config.has_ai_capabilities())
            
            st.success("✅ Paramètres réinitialisés!")
            st.rerun()
    
    with col2:
        if st.button("🧹 Vider Session"):
            # Clear all session
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("✅ Session vidée!")
            st.rerun()
    
    # 7. État complet de la session (debug)
    with st.expander("🔍 État Complet Session (Debug)"):
        st.write("**Toutes les clés de session:**")
        for key in sorted(st.session_state.keys()):
            value = st.session_state[key]
            if isinstance(value, list):
                st.write(f"- **{key}:** Liste de {len(value)} éléments")
            elif isinstance(value, dict):
                st.write(f"- **{key}:** Dict avec {len(value)} clés")
            else:
                st.write(f"- **{key}:** {type(value).__name__} = {str(value)[:100]}...")

if __name__ == "__main__":
    main()