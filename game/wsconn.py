"""One open websocket, as the game server and the gateway both use it.

Everything for a connection goes through a single writer task, so a slow client never blocks the game loop or other
players. Ordinary messages (results, chat, notices) queue in order; the per-second tick update is a single slot, so a
client that falls behind skips ticks instead of building a backlog. A client that stops reading altogether (200 queued
messages) is hung up on, and the page reconnects and gets a fresh `init`."""
import asyncio
from collections import deque


class Conn:
    remote = False                      # True for the stand-in the core keeps for a client that is on a gateway

    def __init__(self, ws, token, registry=None):
        self.ws, self.token = ws, token
        self.registry = registry         # a dict keyed by websocket: the connection removes itself when it ends
        self.outbox = deque()
        self.tick = None
        self.wake = asyncio.Event()
        self.last_query = {}
        self.task = None
        self.alive = True
        self.limit = 200                 # queued messages before a client that is not reading is hung up on

    def push(self, text):
        if not self.alive:
            return
        if len(self.outbox) > self.limit:             # not reading at all: drop the connection
            self.close(hang_up=True)
            return
        self.outbox.append(text)
        self.wake.set()

    def push_tick(self, text):
        if self.alive:
            self.tick = text
            self.wake.set()

    def _forget(self):
        if self.registry is not None:
            self.registry.pop(self.ws, None)

    def close(self, hang_up=False):
        """Stop sending to this client. With `hang_up` the socket itself is closed too, so the page notices and
        reconnects (and gets a fresh `init`) instead of sitting there silently."""
        was_alive = self.alive
        self.alive = False
        self._forget()
        self.wake.set()
        if hang_up and was_alive:
            asyncio.get_running_loop().create_task(self._hang_up())

    async def _hang_up(self):
        try:
            await self.ws.close(code=1011)
        except Exception:
            pass

    async def writer(self):
        try:
            while self.alive:
                await self.wake.wait()
                self.wake.clear()
                while self.alive and (self.outbox or self.tick is not None):
                    if self.outbox:
                        text = self.outbox.popleft()
                    else:
                        text, self.tick = self.tick, None
                    await asyncio.wait_for(self.ws.send_text(text), timeout=3)
        except Exception:
            self.close(hang_up=True)               # a send failed or timed out: hang up so the page reconnects
        finally:
            self.alive = False
            self._forget()
