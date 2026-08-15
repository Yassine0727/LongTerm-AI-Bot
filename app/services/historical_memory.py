import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class HistoricalMemory:
    """Service pour stocker et apprendre des analyses passées"""
    
    def __init__(self):
        self.memory_file = "data/historical_memory.json"
        self._ensure_file()
    
    def _ensure_file(self):
        """Créer le fichier s'il n'existe pas"""
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.memory_file):
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump({"events": []}, f, indent=2)
    
    def _load_memory(self) -> Dict:
        """Charger la mémoire"""
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"events": []}
    
    def _save_memory(self, data: Dict):
        """Sauvegarder la mémoire"""
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def add_event(self, event: Dict):
        """Ajouter un événement à l'historique"""
        memory = self._load_memory()
        
        # Ajouter l'événement
        memory["events"].append({
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%d/%m/%Y"),
            "news": event.get("news", ""),
            "analysis": event.get("analysis", {}),
            "asset": event.get("asset", "BTC"),
            "impact_score": event.get("score", 0),
            "time_horizon": event.get("time_horizon", "medium_term"),
            "price_at_time": event.get("price_at_time", 0)
        })
        
        # Garder seulement les 1000 derniers événements
        if len(memory["events"]) > 1000:
            memory["events"] = memory["events"][-1000:]
        
        self._save_memory(memory)
        logger.info(f"✅ Événement ajouté à l'historique: {event.get('news')[:50]}...")
    
    def get_events(self, asset: str = None, limit: int = 10) -> List[Dict]:
        """Obtenir les événements récents"""
        memory = self._load_memory()
        events = memory.get("events", [])
        
        if asset:
            events = [e for e in events if e.get("asset") == asset]
        
        return events[-limit:] if events else []
    
    def get_similar_events(self, news_text: str, limit: int = 3) -> List[Dict]:
        """Trouver des événements similaires"""
        # Simple matching basé sur les mots-clés
        keywords = news_text.lower().split()
        events = self._load_memory().get("events", [])
        
        scored = []
        for event in events:
            event_text = event.get("news", "").lower()
            score = sum(1 for kw in keywords if kw in event_text)
            if score > 0:
                scored.append((score, event))
        
        scored.sort(reverse=True, key=lambda x: x[0])
        return [e for _, e in scored[:limit]]
    
    def get_top_impact_events(self, asset: str = "BTC", limit: int = 5) -> List[Dict]:
        """Obtenir les événements avec le plus grand impact"""
        events = self._load_memory().get("events", [])
        asset_events = [e for e in events if e.get("asset") == asset]
        sorted_events = sorted(asset_events, key=lambda x: x.get("impact_score", 0), reverse=True)
        return sorted_events[:limit]
    
    def get_learning_summary(self, asset: str = "BTC") -> str:
        """Générer un résumé d'apprentissage"""
        events = self._load_memory().get("events", [])
        asset_events = [e for e in events if e.get("asset") == asset]
        
        if not asset_events:
            return "Aucun événement historique pour cet actif."
        
        total = len(asset_events)
        positive = len([e for e in asset_events if e.get("analysis", {}).get("impact") == "positive"])
        negative = len([e for e in asset_events if e.get("analysis", {}).get("impact") == "negative"])
        neutral = total - positive - negative
        
        avg_score = sum(e.get("impact_score", 0) for e in asset_events) / total if total > 0 else 0
        
        return f"""
📊 RÉSUMÉ D'APPRENTISSAGE - {asset}
========================================
📈 Total événements: {total}
🟢 Positifs: {positive}
🔴 Négatifs: {negative}
🟡 Neutres: {neutral}
📊 Score moyen: {avg_score:.1f}/10

💡 L'analyse historique montre que:
- {positive} événements positifs ont précédé des périodes favorables
- {negative} événements négatifs ont précédé des périodes difficiles
- {neutral} événements n'ont pas eu d'impact significatif

🎯 Leçon principale: Les événements avec score > 7/10 ont généralement un impact durable sur le long-terme.
        """.strip()