import logging
from typing import Dict, Optional
from datetime import datetime

from app.services.ai_service import AIService
from app.services.binance_service import BinanceService
from app.services.notification_service import NotificationService
from app.core.database import Database

logger = logging.getLogger(__name__)

class AnalyzerService:
    def __init__(self):
        self.ai_service = AIService()
        self.binance = BinanceService()
        self.notifier = NotificationService()
        self.analysis_count = 0
        self.last_weekly_report = None
    
    def _check_high_impact_keywords(self, text: str) -> int:
        """Vérifier si le texte contient des mots-clés à fort impact"""
        text_lower = text.lower()
        
        # Mots-clés TRÈS FORTS (score 9-10)
        very_strong = [
            "fed", "federal reserve", "réserve fédérale", "taux d'intérêt", 
            "interest rate", "guerre", "war", "crise", "crisis",
            "récession", "recession", "inflation", "hyperinflation",
            "banque centrale", "central bank", "effondrement", "collapse",
            "attaque", "attack", "terroriste", "terrorist",
            "poutine", "putin", "biden", "trump", "élection", "election"
        ]
        
        # Mots-clés FORTS (score 7-8)
        strong = [
            "blackrock", "vanguard", "fidelity", "institutionnel", "institutional",
            "etf", "sec", "regulation", "régulation", "loi", "law",
            "adoption", "massive", "record", "historique", "historic",
            "banque", "bank", "finance", "investissement", "investment",
            "bitcoin", "ethereum", "gold", "or", "crypto",
            "goldman sachs", "morgan stanley", "jpmorgan"
        ]
        
        for word in very_strong:
            if word in text_lower:
                return 9
        
        for word in strong:
            if word in text_lower:
                return 7
        
        return 0
    
    def _generate_detailed_impact(self, analysis: Dict) -> str:
        """Générer un impact détaillé en arabe"""
        asset = analysis.get('asset', 'Unknown')
        impact = analysis.get('impact', 'neutral')
        score = analysis.get('score', 0)
        time_horizon = analysis.get('time_horizon', 'medium_term')
        reason = analysis.get('reason', '')
        
        horizon_text = {
            "short_term": "قصير المدى",
            "medium_term": "متوسط المدى",
            "long_term": "طويل المدى"
        }.get(time_horizon, "متوسط المدى")
        
        # Impact détaillé par actif
        btc_impact = analysis.get('btc_impact', '')
        eth_impact = analysis.get('eth_impact', '')
        gold_impact = analysis.get('gold_impact', '')
        
        if not btc_impact:
            if impact == "positive":
                btc_impact = f"تأثير إيجابي على Bitcoin. من المتوقع أن يشهد BTC ارتفاعًا مع زيادة الثقة المؤسسية."
            elif impact == "negative":
                btc_impact = f"تأثير سلبي على Bitcoin. من المتوقع أن يشهد BTC ضغطًا مع زيادة القلق في الأسواق."
            else:
                btc_impact = f"تأثير محايد على Bitcoin. من المتوقع أن يبقى BTC مستقرًا."
        
        if not eth_impact:
            if impact == "positive":
                eth_impact = f"تأثير إيجابي على Ethereum. من المتوقع أن يشهد ETH ارتفاعًا مع تحسن المعنويات."
            elif impact == "negative":
                eth_impact = f"تأثير سلبي على Ethereum. من المتوقع أن يشهد ETH تراجعًا مع انخفاض الثقة."
            else:
                eth_impact = f"تأثير محايد على Ethereum. من المتوقع أن يبقى ETH مستقرًا."
        
        if not gold_impact:
            if impact == "positive":
                gold_impact = f"تأثير إيجابي على Gold. من المتوقع أن يشهد الذهب ارتفاعًا مع زيادة الطلب كملاذ آمن."
            elif impact == "negative":
                gold_impact = f"تأثير سلبي على Gold. من المتوقع أن يشهد الذهب ضغطًا مع تحسن شهية المخاطرة."
            else:
                gold_impact = f"تأثير محايد على Gold. من المتوقع أن يبقى الذهب مستقرًا."
        
        detailed = f"""
📰 **الخبر**:
{analysis.get('original_text', '')}

📊 **التحليل المفصل**:
{reason}

{'='*40}

📈 **تأثير الخبر على الأصول**:

🟠 **Bitcoin (BTC)**:
{btc_impact}

🔵 **Ethereum (ETH)**:
{eth_impact}

🟡 **Gold (XAU)**:
{gold_impact}

{'='*40}

📊 **التقييم العام**:
• التأثير: {analysis.get('impact', 'neutral')} (التقييم: {score}/10)
• الأفق الزمني: {horizon_text}
• الثقة: {analysis.get('confidence', 'medium')}

📜 **المقارنة التاريخية**:
{analysis.get('historical_comparison', 'لا توجد مقارنة تاريخية متاحة')}

🎯 **هل يغير الاستراتيجية؟**
{'✅ نعم، قد يتطلب إعادة تقييم' if analysis.get('change_investment_strategy') else '❌ لا، لا يغير الاستراتيجية الحالية'}

⚠️ **تنبيه**: هذا تحليل استثماري مبني على البيانات المتاحة. الأسواق متقلبة وقد تتغير الظروف.
        """.strip()
        
        return detailed
    
    async def analyze_message(self, text: str, message_id: str, date=None) -> Optional[Dict]:
        """Analyser un message Telegram"""
        try:
            logger.info(f"📩 Analyzing: {text[:100]}...")
            
            # 1. Analyser avec DeepSeek
            result = await self.ai_service.analyze(text)
            
            if not result.get("success"):
                logger.warning(f"⚠️ Analysis failed: {result.get('error')}")
                return None
            
            analysis = result.get("analysis", {})
            
            # 2. Forcer le score si mots-clés forts détectés
            keyword_score = self._check_high_impact_keywords(text)
            current_score = analysis.get("score", 0)
            
            if keyword_score > 0 and current_score < keyword_score:
                analysis["score"] = keyword_score
                logger.info(f"📈 Score forcé de {current_score} à {keyword_score}/10 (mots-clés détectés)")
            
            # 3. S'assurer que tous les champs existent
            if "summary" not in analysis or not analysis.get("summary"):
                analysis["summary"] = analysis.get("reason", "Analyse en cours...")
            
            if "detailed_analysis" not in analysis:
                analysis["detailed_analysis"] = analysis.get("reason", "Analyse détaillée non disponible")
            
            if "btc_impact" not in analysis:
                analysis["btc_impact"] = ""
            
            if "eth_impact" not in analysis:
                analysis["eth_impact"] = ""
            
            if "gold_impact" not in analysis:
                analysis["gold_impact"] = ""
            
            # 4. Générer un impact détaillé si manquant
            if "detailed_impact" not in analysis:
                analysis["detailed_impact"] = self._generate_detailed_impact(analysis)
            
            # 5. Afficher les détails de l'analyse
            score = analysis.get("score", 0)
            asset = analysis.get("asset", "Unknown")
            impact = analysis.get("impact", "neutral")
            
            logger.info(f"📊 RÉSULTAT: {asset} - {impact} - Score: {score}/10")
            logger.info(f"   📝 Raison: {analysis.get('reason', 'N/A')}")
            
            if analysis.get("historical_comparison"):
                logger.info(f"   📜 Comparaison: {analysis.get('historical_comparison')}")
            
            # 6. Sauvegarder
            analysis["message_id"] = message_id
            analysis["timestamp"] = datetime.now().isoformat()
            
            Database.save_analysis(analysis)
            self.analysis_count += 1
            
            logger.info(f"✅ Analysis saved: {analysis.get('asset')} - {analysis.get('impact')}")
            
            # 7. Envoyer une alerte si score >= 7
            if score >= 7:
                logger.info(f"🔔 ALERTE ENVOYEE: {asset} - Score: {score}/10")
                await self.notifier.send_alert(analysis)
            else:
                logger.info(f"⏭️ Pas d'alerte: Score {score}/10 < 7")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Analyze error: {e}")
            return None
    
    async def check_prices_and_alert(self):
        """Vérifier les prix et envoyer des alertes"""
        symbols = ["BTC", "ETH", "GOLD"]
        
        logger.info("📊 Vérification des prix...")
        
        for symbol in symbols:
            try:
                alert = await self.binance.check_and_alert(symbol)
                if alert:
                    await self.notifier.send_price_alert(alert)
            except Exception as e:
                logger.error(f"❌ Error checking {symbol}: {e}")
        
        logger.info("✅ Vérification terminée")
    
    async def generate_weekly_report(self) -> Optional[Dict]:
        """Générer et envoyer le rapport hebdomadaire"""
        try:
            report = await self.binance.get_weekly_report()
            await self.notifier.send_weekly_report(report)
            self.last_weekly_report = report
            return report
        except Exception as e:
            logger.error(f"❌ Error generating weekly report: {e}")
            return None
    
    def get_stats(self) -> Dict:
        return {
            "total_analyzed": self.analysis_count,
            "total_saved": Database.get_analysis_count(),
            "last_weekly_report": self.last_weekly_report is not None
        }
    
    async def save_prices_to_history(self):
        """Enregistrer les prix actuels dans l'historique"""
        try:
            prices = {}
            for symbol in ["BTC", "ETH", "GOLD"]:
                details = await self.binance.get_price_with_details(symbol)
                prices[symbol] = details
            
            from app.services.price_recorder import PriceRecorder
            recorder = PriceRecorder()
            await recorder.save_prices(prices)
            return True
        except Exception as e:
            logger.error(f"Error saving prices: {e}")
            return False
    
    async def get_price_history(self, limit: int = 100) -> list:
        """Obtenir l'historique des prix"""
        from app.services.price_recorder import PriceRecorder
        recorder = PriceRecorder()
        return recorder.get_history(limit)
    
    async def get_last_price(self, symbol: str) -> Dict:
        """Obtenir le dernier prix enregistré"""
        from app.services.price_recorder import PriceRecorder
        recorder = PriceRecorder()
        return recorder.get_last_price(symbol)
    
    async def get_daily_summary(self, date: str = None) -> Dict:
        """Obtenir le résumé journalier"""
        from app.services.price_recorder import PriceRecorder
        recorder = PriceRecorder()
        return recorder.get_daily_summary(date)