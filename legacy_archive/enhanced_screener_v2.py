# enhanced_screener_v2.py - Screener avancé avec détection d'anomalies ML
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from data.advanced_anomaly_detector import AdvancedAnomalyDetector
from utils.config import Config

class EnhancedScreenerV2:
    """Screener d'options avancé avec détection d'anomalies ML et sources professionnelles"""
    
    def __init__(self, 
                 enable_ai: bool = True,
                 enable_anomaly_detection: bool = True,
                 polygon_api_key: Optional[str] = None):
        
        # Configuration des modules
        self.ai_enabled = enable_ai if enable_ai is not None else Config.has_ai_capabilities()
        self.anomaly_enabled = enable_anomaly_detection
        
        # Initialiser les composants
        if self.ai_enabled:
            try:
                from data.ai_analysis_manager import AIAnalysisManager
                self.ai_manager = AIAnalysisManager()
                print("✅ AI Analysis Manager initialized")
            except ImportError as e:
                print(f"⚠️ AI Manager not available: {e}")
                self.ai_manager = None
                self.ai_enabled = False
        else:
            self.ai_manager = None
        
        # Détecteur d'anomalies avancé
        if self.anomaly_enabled:
            self.anomaly_detector = AdvancedAnomalyDetector(polygon_api_key)
            print("✅ Advanced Anomaly Detector initialized")
        else:
            self.anomaly_detector = None
        
        # Screener de base
        try:
            from data.screener_logic import OptionsScreener
            self.base_screener = OptionsScreener()
            print("✅ Base Options Screener loaded")
        except ImportError as e:
            print(f"⚠️ Base screener not available: {e}")
            self.base_screener = None
        
        print("🚀 Enhanced Screener V2 initialized:")
        print(f"   AI: {'✅' if self.ai_enabled else '❌'}")
        print(f"   Anomaly Detection: {'✅' if self.anomaly_enabled else '❌'}")
    
    async def comprehensive_screening(self,
                                    tickers: List[str],
                                    screening_params: Dict = None,
                                    enable_ai_analysis: bool = True,
                                    enable_anomaly_detection: bool = True,
                                    progress_callback: Optional[callable] = None) -> Dict:
        """
        Screening complet intégrant:
        1. Detection d'anomalies de marché (volume, trades)
        2. Detection d'anomalies d'options (ML)
        3. Screening traditionnel d'options
        4. Analyse IA des résultats
        """
        
        if progress_callback:
            progress_callback(0.1, "Initializing comprehensive screening...")
        
        results = {
            'timestamp': datetime.now(),
            'tickers_scanned': tickers,
            'market_anomalies': {},
            'options_anomalies': {},
            'traditional_screening': {},
            'ai_enhanced_results': {},
            'combined_signals': {},
            'summary': {}
        }
        
        # 1. PHASE 1: Détection d'anomalies de marché
        if self.anomaly_enabled and enable_anomaly_detection:
            if progress_callback:
                progress_callback(0.2, "Building anomaly detection baseline...")
            
            # Construire la baseline historique pour tous les tickers
            self.anomaly_detector.build_historical_baseline(tickers, days_back=60)
            
            if progress_callback:
                progress_callback(0.3, "Detecting market anomalies...")
            
            # Scanner les anomalies pour aujourd'hui
            today = datetime.now().strftime('%Y-%m-%d')
            market_anomalies = self.anomaly_detector.comprehensive_anomaly_scan(tickers, today)
            results['market_anomalies'] = market_anomalies
            
            print("📊 Market anomalies detected:")
            print(f"   Volume: {len(market_anomalies.get('volume_anomalies', []))}")
            print(f"   Trades: {len(market_anomalies.get('trades_anomalies', []))}")
            print(f"   Combined: {len(market_anomalies.get('combined_anomalies', []))}")
        
        # 2. PHASE 2: Identifier les tickers prioritaires basés sur les anomalies
        priority_tickers = self._get_priority_tickers_from_anomalies(
            results.get('market_anomalies', {})
        )
        
        if priority_tickers:
            print(f"🎯 Priority tickers identified: {', '.join(priority_tickers[:5])}")
        else:
            priority_tickers = tickers  # Fallback sur tous les tickers
        
        if progress_callback:
            progress_callback(0.4, f"Screening {len(priority_tickers)} priority tickers...")
        
        # 3. PHASE 3: Screening traditionnel sur les tickers prioritaires
        if self.base_screener:
            traditional_results = await self._run_traditional_screening(
                priority_tickers, 
                screening_params,
                progress_callback
            )
            results['traditional_screening'] = traditional_results
        
        # 4. PHASE 4: Analyse des anomalies d'options sur les résultats prioritaires
        if self.anomaly_enabled and enable_anomaly_detection:
            if progress_callback:
                progress_callback(0.6, "Analyzing options anomalies...")
            
            options_anomalies = await self._analyze_options_anomalies(
                priority_tickers[:10],  # Limiter pour éviter les timeouts
                today
            )
            results['options_anomalies'] = options_anomalies
        
        # 5. PHASE 5: Enrichissement IA des meilleurs résultats
        if self.ai_enabled and enable_ai_analysis and self.ai_manager:
            if progress_callback:
                progress_callback(0.8, "Running AI analysis on top results...")
            
            ai_enhanced = await self._run_ai_enhancement(
                results, 
                progress_callback
            )
            results['ai_enhanced_results'] = ai_enhanced
        
        # 6. PHASE 6: Combiner et scorer les signaux
        if progress_callback:
            progress_callback(0.9, "Combining signals and scoring...")
        
        combined_signals = self._combine_all_signals(results)
        results['combined_signals'] = combined_signals
        
        # 7. PHASE 7: Générer le résumé final
        summary = self._generate_comprehensive_summary(results)
        results['summary'] = summary
        
        if progress_callback:
            progress_callback(1.0, "Comprehensive screening completed!")
        
        print("\n🎉 COMPREHENSIVE SCREENING COMPLETED")
        print("=" * 60)
        print(f"📊 Market Anomalies: {len(results['market_anomalies'].get('volume_anomalies', []))} volume, {len(results['market_anomalies'].get('trades_anomalies', []))} trades")
        print(f"📋 Options Anomalies: {len(results.get('options_anomalies', {}))}")
        print(f"🎯 Combined Signals: {len(results['combined_signals'])}")
        print(f"⭐ Top Signal: {results['summary']['top_signal']['ticker'] if results['summary'].get('top_signal') else 'None'}")
        
        return results
    
    async def _run_traditional_screening(self, 
                                       tickers: List[str], 
                                       screening_params: Dict,
                                       progress_callback: Optional[callable] = None) -> Dict:
        """Lance le screening traditionnel d'options"""
        
        if not self.base_screener:
            return {}
        
        # Paramètres par défaut
        default_params = {
            'option_type': 'call',
            'max_dte': 30,
            'min_volume': 1000,
            'min_oi': 500,
            'min_whale_score': 60
        }
        
        if screening_params:
            default_params.update(screening_params)
        
        try:
            # Utiliser le screener existant (adapter selon votre interface)
            if hasattr(self.base_screener, 'screen_big_calls'):
                calls_results = self.base_screener.screen_big_calls(
                    tickers,
                    default_params['max_dte'],
                    default_params['min_volume'],
                    default_params['min_oi'],
                    default_params['min_whale_score']
                )
                
                puts_results = self.base_screener.screen_big_puts(
                    tickers,
                    default_params['max_dte'],
                    default_params['min_volume'],
                    default_params['min_oi'],
                    default_params['min_whale_score']
                )
                
                all_results = calls_results + puts_results
                
                return {
                    'calls': calls_results,
                    'puts': puts_results,
                    'all': all_results,
                    'total_count': len(all_results)
                }
            else:
                print("⚠️ Base screener methods not available")
                return {}
                
        except Exception as e:
            print(f"❌ Error in traditional screening: {e}")
            return {}
    
    async def _analyze_options_anomalies(self, tickers: List[str], date: str) -> Dict:
        """Analyse les anomalies d'options pour les tickers prioritaires"""
        
        if not self.anomaly_detector:
            return {}
        
        options_anomalies = {}
        
        for ticker in tickers:
            try:
                anomalies = self.anomaly_detector.detect_options_anomalies(ticker, date)
                if anomalies:
                    options_anomalies[ticker] = anomalies
                    print(f"📋 {ticker}: {len(anomalies)} options anomalies detected")
            except Exception as e:
                print(f"⚠️ Error analyzing options anomalies for {ticker}: {e}")
                continue
        
        return options_anomalies
    
    async def _run_ai_enhancement(self, results: Dict, progress_callback: Optional[callable] = None) -> Dict:
        """Lance l'analyse IA sur les meilleurs résultats"""
        
        if not self.ai_manager:
            return {}
        
        ai_enhanced = {}
        
        try:
            # Identifier les tickers les plus intéressants
            top_tickers = set()
            
            # Ajouter les tickers avec anomalies de marché
            market_anomalies = results.get('market_anomalies', {})
            for anomaly in market_anomalies.get('volume_anomalies', [])[:3]:
                top_tickers.add(anomaly.ticker)
            for anomaly in market_anomalies.get('trades_anomalies', [])[:3]:
                top_tickers.add(anomaly.ticker)
            
            # Ajouter les tickers avec bons résultats de screening traditionnel
            traditional = results.get('traditional_screening', {})
            if traditional.get('all'):
                for result in traditional['all'][:5]:
                    top_tickers.add(result.symbol)
            
            # Limiter à 5 tickers pour éviter les timeouts
            top_tickers = list(top_tickers)[:5]
            
            for ticker in top_tickers:
                try:
                    # Préparer les données pour l'IA
                    option_data = self._prepare_ai_data_for_ticker(ticker, results)
                    
                    if option_data:
                        ai_analysis = await self.ai_manager.comprehensive_analysis(ticker, option_data)
                        ai_enhanced[ticker] = ai_analysis
                        
                        if progress_callback:
                            progress_callback(0.8 + (len(ai_enhanced) / len(top_tickers)) * 0.1, 
                                            f"AI analyzing {ticker}...")
                        
                        print(f"🤖 AI analysis completed for {ticker}")
                
                except Exception as e:
                    print(f"❌ AI analysis failed for {ticker}: {e}")
                    continue
        
        except Exception as e:
            print(f"❌ Error in AI enhancement: {e}")
        
        return ai_enhanced
    
    def _prepare_ai_data_for_ticker(self, ticker: str, results: Dict) -> Optional[Dict]:
        """Prépare les données pour l'analyse IA d'un ticker"""
        
        try:
            ai_data = {
                'ticker': ticker,
                'timestamp': datetime.now(),
                'market_anomalies': {},
                'options_data': {},
                'traditional_screening': {}
            }
            
            # Ajouter les anomalies de marché
            market_anomalies = results.get('market_anomalies', {})
            
            # Volume anomalies
            for anomaly in market_anomalies.get('volume_anomalies', []):
                if anomaly.ticker == ticker:
                    ai_data['market_anomalies']['volume'] = {
                        'z_score': anomaly.z_score,
                        'severity_score': anomaly.severity_score,
                        'volume_ratio': anomaly.details.get('volume_ratio', 0),
                        'price_change_pct': anomaly.details.get('price_change_pct', 0)
                    }
            
            # Trades anomalies
            for anomaly in market_anomalies.get('trades_anomalies', []):
                if anomaly.ticker == ticker:
                    ai_data['market_anomalies']['trades'] = {
                        'z_score': anomaly.z_score,
                        'severity_score': anomaly.severity_score,
                        'trades_ratio': anomaly.details.get('trades_ratio', 0)
                    }
            
            # Options anomalies
            options_anomalies = results.get('options_anomalies', {})
            if ticker in options_anomalies:
                ai_data['options_data']['anomalies'] = []
                for opt_anomaly in options_anomalies[ticker][:3]:  # Top 3
                    ai_data['options_data']['anomalies'].append({
                        'strike': opt_anomaly.strike,
                        'option_type': opt_anomaly.option_type,
                        'anomaly_score': opt_anomaly.anomaly_score,
                        'anomaly_features': opt_anomaly.anomaly_features,
                        'bid_ask_spread': opt_anomaly.ask - opt_anomaly.bid,
                        'implied_volatility': opt_anomaly.implied_volatility
                    })
            
            # Traditional screening results
            traditional = results.get('traditional_screening', {})
            if traditional.get('all'):
                ticker_results = [r for r in traditional['all'] if r.symbol == ticker]
                if ticker_results:
                    best_result = max(ticker_results, key=lambda x: x.whale_score)
                    ai_data['traditional_screening'] = {
                        'whale_score': best_result.whale_score,
                        'volume_1d': best_result.volume_1d,
                        'open_interest': best_result.open_interest,
                        'strike': best_result.strike,
                        'side': best_result.side,
                        'dte': best_result.dte
                    }
            
            return ai_data if ai_data['market_anomalies'] or ai_data['options_data'] or ai_data['traditional_screening'] else None
            
        except Exception as e:
            print(f"❌ Error preparing AI data for {ticker}: {e}")
            return None
    
    def _get_priority_tickers_from_anomalies(self, market_anomalies: Dict) -> List[str]:
        """Extrait les tickers prioritaires des anomalies détectées"""
        
        priority_tickers = set()
        
        # Ajouter les tickers avec anomalies de volume
        for anomaly in market_anomalies.get('volume_anomalies', [])[:10]:
            priority_tickers.add(anomaly.ticker)
        
        # Ajouter les tickers avec anomalies de trades  
        for anomaly in market_anomalies.get('trades_anomalies', [])[:10]:
            priority_tickers.add(anomaly.ticker)
        
        # Ajouter les tickers avec anomalies combinées
        for combined in market_anomalies.get('combined_anomalies', [])[:5]:
            priority_tickers.add(combined['ticker'])
        
        return list(priority_tickers)
    
    def _combine_all_signals(self, results: Dict) -> List[Dict]:
        """Combine tous les signaux pour créer un score composite"""
        
        combined_signals = {}
        
        # 1. Scorer les anomalies de marché
        market_anomalies = results.get('market_anomalies', {})
        
        for anomaly in market_anomalies.get('volume_anomalies', []):
            ticker = anomaly.ticker
            if ticker not in combined_signals:
                combined_signals[ticker] = {'ticker': ticker, 'scores': {}, 'total_score': 0}
            
            combined_signals[ticker]['scores']['volume_anomaly'] = anomaly.severity_score
            combined_signals[ticker]['total_score'] += anomaly.severity_score
        
        for anomaly in market_anomalies.get('trades_anomalies', []):
            ticker = anomaly.ticker
            if ticker not in combined_signals:
                combined_signals[ticker] = {'ticker': ticker, 'scores': {}, 'total_score': 0}
            
            combined_signals[ticker]['scores']['trades_anomaly'] = anomaly.severity_score
            combined_signals[ticker]['total_score'] += anomaly.severity_score
        
        # 2. Scorer les résultats de screening traditionnel
        traditional = results.get('traditional_screening', {})
        if traditional.get('all'):
            for result in traditional['all']:
                ticker = result.symbol
                if ticker not in combined_signals:
                    combined_signals[ticker] = {'ticker': ticker, 'scores': {}, 'total_score': 0}
                
                combined_signals[ticker]['scores']['whale_score'] = result.whale_score
                combined_signals[ticker]['total_score'] += result.whale_score
        
        # 3. Scorer les anomalies d'options
        options_anomalies = results.get('options_anomalies', {})
        for ticker, anomalies_list in options_anomalies.items():
            if ticker not in combined_signals:
                combined_signals[ticker] = {'ticker': ticker, 'scores': {}, 'total_score': 0}
            
            avg_options_score = sum(a.anomaly_score for a in anomalies_list) / len(anomalies_list)
            combined_signals[ticker]['scores']['options_anomaly'] = avg_options_score
            combined_signals[ticker]['total_score'] += avg_options_score
        
        # 4. Ajouter les bonus IA
        ai_enhanced = results.get('ai_enhanced_results', {})
        for ticker, ai_analysis in ai_enhanced.items():
            if ticker in combined_signals:
                # Bonus basé sur la confiance de l'IA
                ai_confidence = getattr(ai_analysis, 'confidence_score', 0.5)
                ai_bonus = ai_confidence * 50  # Bonus de 0 à 50 points
                combined_signals[ticker]['scores']['ai_confidence'] = ai_bonus
                combined_signals[ticker]['total_score'] += ai_bonus
        
        # Convertir en liste et trier
        signals_list = list(combined_signals.values())
        signals_list.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Ajouter les rangs et niveaux de risque
        for i, signal in enumerate(signals_list, 1):
            signal['rank'] = i
            signal['risk_level'] = (
                'HIGH' if signal['total_score'] > 200 else
                'MEDIUM' if signal['total_score'] > 100 else
                'LOW'
            )
        
        return signals_list
    
    def _generate_comprehensive_summary(self, results: Dict) -> Dict:
        """Génère un résumé complet des résultats"""
        
        summary = {
            'timestamp': datetime.now(),
            'total_tickers_analyzed': len(results.get('tickers_scanned', [])),
            'market_anomalies_count': {
                'volume': len(results.get('market_anomalies', {}).get('volume_anomalies', [])),
                'trades': len(results.get('market_anomalies', {}).get('trades_anomalies', [])),
                'combined': len(results.get('market_anomalies', {}).get('combined_anomalies', []))
            },
            'options_anomalies_count': len(results.get('options_anomalies', {})),
            'traditional_screening_count': len(results.get('traditional_screening', {}).get('all', [])),
            'ai_enhanced_count': len(results.get('ai_enhanced_results', {})),
            'total_signals': len(results.get('combined_signals', [])),
            'top_signal': None,
            'risk_distribution': {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0},
            'recommendations': []
        }
        
        # Top signal
        combined_signals = results.get('combined_signals', [])
        if combined_signals:
            summary['top_signal'] = combined_signals[0]
        
        # Distribution des risques
        for signal in combined_signals:
            risk_level = signal.get('risk_level', 'LOW')
            summary['risk_distribution'][risk_level] += 1
        
        # Recommandations
        if summary['market_anomalies_count']['volume'] > 5:
            summary['recommendations'].append("High volume activity detected - monitor for breakouts")
        
        if summary['options_anomalies_count'] > 0:
            summary['recommendations'].append("Options pricing anomalies suggest institutional activity")
        
        if summary['total_signals'] > 10:
            summary['recommendations'].append("Multiple signals detected - consider diversified approach")
        elif summary['total_signals'] > 0:
            summary['recommendations'].append("Focus on top-ranked signals for best opportunities")
        
        return summary
    
    def save_results(self, results: Dict, filename: str = None):
        """Sauvegarde les résultats du screening complet"""
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"enhanced_screening_results_{timestamp}.json"
        
        # Préparer les données pour JSON (serializable)
        json_results = {
            'timestamp': results['timestamp'].isoformat(),
            'tickers_scanned': results['tickers_scanned'],
            'summary': {
                **results['summary'],
                'timestamp': results['summary']['timestamp'].isoformat()
            },
            'combined_signals_count': len(results['combined_signals']),
            'top_signals': results['combined_signals'][:10] if results['combined_signals'] else []
        }
        
        import json
        with open(filename, 'w') as f:
            json.dump(json_results, f, indent=2, default=str)
        
        print(f"💾 Results saved to {filename}")

# Fonction de test
async def test_enhanced_screener_v2():
    """Test du screener avancé V2"""
    print("🧪 Testing Enhanced Screener V2...")
    
    screener = EnhancedScreenerV2(
        enable_ai=True,
        enable_anomaly_detection=True
    )
    
    # Tickers de test
    test_tickers = ['SPY', 'QQQ', 'TSLA', 'NVDA', 'AAPL']
    
    # Paramètres de screening
    screening_params = {
        'option_type': 'call',
        'max_dte': 30,
        'min_volume': 500,
        'min_oi': 300,
        'min_whale_score': 50
    }
    
    def progress_callback(progress, message):
        print(f"[{progress*100:5.1f}%] {message}")
    
    # Lance le screening complet
    results = await screener.comprehensive_screening(
        tickers=test_tickers,
        screening_params=screening_params,
        enable_ai_analysis=True,
        enable_anomaly_detection=True,
        progress_callback=progress_callback
    )
    
    # Sauvegarder les résultats
    screener.save_results(results)
    
    print("✅ Enhanced Screener V2 test completed!")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_enhanced_screener_v2())