#!/usr/bin/env python3
"""
Debug complet du workflow Streamlit - simule exactement le processus de scanning
"""

import sys
import os
sys.path.insert(0, os.getcwd())

# Mock complet de Streamlit
class MockSessionState:
    def __init__(self):
        self.data = {}
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def __getitem__(self, key):
        return self.data[key]
    
    def __setitem__(self, key, value):
        self.data[key] = value
    
    def __contains__(self, key):
        return key in self.data
    
    def setdefault(self, key, default=None):
        if key not in self.data:
            self.data[key] = default
        return self.data[key]
    
    def pop(self, key, default=None):
        return self.data.pop(key, default)

import streamlit as st
st.session_state = MockSessionState()

from ui.dashboard import OptionsDashboard

def simulate_streamlit_scanning():
    """Simule exactement ce qui se passe quand l'utilisateur clique sur 'Scan' dans Streamlit"""
    
    print("🎬 SIMULATION COMPLÈTE DU WORKFLOW STREAMLIT")
    print("=" * 70)
    
    # 1. Configuration initiale comme dans Streamlit
    print("\n📋 Phase 1: Configuration initiale...")
    dashboard = OptionsDashboard()
    
    # Paramètres par défaut
    print(f"  AI enabled: {st.session_state.get('ai_enabled', False)}")
    print(f"  Volume min: {st.session_state.get('min_volume', 'N/A')}")
    print(f"  OI min: {st.session_state.get('min_oi', 'N/A')}")
    print(f"  Whale score min: {st.session_state.get('min_whale_score', 'N/A')}")
    print(f"  Max DTE: {st.session_state.get('max_dte', 'N/A')}")
    
    # 2. Charger des symboles (simulation)
    print("\n📈 Phase 2: Chargement symboles...")
    test_symbols = ['SPY']  # Utiliser SPY qui fonctionne
    st.session_state['optionable_symbols'] = test_symbols
    st.session_state['symbols_loaded'] = True
    print(f"  Symboles chargés: {test_symbols}")
    
    # 3. Déclencher le scan CALLS
    print("\n🚀 Phase 3: Déclenchement du scan CALLS...")
    option_type = 'calls'
    st.session_state['trigger_scan'] = option_type
    st.session_state['active_tab'] = option_type
    
    print(f"  Trigger scan: {st.session_state.get('trigger_scan')}")
    print(f"  Active tab: {st.session_state.get('active_tab')}")
    
    # 4. Simulation de render_options_tab (partie critique)
    print("\n🎭 Phase 4: Simulation render_options_tab...")
    
    # Variables qui simulent l'état Streamlit
    has_trigger = st.session_state.get("trigger_scan") == option_type
    is_scanning = st.session_state.get("is_scanning", False) 
    
    print(f"  has_trigger: {has_trigger}")
    print(f"  is_scanning: {is_scanning}")
    print(f"  should_scan: {has_trigger and not is_scanning}")
    
    if has_trigger and not is_scanning:
        print("  ✅ Conditions remplies pour démarrer le scan!")
        
        # 5. Simulation de l'initialisation du scan
        print("\n⚙️ Phase 5: Initialisation du scan...")
        
        symbols_to_process = st.session_state.get('optionable_symbols', [])
        print(f"  Symboles à traiter: {symbols_to_process}")
        
        if not symbols_to_process:
            print("  ❌ PROBLÈME: Aucun symbole à traiter!")
            return
        
        # État du scan
        st.session_state['is_scanning'] = True
        st.session_state['scan_option_type'] = option_type
        st.session_state['symbols_to_scan'] = symbols_to_process
        st.session_state['current_scan_index'] = 0
        st.session_state['scan_results'] = []
        st.session_state['trigger_scan'] = None  # Reset
        
        print("  État scanning initialisé")
        print(f"  scan_option_type: {st.session_state.get('scan_option_type')}")
        print(f"  symbols_to_scan: {st.session_state.get('symbols_to_scan')}")
        
        # 6. Simulation du scanning par chunks 
        print("\n🔄 Phase 6: Exécution du scanning...")
        
        # Simuler exactement _render_scanning_progress  
        symbols_to_scan = st.session_state.get('symbols_to_scan', [])
        current_scan_index = st.session_state.get('current_scan_index', 0)
        scan_results = st.session_state.get('scan_results', [])
        
        print("  Scanning state:")
        print(f"    symbols_to_scan: {symbols_to_scan}")  
        print(f"    current_scan_index: {current_scan_index}")
        print(f"    scan_results count: {len(scan_results)}")
        
        # Simuler le processus chunk par chunk
        if current_scan_index < len(symbols_to_scan):
            print(f"  🎯 Processing chunk {current_scan_index + 1}/{len(symbols_to_scan)}")
            
            # Callback de progression
            def progress_callback(idx, symbol, options_found, details=""):
                print(f"    Progress: [{idx+1}/{len(symbols_to_scan)}] {symbol}: {options_found} - {details}")
            
            # Appel réel du screening
            try:
                chunk_results = dashboard._run_enhanced_screening(
                    option_type=option_type.rstrip('s'),  # 'calls' -> 'call'
                    symbols=[symbols_to_scan[current_scan_index]], 
                    progress_callback=progress_callback
                )
                
                print(f"    ✅ Chunk results: {len(chunk_results)} options found")
                
                # Ajouter aux résultats
                scan_results.extend(chunk_results)
                st.session_state['scan_results'] = scan_results
                st.session_state['current_scan_index'] = current_scan_index + 1
                
                print(f"    📊 Total results so far: {len(scan_results)}")
                
                # Si terminé
                if st.session_state['current_scan_index'] >= len(symbols_to_scan):
                    print("  🏁 Scan terminé!")
                    
                    # Finalize scan
                    st.session_state['is_scanning'] = False
                    st.session_state[f'{option_type}_results'] = scan_results
                    
                    print(f"  📋 Résultats finaux stockés dans '{option_type}_results': {len(scan_results)} options")
                    
                    # Afficher les résultats
                    if scan_results:
                        print("\n🏆 TOP 5 RÉSULTATS:")
                        sorted_results = sorted(scan_results, key=lambda x: x.volume_1d, reverse=True)
                        for i, result in enumerate(sorted_results[:5], 1):
                            print(f"    {i}. {result.symbol} ${result.strike} - "
                                  f"Vol: {result.volume_1d:,} | Score: {result.whale_score:.1f}")
                    
                else:
                    print(f"  ⏳ Scan en cours... {current_scan_index + 1}/{len(symbols_to_scan)}")
                
            except Exception as e:
                print(f"    ❌ Erreur dans le scanning: {e}")
                import traceback
                traceback.print_exc()
    
    else:
        print("  ❌ Conditions non remplies pour le scan")
    
    # 7. Vérification finale des résultats stockés 
    print("\n📊 Phase 7: Vérification des résultats stockés...")
    
    calls_results = st.session_state.get('calls_results', [])
    puts_results = st.session_state.get('puts_results', [])
    
    print(f"  calls_results: {len(calls_results)} options")
    print(f"  puts_results: {len(puts_results)} options")
    
    # Simulation du rendering des résultats
    print("\n🎨 Phase 8: Simulation render_results_section...")
    
    # Exactement comme dans _render_results_section
    results_key = f"{option_type}_results"
    results = st.session_state.get(results_key, [])
    
    print(f"  Checking results_key: '{results_key}'")
    print(f"  Found {len(results)} results in session state")
    
    if results:
        print(f"  ✅ SUCCÈS! {len(results)} options trouvées pour affichage")
        
        # Simuler le filtrage/tri comme dans Streamlit
        sorted_results = sorted(results, key=lambda x: getattr(x, 'volume_1d', 0), reverse=True)
        
        print("  📋 Options triées par volume:")
        for i, result in enumerate(sorted_results[:10], 1):
            print(f"    {i:2d}. {result.symbol} ${result.strike} - "
                  f"Vol: {getattr(result, 'volume_1d', 0):,} | "
                  f"Score: {getattr(result, 'whale_score', 0):.1f}")
    else:
        print("  ❌ PROBLÈME: Aucun résultat trouvé pour l'affichage!")
        print(f"  Session state keys: {list(st.session_state.data.keys())}")

def main():
    print("🔍 DEBUG STREAMLIT WORKFLOW COMPLET")
    print("=" * 70)
    
    # Simulation complète
    simulate_streamlit_scanning()
    
    print(f"\n{'=' * 70}")
    print("🎯 RÉSUMÉ DU DIAGNOSTIC")
    print("=" * 70)
    
    # Vérifier l'état final
    final_state = {
        'optionable_symbols': st.session_state.get('optionable_symbols', []),
        'calls_results': st.session_state.get('calls_results', []),
        'puts_results': st.session_state.get('puts_results', []),
        'is_scanning': st.session_state.get('is_scanning', False),
        'trigger_scan': st.session_state.get('trigger_scan'),
    }
    
    for key, value in final_state.items():
        if isinstance(value, list):
            print(f"{key}: {len(value)} items")
        else:
            print(f"{key}: {value}")

if __name__ == "__main__":
    main()