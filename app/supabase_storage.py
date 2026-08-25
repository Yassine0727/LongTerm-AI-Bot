# app/supabase_storage.py
from supabase import create_client, Client
import os
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class SupabaseStorage:
    def __init__(self):
        # Récupérer les variables d'environnement
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')  # La SECRET KEY
        
        self.supabase = None
        self.connected = False
        
        if not self.url:
            logger.error("❌ SUPABASE_URL non configuré")
            return
        
        if not self.key:
            logger.error("❌ SUPABASE_KEY non configuré")
            logger.info("   Utilisez la SECRET KEY (sb_secret_...) pas la publishable")
            return
        
        try:
            # Nettoyer la clé (supprimer les espaces et retours à la ligne)
            self.key = self.key.strip()
            
            # Créer le client
            self.supabase = create_client(self.url, self.key)
            self.connected = True
            logger.info("✅ Supabase connecté avec la SECRET KEY")
            
            # Tester la connexion
            test = self.supabase.table('analyses').select('count').limit(1).execute()
            logger.info("✅ Test de connexion Supabase réussi")
            
        except Exception as e:
            logger.error(f"❌ Erreur connexion Supabase: {e}")
            logger.info("   Vérifiez que la clé est correcte et que RLS est configuré")
    
    def save_analysis(self, analysis_data):
        """Sauvegarde une analyse dans Supabase"""
        try:
            if not self.connected:
                logger.error("❌ Supabase non connecté")
                return False
            
            # Préparer les données
            data = {
                'id': analysis_data.get('id', f"analysis_{datetime.now().timestamp()}"),
                'timestamp': analysis_data.get('timestamp', datetime.now().isoformat()),
                'asset': analysis_data.get('asset', 'UNKNOWN'),
                'impact': analysis_data.get('impact', 'neutral'),
                'score': analysis_data.get('score', 0),
                'summary': analysis_data.get('summary', ''),
                'analysis': analysis_data.get('analysis', {}),
                'message_id': analysis_data.get('message_id', ''),
                'source': 'telegram'
            }
            
            # Insérer dans Supabase
            result = self.supabase.table('analyses').insert(data).execute()
            
            if result.data:
                logger.info(f"✅ Analyse sauvegardée dans Supabase: {result.data[0]['id']}")
                
                # Incrémenter les stats
                try:
                    # Récupérer les stats actuelles
                    stats_result = self.supabase.table('stats').select('*').eq('key', 'total_analyses').execute()
                    
                    if stats_result.data:
                        current = stats_result.data[0]['value']
                        self.supabase.table('stats').update({
                            'value': current + 1,
                            'updated_at': datetime.now().isoformat()
                        }).eq('key', 'total_analyses').execute()
                    else:
                        self.supabase.table('stats').insert({
                            'key': 'total_analyses',
                            'value': 1,
                            'updated_at': datetime.now().isoformat()
                        }).execute()
                except Exception as e:
                    logger.error(f"❌ Erreur mise à jour stats: {e}")
                
                return True
            else:
                logger.error(f"❌ Erreur sauvegarde: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde Supabase: {e}")
            return False
    
    def save_stats(self, stats_data):
        """Sauvegarde les statistiques personnalisées"""
        try:
            if not self.connected:
                return False
            
            for key, value in stats_data.items():
                result = self.supabase.table('stats').upsert({
                    'key': key,
                    'value': value,
                    'updated_at': datetime.now().isoformat()
                }).execute()
            
            logger.info("✅ Stats sauvegardées")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde stats: {e}")
            return False
    
    def get_analyses(self, limit=20, offset=0):
        """Récupère les dernières analyses"""
        try:
            if not self.connected:
                return []
            
            result = self.supabase.table('analyses')\
                .select('*')\
                .order('timestamp', desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération analyses: {e}")
            return []
    
    def get_analyses_by_asset(self, asset, limit=20):
        """Récupère les analyses par actif"""
        try:
            if not self.connected:
                return []
            
            result = self.supabase.table('analyses')\
                .select('*')\
                .eq('asset', asset)\
                .order('timestamp', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return []
    
    def get_stats(self):
        """Récupère toutes les statistiques"""
        try:
            if not self.connected:
                return {}
            
            result = self.supabase.table('stats').select('*').execute()
            
            if result.data:
                return {item['key']: item['value'] for item in result.data}
            return {}
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération stats: {e}")
            return {}
    
    def get_total_count(self):
        """Récupère le nombre total d'analyses"""
        try:
            if not self.connected:
                return 0
            
            result = self.supabase.table('analyses').select('id', count='exact').execute()
            return result.count if hasattr(result, 'count') else 0
            
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return 0
