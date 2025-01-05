from fastapi import WebSocket
from typing import Dict, Set
from datetime import datetime

class VisitTracker:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # IP -> WebSocket
        self.page_views: Dict[str, int] = {}
        self.total_visits: int = 0

    def get_client_ip(self, websocket: WebSocket) -> str:
        """获取WebSocket客户端的IP地址"""
        client = websocket.client
        if client is None:
            return "unknown"
        return client.host or "unknown"

    async def connect(self, websocket: WebSocket):
        """处理新的WebSocket连接"""
        await websocket.accept()
        client_ip = self.get_client_ip(websocket)
        
        # 如果这个IP之前没有连接，则计为新访问
        if client_ip not in self.active_connections:
            self.total_visits += 1
        
        # 更新连接
        self.active_connections[client_ip] = websocket
        await self.broadcast_stats()

    async def disconnect(self, websocket: WebSocket):
        """处理WebSocket断开连接"""
        client_ip = self.get_client_ip(websocket)
        if client_ip in self.active_connections:
            del self.active_connections[client_ip]
            await self.broadcast_stats()

    def get_active_connections(self) -> int:
        """获取活动连接数（基于唯一IP）"""
        return len(self.active_connections)

    async def broadcast_stats(self):
        """广播访问统计信息给所有连接的客户端"""
        if not self.active_connections:
            return

        stats = {
            "active_users": self.get_active_connections(),
            "total_visits": self.total_visits,
            "page_views": self.page_views.get('home', 0)
        }

        # 向所有连接的客户端发送更新
        disconnected_ips = set()
        for ip, connection in self.active_connections.items():
            try:
                await connection.send_json(stats)
            except:
                disconnected_ips.add(ip)

        # 清理断开的连接
        for ip in disconnected_ips:
            del self.active_connections[ip]

    def increment_page_view(self, page: str):
        """增加页面访问计数"""
        self.page_views[page] = self.page_views.get(page, 0) + 1

    def get_page_views(self, page: str) -> int:
        """获取页面访问计数"""
        return self.page_views.get(page, 0)

visit_tracker = VisitTracker()
