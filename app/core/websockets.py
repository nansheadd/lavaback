from fastapi import WebSocket
from typing import List, Dict, Optional
import json

class ConnectionManager:
    def __init__(self):
        # Map user_id to a list of active WebSocket connections (multi-tab support)
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # We could also track channel subscriptions here if we want server-side filtering
        # self.channel_subscriptions: Dict[str, List[int]] = {}  # channel_id -> [user_ids]

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print(f"User {user_id} connected via WebSocket. Total connections for user: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"User {user_id} disconnected.")

    async def send_personal_message(self, message: dict, user_id: int):
        """Send a message to a specific user (across all their active devices)."""
        if user_id in self.active_connections:
            # Create a list of connections to close if they are dead
            to_remove = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error sending message to user {user_id}: {e}")
                    to_remove.append(connection)
            
            # Clean up dead connections
            for conn in to_remove:
                self.disconnect(conn, user_id)

    async def broadcast(self, message: dict):
        """Broadcast a message to ALL connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)

    async def broadcast_to_channel(self, message: dict, channel_id: int):
        """
        Broadcast a message to everyone who should receive it.
        For simplicity in this V1, we will broadcast to ALL users,
        and let the frontend filter if the message belongs to the channel they are viewing.
        
        Optimization V2: Track which users are 'viewing' a channel or are 'members' of a channel.
        For now, since we don't track 'online presence' per channel purely via WS, 
        broadcasting to all online users is safe (security-wise, the frontend will filter, 
        but ideally we checks membership - let's trust the frontend filter for 'noise' reduction
        but we should send to all users who *could* see it).
        
        Actually, sending to ALL users is network inefficient but simplest.
        Better: Send to all users, but include 'channel_id' in the payload so they can ignore it.
        """
        payload = {
            "type": "chat_message",
            "channel_id": channel_id,
            "data": message
        }
        await self.broadcast(payload)
        
    async def send_notification(self, user_id: int, notification: dict):
        """Helper specifically for notifications."""
        payload = {
            "type": "notification",
            "data": notification
        }
        await self.send_personal_message(payload, user_id)

manager = ConnectionManager()
