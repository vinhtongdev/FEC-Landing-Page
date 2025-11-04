# management/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class DashboardCustomerConsumer(AsyncWebsocketConsumer):
    GROUP = "dashboard_customers"

    async def connect(self):
        await self.accept()
        user = self.scope.get("user")

        # Chặn non-staff: đóng 4401, KHÔNG gửi gì khác để client không reload
        if not (user and user.is_authenticated and (user.is_staff or user.is_superuser)):
            await self.close(code=4401)
            return

        try:
            # 1) Channel layer tồn tại không?
            if self.channel_layer is None:
                await self.send(text_data=json.dumps({
                    "kind": "error", "where": "connect", "detail": "channel_layer_none"
                }))
                await self.close(code=1011)
                return

            # 2) Thử join group
            await self.channel_layer.group_add(self.GROUP, self.channel_name)

            # Ping nhẹ để bạn thấy kết nối ok (frontend KHÔNG reload vì chỉ xử lý kind='customer_created')
            await self.send(text_data=json.dumps({"kind": "ws_ready"}))

        except Exception as e:
            import traceback; traceback.print_exc()
            # Gửi lỗi gọn cho console của bạn
            await self.send(text_data=json.dumps({
                "kind": "error", "where": "group_add", "detail": str(e)[:300]
            }))
            await self.close(code=1011)

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.GROUP, self.channel_name)
        except Exception:
            import traceback; traceback.print_exc()

    async def add_message(self, event):
        await self.send(text_data=json.dumps(event.get("data", {})))
