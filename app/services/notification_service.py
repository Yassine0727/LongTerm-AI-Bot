import logging
from typing import Dict
from datetime import datetime

from app.services.telegram_notify import TelegramNotify
from app.services.sendgrid_service import SendGridService

logger = logging.getLogger(__name__)

class NotificationService:
    """Service d'envoi de notifications (Telegram + SendGrid) en Arabe"""
    
    def __init__(self):
        self.telegram = TelegramNotify()
        self.email = SendGridService()
    
    def _get_impact_emoji(self, impact: str) -> str:
        if impact == "positive":
            return "🟢"
        elif impact == "negative":
            return "🔴"
        else:
            return "🟡"
    
    def _get_impact_ar(self, impact: str) -> str:
        if impact == "positive":
            return "إيجابي"
        elif impact == "negative":
            return "سلبي"
        else:
            return "محايد"
    
    def _get_horizon_ar(self, horizon: str) -> str:
        horizons = {
            "short_term": "قصير المدى (أيام - أسابيع)",
            "medium_term": "متوسط المدى (شهور)",
            "long_term": "طويل المدى (سنوات)"
        }
        return horizons.get(horizon, "متوسط المدى")
    
    async def send_price_alert(self, alert_data: Dict) -> bool:
        """Envoyer une alerte de prix en arabe"""
        symbol = alert_data.get("symbol", "Unknown")
        old_price = alert_data.get("old_price", 0)
        current_price = alert_data.get("current_price", 0)
        change = alert_data.get("change_percent", 0)
        
        emoji = "🚀" if change > 0 else "📉"
        direction = "ارتفاع" if change > 0 else "انخفاض"
        
        # Message Telegram
        telegram_msg = f"""
📊 <b>تنبيه سعر {symbol}</b>

{emoji} <b>{direction} {abs(change):.2f}%</b>

💰 <b>السعر السابق:</b> ${old_price:,.2f}
💰 <b>السعر الحالي:</b> ${current_price:,.2f}
📊 <b>التغير:</b> {change:+.2f}%

<i>⚠️ هذا تنبيه سعر فقط.</i>
<i>⚠️ ليس توصية شراء أو بيع.</i>

📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
        """.strip()
        
        # Email HTML
        email_content = f"""
        <html dir="rtl">
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background: #0a0a0a; color: #e5e5e5; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #1a1a1a; padding: 30px; border-radius: 12px; border: 1px solid #333; }}
                .header {{ text-align: center; padding-bottom: 20px; border-bottom: 1px solid #333; }}
                .header h1 {{ color: #f7931a; }}
                .content {{ padding: 20px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; padding-top: 20px; border-top: 1px solid #333; }}
                .highlight {{ color: #fbbf24; font-weight: bold; }}
                .positive {{ color: #34d399; }}
                .negative {{ color: #f87171; }}
                .divider {{ border: none; border-top: 1px solid #333; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⬡ LongTerm AI</h1>
                    <p style="color: #666;">بوت تحليل الاستثمار</p>
                </div>
                <div class="content">
                    <h2>📊 تنبيه سعر {symbol}</h2>
                    <p><span class="highlight">{emoji} {direction} {abs(change):.2f}%</span></p>
                    <p><strong>💰 السعر السابق:</strong> ${old_price:,.2f}</p>
                    <p><strong>💰 السعر الحالي:</strong> ${current_price:,.2f}</p>
                    <p><strong>📊 التغير:</strong> <span class="{'positive' if change > 0 else 'negative'}">{change:+.2f}%</span></p>
                    <hr class="divider">
                    <p style="color: #666; font-size: 14px;"><i>⚠️ هذا تنبيه سعر فقط. ليس توصية شراء أو بيع.</i></p>
                    <p style="color: #444; font-size: 12px;">📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                </div>
                <div class="footer"><p>🤖 تم إنشاؤه بواسطة LongTerm AI Bot</p></div>
            </div>
        </body>
        </html>
        """
        
        # Envoyer
        telegram_ok = await self.telegram.send_message(telegram_msg)
        email_ok = await self.email.send_email(f"📊 تنبيه سعر {symbol}", email_content)
        
        return telegram_ok or email_ok
    
    async def send_alert(self, analysis: Dict) -> bool:
        """Envoyer une alerte d'analyse en arabe avec détails"""
        asset = analysis.get('asset', 'Unknown')
        impact = analysis.get('impact', 'neutral')
        score = analysis.get('score', 0)
        reason = analysis.get('reason', '')
        original_text = analysis.get('original_text', '')
        time_horizon = analysis.get('time_horizon', 'medium_term')
        historical_comparison = analysis.get('historical_comparison', '')
        confidence = analysis.get('confidence', 'medium')
        
        # Récupérer les impacts détaillés par actif
        btc_impact = analysis.get('btc_impact', '')
        eth_impact = analysis.get('eth_impact', '')
        gold_impact = analysis.get('gold_impact', '')
        detailed_analysis = analysis.get('detailed_analysis', '')
        
        emoji = self._get_impact_emoji(impact)
        impact_ar = self._get_impact_ar(impact)
        horizon_ar = self._get_horizon_ar(time_horizon)
        
        confidence_ar = {
            "high": "عالية",
            "medium": "متوسطة",
            "low": "منخفضة"
        }.get(confidence, "متوسطة")
        
        # Construction du message détaillé
        detailed_msg = f"""
{emoji} <b>تنبيه مهم - {asset}</b>

📰 <b>الخبر:</b>
{original_text}

📊 <b>التحليل المفصل:</b>
{detailed_analysis if detailed_analysis else reason}

{'='*40}

📈 <b>تأثير الخبر على الأصول:</b>

🟠 <b>Bitcoin (BTC):</b>
{btc_impact if btc_impact else "تأثير إيجابي معتدل على Bitcoin مع زيادة الثقة المؤسسية"}

🔵 <b>Ethereum (ETH):</b>
{eth_impact if eth_impact else "تأثير إيجابي معتدل على Ethereum مع تحسن المعنويات"}

🟡 <b>Gold (XAU):</b>
{gold_impact if gold_impact else "تأثير محايد على Gold"}

{'='*40}

📊 <b>التقييم العام:</b>
• التأثير: {impact_ar} (التقييم: {score}/10)
• الأفق الزمني: {horizon_ar}
• الثقة: {confidence_ar}

📜 <b>المقارنة التاريخية:</b>
{historical_comparison if historical_comparison else "لا توجد مقارنة تاريخية متاحة"}

🎯 <b>هل يغير الاستراتيجية؟</b>
{'✅ نعم، قد يتطلب إعادة تقييم' if analysis.get('change_investment_strategy') else '❌ لا، لا يغير الاستراتيجية الحالية'}

⚠️ <b>تنبيه مهم:</b> هذا تحليل استثماري مبني على البيانات المتاحة. الأسواق متقلبة وقد تتغير الظروف.

📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
        """.strip()
        
        # Email HTML
        email_content = f"""
        <html dir="rtl">
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background: #0a0a0a; color: #e5e5e5; padding: 20px; }}
                .container {{ max-width: 700px; margin: 0 auto; background: #1a1a1a; padding: 30px; border-radius: 12px; border: 1px solid #333; }}
                .header {{ text-align: center; padding-bottom: 20px; border-bottom: 1px solid #333; }}
                .header h1 {{ color: #f7931a; }}
                .content {{ padding: 20px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; padding-top: 20px; border-top: 1px solid #333; }}
                .highlight {{ color: #fbbf24; font-weight: bold; }}
                .positive {{ background: #064e3b; color: #34d399; padding: 2px 12px; border-radius: 12px; }}
                .negative {{ background: #4a1a1a; color: #f87171; padding: 2px 12px; border-radius: 12px; }}
                .neutral {{ background: #1e3a5f; color: #60a5fa; padding: 2px 12px; border-radius: 12px; }}
                .divider {{ border: none; border-top: 1px solid #333; margin: 15px 0; }}
                .box {{ background: #0a0a0a; padding: 12px; border-radius: 8px; border: 1px solid #222; margin: 8px 0; }}
                .impact-box {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-weight: bold; }}
                .impact-box.positive {{ background: #064e3b; color: #34d399; }}
                .impact-box.negative {{ background: #4a1a1a; color: #f87171; }}
                .impact-box.neutral {{ background: #1e3a5f; color: #60a5fa; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⬡ LongTerm AI</h1>
                    <p style="color: #666;">بوت تحليل الاستثمار</p>
                </div>
                <div class="content">
                    <h2>{emoji} تنبيه مهم - {asset}</h2>
                    
                    <div class="box">
                        <p><strong>📰 الخبر:</strong></p>
                        <p>{original_text}</p>
                    </div>
                    
                    <div class="box">
                        <p><strong>📊 التحليل المفصل:</strong></p>
                        <p>{detailed_analysis if detailed_analysis else reason}</p>
                    </div>
                    
                    <hr class="divider">
                    
                    <h3>📈 تأثير الخبر على الأصول</h3>
                    
                    <div class="box">
                        <p><strong>🟠 Bitcoin (BTC):</strong></p>
                        <p>{btc_impact if btc_impact else "تأثير إيجابي معتدل على Bitcoin مع زيادة الثقة المؤسسية"}</p>
                    </div>
                    
                    <div class="box">
                        <p><strong>🔵 Ethereum (ETH):</strong></p>
                        <p>{eth_impact if eth_impact else "تأثير إيجابي معتدل على Ethereum مع تحسن المعنويات"}</p>
                    </div>
                    
                    <div class="box">
                        <p><strong>🟡 Gold (XAU):</strong></p>
                        <p>{gold_impact if gold_impact else "تأثير محايد على Gold"}</p>
                    </div>
                    
                    <hr class="divider">
                    
                    <h3>📊 التقييم العام</h3>
                    <p><strong>التأثير:</strong> <span class="impact-box {impact}">{impact_ar}</span></p>
                    <p><strong>التقييم:</strong> <span class="highlight">{score}/10</span></p>
                    <p><strong>الأفق الزمني:</strong> {horizon_ar}</p>
                    <p><strong>الثقة:</strong> <span class="highlight">{confidence_ar}</span></p>
                    
                    <div class="box">
                        <p><strong>📜 المقارنة التاريخية:</strong></p>
                        <p>{historical_comparison if historical_comparison else "لا توجد مقارنة تاريخية متاحة"}</p>
                    </div>
                    
                    <p><strong>🎯 هل يغير الاستراتيجية؟</strong><br>
                    {'🔄 نعم، قد يتطلب إعادة تقييم' if analysis.get('change_investment_strategy') else '✅ لا، لا يغير الاستراتيجية الحالية'}</p>
                    
                    <hr class="divider">
                    
                    <p style="color: #666; font-size: 14px;">
                        <i>⚠️ هذا تحليل استثماري مبني على البيانات المتاحة.<br>الأسواق متقلبة وقد تتغير الظروف.</i>
                    </p>
                    
                    <p style="color: #444; font-size: 12px;">
                        📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
                    </p>
                </div>
                <div class="footer">
                    <p>🤖 تم إنشاؤه بواسطة LongTerm AI Bot</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Envoyer
        telegram_ok = await self.telegram.send_message(detailed_msg)
        email_ok = await self.email.send_email(f"{emoji} تنبيه مهم - {asset}", email_content)
        
        return telegram_ok or email_ok
    
    async def send_weekly_report(self, report: Dict) -> bool:
        """Envoyer le rapport hebdomadaire détaillé en arabe avec portefeuille"""
        assets = report.get("assets", {})
        summary = report.get("summary", {})
        
        # === RÉCUPÉRER LE PORTEFEUILLE ===
        from app.services.portfolio_service import PortfolioService
        portfolio = PortfolioService()
        portfolio_summary = portfolio.get_portfolio_summary()
        
        # === MESSAGE TELEGRAM ===
        telegram_msg = f"""
📊 <b>التقرير الأسبوعي</b>
📅 {datetime.now().strftime('%d/%m/%Y')}

📈 <b>ملخص الأسواق</b>
• التغير الإجمالي: {summary.get('avg_change', 0):+.2f}%
• أفضل أداء: {summary.get('best_performer', 'N/A')}
• أسوأ أداء: {summary.get('worst_performer', 'N/A')}
• الاتجاه العام: {'🟢 إيجابي' if summary.get('overall_sentiment') == 'positive' else '🔴 سلبي' if summary.get('overall_sentiment') == 'negative' else '🟡 محايد'}

{'='*30}

📊 <b>أداء الأصول</b>

"""
        
        for symbol, data in assets.items():
            if "error" in data:
                continue
            
            change = data.get('change_7d', 0)
            emoji = "🚀" if change > 10 else "📈" if change > 5 else "📊" if change > 0 else "📉" if change > -5 else "📉"
            performance_ar = {
                "excellent": "ممتاز",
                "good": "جيد",
                "stable": "مستقر",
                "weak": "ضعيف"
            }.get(data.get('performance', 'stable'), "مستقر")
            
            max_date = data.get('max_date', '')[:10] if data.get('max_date') else 'N/A'
            min_date = data.get('min_date', '')[:10] if data.get('min_date') else 'N/A'
            
            telegram_msg += f"""
<b>{symbol}</b> {emoji}
━━━━━━━━━━━━━━━━━━━━
💰 <b>الافتتاح:</b> ${data.get('start_price', 0):,.2f}
💰 <b>الإغلاق:</b> ${data.get('end_price', 0):,.2f}
📊 <b>التغير:</b> {change:+.2f}%

📈 <b>القيمة الأعلى:</b> ${data.get('max_price', 0):,.2f}
   📅 التاريخ: {max_date}

📉 <b>القيمة الأدنى:</b> ${data.get('min_price', 0):,.2f}
   📅 التاريخ: {min_date}

📊 <b>المعدل:</b> ${data.get('avg_price', 0):,.2f}
🏆 <b>الأداء:</b> {performance_ar}

📋 <b>التغيرات اليومية:</b>
"""
            for daily in data.get('daily_prices', [])[:7]:
                day_change = daily.get('change', 0)
                day_emoji = "📈" if day_change > 0 else "📉" if day_change < 0 else "➡️"
                telegram_msg += f"   • {daily.get('date', '')}: ${daily.get('price', 0):,.2f} {day_emoji} {day_change:+.2f}%\n"
            
            telegram_msg += "\n"
        
        # === SECTION PORTEFEUILLE ===
        if portfolio_summary:
            total_invested = portfolio_summary.get('total_invested_tnd', 0)
            total_current = portfolio_summary.get('total_current_usd', 0)
            total_profit = portfolio_summary.get('total_profit_tnd', 0)
            roi = portfolio_summary.get('roi_percent', 0)
            
            telegram_msg += f"""
{'='*30}
💰 <b>ملخص المحفظة</b>
• إجمالي المستثمر: {total_invested:,.2f} TND
• القيمة الحالية: {total_current:,.2f} USD
• الربح/الخسارة: {total_profit:+.2f} TND
• العائد على الاستثمار: {roi:+.2f}%

📊 <b>تفاصيل المحفظة</b>
"""
            
            for asset, data in portfolio_summary.get('assets', {}).items():
                profit = data.get('profit_tnd', 0)
                roi_asset = data.get('roi_percent', 0)
                emoji_asset = "✅" if profit >= 0 else "❌"
                
                telegram_msg += f"""
{emoji_asset} <b>{asset}</b>
   الكمية: {data.get('quantity', 0):.8f}
   المستثمر: {data.get('invested_tnd', 0):,.2f} TND
   القيمة: ${data.get('current_value_usd', 0):,.2f}
   الربح: {profit:+.2f} TND ({roi_asset:+.2f}%)
"""
            
            # Meilleur et pire performeur du portefeuille
            best_asset = None
            worst_asset = None
            best_roi = -100
            worst_roi = 100
            
            for asset, data in portfolio_summary.get('assets', {}).items():
                roi_asset = data.get('roi_percent', 0)
                if roi_asset > best_roi:
                    best_roi = roi_asset
                    best_asset = asset
                if roi_asset < worst_roi:
                    worst_roi = roi_asset
                    worst_asset = asset
            
            if best_asset:
                telegram_msg += f"""
🏆 <b>أفضل أداء في المحفظة:</b> {best_asset} ({best_roi:+.2f}%)
📉 <b>أسوأ أداء في المحفظة:</b> {worst_asset} ({worst_roi:+.2f}%)
"""
        
        telegram_msg += f"""
{'='*30}
📊 <b>تحليل الأسبوع</b>
• {'الأسواق في اتجاه صاعد' if summary.get('overall_sentiment') == 'positive' else 'الأسواق في اتجاه هابط' if summary.get('overall_sentiment') == 'negative' else 'الأسواق في حالة استقرار'}
• أفضل أسبوع كان لـ {summary.get('best_performer', 'N/A')}
• {summary.get('worst_performer', 'N/A')} سجل أضعف أداء

⚠️ <i>هذا تقرير تحليلي، وليس توصية استثمارية.</i>
🤖 تم إنشاؤه بواسطة LongTerm AI Bot
        """.strip()
        
        # Envoyer Telegram
        telegram_ok = await self.telegram.send_message(telegram_msg)
        
        # === EMAIL (SendGrid) ===
        email_content = f"""
        <html dir="rtl">
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background: #0a0a0a; color: #e5e5e5; padding: 20px; }}
                .container {{ max-width: 800px; margin: 0 auto; background: #1a1a1a; padding: 30px; border-radius: 12px; border: 1px solid #333; }}
                .header {{ text-align: center; padding-bottom: 20px; border-bottom: 1px solid #333; }}
                .header h1 {{ color: #f7931a; }}
                .content {{ padding: 20px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; padding-top: 20px; border-top: 1px solid #333; }}
                .highlight {{ color: #fbbf24; font-weight: bold; }}
                .positive {{ color: #34d399; }}
                .negative {{ color: #f87171; }}
                .divider {{ border: none; border-top: 1px solid #333; margin: 15px 0; }}
                .asset-card {{ background: #0a0a0a; padding: 15px; border-radius: 8px; border: 1px solid #222; margin: 10px 0; }}
                .asset-title {{ font-size: 18px; font-weight: bold; color: #f7931a; }}
                .row {{ display: flex; justify-content: space-between; padding: 4px 0; }}
                .box {{ background: #0a0a0a; padding: 12px; border-radius: 8px; border: 1px solid #222; margin: 8px 0; }}
                .portfolio-card {{ background: #0a0a0a; padding: 15px; border-radius: 8px; border: 1px solid #222; margin: 10px 0; }}
                .portfolio-title {{ font-size: 16px; font-weight: bold; color: #34d399; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⬡ LongTerm AI</h1>
                    <p style="color: #666;">التقرير الأسبوعي - {datetime.now().strftime('%d/%m/%Y')}</p>
                </div>
                <div class="content">
                    <h2>📊 ملخص الأسواق</h2>
                    <div class="box">
                        <div class="row"><span>📈 التغير الإجمالي:</span> <span class="{'positive' if summary.get('avg_change', 0) > 0 else 'negative'}">{summary.get('avg_change', 0):+.2f}%</span></div>
                        <div class="row"><span>🏆 أفضل أداء:</span> <span class="highlight">{summary.get('best_performer', 'N/A')}</span></div>
                        <div class="row"><span>📉 أسوأ أداء:</span> <span>{summary.get('worst_performer', 'N/A')}</span></div>
                        <div class="row"><span>📊 الاتجاه العام:</span> <span>{'🟢 إيجابي' if summary.get('overall_sentiment') == 'positive' else '🔴 سلبي' if summary.get('overall_sentiment') == 'negative' else '🟡 محايد'}</span></div>
                    </div>
        """
        
        # Ajouter chaque actif
        for symbol, data in assets.items():
            if "error" in data:
                continue
            
            change = data.get('change_7d', 0)
            performance_ar = {
                "excellent": "ممتاز",
                "good": "جيد",
                "stable": "مستقر",
                "weak": "ضعيف"
            }.get(data.get('performance', 'stable'), "مستقر")
            
            max_date = data.get('max_date', '')[:10] if data.get('max_date') else 'N/A'
            min_date = data.get('min_date', '')[:10] if data.get('min_date') else 'N/A'
            
            email_content += f"""
                <div class="asset-card">
                    <div class="asset-title">{symbol}</div>
                    <div class="row"><span>💰 الافتتاح:</span> <span>${data.get('start_price', 0):,.2f}</span></div>
                    <div class="row"><span>💰 الإغلاق:</span> <span>${data.get('end_price', 0):,.2f}</span></div>
                    <div class="row"><span>📊 التغير:</span> <span class="{'positive' if change > 0 else 'negative'}">{change:+.2f}%</span></div>
                    <div class="row"><span>📈 الأعلى:</span> <span>${data.get('max_price', 0):,.2f} <span style="color:#666;">({max_date})</span></span></div>
                    <div class="row"><span>📉 الأدنى:</span> <span>${data.get('min_price', 0):,.2f} <span style="color:#666;">({min_date})</span></span></div>
                    <div class="row"><span>🏆 الأداء:</span> <span class="highlight">{performance_ar}</span></div>
                </div>
        """
        
        # Section Portefeuille
        if portfolio_summary:
            total_invested = portfolio_summary.get('total_invested_tnd', 0)
            total_current = portfolio_summary.get('total_current_usd', 0)
            total_profit = portfolio_summary.get('total_profit_tnd', 0)
            roi = portfolio_summary.get('roi_percent', 0)
            
            email_content += f"""
                <hr class="divider">
                <h2>💰 ملخص المحفظة</h2>
                <div class="box">
                    <div class="row"><span>إجمالي المستثمر:</span> <span class="highlight">{total_invested:,.2f} TND</span></div>
                    <div class="row"><span>القيمة الحالية:</span> <span class="highlight">{total_current:,.2f} USD</span></div>
                    <div class="row"><span>الربح/الخسارة:</span> <span class="{'positive' if total_profit >= 0 else 'negative'}">{total_profit:+.2f} TND</span></div>
                    <div class="row"><span>العائد على الاستثمار:</span> <span class="{'positive' if roi >= 0 else 'negative'}">{roi:+.2f}%</span></div>
                </div>
                
                <h3>📊 تفاصيل المحفظة</h3>
        """
            
            for asset, data in portfolio_summary.get('assets', {}).items():
                profit = data.get('profit_tnd', 0)
                roi_asset = data.get('roi_percent', 0)
                emoji_asset = "✅" if profit >= 0 else "❌"
                
                email_content += f"""
                <div class="portfolio-card">
                    <div class="portfolio-title">{emoji_asset} {asset}</div>
                    <div class="row"><span>الكمية:</span> <span>{data.get('quantity', 0):.8f}</span></div>
                    <div class="row"><span>المستثمر:</span> <span>{data.get('invested_tnd', 0):,.2f} TND</span></div>
                    <div class="row"><span>القيمة:</span> <span>${data.get('current_value_usd', 0):,.2f}</span></div>
                    <div class="row"><span>الربح:</span> <span class="{'positive' if profit >= 0 else 'negative'}">{profit:+.2f} TND ({roi_asset:+.2f}%)</span></div>
                </div>
            """
            
            # Meilleur et pire performeur
            best_asset = None
            worst_asset = None
            best_roi = -100
            worst_roi = 100
            
            for asset, data in portfolio_summary.get('assets', {}).items():
                roi_asset = data.get('roi_percent', 0)
                if roi_asset > best_roi:
                    best_roi = roi_asset
                    best_asset = asset
                if roi_asset < worst_roi:
                    worst_roi = roi_asset
                    worst_asset = asset
            
            if best_asset:
                email_content += f"""
                <div class="box">
                    <div class="row"><span>🏆 أفضل أداء في المحفظة:</span> <span class="highlight">{best_asset} ({best_roi:+.2f}%)</span></div>
                    <div class="row"><span>📉 أسوأ أداء في المحفظة:</span> <span class="negative">{worst_asset} ({worst_roi:+.2f}%)</span></div>
                </div>
            """
        
        email_content += f"""
                <hr class="divider">
                <p style="color: #666; font-size: 14px;">
                    <i>⚠️ هذا تقرير تحليلي، وليس توصية استثمارية.</i>
                </p>
            </div>
            <div class="footer">
                <p>🤖 تم إنشاؤه بواسطة LongTerm AI Bot</p>
            </div>
        </div>
    </body>
    </html>
    """
        
        email_ok = await self.email.send_email(f"📊 التقرير الأسبوعي - {datetime.now().strftime('%d/%m/%Y')}", email_content)
        
        return telegram_ok or email_ok
    
    async def send_test(self) -> bool:
        """Envoyer un test en arabe"""
        test_msg = f"""
🔔 <b>اختبار التنبيه</b>

✅ تم تهيئة بوت LongTerm AI بنجاح !

📅 تم الاختبار في: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🤖 الإصدار: v3.0

💡 ستتلقى الآن :
   • تنبيهات الأسعار
   • تحليلات الأخبار المهمة
   • تقارير أسبوعية
        """.strip()
        
        telegram_ok = await self.telegram.send_message(test_msg)
        email_ok = await self.email.send_test_email()
        
        return telegram_ok or email_ok
    
    def get_status(self) -> Dict:
        return {
            "telegram": {
                "enabled": self.telegram.enabled,
                "configured": bool(self.telegram.bot_token)
            },
            "sendgrid": {
                "enabled": self.email.enabled,
                "configured": bool(self.email.api_key)
            }
        }