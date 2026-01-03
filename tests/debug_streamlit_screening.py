#!/usr/bin/env python3
"""
Debug du screening Streamlit - simule exactement ce qui se passe dans l'interface
"""

import sys
import os
sys.path.insert(0, os.getcwd())

# Simulation de l'état Streamlit
class MockSessionState:
    def __init__(self):
        self.data = {}
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def __getitem__(self, key):
        return self.data[key]
    
    def __contains__(self, key):
        return key in self.data
    
    def setdefault(self, key, default=None):
        if key not in self.data:
            self.data[key] = default
        return self.data[key]
    
    def __setitem__(self, key, value):
        self.data[key] = value

# Mock Streamlit
import streamlit as st
st.session_state = MockSessionState()

from data.screener_logic import OptionsScreener
from data.enhanced_screener import EnhancedOptionsScreener  
from utils.config import Config
from ui.dashboard import OptionsDashboard

def main():
    print("🔍 DEBUG SCREENING STREAMLIT")
    print("=" * 60)
    
    # Configuration des paramètres comme dans Streamlit
    print("\n📋 Configuration de l'état session (comme Streamlit)...")
    
    # Paramètres par défaut comme dans _init_session_state
    st.session_state['max_dte'] = Config.DEFAULT_DTE
    st.session_state['min_volume'] = Config.get_min_volume_threshold()
    st.session_state['min_oi'] = Config.get_min_open_interest_threshold()
    st.session_state['min_whale_score'] = Config.get_min_whale_score()
    st.session_state['ai_enabled'] = Config.has_ai_capabilities()
    st.session_state['ai_top_n'] = 5
    
    print(f"  max_dte: {st.session_state.get('max_dte')}")
    print(f"  min_volume: {st.session_state.get('min_volume')}")
    print(f"  min_oi: {st.session_state.get('min_oi')}")
    print(f"  min_whale_score: {st.session_state.get('min_whale_score')}")
    print(f"  ai_enabled: {st.session_state.get('ai_enabled')}")
    
    # Symboles de test
    test_symbols = ['SPY']  
    st.session_state['optionable_symbols'] = test_symbols
    
    print(f"\n🎯 Symboles configurés: {test_symbols}")
    
    # Créer le dashboard comme dans Streamlit
    print("\n🏗️ Création du dashboard...")
    dashboard = OptionsDashboard()
    
    print("\n📊 Test 1: Screening classique (non-AI)...")
    st.session_state['ai_enabled'] = False
    
    try:
        # Simuler exactement _run_enhanced_screening
        def mock_progress_callback(idx, symbol, options_found, details=""):
            print(f"  [{idx+1}/{len(test_symbols)}] {symbol}: {options_found} options - {details}")
        
        results = dashboard._run_enhanced_screening(
            option_type='call',
            symbols=test_symbols,
            progress_callback=mock_progress_callback
        )
        
        print(f"✅ Screening classique: {len(results)} calls trouvés")
        
        if results:
            for i, result in enumerate(results[:3], 1):
                print(f"  {i}. {result.symbol} ${result.strike} - "
                      f"Vol: {result.volume_1d:,} | Score: {result.whale_score:.1f}")
        
    except Exception as e:
        print(f"❌ Erreur screening classique: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n📊 Test 2: Screening avec AI...")
    st.session_state['ai_enabled'] = True
    
    try:
        results_ai = dashboard._run_enhanced_screening(
            option_type='call', 
            symbols=test_symbols,
            progress_callback=mock_progress_callback
        )
        
        print(f"✅ Screening AI: {len(results_ai)} calls trouvés")
        
        if results_ai:
            for i, result in enumerate(results_ai[:3], 1):
                print(f"  {i}. {result.symbol} ${result.strike} - "
                      f"Vol: {result.volume_1d:,} | Score: {result.whale_score:.1f}")
        
    except Exception as e:
        print(f"❌ Erreur screening AI: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n📊 Test 3: Enhanced Screener directement...")
    
    try:
        enhanced_screener = EnhancedOptionsScreener()
        
        # Test paramètres directs
        direct_results = enhanced_screener.screen_options(
            symbols=test_symbols,
            option_type='call',
            max_dte=st.session_state.get('max_dte', 7),
            min_volume=st.session_state.get('min_volume', Config.get_min_volume_threshold()),
            min_oi=st.session_state.get('min_oi', Config.get_min_open_interest_threshold()),
            min_whale_score=st.session_state.get('min_whale_score', Config.get_min_whale_score())
        )
        
        print(f"✅ Enhanced Screener direct: {len(direct_results)} calls trouvés")
        
        if direct_results:
            for i, result in enumerate(direct_results[:3], 1):
                print(f"  {i}. {result.symbol} ${result.strike} - "
                      f"Vol: {result.volume_1d:,} | Score: {result.whale_score:.1f}")
        
    except Exception as e:
        print(f"❌ Erreur Enhanced Screener: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n📊 Test 4: Screening original directement...")
    
    try:
        original_screener = OptionsScreener(use_async=False, enable_historical=False)
        
        original_results = original_screener._screen_options(
            symbols=test_symbols,
            option_type='call',
            max_dte=st.session_state.get('max_dte', 7),
            min_volume=st.session_state.get('min_volume', Config.get_min_volume_threshold()),
            min_oi=st.session_state.get('min_oi', Config.get_min_open_interest_threshold()),
            min_whale_score=st.session_state.get('min_whale_score', Config.get_min_whale_score())
        )
        
        print(f"✅ Screener original: {len(original_results)} calls trouvés")
        
    except Exception as e:
        print(f"❌ Erreur screener original: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'=' * 60}")
    print("📊 DIAGNOSTIC")
    print(f"{'=' * 60}")
    print(f"Environnement: {Config.get_tradier_environment()}")
    print("Paramètres utilisés:")
    print(f"  Volume min: {st.session_state.get('min_volume')}")
    print(f"  OI min: {st.session_state.get('min_oi')}")
    print(f"  Whale score min: {st.session_state.get('min_whale_score')}")
    print(f"  DTE max: {st.session_state.get('max_dte')}")
    
    # Vérifier les différences avec nos tests précédents
    print("\nComparaison avec test précédent:")
    print(f"  Config.get_min_volume_threshold(): {Config.get_min_volume_threshold()}")
    print(f"  Config.get_min_open_interest_threshold(): {Config.get_min_open_interest_threshold()}")
    print(f"  Config.get_min_whale_score(): {Config.get_min_whale_score()}")

if __name__ == "__main__":
    main()