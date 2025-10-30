import json
from channels.generic.websocket import AsyncWebsocketConsumer

class DashboardCustomerConsumer(AsyncWebsocketConsumer):
    GROUP = "dashboard_customers"
    
    async def connect(self):
        user = self.scope.get("user")
        # chỉ staff/superuser được nghe
        if user and user.is_authenticated and (user.is_staff or user.is_superuser):
            await self.channel_layer.group_add(self.GROUP, self.channel_name)
            await self.accept()
        else:
            await self.close()
        
    async def disconnect(self, close_code):
        await self.channel_layer.group_discards(self.GROUP, self.channel_name)
        
    # Nhận tin nhắn từ nhóm
    async def add_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))