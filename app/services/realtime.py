from typing import Dict, Set, Tuple, Any
from fastapi import WebSocket


class ConnectionManager:
  def __init__(self) -> None:
    self._chat_connections: Dict[Tuple[int, int], Set[WebSocket]] = {}
    self._company_connections: Dict[int, Set[WebSocket]] = {}

  async def connect(self, websocket: WebSocket, company_id: int, chat_id: int) -> None:
    key = (company_id, chat_id)
    if key not in self._chat_connections:
      self._chat_connections[key] = set()
    self._chat_connections[key].add(websocket)

  def disconnect(self, websocket: WebSocket, company_id: int, chat_id: int) -> None:
    key = (company_id, chat_id)
    if key in self._chat_connections:
      if websocket in self._chat_connections[key]:
        self._chat_connections[key].remove(websocket)
      if not self._chat_connections[key]:
        del self._chat_connections[key]

  async def connect_company(self, websocket: WebSocket, company_id: int) -> None:
    if company_id not in self._company_connections:
      self._company_connections[company_id] = set()
    self._company_connections[company_id].add(websocket)

  def disconnect_company(self, websocket: WebSocket, company_id: int) -> None:
    if company_id in self._company_connections:
      if websocket in self._company_connections[company_id]:
        self._company_connections[company_id].remove(websocket)
      if not self._company_connections[company_id]:
        del self._company_connections[company_id]

  async def send_personal_message(self, message: Any, websocket: WebSocket) -> None:
    try:
      await websocket.send_json(message)
    except Exception:
      pass

  async def broadcast_to_chat(self, company_id: int, chat_id: int, event: str, data: Any) -> None:
    key = (company_id, chat_id)
    if key not in self._chat_connections:
      return
    dead_connections: Set[WebSocket] = set()
    for connection in list(self._chat_connections[key]):
      try:
        await connection.send_json({
          "event": event,
          "data": data
        })
      except Exception:
        dead_connections.add(connection)
    for conn in dead_connections:
      self._chat_connections[key].discard(conn)
    if key in self._chat_connections and not self._chat_connections[key]:
      del self._chat_connections[key]

  async def broadcast_to_company(self, company_id: int, event: str, data: Any) -> None:
    if company_id not in self._company_connections:
      return
    dead_connections: Set[WebSocket] = set()
    for connection in list(self._company_connections[company_id]):
      try:
        await connection.send_json({
          "event": event,
          "data": data
        })
      except Exception:
        dead_connections.add(connection)
    for conn in dead_connections:
      self._company_connections[company_id].discard(conn)
    if company_id in self._company_connections and not self._company_connections[company_id]:
      del self._company_connections[company_id]


manager = ConnectionManager()


