# management/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

class HubConsumer(AsyncWebsocketConsumer):
    DASHBOARD_GROUP = "dashboard_customers"
    MANAGERS_GROUP  = "managers"

    @sync_to_async
    def _is_manager(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        # Cho phép cả Group 'manage' hoặc quyền riêng nếu bạn dùng
        return (
            user.groups.filter(name="manage").exists()
            or user.has_perm("management.can_manage_customers")
            or user.is_staff  # nếu muốn coi staff là manager trong dev
        )

    async def connect(self):
        user = self.scope.get("user")
        if not (user and user.is_authenticated):
            await self.close(code=4401); return

        await self.accept()

        joined = []
        if self.channel_layer is not None:
            await self.channel_layer.group_add(self.DASHBOARD_GROUP, self.channel_name)
            joined.append(self.DASHBOARD_GROUP)
            if await self._is_manager(user):
                await self.channel_layer.group_add(self.MANAGERS_GROUP, self.channel_name)
                joined.append(self.MANAGERS_GROUP)

        await self.send(text_data=json.dumps({"kind": "ws_ready", "joined": joined}))

    async def disconnect(self, code):
        try:
            if self.channel_layer is not None:
                await self.channel_layer.group_discard(self.DASHBOARD_GROUP, self.channel_name)
                await self.channel_layer.group_discard(self.MANAGERS_GROUP,  self.channel_name)
        except Exception:
            pass

    async def add_message(self, event):
        await self.send(text_data=json.dumps(event.get("data", {})))

    async def approval_request(self, event):
        payload = event.get("data", {})
        payload.setdefault("kind", "approve_request")
        await self.send(text_data=json.dumps(payload))
