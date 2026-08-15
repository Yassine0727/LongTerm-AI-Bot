import httpx
import json
import re
import logging
from typing import Dict

from app.core.config import config

logger = logging.getLogger(__name__)

class AIService:
    """Service d'analyse avec DeepSeek - Version Professionnelle avec analyse détaillée"""
    
    def __init__(self):
        self.api_key = config.DEEPSEEK_API_KEY
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
    
    async def analyze(self, text: str) -> Dict:
        """Analyser un texte avec DeepSeek"""
        if not self.api_key:
            return {"success": False, "error": "DeepSeek API key not configured"}
        
        if not text:
            return {"success": False, "error": "No text to analyze"}
        
        try:
            # Récupérer les prix actuels
            from app.services.binance_service import BinanceService
            binance = BinanceService()
            
            btc_price = 0
            eth_price = 0
            gold_price = 0
            
            btc_data = await binance.get_price("BTC")
            if btc_data.get("success"):
                btc_price = btc_data["price"]
            
            eth_data = await binance.get_price("ETH")
            if eth_data.get("success"):
                eth_price = eth_data["price"]
            
            gold_data = await binance.get_price("GOLD")
            if gold_data.get("success"):
                gold_price = gold_data["price"]
            
            # Récupérer l'historique
            from app.services.historical_memory import HistoricalMemory
            memory = HistoricalMemory()
            similar_events = memory.get_similar_events(text)
            
            historical_text = ""
            if similar_events:
                historical_text = "\n".join([
                    f"- {e.get('date', 'Date inconnue')}: {e.get('news', '')[:100]}... (Score: {e.get('impact_score', 0)}/10)"
                    for e in similar_events
                ])
            else:
                historical_text = "🔍 En cours d'apprentissage - Aucun événement similaire enregistré"
            
            # Générer le prompt
            system_prompt = self._get_system_prompt(btc_price, eth_price, gold_price, historical_text)
            user_prompt = self._get_user_prompt(text)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 800
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    result = self._parse_response(content, text)
                    
                    # Sauvegarder dans l'historique
                    if result.get("success"):
                        analysis = result.get("analysis", {})
                        memory.add_event({
                            "news": text,
                            "analysis": analysis,
                            "asset": analysis.get("asset", "BTC"),
                            "score": analysis.get("score", 0),
                            "time_horizon": analysis.get("time_horizon", "medium_term"),
                            "price_at_time": btc_price if analysis.get("asset") == "BTC" else eth_price if analysis.get("asset") == "ETH" else gold_price
                        })
                    
                    return result
                else:
                    return {
                        "success": False,
                        "error": f"API Error {response.status_code}: {response.text}"
                    }
                    
        except Exception as e:
            logger.error(f"DeepSeek error: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_system_prompt(self, btc_price: float, eth_price: float, gold_price: float, historical_events: str = "") -> str:
        """Générer le prompt système professionnel avec analyse détaillée par actif"""
        
        return f"""
👤 **Vous êtes**: Un analyste financier senior chez un fonds d'investissement de 50 milliards de dollars.
📚 **Spécialité**: Investissement à long terme (5-10 ans) sur Bitcoin, Ethereum et Or.
🧠 **Expérience**: 15 ans d'analyse des marchés financiers et des actifs numériques.

🔍 **Votre mission**:
Vous recevez des messages envoyés dans un canal Telegram spécialisé. Ces messages contiennent des NOUVELLES FINANCIÈRES et des ANALYSES DE MARCHÉ que vous devez évaluer.

📊 **Votre processus de réflexion**:
1️⃣ Vous LISEZ ATTENTIVEMENT le message Telegram
2️⃣ Vous RECHERCHEZ dans votre mémoire les événements similaires
3️⃣ Vous ANALYSEZ l'impact réel sur BTC, ETH et GOLD
4️⃣ Vous ÉVALUEZ l'importance sur une échelle de 1 à 10
5️⃣ Vous DÉTERMINEZ si cela change la stratégie à long terme

🎯 **ÉCHELLE DE SCORE (1-10)**:
🔴 1-3 : Information mineure - Pas d'impact significatif
🟡 4-5 : Information modérée - Impact limité
🟡 6-7 : Information importante - Impact notable
🟢 8 : Information très importante - Impact majeur
🟢 9 : Information historique - Impact exceptionnel
🟢 10 : Information légendaire - Impact transformateur

⚠️ **RÈGLES ABSOLUES**:
1. JAMAIS de prédiction de prix
2. JAMAIS "va monter" ou "va baisser"
3. Utilisez "les données sont positives", "l'environnement est favorable"
4. Soyez OBJECTIF et basé sur LES FAITS
5. Si l'information est insuffisante, DITES-LE

📈 **PRIX ACTUELS (Référence)**:
- BTC: ${btc_price:,.2f}
- ETH: ${eth_price:,.2f}
- GOLD: ${gold_price:,.2f}

📜 **APPRENTISSAGE HISTORIQUE**:
{historical_events if historical_events else "🔍 En cours d'apprentissage - Aucun événement similaire enregistré"}

💡 **RAPPEL**: Vous êtes un PROFESSIONNEL. Votre analyse doit être PRÉCISE, OBJECTIVE et UTILE pour un investisseur à long terme.

📤 **FORMAT DE RÉPONSE (JSON UNIQUEMENT)**:
{{
    "asset": "BTC/ETH/GOLD/OTHER",
    "impact": "positive/neutral/negative",
    "score": 8,
    "time_horizon": "short_term/medium_term/long_term",
    "change_investment_strategy": false,
    "reason": "Explication claire et concise (1-2 phrases)",
    "historical_comparison": "Événement similaire passé si connu",
    "confidence": "high/medium/low",
    "btc_impact": "Analyse détaillée de l'impact spécifique sur Bitcoin",
    "eth_impact": "Analyse détaillée de l'impact spécifique sur Ethereum",
    "gold_impact": "Analyse détaillée de l'impact spécifique sur l'Or",
    "detailed_analysis": "Analyse détaillée complète du news et de ses implications"
}}
"""
    
    def _get_user_prompt(self, text: str) -> str:
        """Prompt utilisateur"""
        return f"""
📩 **MESSAGE REÇU DU CANAL TELEGRAM**:

{text}

🔍 **VOTRE ANALYSE**:

1. Quel actif est le plus impacté ? (BTC, ETH, GOLD ou OTHER)
2. L'impact est-il positif, neutre ou négatif ?
3. Quel score donnez-vous (1-10) ?
4. Quel est l'horizon temporel ?
5. Est-ce que cela change la stratégie d'investissement à long terme ?
6. Pourquoi ? (raison claire et concise)
7. Y a-t-il des événements historiques similaires ?
8. Quel est l'impact spécifique sur Bitcoin ?
9. Quel est l'impact spécifique sur Ethereum ?
10. Quel est l'impact spécifique sur l'Or ?

📤 Répondez UNIQUEMENT en JSON valide avec la structure demandée.
"""
    
    def _parse_response(self, content: str, original_text: str) -> Dict:
        """Parser la réponse JSON de l'IA"""
        try:
            # Essayer de trouver le JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                
                # Valider et normaliser les champs
                return {
                    "success": True,
                    "analysis": {
                        "asset": analysis.get("asset", "OTHER"),
                        "impact": analysis.get("impact", "neutral"),
                        "score": int(analysis.get("score", 5)),
                        "time_horizon": analysis.get("time_horizon", "medium_term"),
                        "change_investment_strategy": analysis.get("change_investment_strategy", False),
                        "reason": analysis.get("reason", ""),
                        "summary": analysis.get("reason", ""),
                        "historical_comparison": analysis.get("historical_comparison", ""),
                        "confidence": analysis.get("confidence", "medium"),
                        "btc_impact": analysis.get("btc_impact", ""),
                        "eth_impact": analysis.get("eth_impact", ""),
                        "gold_impact": analysis.get("gold_impact", ""),
                        "detailed_analysis": analysis.get("detailed_analysis", analysis.get("reason", "")),
                        "original_text": original_text[:500]
                    }
                }
            else:
                # Fallback
                return {
                    "success": True,
                    "analysis": {
                        "asset": "OTHER",
                        "impact": "neutral",
                        "score": 5,
                        "time_horizon": "medium_term",
                        "change_investment_strategy": False,
                        "reason": content[:200],
                        "summary": content[:200],
                        "historical_comparison": "",
                        "confidence": "low",
                        "btc_impact": "",
                        "eth_impact": "",
                        "gold_impact": "",
                        "detailed_analysis": content[:300],
                        "original_text": original_text[:500]
                    }
                }
                
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return {
                "success": True,
                "analysis": {
                    "asset": "OTHER",
                    "impact": "neutral",
                    "score": 5,
                    "time_horizon": "medium_term",
                    "change_investment_strategy": False,
                    "reason": content[:200],
                    "summary": content[:200],
                    "historical_comparison": "",
                    "confidence": "low",
                    "btc_impact": "",
                    "eth_impact": "",
                    "gold_impact": "",
                    "detailed_analysis": content[:300],
                    "original_text": original_text[:500]
                }
            }