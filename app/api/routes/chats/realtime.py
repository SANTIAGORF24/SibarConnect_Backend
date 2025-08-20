from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.realtime import manager


router = APIRouter()


@router.websocket("/ws/company/{company_id}")
async def websocket_company_endpoint(websocket: WebSocket, company_id: int):
  await websocket.accept()
  await manager.connect_company(websocket, company_id)
  try:
    while True:
      await websocket.receive_text()
  except WebSocketDisconnect:
    manager.disconnect_company(websocket, company_id)


@router.websocket("/ws/{company_id}/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, company_id: int, chat_id: int):
  await websocket.accept()
  await manager.connect(websocket, company_id, chat_id)
  try:
    while True:
      await websocket.receive_text()
  except WebSocketDisconnect:
    manager.disconnect(websocket, company_id, chat_id)


