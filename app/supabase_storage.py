# app/supabase_storage.py
import os
import requests
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SupabaseStorage:
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        self.connected = False
        
        if not self.url or not self.key:
            logger.warning("⚠️ SUPABASE_URL ou SUPABASE_KEY non configuré")
            return
        
        try:
            self.headers = {
                'apikey': self.key,
                'Authorization': f'Bearer {self.key}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
            
            # Tester la connexion
            test_url = f"{self.url}/rest/v1/stats?limit=1"
            response = requests.get(test_url, headers=self.headers, timeout=5)
            
            if response.status_code in [200, 404]:
                self.connected = True
                logger.info("✅ Supabase connecté (via REST API)")
            else:
                logger.warning(f"⚠️ Erreur connexion Supabase: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"⚠️ Erreur connexion Supabase: {e}")
    
    def _request(self, method, endpoint, data=None):
        """Fait une requête à l'API Supabase"""
        try:
            url = f"{self.url}/rest/v1/{endpoint}"
            response = requests.request(method, url, headers=self.headers, json=data, timeout=10)
            
            if response.status_code in [200, 201]:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.error(f"❌ Erreur Supabase: {response.status_code} - {response.text[:100]}")
                return None
        except Exception as e:
            logger.error(f"❌ Erreur requête: {e}")
            return None
    
    def _update_stats(self, key, increment=1):
        """Incrémente une statistique dans Supabase"""
        try:
            if not self.connected:
                return False
            
            # Vérifier si la stat existe
            result = self._request('GET', f'stats?key=eq.{key}')
            
            if result and len(result) > 0:
                # Mettre à jour
                current = result[0].get('value', 0)
                new_value = current + increment
                update_result = self._request('PATCH', f'stats?key=eq.{key}', {'value': new_value})
                if update_result:
                    logger.info(f"📊 Stat {key} mise à jour: {current} → {new_value}")
                    return True
            else:
                # Créer la stat
                create_result = self._request('POST', 'stats', {'key': key, 'value': increment})
                if create_result:
                    logger.info(f"📊 Stat {key} créée avec la valeur {increment}")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"❌ Erreur mise à jour stats: {e}")
            return False
    
    def save_analysis(self, analysis_data):
        """Sauvegarde une analyse dans Supabase et met à jour les stats"""
        if not self.connected:
            logger.warning("⚠️ Supabase non connecté, analyse non sauvegardée")
            return False
        
        try:
            # Préparer les données
            data = {
                'id': analysis_data.get('id', f"analysis_{int(datetime.now().timestamp())}"),
                'timestamp': analysis_data.get('timestamp', datetime.now().isoformat()),
                'asset': analysis_data.get('asset', 'UNKNOWN'),
                'impact': analysis_data.get('impact', 'neutral'),
                'score': analysis_data.get('score', 0),
                'summary': analysis_data.get('summary', ''),
                'analysis': json.dumps(analysis_data.get('analysis', {})),
                'message_id': analysis_data.get('message_id', '')
            }
            
            # Insérer l'analyse
            result = self._request('POST', 'analyses', data)
            
            if result:
                logger.info(f"✅ Analyse sauvegardée dans Supabase (ID: {data['id']})")
                
                # === METTRE À JOUR LES STATISTIQUES ===
                # 1. Incrémenter le total des analyses
                self._update_stats('total_analyses', 1)
                
                # 2. Si score >= 7, incrémenter les alertes
                if data.get('score', 0) >= 7:
                    self._update_stats('total_alerts', 1)
                
                return True
            else:
                logger.error("❌ Échec de l'insertion de l'analyse")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde: {e}")
            return False
    
    def save_stats(self, stats_data):
        """Sauvegarde les statistiques personnalisées"""
        if not self.connected:
            return False
        
        try:
            for key, value in stats_data.items():
                # Vérifier si la stat existe
                result = self._request('GET', f'stats?key=eq.{key}')
                
                if result and len(result) > 0:
                    # Mettre à jour
                    self._request('PATCH', f'stats?key=eq.{key}', {'value': value})
                else:
                    # Créer
                    self._request('POST', 'stats', {'key': key, 'value': value})
            
            logger.info(f"✅ Stats sauvegardées: {stats_data}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde stats: {e}")
            return False
    
    def get_analyses(self, limit=20, offset=0):
        """Récupère les dernières analyses"""
        if not self.connected:
            return []
        
        try:
            endpoint = f"analyses?order=timestamp.desc&limit={limit}&offset={offset}"
            result = self._request('GET', endpoint)
            return result if result else []
        except Exception as e:
            logger.error(f"❌ Erreur récupération analyses: {e}")
            return []
    
    def get_analyses_by_asset(self, asset, limit=20):
        """Récupère les analyses par actif"""
        if not self.connected:
            return []
        
        try:
            endpoint = f"analyses?asset=eq.{asset}&order=timestamp.desc&limit={limit}"
            result = self._request('GET', endpoint)
            return result if result else []
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return []
    
    def get_stats(self):
        """Récupère toutes les statistiques"""
        if not self.connected:
            return {}
        
        try:
            result = self._request('GET', 'stats')
            if result:
                stats = {}
                for item in result:
                    stats[item['key']] = item['value']
                logger.info(f"📊 Stats récupérées: {stats}")
                return stats
            return {}
        except Exception as e:
            logger.error(f"❌ Erreur récupération stats: {e}")
            return {}
    
    def get_total_count(self):
        """Récupère le nombre total d'analyses"""
        if not self.connected:
            return 0
        
        try:
            result = self._request('GET', 'analyses?select=id')
            return len(result) if result else 0
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return 0
    
    def get_stats_by_key(self, key):
        """Récupère une statistique spécifique"""
        if not self.connected:
            return 0
        
        try:
            result = self._request('GET', f'stats?key=eq.{key}')
            if result and len(result) > 0:
                return result[0].get('value', 0)
            return 0
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return 0
    
    def reset_stats(self):
        """Réinitialise toutes les statistiques à 0"""
        if not self.connected:
            return False
        
        try:
            stats_keys = ['total_analyses', 'total_alerts', 'total_reports']
            for key in stats_keys:
                result = self._request('GET', f'stats?key=eq.{key}')
                if result and len(result) > 0:
                    self._request('PATCH', f'stats?key=eq.{key}', {'value': 0})
                else:
                    self._request('POST', 'stats', {'key': key, 'value': 0})
            
            logger.info("✅ Statistiques réinitialisées")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur réinitialisation: {e}")
            return False
