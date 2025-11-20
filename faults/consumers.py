import json
from channels.generic.websocket import AsyncWebsocketConsumer

class FaultsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Optional: ek common group join karo agar future me broadcast karna ho
        self.group_name = "faults_stream"
        try:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
        except Exception:
            # Agar Redis/channel layer unavailable ho to silently continue
            pass

        await self.accept()
        await self.send(text_data=json.dumps({"message": "connected"}))

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception:
            pass

    async def receive(self, text_data=None, bytes_data=None):
        # Client se aane wale messages optional; echo/ping handle
        if text_data:
            await self.send(text_data=text_data)

    # Server-side broadcast handler example:
    async def fault_event(self, event):
        # event dict me "type": "fault.event", "payload": {...}
        payload = event.get("payload", {})
        await self.send(text_data=json.dumps(payload))
