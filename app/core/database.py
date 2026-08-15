import json
import os
from datetime import datetime
from typing import List, Dict

DB_FILE = "data/analyses.json"

def ensure_data_dir():
    os.makedirs("data", exist_ok=True)

class Database:
    @staticmethod
    def save_analysis(analysis: Dict) -> bool:
        ensure_data_dir()
        try:
            data = Database.get_all_analyses()
            data.append({
                "timestamp": datetime.now().isoformat(),
                "analysis": analysis
            })
            if len(data) > 100:
                data = data[-100:]
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving: {e}")
            return False
    
    @staticmethod
    def get_all_analyses() -> List[Dict]:
        ensure_data_dir()
        try:
            if os.path.exists(DB_FILE):
                with open(DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return []
    
    @staticmethod
    def get_recent_analyses(limit: int = 20) -> List[Dict]:
        data = Database.get_all_analyses()
        return data[-limit:] if data else []
    
    @staticmethod
    def get_analysis_count() -> int:
        return len(Database.get_all_analyses())
    
    @staticmethod
    def clear_all() -> bool:
        """Supprimer toutes les données de la base"""
        try:
            # Supprimer le fichier d'analyses
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
                print(f"🗑️ Fichier supprimé: {DB_FILE}")
            
            # Supprimer les autres fichiers de données
            data_files = [
                "data/portfolio_data.json",
                "data/price_history.json",
                "data/settings.json"
            ]
            
            for file in data_files:
                if os.path.exists(file):
                    os.remove(file)
                    print(f"🗑️ Fichier supprimé: {file}")
            
            # Recréer le dossier data si nécessaire
            ensure_data_dir()
            
            # Créer un fichier analyses.json vide
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2)
            
            print("✅ Base de données réinitialisée avec succès")
            return True
            
        except Exception as e:
            print(f"❌ Erreur clear_all: {e}")
            return False
    
    @staticmethod
    def delete_analysis_by_index(index: int) -> bool:
        """Supprimer une analyse par son index"""
        try:
            data = Database.get_all_analyses()
            if 0 <= index < len(data):
                removed = data.pop(index)
                with open(DB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"🗑️ Analyse supprimée: {removed.get('timestamp', 'unknown')}")
                return True
            return False
        except Exception as e:
            print(f"❌ Erreur delete_analysis: {e}")
            return False
    
    @staticmethod
    def delete_analyses_by_asset(asset: str) -> int:
        """Supprimer toutes les analyses pour un actif spécifique"""
        try:
            data = Database.get_all_analyses()
            original_count = len(data)
            new_data = []
            for item in data:
                if item.get('analysis', {}).get('asset', '').upper() != asset.upper():
                    new_data.append(item)
            
            removed_count = original_count - len(new_data)
            
            if removed_count > 0:
                with open(DB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(new_data, f, indent=2, ensure_ascii=False)
                print(f"🗑️ {removed_count} analyses supprimées pour {asset}")
            
            return removed_count
        except Exception as e:
            print(f"❌ Erreur delete_analyses_by_asset: {e}")
            return 0
    
    @staticmethod
    def clear_price_history() -> bool:
        """Supprimer l'historique des prix"""
        try:
            price_file = "data/price_history.json"
            if os.path.exists(price_file):
                os.remove(price_file)
                print(f"🗑️ Historique des prix supprimé")
            
            # Créer un fichier vide
            with open(price_file, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2)
            
            return True
        except Exception as e:
            print(f"❌ Erreur clear_price_history: {e}")
            return False
    
    @staticmethod
    def clear_portfolio() -> bool:
        """Supprimer les données du portefeuille"""
        try:
            portfolio_file = "data/portfolio_data.json"
            if os.path.exists(portfolio_file):
                os.remove(portfolio_file)
                print(f"🗑️ Données du portefeuille supprimées")
            
            # Créer un fichier vide
            with open(portfolio_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2)
            
            return True
        except Exception as e:
            print(f"❌ Erreur clear_portfolio: {e}")
            return False
    
    @staticmethod
    def get_stats() -> Dict:
        """Obtenir des statistiques sur la base de données"""
        try:
            analyses = Database.get_all_analyses()
            total = len(analyses)
            
            # Compter par actif
            asset_counts = {}
            for item in analyses:
                asset = item.get('analysis', {}).get('asset', 'unknown')
                asset_counts[asset] = asset_counts.get(asset, 0) + 1
            
            # Compter par impact
            impact_counts = {}
            for item in analyses:
                impact = item.get('analysis', {}).get('impact', 'unknown')
                impact_counts[impact] = impact_counts.get(impact, 0) + 1
            
            return {
                "total_analyses": total,
                "by_asset": asset_counts,
                "by_impact": impact_counts,
                "last_analysis": analyses[-1].get('timestamp') if analyses else None
            }
            
        except Exception as e:
            print(f"❌ Erreur get_stats: {e}")
            return {}
    
    @staticmethod
    def export_all_data() -> Dict:
        """Exporter toutes les données en un seul fichier"""
        try:
            ensure_data_dir()
            
            data = {
                "export_date": datetime.now().isoformat(),
                "version": "1.0",
                "analyses": Database.get_all_analyses(),
                "price_history": [],
                "portfolio": {}
            }
            
            # Charger l'historique des prix
            price_file = "data/price_history.json"
            if os.path.exists(price_file):
                with open(price_file, 'r', encoding='utf-8') as f:
                    data["price_history"] = json.load(f)
            
            # Charger le portefeuille
            portfolio_file = "data/portfolio_data.json"
            if os.path.exists(portfolio_file):
                with open(portfolio_file, 'r', encoding='utf-8') as f:
                    data["portfolio"] = json.load(f)
            
            return data
            
        except Exception as e:
            print(f"❌ Erreur export_all_data: {e}")
            return {}
    
    @staticmethod
    def import_data(data: Dict) -> bool:
        """Importer des données depuis un fichier"""
        try:
            ensure_data_dir()
            
            # Importer les analyses
            if 'analyses' in data:
                with open(DB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data['analyses'], f, indent=2, ensure_ascii=False)
            
            # Importer l'historique des prix
            if 'price_history' in data:
                price_file = "data/price_history.json"
                with open(price_file, 'w', encoding='utf-8') as f:
                    json.dump(data['price_history'], f, indent=2)
            
            # Importer le portefeuille
            if 'portfolio' in data:
                portfolio_file = "data/portfolio_data.json"
                with open(portfolio_file, 'w', encoding='utf-8') as f:
                    json.dump(data['portfolio'], f, indent=2)
            
            print("✅ Données importées avec succès")
            return True
            
        except Exception as e:
            print(f"❌ Erreur import_data: {e}")
            return False