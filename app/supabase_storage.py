# app/supabase_storage.py - Version avec requests uniquement
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
        
        self.headers = {
            'apikey': self.key,
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        
        try:
            # Tester la connexion
            test_url = f"{self.url}/rest/v1/stats?limit=1"
            response = requests.get(test_url, headers=self.headers, timeout=5)
            self.connected = True
            logger.info("✅ Supabase connecté (via REST API)")
        except Exception as e:
            logger.warning(f"⚠️ Supabase non disponible: {e}")
    
    def _request(self, method, endpoint, data=None):
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
    
    def save_analysis(self, analysis_data):
        if not self.connected:
            return False
        
        try:
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
            
            result = self._request('POST', 'analyses', data)
            if result:
                logger.info("✅ Analyse sauvegardée dans Supabase")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde: {e}")
            return False
    
    def get_analyses(self, limit=20, offset=0):
        if not self.connected:
            return []
        
        try:
            endpoint = f"analyses?order=timestamp.desc&limit={limit}&offset={offset}"
            result = self._request('GET', endpoint)
            return result if result else []
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return []
    
    def get_stats(self):
        if not self.connected:
            return {}
        
        try:
            result = self._request('GET', 'stats')
            if result:
                return {item['key']: item['value'] for item in result}
            return {}
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return {}
    
    def get_total_count(self):
        if not self.connected:
            return 0
        
        try:
            result = self._request('GET', 'analyses?select=id')
            return len(result) if result else 0
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return 0
    
    def get_analyses_by_asset(self, asset, limit=20):
        if not self.connected:
            return []
        
        try:
            endpoint = f"analyses?asset=eq.{asset}&order=timestamp.desc&limit={limit}"
            result = self._request('GET', endpoint)
            return result if result else []
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return []
