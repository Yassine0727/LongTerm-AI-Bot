import sendgrid
import logging
from sendgrid.helpers.mail import Mail
from datetime import datetime
from typing import List, Dict

from app.core.config import config

logger = logging.getLogger(__name__)

class SendGridService:
    """Service d'envoi d'emails via SendGrid"""
    
    def __init__(self):
        self.enabled = config.SENDGRID_ENABLED if hasattr(config, 'SENDGRID_ENABLED') else False
        self.api_key = config.SENDGRID_API_KEY if hasattr(config, 'SENDGRID_API_KEY') else ""
        self.from_email = config.SENDGRID_FROM_EMAIL if hasattr(config, 'SENDGRID_FROM_EMAIL') else ""
        self.to_emails = []
        
        if hasattr(config, 'SENDGRID_TO_EMAIL') and config.SENDGRID_TO_EMAIL:
            self.to_emails.append(config.SENDGRID_TO_EMAIL)
        if hasattr(config, 'SENDGRID_TO_EMAIL_2') and config.SENDGRID_TO_EMAIL_2:
            self.to_emails.append(config.SENDGRID_TO_EMAIL_2)
    
    async def send_email(self, subject: str, content: str) -> bool:
        """Envoyer un email via SendGrid"""
        if not self.enabled:
            logger.info("📧 SendGrid desactive")
            return False
        
        if not self.api_key:
            logger.error("❌ SendGrid API key manquante")
            return False
        
        if not self.to_emails:
            logger.error("❌ Aucun destinataire SendGrid configure")
            return False
        
        try:
            sg = sendgrid.SendGridAPIClient(api_key=self.api_key)
            
            for to_email in self.to_emails:
                mail = Mail(
                    from_email=self.from_email,
                    to_emails=to_email,
                    subject=subject,
                    html_content=content
                )
                response = sg.send(mail)
                
                if response.status_code == 202:
                    logger.info(f"✅ Email envoyé à {to_email}")
                else:
                    logger.error(f"❌ Erreur SendGrid: {response.status_code}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur SendGrid: {e}")
            return False
    
    async def send_alert_email(self, analysis: Dict) -> bool:
        """Envoyer un email d'alerte"""
        asset = analysis.get('asset', 'Unknown')
        impact = analysis.get('impact', 'neutral')
        score = analysis.get('score', 0)
        reason = analysis.get('reason', '')
        time_horizon = analysis.get('time_horizon', 'medium_term')
        
        emoji = "🟢" if impact == "positive" else "🔴" if impact == "negative" else "🟡"
        
        subject = f"{emoji} ALERTE - {asset} - Score: {score}/10"
        
        content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background: #0a0a0a; color: #e5e5e5; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #1a1a1a; padding: 30px; border-radius: 12px; border: 1px solid #333; }}
                .header {{ text-align: center; padding-bottom: 20px; border-bottom: 1px solid #333; }}
                .header h1 {{ color: #f7931a; }}
                .content {{ padding: 20px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; padding-top: 20px; border-top: 1px solid #333; }}
                .badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-weight: bold; }}
                .badge.positive {{ background: #064e3b; color: #34d399; }}
                .badge.negative {{ background: #4a1a1a; color: #f87171; }}
                .badge.neutral {{ background: #1e3a5f; color: #60a5fa; }}
                .divider {{ border: none; border-top: 1px solid #333; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⬡ LongTerm AI</h1>
                    <p style="color: #666;">Investment Analysis Bot</p>
                </div>
                <div class="content">
                    <h2>🔔 ALERTE IMPORTANTE</h2>
                    
                    <p><strong>Actif:</strong> {asset}</p>
                    <p><strong>Impact:</strong> <span class="badge {impact}">{impact.upper()}</span></p>
                    <p><strong>Score:</strong> {score}/10</p>
                    <p><strong>Horizon:</strong> {time_horizon.replace('_', ' ')}</p>
                    
                    <hr class="divider">
                    
                    <h3>📰 Résumé</h3>
                    <p>{analysis.get('original_text', '')}</p>
                    
                    <h3>💡 Pourquoi c'est important</h3>
                    <p>{reason}</p>
                    
                    <h3>📊 Comparaison historique</h3>
                    <p>{analysis.get('historical_comparison', 'Aucune donnée')}</p>
                    
                    <hr class="divider">
                    
                    <p style="color: #666; font-size: 14px;">
                        <strong>Confiance:</strong> {analysis.get('confidence', 'medium').upper()}<br>
                        <strong>Changement stratégique:</strong> {'✅ OUI' if analysis.get('change_investment_strategy') else '❌ NON'}
                    </p>
                </div>
                <div class="footer">
                    <p>🤖 Généré par LongTerm AI Bot</p>
                    <p style="color: #444;">⚠️ Ceci est une analyse, pas une prédiction.</p>
                    <p style="color: #444;">📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(subject, content)
    
    async def send_weekly_report_email(self, report: Dict) -> bool:
        """Envoyer le rapport hebdomadaire par email"""
        subject = f"📊 Rapport Hebdomadaire - {datetime.now().strftime('%d/%m/%Y')}"
        
        content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background: #0a0a0a; color: #e5e5e5; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #1a1a1a; padding: 30px; border-radius: 12px; border: 1px solid #333; }}
                .header {{ text-align: center; padding-bottom: 20px; border-bottom: 1px solid #333; }}
                .header h1 {{ color: #f7931a; }}
                .content {{ padding: 20px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; padding-top: 20px; border-top: 1px solid #333; }}
                .divider {{ border: none; border-top: 1px solid #333; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⬡ LongTerm AI</h1>
                    <p style="color: #666;">Investment Analysis Bot</p>
                </div>
                <div class="content">
                    <h2>📊 RAPPORT HEBDOMADAIRE</h2>
                    <p style="color: #666;">{datetime.now().strftime('%d/%m/%Y')}</p>
                    
                    <hr class="divider">
        """
        
        for symbol, data in report.get("assets", {}).items():
            if "error" in data:
                continue
            
            change = data.get('change_7d', 0)
            emoji = "✅" if change > 0 else "❌" if change < 0 else "⚪"
            
            content += f"""
                    <h3>{symbol}</h3>
                    <ul>
                        <li>Début: ${data.get('start_price', 0):,.2f}</li>
                        <li>Actuel: ${data.get('end_price', 0):,.2f}</li>
                        <li>Variation: {change:+.2f}% {emoji}</li>
                        <li>📈 Max: ${data.get('max_price', 0):,.2f}</li>
                        <li>📉 Min: ${data.get('min_price', 0):,.2f}</li>
                    </ul>
                    <hr class="divider">
            """
        
        content += """
                </div>
                <div class="footer">
                    <p>🤖 Généré par LongTerm AI Bot</p>
                    <p style="color: #444;">⚠️ Ce rapport est une analyse, pas une prédiction.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(subject, content)
    
    async def send_test_email(self) -> bool:
        """Envoyer un email de test"""
        subject = "🔔 TEST - LongTerm AI Bot"
        
        content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background: #0a0a0a; color: #e5e5e5; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #1a1a1a; padding: 30px; border-radius: 12px; border: 1px solid #333; }}
                .header {{ text-align: center; padding-bottom: 20px; border-bottom: 1px solid #333; }}
                .header h1 {{ color: #f7931a; }}
                .content {{ padding: 20px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; padding-top: 20px; border-top: 1px solid #333; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⬡ LongTerm AI</h1>
                    <p style="color: #666;">Investment Analysis Bot</p>
                </div>
                <div class="content">
                    <h2>🔔 TEST DE NOTIFICATION</h2>
                    
                    <p>✅ Votre bot LongTerm AI est configuré avec SendGrid !</p>
                    
                    <p>📅 Test effectué à: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                    
                    <hr style="border: none; border-top: 1px solid #333; margin: 15px 0;">
                    
                    <p style="color: #666; font-size: 14px;">
                        💡 Vous recevrez désormais :<br>
                        • Alertes de prix<br>
                        • Analyses importantes<br>
                        • Rapports hebdomadaires
                    </p>
                </div>
                <div class="footer">
                    <p>🤖 LongTerm AI Bot v3.0</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(subject, content)