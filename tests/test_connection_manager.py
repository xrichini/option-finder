import asyncio
import pytest

from app import ConnectionManager


class MockWebSocket:
    def __init__(self):
        self.accepted = False
        self.sent = []

    async def accept(self):
        self.accepted = True

    async def send_text(self, text: str):
        # simulate async send
        await asyncio.sleep(0)
        self.sent.append(text)


@pytest.mark.asyncio
async def test_connect_and_send_personal_message():
    manager = ConnectionManager()
    ws = MockWebSocket()

    await manager.connect(ws)
    assert ws.accepted
    assert len(manager.active_connections) == 1

    await manager.send_personal_message({"type": "test", "payload": 123}, ws)
    assert len(ws.sent) == 1

    manager.disconnect(ws)
    assert len(manager.active_connections) == 0


@pytest.mark.asyncio
async def test_broadcast_to_multiple_connections():
    manager = ConnectionManager()
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()

    await manager.connect(ws1)
    await manager.connect(ws2)

    assert len(manager.active_connections) == 2

    await manager.broadcast({"type": "broadcast", "value": "ok"})

    # both should have received one message
    assert len(ws1.sent) == 1
    assert len(ws2.sent) == 1

    manager.disconnect(ws1)
    manager.disconnect(ws2)
    assert len(manager.active_connections) == 0
