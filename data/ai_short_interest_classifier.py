#!/usr/bin/env python3
"""
AI Short Interest Classifier - Classe les résultats Short Interest + Unusual Whales
Ajoute une couche IA pour filtrer et prioriser les résultats du pipeline SI→Options
"""

import json
from datetime import datetime
from typing import List, Dict, Any
import requests
from dataclasses import dataclass
from utils.config import Config
import logging

logger = logging.getLogger(__name__)

@dataclass
class ShortSqueezeAnalysis:
    """Analyse IA d'une opportunité Short Interest + Options"""
    symbol: str
    squeeze_probability: float  # 0-100
    strategy_recommendation: str  # "BUY_CALLS", "SELL_PUTS", "AVOID", "HEDGE"
    confidence_level: float  # 0-100
    risk_reward_ratio: float
    target_timeframe: str  # "1-3 days", "1-2 weeks", "1 month+"
    entry_timing: str  # "IMMEDIATE", "ON_DIP", "WAIT_CATALYST"
    key_factors: List[str]
    risk_warnings: List[str]
    ai_score: float  # Score composite IA (0-100)
    
class AIShortInterestClassifier:
    """Classificateur IA pour opportunités Short Interest + Options"""
    
    def __init__(self):
        self.openai_api_url = "https://api.openai.com/v1/chat/completions"
    
    async def analyze_short_interest_opportunity(
        self, 
        opportunity: Dict[str, Any],
        short_interest_data: Dict[str, Any]
    ) -> ShortSqueezeAnalysis:
        """
        Analyse une opportunité combinant Short Interest + Activity Options avec IA
        
        Args:
            opportunity: Données de l'option (volume, OI, greeks, etc.)
            short_interest_data: Données short interest du symbole
            
        Returns:
            Analyse IA complète de l'opportunité squeeze
        """
        
        openai_key = Config.get_openai_api_key()
        if not openai_key:
            return self._create_fallback_analysis(opportunity, "OpenAI API key not configured")
        
        # Préparer les données pour l'IA
        prompt = self._build_squeeze_analysis_prompt(opportunity, short_interest_data)
        
        headers = {
            'Authorization': f'Bearer {openai_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'gpt-4',
            'messages': [
                {
                    'role': 'system', 
                    'content': self._get_system_prompt()
                },
                {
                    'role': 'user', 
                    'content': prompt
                }
            ],
            'max_tokens': 1200,
            'temperature': 0.1
        }
        
        try:
            response = requests.post(self.openai_api_url, json=payload, headers=headers, timeout=45)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Parse la réponse JSON
            analysis_data = self._parse_ai_response(content)
            
            return ShortSqueezeAnalysis(
                symbol=opportunity.get('underlying_symbol', 'UNKNOWN'),
                squeeze_probability=analysis_data.get('squeeze_probability', 50),
                strategy_recommendation=analysis_data.get('strategy_recommendation', 'AVOID'),
                confidence_level=analysis_data.get('confidence_level', 70),
                risk_reward_ratio=analysis_data.get('risk_reward_ratio', 1.0),
                target_timeframe=analysis_data.get('target_timeframe', '1-2 weeks'),
                entry_timing=analysis_data.get('entry_timing', 'WAIT_CATALYST'),
                key_factors=analysis_data.get('key_factors', []),
                risk_warnings=analysis_data.get('risk_warnings', []),
                ai_score=analysis_data.get('ai_score', 50)
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur analyse IA pour {opportunity.get('underlying_symbol', 'UNKNOWN')}: {e}")
            return self._create_fallback_analysis(opportunity, str(e))
    
    def _get_system_prompt(self) -> str:
        """Prompt système spécialisé Short Interest + Options"""
        return """Tu es un expert en analyse quantitative spécialisé dans les short squeezes et l'activité options institutionnelle. 

Ta mission: analyser les opportunités combinant FORT SHORT INTEREST + ACTIVITÉ OPTIONS ANORMALE pour détecter les setups de squeeze potentiels.

Expertise:
- Short squeeze mechanics & catalysts
- Unusual options flow analysis (Unusual Whales methodology)  
- Market microstructure & liquidity
- Risk management institutionnel

Tu dois:
1. Évaluer la probabilité de squeeze (0-100%)
2. Recommander une stratégie précise
3. Quantifier le risk/reward
4. Identifier les timing d'entrée optimaux
5. Alerter sur les risques spécifiques

Réponds TOUJOURS en JSON valide."""

    def _build_squeeze_analysis_prompt(
        self, 
        opportunity: Dict[str, Any], 
        short_interest_data: Dict[str, Any]
    ) -> str:
        """Construit le prompt d'analyse squeeze"""
        
        # Extraire les données clés
        symbol = opportunity.get('underlying_symbol', 'UNKNOWN')
        option_type = opportunity.get('option_type', 'UNKNOWN')
        volume = opportunity.get('volume', 0)
        open_interest = opportunity.get('open_interest', 0)
        vol_oi_ratio = volume / max(open_interest, 1)
        whale_score = opportunity.get('whale_score', 0)
        dte = opportunity.get('dte', 0)
        strike = opportunity.get('strike', 0)
        underlying_price = opportunity.get('underlying_price', 0)
        
        # Données Short Interest
        short_pct = short_interest_data.get('short_interest_percent', 0)
        market_cap = short_interest_data.get('market_cap', 0)
        float_shares = short_interest_data.get('float', 0)
        avg_volume = short_interest_data.get('volume', 0)
        days_to_cover = short_interest_data.get('days_to_cover', 0)
        
        # Calcul moneyness
        moneyness = "OTM"
        if underlying_price and strike:
            if option_type.upper() == "CALL":
                moneyness = "ITM" if underlying_price > strike else ("ATM" if abs(underlying_price - strike) / underlying_price < 0.02 else "OTM")
            else:  # PUT
                moneyness = "ITM" if underlying_price < strike else ("ATM" if abs(underlying_price - strike) / underlying_price < 0.02 else "OTM")
        
        return f"""
        ANALYSE SHORT SQUEEZE OPPORTUNITY
        ================================
        
        📊 STOCK DATA:
        Symbol: {symbol}
        Short Interest: {short_pct}%
        Market Cap: ${market_cap:,} 
        Float: {float_shares:,} shares
        Avg Volume: {avg_volume:,}
        Days to Cover: {days_to_cover:.1f}
        
        🎯 OPTIONS ACTIVITY:
        Type: {option_type} {strike} strike (DTE: {dte})
        Moneyness: {moneyness}
        Volume: {volume:,} contracts  
        Open Interest: {open_interest:,}
        Vol/OI Ratio: {vol_oi_ratio:.2f}
        Unusual Whales Score: {whale_score:.1f}/100
        Underlying Price: ${underlying_price:.2f}
        
        🧠 MISSION IA:
        Évalue cette opportunité de SHORT SQUEEZE basée sur:
        1. Short Interest élevé ({short_pct}%) 
        2. Activité options anormale (score UW: {whale_score})
        3. Setup technique et timing
        
        Réponds en JSON:
        {{
            "squeeze_probability": <0-100: probabilité de squeeze dans les 30 jours>,
            "strategy_recommendation": "<BUY_CALLS|SELL_PUTS|BUY_STRADDLE|AVOID>",
            "confidence_level": <0-100: confiance dans l'analyse>,
            "risk_reward_ratio": <1.0-10.0: ratio risque/récompense estimé>,
            "target_timeframe": "<1-3 days|1-2 weeks|2-4 weeks|1+ month>",
            "entry_timing": "<IMMEDIATE|ON_DIP|WAIT_CATALYST|AFTER_EARNINGS>",
            "key_factors": [
                "Facteur haussier 1",
                "Facteur haussier 2", 
                "Facteur technique 3"
            ],
            "risk_warnings": [
                "Risque principal 1",
                "Risque principal 2",
                "Contrainte temporelle"
            ],
            "ai_score": <0-100: score composite IA final>,
            "reasoning": "Explication détaillée du raisonnement (2-3 phrases)"
        }}
        
        🎯 FOCUS SUR:
        - Catalysts potentiels de squeeze
        - Liquidité et capacité d'absorption
        - Timing optimal vs expiration  
        - Corrélation SI% vs activité options
        - Risques de manipulation ou piège
        """
    
    def _parse_ai_response(self, content: str) -> Dict[str, Any]:
        """Parse la réponse IA et extrait les données"""
        try:
            # Nettoyer le JSON
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"❌ Erreur parsing réponse IA: {e}")
            return {
                'squeeze_probability': 50,
                'strategy_recommendation': 'AVOID',
                'confidence_level': 30,
                'risk_reward_ratio': 1.0,
                'target_timeframe': '1-2 weeks',
                'entry_timing': 'WAIT_CATALYST',
                'key_factors': ['Analyse IA indisponible'],
                'risk_warnings': ['Erreur de parsing', 'Éviter cette position'],
                'ai_score': 25
            }
    
    def _create_fallback_analysis(self, opportunity: Dict[str, Any], error_msg: str) -> ShortSqueezeAnalysis:
        """Crée une analyse fallback en cas d'erreur"""
        return ShortSqueezeAnalysis(
            symbol=opportunity.get('underlying_symbol', 'UNKNOWN'),
            squeeze_probability=30,
            strategy_recommendation='AVOID',
            confidence_level=25,
            risk_reward_ratio=1.0,
            target_timeframe='Unknown',
            entry_timing='WAIT_CATALYST',
            key_factors=['IA unavailable'],
            risk_warnings=[f'Analysis error: {error_msg}', 'Manual analysis required'],
            ai_score=25
        )
    
    async def classify_short_interest_results(
        self, 
        opportunities: List[Dict[str, Any]],
        short_interest_stocks: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Classe et filtre tous les résultats Short Interest + Options avec IA
        
        Args:
            opportunities: Liste des opportunités options
            short_interest_stocks: Dict des données short interest par symbole
            
        Returns:
            Liste des opportunités classées avec analyse IA
        """
        
        logger.info(f"🧠 Classification IA de {len(opportunities)} opportunités Short Interest")
        
        enriched_opportunities = []
        
        for i, opp in enumerate(opportunities):
            try:
                symbol = opp.get('underlying_symbol', '').upper()
                
                # Récupérer les données short interest pour ce symbole
                si_data = short_interest_stocks.get(symbol, {})
                
                if not si_data:
                    logger.warning(f"⚠️ Pas de données SI pour {symbol}, skip analyse IA")
                    continue
                
                # Analyse IA de l'opportunité
                ai_analysis = await self.analyze_short_interest_opportunity(opp, si_data)
                
                # Enrichir l'opportunité avec l'analyse IA
                enriched_opp = {
                    **opp,  # Données originales
                    
                    # Enrichissement IA
                    'ai_squeeze_probability': ai_analysis.squeeze_probability,
                    'ai_strategy_recommendation': ai_analysis.strategy_recommendation,
                    'ai_confidence': ai_analysis.confidence_level,
                    'ai_risk_reward_ratio': ai_analysis.risk_reward_ratio,
                    'ai_target_timeframe': ai_analysis.target_timeframe,
                    'ai_entry_timing': ai_analysis.entry_timing,
                    'ai_key_factors': ai_analysis.key_factors,
                    'ai_risk_warnings': ai_analysis.risk_warnings,
                    'ai_score': ai_analysis.ai_score,
                    
                    # Données Short Interest incluses
                    'short_interest_percent': si_data.get('short_interest_percent', 0),
                    'days_to_cover': si_data.get('days_to_cover', 0),
                    'float_shares': si_data.get('float', 0),
                    
                    # Métadonnées
                    'ai_analysis_timestamp': datetime.now().isoformat(),
                    'analysis_type': 'short_interest_squeeze'
                }
                
                enriched_opportunities.append(enriched_opp)
                
                logger.info(f"✅ IA Analysis {symbol}: Score={ai_analysis.ai_score:.1f}, Squeeze={ai_analysis.squeeze_probability:.1f}%, Strategy={ai_analysis.strategy_recommendation}")
                
            except Exception as e:
                logger.error(f"❌ Erreur classification IA pour {opp.get('underlying_symbol', 'UNKNOWN')}: {e}")
                continue
        
        # Trier par score IA décroissant
        enriched_opportunities.sort(key=lambda x: x.get('ai_score', 0), reverse=True)
        
        logger.info(f"🎯 Classification IA terminée: {len(enriched_opportunities)} opportunités analysées")
        
        return enriched_opportunities

    def filter_by_ai_criteria(
        self, 
        opportunities: List[Dict[str, Any]],
        min_ai_score: float = 70,
        min_squeeze_probability: float = 60,
        allowed_strategies: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Filtre les opportunités selon les critères IA
        
        Args:
            opportunities: Opportunités avec analyse IA
            min_ai_score: Score IA minimum
            min_squeeze_probability: Probabilité squeeze minimum
            allowed_strategies: Stratégies autorisées
            
        Returns:
            Liste filtrée des meilleures opportunités
        """
        
        if allowed_strategies is None:
            allowed_strategies = ['BUY_CALLS', 'SELL_PUTS', 'BUY_STRADDLE']
        
        filtered = []
        
        for opp in opportunities:
            # Vérifications des critères IA
            ai_score = opp.get('ai_score', 0)
            squeeze_prob = opp.get('ai_squeeze_probability', 0)
            strategy = opp.get('ai_strategy_recommendation', 'AVOID')
            
            if (ai_score >= min_ai_score and 
                squeeze_prob >= min_squeeze_probability and 
                strategy in allowed_strategies):
                
                filtered.append(opp)
        
        logger.info(f"🔍 Filtrage IA: {len(filtered)}/{len(opportunities)} opportunités retenues")
        logger.info(f"   Critères: AI Score≥{min_ai_score}, Squeeze≥{min_squeeze_probability}%, Strategies={allowed_strategies}")
        
        return filtered