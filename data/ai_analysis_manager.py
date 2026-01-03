# ai_analysis_manager.py
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Optional
import requests
from dataclasses import dataclass, asdict
from utils.config import Config

@dataclass
class AIAnalysisResult:
    """Result of AI-enhanced analysis"""
    ticker: str
    analysis_type: str  # 'fundamental', 'sentiment', 'options_strategy', 'catalyst'
    confidence_score: float  # 0-100
    summary: str
    detailed_analysis: Dict
    recommendations: List[str]
    risk_factors: List[str]
    timestamp: datetime
    source: str  # 'openai', 'perplexity', 'combined'

@dataclass 
class MarketCatalyst:
    """Market catalyst or event"""
    ticker: str
    event_type: str  # 'earnings', 'news', 'analyst_upgrade', 'insider_trading'
    description: str
    impact_sentiment: str  # 'bullish', 'bearish', 'neutral'
    confidence: float
    source_url: Optional[str] = None
    publication_date: Optional[datetime] = None

class AIAnalysisManager:
    """Manages AI-enhanced analysis using OpenAI and Perplexity"""
    
    def __init__(self):
        self.openai_api_url = "https://api.openai.com/v1/chat/completions"
        self.perplexity_api_url = "https://api.perplexity.ai/chat/completions"
        self.session = requests.Session()
    
    async def analyze_ticker_fundamentals(self, ticker: str, option_data: Dict) -> AIAnalysisResult:
        """Analyze ticker fundamentals using OpenAI"""
        openai_key = Config.get_openai_api_key()
        if not openai_key:
            return self._create_error_result(ticker, "fundamental", "OpenAI API key not configured")
        
        # Prepare prompt with current option activity data
        prompt = f"""
        Analyze the fundamental outlook for {ticker} given this unusual options activity:
        
        Options Data:
        - Whale Score: {option_data.get('whale_score', 'N/A')}
        - Volume/OI Ratio: {option_data.get('vol_oi_ratio', 'N/A')}
        - Volume: {option_data.get('volume_1d', 'N/A')} (1-day)
        - Open Interest: {option_data.get('open_interest', 'N/A')}
        - Strike: ${option_data.get('strike', 'N/A')}
        - Expiration: {option_data.get('expiration', 'N/A')}
        - Option Type: {option_data.get('side', 'N/A')}
        
        Please provide a JSON response with:
        {{
            "summary": "Brief 1-2 sentence summary",
            "confidence": 85,
            "detailed_analysis": {{
                "fundamental_score": "0-100 fundamental strength",
                "technical_outlook": "Technical analysis summary",
                "options_significance": "Why this options activity matters"
            }},
            "recommendations": ["Action item 1", "Action item 2"],
            "risk_factors": ["Risk 1", "Risk 2"]
        }}
        
        Focus on:
        1. Why institutions might be making this bet
        2. Fundamental catalysts that support this position
        3. Risk factors to consider
        """
        
        headers = {
            'Authorization': f'Bearer {openai_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'gpt-4',
            'messages': [
                {'role': 'system', 'content': 'You are a professional financial analyst providing objective fundamental analysis. Always respond with valid JSON.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 1000,
            'temperature': 0.1
        }
        
        try:
            response = requests.post(self.openai_api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Clean and parse JSON response
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            
            analysis_data = json.loads(content)
            
            return AIAnalysisResult(
                ticker=ticker,
                analysis_type="fundamental",
                confidence_score=analysis_data.get('confidence', 75),
                summary=analysis_data.get('summary', ''),
                detailed_analysis=analysis_data.get('detailed_analysis', {}),
                recommendations=analysis_data.get('recommendations', []),
                risk_factors=analysis_data.get('risk_factors', []),
                timestamp=datetime.now(),
                source="openai"
            )
            
        except Exception as e:
            print(f"Error in fundamental analysis for {ticker}: {e}")
            return self._create_error_result(ticker, "fundamental", str(e))
    
    async def get_market_catalysts(self, ticker: str) -> List[MarketCatalyst]:
        """Get recent market catalysts using Perplexity"""
        perplexity_key = Config.get_perplexity_api_key()
        if not perplexity_key:
            print(f"Perplexity API key not configured for {ticker}")
            return []
        
        prompt = f"""
        Search for recent market catalysts and news for {ticker} in the last 7 days that could 
        explain unusual options activity. Include:
        - Earnings announcements or guidance changes
        - Analyst upgrades/downgrades with price targets
        - Major news events or product launches
        - Insider trading or institutional activity
        - Sector developments affecting {ticker}
        - Merger/acquisition rumors
        
        For each catalyst found:
        1. Describe the event briefly
        2. Indicate if it's bullish, bearish, or neutral for {ticker}
        3. Provide confidence level and source if available
        
        If no significant catalysts found, say "No major catalysts found in recent period."
        """
        
        headers = {
            'Authorization': f'Bearer {perplexity_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'llama-3.1-sonar-small-128k-online',  # Uses real-time search
            'messages': [
                {'role': 'system', 'content': 'You are a financial analyst searching for market catalysts. Provide factual, recent information with sources when possible.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 800,
            'temperature': 0.1,
        }
        
        try:
            response = requests.post(self.perplexity_api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Parse the response to extract catalysts
            catalysts = self._parse_catalysts_from_text(ticker, content)
            return catalysts
            
        except Exception as e:
            print(f"Error getting catalysts for {ticker}: {e}")
            return []
    
    async def get_sentiment_analysis(self, ticker: str) -> AIAnalysisResult:
        """Get sentiment analysis using Perplexity's real-time search"""
        perplexity_key = Config.get_perplexity_api_key()
        if not perplexity_key:
            return self._create_error_result(ticker, "sentiment", "Perplexity API not available")
        
        prompt = f"""
        Analyze current market sentiment for {ticker} in the last 3-5 days based on:
        - Recent news articles and financial media coverage
        - Social media sentiment trends (Twitter/X, Reddit WallStreetBets, etc.)
        - Analyst reports and price target changes
        - Options flow and unusual activity patterns
        
        Provide:
        1. Overall sentiment score (0-100, where 50 is neutral, above 50 is bullish, below 50 is bearish)
        2. Key bullish factors currently driving positive sentiment
        3. Key bearish factors or concerns in the market
        4. Confidence level in this sentiment analysis
        
        Focus on actionable insights that could explain unusual options activity.
        """
        
        headers = {
            'Authorization': f'Bearer {perplexity_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'llama-3.1-sonar-small-128k-online',
            'messages': [
                {'role': 'system', 'content': 'You are a financial sentiment analyst providing objective market sentiment analysis based on current information.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 600,
            'temperature': 0.1
        }
        
        try:
            response = requests.post(self.perplexity_api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Parse sentiment score and analysis
            sentiment_data = self._parse_sentiment_analysis(content)
            
            return AIAnalysisResult(
                ticker=ticker,
                analysis_type="sentiment",
                confidence_score=sentiment_data.get('confidence', 75),
                summary=sentiment_data.get('summary', content[:200] + '...'),
                detailed_analysis=sentiment_data,
                recommendations=sentiment_data.get('recommendations', []),
                risk_factors=sentiment_data.get('risk_factors', []),
                timestamp=datetime.now(),
                source="perplexity"
            )
            
        except Exception as e:
            print(f"Error in sentiment analysis for {ticker}: {e}")
            return self._create_error_result(ticker, "sentiment", str(e))
    
    async def analyze_options_strategy(self, option_results: List, market_conditions: Dict = None) -> AIAnalysisResult:
        """Analyze options strategy using OpenAI"""
        openai_key = Config.get_openai_api_key()
        if not openai_key or not option_results:
            return self._create_error_result("PORTFOLIO", "options_strategy", "OpenAI API not available or no data")
        
        # Prepare top options data
        top_options = sorted(option_results, key=lambda x: x.whale_score, reverse=True)[:5]
        options_data = []
        
        for result in top_options:
            options_data.append({
                'ticker': result.symbol,
                'type': result.side,
                'strike': result.strike,
                'dte': result.dte,
                'whale_score': round(result.whale_score, 1),
                'vol_oi_ratio': round(result.vol_oi_ratio, 2),
                'volume': result.volume_1d,
                'open_interest': result.open_interest
            })
        
        market_info = market_conditions or {}
        
        prompt = f"""
        Analyze these top unusual options positions and provide strategic recommendations:
        
        Options Activity: {json.dumps(options_data, indent=2)}
        
        Market Context:
        - VIX Level: {market_info.get('vix', 'Unknown')}
        - Market Trend: {market_info.get('trend', 'Unknown')}
        
        Provide a JSON response:
        {{
            "strategy_summary": "Overall strategy recommendation",
            "confidence": 85,
            "detailed_strategies": {{
                "high_conviction_plays": ["Top 2-3 positions to watch"],
                "risk_management": "Risk management approach",
                "timing_considerations": "Market timing factors"
            }},
            "recommendations": ["Actionable recommendation 1", "Actionable recommendation 2"],
            "risk_factors": ["Key risk 1", "Key risk 2"]
        }}
        
        Focus on:
        1. Which positions show strongest institutional conviction
        2. Appropriate position sizing and risk management
        3. Entry/exit timing strategies
        4. Correlation risks across positions
        """
        
        headers = {
            'Authorization': f'Bearer {openai_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'gpt-4',
            'messages': [
                {'role': 'system', 'content': 'You are a professional options strategist providing institutional-level analysis. Always respond with valid JSON.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 1000,
            'temperature': 0.1
        }
        
        try:
            response = requests.post(self.openai_api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Clean JSON
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
                
            analysis_data = json.loads(content)
            
            return AIAnalysisResult(
                ticker="PORTFOLIO",
                analysis_type="options_strategy",
                confidence_score=analysis_data.get('confidence', 80),
                summary=analysis_data.get('strategy_summary', ''),
                detailed_analysis=analysis_data.get('detailed_strategies', {}),
                recommendations=analysis_data.get('recommendations', []),
                risk_factors=analysis_data.get('risk_factors', []),
                timestamp=datetime.now(),
                source="openai"
            )
            
        except Exception as e:
            print(f"Error in options strategy analysis: {e}")
            return self._create_error_result("PORTFOLIO", "options_strategy", str(e))
    
    async def comprehensive_analysis(self, ticker: str, option_data: Dict) -> Dict[str, AIAnalysisResult]:
        """Run comprehensive analysis combining all AI services"""
        print(f"🤖 Running AI analysis for {ticker}...")
        
        try:
            # Run analyses in parallel where possible
            tasks = [
                self.analyze_ticker_fundamentals(ticker, option_data),
                self.get_sentiment_analysis(ticker)
            ]
            
            fundamental_result, sentiment_result = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Get market catalysts (sequential due to API rate limits)
            catalysts = await self.get_market_catalysts(ticker)
            
            results = {}
            
            if not isinstance(fundamental_result, Exception):
                results['fundamental'] = fundamental_result
                
            if not isinstance(sentiment_result, Exception):
                results['sentiment'] = sentiment_result
            
            # Add catalyst summary if available
            if catalysts:
                catalyst_summary = self._create_catalyst_summary(ticker, catalysts)
                results['catalysts'] = catalyst_summary
            
            return results
            
        except Exception as e:
            print(f"Error in comprehensive analysis for {ticker}: {e}")
            return {}
    
    def _parse_catalysts_from_text(self, ticker: str, content: str) -> List[MarketCatalyst]:
        """Parse market catalysts from Perplexity response"""
        catalysts = []
        
        # Simple keyword-based parsing
        content_lower = content.lower()
        
        # Look for earnings mentions
        if "earnings" in content_lower or "eps" in content_lower or "guidance" in content_lower:
            sentiment = "bullish" if any(word in content_lower for word in ["beat", "raise", "increase", "strong"]) else "neutral"
            catalysts.append(MarketCatalyst(
                ticker=ticker,
                event_type="earnings",
                description="Earnings-related catalyst detected",
                impact_sentiment=sentiment,
                confidence=0.7
            ))
        
        # Look for analyst activity
        if "upgrade" in content_lower or "downgrade" in content_lower or "price target" in content_lower:
            sentiment = "bullish" if "upgrade" in content_lower else "bearish" if "downgrade" in content_lower else "neutral"
            catalysts.append(MarketCatalyst(
                ticker=ticker,
                event_type="analyst_action",
                description="Analyst rating or price target change",
                impact_sentiment=sentiment,
                confidence=0.8
            ))
        
        # Look for news events
        if any(word in content_lower for word in ["announcement", "launch", "partnership", "acquisition", "merger"]):
            catalysts.append(MarketCatalyst(
                ticker=ticker,
                event_type="corporate_news",
                description="Corporate announcement or news event",
                impact_sentiment="neutral",
                confidence=0.6
            ))
        
        return catalysts
    
    def _parse_sentiment_analysis(self, content: str) -> Dict:
        """Parse sentiment analysis from text response"""
        sentiment_score = 50  # Default neutral
        confidence = 70
        
        content_lower = content.lower()
        
        # Look for explicit sentiment scores
        import re
        score_match = re.search(r'sentiment.*?(\d{1,3})', content_lower)
        if score_match:
            try:
                sentiment_score = int(score_match.group(1))
                sentiment_score = max(0, min(100, sentiment_score))
            except:
                pass
        else:
            # Keyword-based sentiment scoring
            bullish_words = ["bullish", "positive", "optimistic", "strong", "upgrade", "beat", "outperform"]
            bearish_words = ["bearish", "negative", "pessimistic", "weak", "downgrade", "miss", "underperform"]
            
            bullish_count = sum(1 for word in bullish_words if word in content_lower)
            bearish_count = sum(1 for word in bearish_words if word in content_lower)
            
            if bullish_count > bearish_count:
                sentiment_score = min(85, 50 + (bullish_count - bearish_count) * 10)
            elif bearish_count > bullish_count:
                sentiment_score = max(15, 50 - (bearish_count - bullish_count) * 10)
        
        # Extract key points
        recommendations = []
        risk_factors = []
        
        if sentiment_score > 60:
            recommendations.append("Consider bullish positioning")
        elif sentiment_score < 40:
            recommendations.append("Exercise caution, consider bearish scenarios")
        
        return {
            'sentiment_score': sentiment_score,
            'summary': content[:300] + ('...' if len(content) > 300 else ''),
            'confidence': confidence,
            'recommendations': recommendations,
            'risk_factors': risk_factors,
            'raw_analysis': content
        }
    
    def _create_catalyst_summary(self, ticker: str, catalysts: List[MarketCatalyst]) -> AIAnalysisResult:
        """Create catalyst analysis result"""
        if not catalysts:
            return self._create_error_result(ticker, "catalyst", "No catalysts found")
        
        bullish_count = sum(1 for c in catalysts if c.impact_sentiment == 'bullish')
        bearish_count = sum(1 for c in catalysts if c.impact_sentiment == 'bearish')
        
        overall_sentiment = "neutral"
        if bullish_count > bearish_count:
            overall_sentiment = "bullish"
        elif bearish_count > bullish_count:
            overall_sentiment = "bearish"
        
        catalyst_types = [c.event_type for c in catalysts]
        
        return AIAnalysisResult(
            ticker=ticker,
            analysis_type="catalyst",
            confidence_score=75,
            summary=f"Found {len(catalysts)} catalysts: {', '.join(set(catalyst_types))}. Overall sentiment: {overall_sentiment}",
            detailed_analysis={
                'catalysts': [asdict(c) for c in catalysts],
                'bullish_factors': bullish_count,
                'bearish_factors': bearish_count,
                'overall_sentiment': overall_sentiment
            },
            recommendations=[f"Monitor {c.event_type} developments" for c in catalysts[:2]],
            risk_factors=["Catalyst timing uncertainty", "Market reaction unpredictability"],
            timestamp=datetime.now(),
            source="perplexity"
        )
    
    def _create_error_result(self, ticker: str, analysis_type: str, error_msg: str) -> AIAnalysisResult:
        """Create error result"""
        return AIAnalysisResult(
            ticker=ticker,
            analysis_type=analysis_type,
            confidence_score=0,
            summary=f"Analysis failed: {error_msg}",
            detailed_analysis={'error': error_msg},
            recommendations=[],
            risk_factors=["Analysis unavailable"],
            timestamp=datetime.now(),
            source="error"
        )