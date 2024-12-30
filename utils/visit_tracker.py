from fastapi import WebSocket
from typing import Set, Dict
from sqlalchemy.orm import Session
import models
from datetime import datetime

class VisitTracker:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.page_views: Dict[str, int] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        await self.broadcast_stats()
    
    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        await self.broadcast_stats()
    
    def get_active_connections(self) -> int:
        return len(self.active_connections)
    
    async def broadcast_stats(self):
        if not self.active_connections:
            return
            
        stats = {
            "active_users": self.get_active_connections()
        }
        
        for connection in self.active_connections:
            try:
                await connection.send_json(stats)
            except:
                pass

    def increment_page_view(self, page: str):
        self.page_views[page] = self.page_views.get(page, 0) + 1
    
    def get_page_views(self, page: str) -> int:
        return self.page_views.get(page, 0)

visit_tracker = VisitTracker()

def update_total_visits(db: Session):
    """更新总访问量"""
    stats = db.query(models.VisitStats).first()
    if not stats:
        stats = models.VisitStats(total_visits=1)
        db.add(stats)
    else:
        stats.total_visits += 1
    db.commit()
    return stats.total_visits
