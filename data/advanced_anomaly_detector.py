# advanced_anomaly_detector.py - Détection d'anomalies avancée avec Polygon.io et ML
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pickle
import json
from dataclasses import dataclass
from collections import defaultdict
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

@dataclass
class AnomalyResult:
    """Structure pour les résultats d'anomalies détectées"""
    ticker: str
    date: str
    anomaly_type: str  # 'volume', 'options_pricing', 'trades', 'mixed'
    severity_score: float  # 0-100
    z_score: float
    current_value: float
    historical_avg: float
    historical_std: float
    confidence: float
    details: Dict
    timestamp: datetime

@dataclass
class OptionsAnomalyResult:
    """Structure spécifique aux anomalies d'options"""
    ticker: str
    option_symbol: str
    strike: float
    expiration: str
    option_type: str  # 'call' or 'put'
    anomaly_features: List[str]  # ['bid_ask_spread', 'delta', 'gamma', 'theta', 'vega']
    bid: float
    ask: float
    delta: float
    gamma: float
    theta: float
    vega: float
    implied_volatility: float
    anomaly_score: float
    timestamp: datetime

class AdvancedAnomalyDetector:
    """Détecteur d'anomalies avancé utilisant multiple sources et techniques ML"""
    
    def __init__(self, polygon_api_key: Optional[str] = None):
        self.polygon_api_key = polygon_api_key
        self.base_url = "https://api.polygon.io"
        self.lookup_table = {}
        self.scaler = StandardScaler()
        self.isolation_forest = None
        self.options_detector = None
        
        # Configuration des seuils
        self.volume_threshold = 3.0  # Z-score threshold for volume anomalies
        self.trades_threshold = 3.0  # Z-score threshold for trades anomalies
        self.options_contamination = 0.025  # 2.5% contamination for options anomalies
        
        print("🔍 Advanced Anomaly Detector initialized")
    
    def build_historical_baseline(self, tickers: List[str], days_back: int = 60) -> None:
        """
        Construit une baseline historique pour détecter les anomalies
        Basé sur l'approche Polygon.io avec fenêtre glissante
        """
        print(f"🏗️ Building historical baseline for {len(tickers)} tickers...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        self.lookup_table = defaultdict(dict)
        
        for ticker in tickers:
            try:
                # Récupérer les données agrégées historiques
                historical_data = self._fetch_historical_aggregates(
                    ticker, start_date, end_date
                )
                
                if not historical_data:
                    continue
                
                df = pd.DataFrame(historical_data)
                df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
                df = df.sort_values('date')
                
                # Calculer les moyennes et écarts-types glissants (fenêtre de 5 jours)
                df['volume_5d_avg'] = df['volume'].rolling(window=5).mean().shift(1)
                df['volume_5d_std'] = df['volume'].rolling(window=5).std().shift(1)
                df['trades_5d_avg'] = df['transactions'].rolling(window=5).mean().shift(1)
                df['trades_5d_std'] = df['transactions'].rolling(window=5).std().shift(1)
                
                # Calculer les changements de prix
                df['price_change_pct'] = df['close'].pct_change() * 100
                
                # Stocker dans la lookup table
                for _, row in df.iterrows():
                    date_str = row['date'].strftime('%Y-%m-%d')
                    
                    self.lookup_table[ticker][date_str] = {
                        'volume': row['volume'],
                        'volume_5d_avg': row['volume_5d_avg'],
                        'volume_5d_std': row['volume_5d_std'],
                        'transactions': row['transactions'],
                        'trades_5d_avg': row['trades_5d_avg'],
                        'trades_5d_std': row['trades_5d_std'],
                        'close': row['close'],
                        'price_change_pct': row['price_change_pct'],
                        'high': row['high'],
                        'low': row['low'],
                        'open': row['open']
                    }
                
                print(f"✅ Baseline built for {ticker}: {len(df)} days")
                
            except Exception as e:
                print(f"❌ Error building baseline for {ticker}: {e}")
                continue
        
        print(f"🎯 Historical baseline completed for {len(self.lookup_table)} tickers")
    
    def detect_volume_anomalies(self, date: str, min_z_score: float = 3.0) -> List[AnomalyResult]:
        """
        Détecte les anomalies de volume basées sur l'approche Polygon.io
        """
        anomalies = []
        
        for ticker, date_data in self.lookup_table.items():
            if date not in date_data:
                continue
            
            data = date_data[date]
            
            # Vérifier que nous avons assez de données historiques
            if (pd.isna(data['volume_5d_avg']) or pd.isna(data['volume_5d_std']) or 
                data['volume_5d_std'] == 0):
                continue
            
            # Calculer le Z-score
            volume_z_score = (data['volume'] - data['volume_5d_avg']) / data['volume_5d_std']
            
            if volume_z_score >= min_z_score:
                severity = min(100, (volume_z_score / min_z_score) * 50)
                
                anomaly = AnomalyResult(
                    ticker=ticker,
                    date=date,
                    anomaly_type='volume',
                    severity_score=severity,
                    z_score=volume_z_score,
                    current_value=data['volume'],
                    historical_avg=data['volume_5d_avg'],
                    historical_std=data['volume_5d_std'],
                    confidence=min(0.95, 0.5 + (volume_z_score / 10)),
                    details={
                        'price_change_pct': data.get('price_change_pct', 0),
                        'close_price': data['close'],
                        'volume_ratio': data['volume'] / data['volume_5d_avg'] if data['volume_5d_avg'] > 0 else 0
                    },
                    timestamp=datetime.now()
                )
                
                anomalies.append(anomaly)
        
        # Trier par severity score décroissant
        anomalies.sort(key=lambda x: x.severity_score, reverse=True)
        
        return anomalies
    
    def detect_trades_anomalies(self, date: str, min_z_score: float = 3.0) -> List[AnomalyResult]:
        """
        Détecte les anomalies de nombre de trades
        """
        anomalies = []
        
        for ticker, date_data in self.lookup_table.items():
            if date not in date_data:
                continue
            
            data = date_data[date]
            
            if (pd.isna(data['trades_5d_avg']) or pd.isna(data['trades_5d_std']) or 
                data['trades_5d_std'] == 0):
                continue
            
            trades_z_score = (data['transactions'] - data['trades_5d_avg']) / data['trades_5d_std']
            
            if trades_z_score >= min_z_score:
                severity = min(100, (trades_z_score / min_z_score) * 50)
                
                anomaly = AnomalyResult(
                    ticker=ticker,
                    date=date,
                    anomaly_type='trades',
                    severity_score=severity,
                    z_score=trades_z_score,
                    current_value=data['transactions'],
                    historical_avg=data['trades_5d_avg'],
                    historical_std=data['trades_5d_std'],
                    confidence=min(0.95, 0.5 + (trades_z_score / 10)),
                    details={
                        'price_change_pct': data.get('price_change_pct', 0),
                        'close_price': data['close'],
                        'trades_ratio': data['transactions'] / data['trades_5d_avg'] if data['trades_5d_avg'] > 0 else 0
                    },
                    timestamp=datetime.now()
                )
                
                anomalies.append(anomaly)
        
        anomalies.sort(key=lambda x: x.severity_score, reverse=True)
        return anomalies
    
    def detect_options_anomalies(self, ticker: str, date: str) -> List[OptionsAnomalyResult]:
        """
        Détecte les anomalies dans les prix des options en utilisant Isolation Forest
        Basé sur l'approche de Boris Banushev
        """
        try:
            options_data = self._fetch_options_data(ticker, date)
            
            if not options_data or len(options_data) < 10:
                return []
            
            df = pd.DataFrame(options_data)
            
            # Préparer les features pour la détection d'anomalies
            feature_columns = ['strike', 'delta', 'gamma', 'theta', 'vega', 'implied_volatility']
            
            # Créer des features supplémentaires
            df['bid_ask_spread'] = df['ask'] - df['bid']
            df['bid_ask_mean'] = (df['bid'] + df['ask']) / 2
            df['moneyness'] = df['underlying_price'] - df['strike']  # S - K
            df['time_to_expiry'] = pd.to_datetime(df['expiration']).dt.date
            df['time_to_expiry'] = (pd.to_datetime(df['time_to_expiry']) - pd.to_datetime(date)).dt.days
            
            # Features pour l'isolation forest
            X_features = ['strike', 'delta', 'gamma', 'time_to_expiry', 'moneyness', 'bid_ask_mean']
            X = df[X_features].fillna(0)
            
            if len(X) < 5:
                return []
            
            # Appliquer Isolation Forest
            clf = IsolationForest(
                contamination=self.options_contamination,
                n_estimators=100,
                random_state=42,
                max_features=len(X_features)
            )
            
            anomaly_labels = clf.fit_predict(X)
            anomaly_scores = clf.score_samples(X)
            
            # Identifier les anomalies
            anomalies = []
            
            for idx, (label, score) in enumerate(zip(anomaly_labels, anomaly_scores)):
                if label == -1:  # Anomalie détectée
                    row = df.iloc[idx]
                    
                    # Déterminer quelles features sont anormales
                    anomaly_features = []
                    if abs(row['bid_ask_spread']) > df['bid_ask_spread'].quantile(0.95):
                        anomaly_features.append('bid_ask_spread')
                    if abs(row['delta']) > df['delta'].quantile(0.95):
                        anomaly_features.append('delta')
                    if abs(row['gamma']) > df['gamma'].quantile(0.95):
                        anomaly_features.append('gamma')
                    if abs(row['theta']) > df['theta'].quantile(0.95):
                        anomaly_features.append('theta')
                    if abs(row['vega']) > df['vega'].quantile(0.95):
                        anomaly_features.append('vega')
                    
                    anomaly = OptionsAnomalyResult(
                        ticker=ticker,
                        option_symbol=row['option_symbol'],
                        strike=row['strike'],
                        expiration=row['expiration'],
                        option_type=row['option_type'],
                        anomaly_features=anomaly_features,
                        bid=row['bid'],
                        ask=row['ask'],
                        delta=row.get('delta', 0),
                        gamma=row.get('gamma', 0),
                        theta=row.get('theta', 0),
                        vega=row.get('vega', 0),
                        implied_volatility=row.get('implied_volatility', 0),
                        anomaly_score=abs(score) * 100,  # Convert to 0-100 scale
                        timestamp=datetime.now()
                    )
                    
                    anomalies.append(anomaly)
            
            # Trier par anomaly score décroissant
            anomalies.sort(key=lambda x: x.anomaly_score, reverse=True)
            
            return anomalies
            
        except Exception as e:
            print(f"❌ Error detecting options anomalies for {ticker}: {e}")
            return []
    
    def detect_anomalies_dataframe(self, df: pd.DataFrame, volume_col: str = 'volume', 
                                  price_col: str = 'last') -> pd.DataFrame:
        """
        Détecte les anomalies dans un DataFrame d'options
        Méthode simplifiée pour les tests
        """
        try:
            if len(df) < 5:
                return pd.DataFrame()
            
            # Calcul des Z-scores pour le volume
            if volume_col in df.columns:
                volume_mean = df[volume_col].mean()
                volume_std = df[volume_col].std()
                
                if volume_std > 0:
                    df = df.copy()
                    df['volume_z_score'] = (df[volume_col] - volume_mean) / volume_std
                    
                    # Détecter les anomalies (Z-score > 2.0)
                    anomalies = df[df['volume_z_score'].abs() > 2.0].copy()
                    
                    # Ajouter un score d'anomalie
                    if len(anomalies) > 0:
                        anomalies['anomaly_score'] = anomalies['volume_z_score'].abs() * 10
                        anomalies = anomalies.sort_values('anomaly_score', ascending=False)
                    
                    return anomalies
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ Erreur détection anomalies DataFrame: {e}")
            return pd.DataFrame()
    
    def comprehensive_anomaly_scan(self, tickers: List[str], date: str) -> Dict:
        """
        Scan complet des anomalies pour une date donnée
        """
        print(f"🔍 Running comprehensive anomaly scan for {date}...")
        
        results = {
            'date': date,
            'volume_anomalies': [],
            'trades_anomalies': [],
            'options_anomalies': [],
            'combined_anomalies': [],
            'summary': {}
        }
        
        # 1. Détection d'anomalies de volume
        volume_anomalies = self.detect_volume_anomalies(date, self.volume_threshold)
        results['volume_anomalies'] = volume_anomalies
        
        # 2. Détection d'anomalies de trades
        trades_anomalies = self.detect_trades_anomalies(date, self.trades_threshold)
        results['trades_anomalies'] = trades_anomalies
        
        # 3. Détection d'anomalies d'options pour les tickers les plus anormaux
        top_anomaly_tickers = list(set([a.ticker for a in volume_anomalies[:5]] + 
                                      [a.ticker for a in trades_anomalies[:5]]))
        
        all_options_anomalies = []
        for ticker in top_anomaly_tickers[:10]:  # Limiter pour éviter les timeouts
            try:
                options_anomalies = self.detect_options_anomalies(ticker, date)
                all_options_anomalies.extend(options_anomalies)
            except Exception as e:
                print(f"⚠️ Error processing options for {ticker}: {e}")
                continue
        
        results['options_anomalies'] = all_options_anomalies
        
        # 4. Combiner les anomalies multiples (même ticker avec plusieurs types d'anomalies)
        combined_anomalies = self._combine_anomalies(volume_anomalies, trades_anomalies, all_options_anomalies)
        results['combined_anomalies'] = combined_anomalies
        
        # 5. Résumé
        results['summary'] = {
            'total_volume_anomalies': len(volume_anomalies),
            'total_trades_anomalies': len(trades_anomalies),
            'total_options_anomalies': len(all_options_anomalies),
            'total_combined_anomalies': len(combined_anomalies),
            'top_volume_anomaly': volume_anomalies[0].ticker if volume_anomalies else None,
            'top_trades_anomaly': trades_anomalies[0].ticker if trades_anomalies else None,
            'highest_severity': max([a.severity_score for a in volume_anomalies + trades_anomalies]) if (volume_anomalies or trades_anomalies) else 0
        }
        
        print("✅ Anomaly scan complete:")
        print(f"   📊 Volume anomalies: {len(volume_anomalies)}")
        print(f"   📈 Trades anomalies: {len(trades_anomalies)}")
        print(f"   📋 Options anomalies: {len(all_options_anomalies)}")
        print(f"   🔗 Combined anomalies: {len(combined_anomalies)}")
        
        return results
    
    def _combine_anomalies(self, volume_anomalies, trades_anomalies, options_anomalies) -> List[Dict]:
        """
        Combine les différents types d'anomalies par ticker
        """
        combined = defaultdict(dict)
        
        # Grouper par ticker
        for anomaly in volume_anomalies:
            combined[anomaly.ticker]['volume'] = anomaly
        
        for anomaly in trades_anomalies:
            combined[anomaly.ticker]['trades'] = anomaly
        
        # Grouper les options par ticker
        options_by_ticker = defaultdict(list)
        for anomaly in options_anomalies:
            options_by_ticker[anomaly.ticker].append(anomaly)
        
        for ticker, options_list in options_by_ticker.items():
            combined[ticker]['options'] = options_list
        
        # Créer les anomalies combinées
        combined_anomalies = []
        
        for ticker, anomalies_dict in combined.items():
            if len(anomalies_dict) > 1:  # Multiple types d'anomalies
                combined_score = 0
                anomaly_types = []
                
                if 'volume' in anomalies_dict:
                    combined_score += anomalies_dict['volume'].severity_score
                    anomaly_types.append('volume')
                
                if 'trades' in anomalies_dict:
                    combined_score += anomalies_dict['trades'].severity_score
                    anomaly_types.append('trades')
                
                if 'options' in anomalies_dict:
                    options_score = sum(opt.anomaly_score for opt in anomalies_dict['options']) / len(anomalies_dict['options'])
                    combined_score += options_score
                    anomaly_types.append('options')
                
                combined_anomaly = {
                    'ticker': ticker,
                    'combined_score': combined_score,
                    'anomaly_types': anomaly_types,
                    'volume_anomaly': anomalies_dict.get('volume'),
                    'trades_anomaly': anomalies_dict.get('trades'),
                    'options_anomalies': anomalies_dict.get('options', []),
                    'risk_level': 'HIGH' if combined_score > 150 else 'MEDIUM' if combined_score > 100 else 'LOW'
                }
                
                combined_anomalies.append(combined_anomaly)
        
        # Trier par score combiné
        combined_anomalies.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return combined_anomalies
    
    def _fetch_historical_aggregates(self, ticker: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Récupère les données agrégées historiques via Polygon.io API optimisé
        """
        if not self.polygon_api_key:
            # Mode simulation avec données factices
            return self._generate_mock_data(ticker, start_date, end_date)
        
        try:
            # Utiliser le client Polygon optimisé
            from data.polygon_client import create_polygon_client
            
            if not hasattr(self, '_polygon_client') or self._polygon_client is None:
                self._polygon_client = create_polygon_client(self.polygon_api_key)
            
            # Récupérer les données avec le client optimisé
            stock_bars = self._polygon_client.get_stock_aggregates(
                ticker=ticker,
                from_date=start_date,
                to_date=end_date
            )
            
            # Convertir en format attendu
            results = []
            for bar in stock_bars:
                results.append({
                    'timestamp': bar.timestamp,
                    'volume': bar.volume,
                    'transactions': bar.transactions,
                    'open': bar.open,
                    'close': bar.close,
                    'high': bar.high,
                    'low': bar.low
                })
            
            return results
                
        except Exception as e:
            print(f"❌ Error fetching data for {ticker}: {e}")
            # Fallback sur données simulées
            return self._generate_mock_data(ticker, start_date, end_date)
    
    def _fetch_options_data(self, ticker: str, date: str) -> List[Dict]:
        """
        Récupère les données d'options (simulées pour l'instant)
        """
        # Mode simulation - en production utiliser l'API Polygon.io options
        return self._generate_mock_options_data(ticker, date)
    
    def _generate_mock_data(self, ticker: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Génère des données factices pour les tests
        """
        mock_data = []
        current_date = start_date
        base_volume = np.random.randint(1000000, 10000000)
        base_price = np.random.uniform(50, 500)
        
        while current_date <= end_date:
            # Simuler quelques anomalies occasionnelles
            if np.random.random() < 0.05:  # 5% chance d'anomalie
                volume_multiplier = np.random.uniform(3, 8)
                transactions_multiplier = np.random.uniform(2, 6)
            else:
                volume_multiplier = np.random.uniform(0.7, 1.3)
                transactions_multiplier = np.random.uniform(0.8, 1.2)
            
            volume = int(base_volume * volume_multiplier)
            transactions = int(volume / np.random.uniform(80, 120))
            
            price_change = np.random.normal(0, 0.02)
            current_price = base_price * (1 + price_change)
            
            mock_data.append({
                'timestamp': int(current_date.timestamp() * 1000),
                'volume': volume,
                'transactions': transactions,
                'open': current_price * 0.999,
                'close': current_price,
                'high': current_price * 1.005,
                'low': current_price * 0.995
            })
            
            base_price = current_price
            current_date += timedelta(days=1)
        
        return mock_data
    
    def _generate_mock_options_data(self, ticker: str, date: str) -> List[Dict]:
        """
        Génère des données d'options factices pour les tests
        """
        mock_options = []
        base_price = np.random.uniform(100, 300)
        
        # Générer différents strikes et expirations
        strikes = [base_price * (1 + offset) for offset in [-0.1, -0.05, 0, 0.05, 0.1]]
        expirations = [(datetime.now() + timedelta(days=d)).strftime('%Y-%m-%d') for d in [7, 30, 60, 90]]
        
        for strike in strikes:
            for expiration in expirations:
                for option_type in ['call', 'put']:
                    # Calculer des Greeks réalistes avec quelques anomalies
                    if np.random.random() < 0.1:  # 10% d'anomalies
                        delta = np.random.uniform(-2, 2)  # Delta anormal
                        bid_ask_spread = np.random.uniform(5, 20)  # Spread anormal
                    else:
                        delta = np.random.uniform(-1, 1) if option_type == 'put' else np.random.uniform(0, 1)
                        bid_ask_spread = np.random.uniform(0.1, 2)
                    
                    bid = np.random.uniform(1, 20)
                    ask = bid + bid_ask_spread
                    
                    mock_options.append({
                        'option_symbol': f"{ticker}{datetime.now().strftime('%y%m%d')}{option_type[0].upper()}{int(strike*1000):08d}",
                        'strike': strike,
                        'expiration': expiration,
                        'option_type': option_type,
                        'bid': bid,
                        'ask': ask,
                        'delta': delta,
                        'gamma': np.random.uniform(0, 0.1),
                        'theta': np.random.uniform(-0.5, 0),
                        'vega': np.random.uniform(0, 0.5),
                        'implied_volatility': np.random.uniform(0.1, 0.8),
                        'underlying_price': base_price
                    })
        
        return mock_options
    
    def save_lookup_table(self, filepath: str = "anomaly_lookup_table.pkl"):
        """
        Sauvegarde la lookup table pour réutilisation
        """
        with open(filepath, 'wb') as f:
            pickle.dump(dict(self.lookup_table), f)
        print(f"💾 Lookup table saved to {filepath}")
    
    def load_lookup_table(self, filepath: str = "anomaly_lookup_table.pkl"):
        """
        Charge la lookup table depuis un fichier
        """
        try:
            with open(filepath, 'rb') as f:
                self.lookup_table = pickle.load(f)
            print(f"📂 Lookup table loaded from {filepath}")
            return True
        except FileNotFoundError:
            print(f"⚠️ Lookup table file not found: {filepath}")
            return False

# Fonction utilitaire pour tester le détecteur
def test_advanced_anomaly_detector():
    """Test du détecteur d'anomalies avancé"""
    print("🧪 Testing Advanced Anomaly Detector...")
    
    detector = AdvancedAnomalyDetector()
    
    # Tickers de test
    test_tickers = ['SPY', 'QQQ', 'TSLA', 'NVDA', 'AAPL']
    
    # 1. Construire la baseline
    detector.build_historical_baseline(test_tickers, days_back=30)
    
    # 2. Détecter les anomalies pour aujourd'hui
    today = datetime.now().strftime('%Y-%m-%d')
    results = detector.comprehensive_anomaly_scan(test_tickers, today)
    
    # 3. Afficher les résultats
    print(f"\n📊 ANOMALY SCAN RESULTS FOR {today}")
    print("=" * 60)
    
    print(f"\n🔊 Volume Anomalies ({len(results['volume_anomalies'])}):")
    for anomaly in results['volume_anomalies'][:3]:
        print(f"   {anomaly.ticker}: Z-score {anomaly.z_score:.2f}, "
              f"Severity {anomaly.severity_score:.1f}")
    
    print(f"\n📈 Trades Anomalies ({len(results['trades_anomalies'])}):")
    for anomaly in results['trades_anomalies'][:3]:
        print(f"   {anomaly.ticker}: Z-score {anomaly.z_score:.2f}, "
              f"Severity {anomaly.severity_score:.1f}")
    
    print(f"\n📋 Options Anomalies ({len(results['options_anomalies'])}):")
    for anomaly in results['options_anomalies'][:3]:
        print(f"   {anomaly.ticker} {anomaly.option_type.upper()} ${anomaly.strike}: "
              f"Score {anomaly.anomaly_score:.1f}")
    
    print(f"\n🔗 Combined Anomalies ({len(results['combined_anomalies'])}):")
    for combined in results['combined_anomalies'][:3]:
        print(f"   {combined['ticker']}: Score {combined['combined_score']:.1f} "
              f"({', '.join(combined['anomaly_types'])}) - {combined['risk_level']}")
    
    # 4. Sauvegarder les résultats
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    with open(f"anomaly_results_{timestamp}.json", 'w') as f:
        # Convertir les dataclasses en dictionnaires pour JSON
        json_results = {
            'date': results['date'],
            'summary': results['summary'],
            'volume_anomalies_count': len(results['volume_anomalies']),
            'trades_anomalies_count': len(results['trades_anomalies']),
            'options_anomalies_count': len(results['options_anomalies']),
            'combined_anomalies_count': len(results['combined_anomalies'])
        }
        json.dump(json_results, f, indent=2)
    
    print(f"\n💾 Results saved to anomaly_results_{timestamp}.json")
    print("✅ Advanced Anomaly Detector test completed!")
    
    return results

if __name__ == "__main__":
    test_advanced_anomaly_detector()