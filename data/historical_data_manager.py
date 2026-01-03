# historical_data_manager.py
import sqlite3
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

@dataclass
class HistoricalOptionData:
    """Historical data point for an option"""
    option_symbol: str
    underlying: str
    scan_date: date
    volume_1d: int
    open_interest: int
    last_price: float
    whale_score: float
    vol_oi_ratio: float
    
class HistoricalDataManager:
    """Manages historical options data for anomaly detection"""
    
    def __init__(self, db_path: str = "data/options_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create main historical data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS option_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    option_symbol TEXT NOT NULL,
                    underlying TEXT NOT NULL,
                    scan_date DATE NOT NULL,
                    volume_1d INTEGER NOT NULL,
                    open_interest INTEGER NOT NULL,
                    last_price REAL,
                    whale_score REAL,
                    vol_oi_ratio REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(option_symbol, scan_date)
                )
            """)
            
            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_option_date 
                ON option_history(option_symbol, scan_date)
            """)
            
            # Create index for underlying symbol queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_underlying_date 
                ON option_history(underlying, scan_date)
            """)
            
            conn.commit()
    
    def save_scan_results(self, scan_results: List, scan_date: Optional[date] = None) -> int:
        """
        Save scan results to historical database
        
        Args:
            scan_results: List of OptionScreenerResult objects
            scan_date: Date of scan (defaults to today)
            
        Returns:
            Number of records saved
        """
        if scan_date is None:
            scan_date = date.today()
        
        saved_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for result in scan_results:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO option_history 
                        (option_symbol, underlying, scan_date, volume_1d, open_interest, 
                         last_price, whale_score, vol_oi_ratio)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        result.option_symbol,
                        result.symbol,
                        scan_date.isoformat(),
                        result.volume_1d,
                        result.open_interest,
                        result.last_price,
                        result.whale_score,
                        result.vol_oi_ratio
                    ))
                    saved_count += 1
                    
                except Exception as e:
                    print(f"Error saving {result.option_symbol}: {e}")
                    continue
            
            conn.commit()
        
        print(f"💾 Saved {saved_count} historical records for {scan_date}")
        return saved_count
    
    def get_historical_data(
        self, 
        option_symbol: str, 
        lookback_days: int = 10
    ) -> List[HistoricalOptionData]:
        """
        Get historical data for a specific option
        
        Args:
            option_symbol: OCC option symbol
            lookback_days: Number of days to look back
            
        Returns:
            List of historical data points
        """
        cutoff_date = date.today() - timedelta(days=lookback_days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT option_symbol, underlying, scan_date, volume_1d, 
                       open_interest, last_price, whale_score, vol_oi_ratio
                FROM option_history 
                WHERE option_symbol = ? AND scan_date >= ?
                ORDER BY scan_date DESC
            """, (option_symbol, cutoff_date.isoformat()))
            
            results = []
            for row in cursor.fetchall():
                results.append(HistoricalOptionData(
                    option_symbol=row[0],
                    underlying=row[1],
                    scan_date=datetime.strptime(row[2], "%Y-%m-%d").date(),
                    volume_1d=row[3],
                    open_interest=row[4],
                    last_price=row[5] or 0.0,
                    whale_score=row[6] or 0.0,
                    vol_oi_ratio=row[7] or 0.0
                ))
            
            return results
    
    def calculate_volume_anomaly(
        self, 
        current_volume: int, 
        option_symbol: str, 
        lookback_days: int = 10
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate volume anomaly score compared to historical average
        
        Args:
            current_volume: Today's volume
            option_symbol: OCC option symbol
            lookback_days: Days for historical average
            
        Returns:
            Tuple of (anomaly_score, statistics_dict)
        """
        historical_data = self.get_historical_data(option_symbol, lookback_days)
        
        if len(historical_data) < 3:
            # Not enough historical data
            return 0.0, {"reason": "insufficient_data", "data_points": len(historical_data)}
        
        # Calculate statistics
        historical_volumes = [d.volume_1d for d in historical_data]
        avg_volume = sum(historical_volumes) / len(historical_volumes)
        max_volume = max(historical_volumes)
        min_volume = min(historical_volumes)
        
        if avg_volume == 0:
            return 0.0, {"reason": "zero_average", "avg_volume": avg_volume}
        
        volume_ratio = current_volume / avg_volume
        
        # Anomaly scoring based on deviation from average
        if volume_ratio >= 5.0:      # 500%+ above average
            anomaly_score = 100.0
        elif volume_ratio >= 3.0:    # 300%+ above average  
            anomaly_score = 85.0
        elif volume_ratio >= 2.0:    # 200%+ above average
            anomaly_score = 70.0
        elif volume_ratio >= 1.5:    # 150%+ above average
            anomaly_score = 50.0
        else:
            anomaly_score = max(0, volume_ratio * 30)
        
        stats = {
            "volume_ratio": volume_ratio,
            "avg_volume": avg_volume,
            "max_volume": max_volume,
            "min_volume": min_volume,
            "data_points": len(historical_data),
            "lookback_days": lookback_days
        }
        
        return anomaly_score, stats
    
    def calculate_oi_anomaly(
        self, 
        current_oi: int, 
        option_symbol: str, 
        lookback_days: int = 10
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate Open Interest anomaly score compared to historical average
        
        Args:
            current_oi: Today's Open Interest
            option_symbol: OCC option symbol
            lookback_days: Days for historical average
            
        Returns:
            Tuple of (anomaly_score, statistics_dict)
        """
        historical_data = self.get_historical_data(option_symbol, lookback_days)
        
        if len(historical_data) < 3:
            return 0.0, {"reason": "insufficient_data", "data_points": len(historical_data)}
        
        # Calculate OI statistics
        historical_oi = [d.open_interest for d in historical_data]
        avg_oi = sum(historical_oi) / len(historical_oi)
        
        if avg_oi == 0:
            return 0.0, {"reason": "zero_average", "avg_oi": avg_oi}
        
        oi_ratio = current_oi / avg_oi
        
        # OI anomaly scoring (less aggressive than volume)
        if oi_ratio >= 3.0:      # 300%+ above average
            anomaly_score = 80.0
        elif oi_ratio >= 2.0:    # 200%+ above average  
            anomaly_score = 60.0
        elif oi_ratio >= 1.5:    # 150%+ above average
            anomaly_score = 40.0
        elif oi_ratio <= 0.5:    # 50% below average (unusual decrease)
            anomaly_score = 30.0
        else:
            anomaly_score = max(0, (oi_ratio - 1.0) * 50)
        
        stats = {
            "oi_ratio": oi_ratio,
            "avg_oi": avg_oi,
            "data_points": len(historical_data),
            "lookback_days": lookback_days
        }
        
        return anomaly_score, stats
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get statistics about the historical database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total records
            cursor.execute("SELECT COUNT(*) FROM option_history")
            total_records = cursor.fetchone()[0]
            
            # Unique options
            cursor.execute("SELECT COUNT(DISTINCT option_symbol) FROM option_history")
            unique_options = cursor.fetchone()[0]
            
            # Unique underlyings
            cursor.execute("SELECT COUNT(DISTINCT underlying) FROM option_history")
            unique_underlyings = cursor.fetchone()[0]
            
            # Date range
            cursor.execute("SELECT MIN(scan_date), MAX(scan_date) FROM option_history")
            date_range = cursor.fetchone()
            
            return {
                "total_records": total_records,
                "unique_options": unique_options,
                "unique_underlyings": unique_underlyings,
                "earliest_date": date_range[0],
                "latest_date": date_range[1]
            }
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """
        Clean up old historical data
        
        Args:
            days_to_keep: Number of days to retain
            
        Returns:
            Number of records deleted
        """
        cutoff_date = date.today() - timedelta(days=days_to_keep)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM option_history 
                WHERE scan_date < ?
            """, (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
        
        print(f"🗑️ Cleaned up {deleted_count} old records (older than {days_to_keep} days)")
        return deleted_count