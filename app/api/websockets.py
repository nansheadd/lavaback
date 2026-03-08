from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.websockets import manager

from jose import jwt, JWTError
from app.auth import SECRET_KEY, ALGORITHM
# from app.core.config import settings # Removed as it does not exist

router = APIRouter()

async def get_current_user_ws(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Custom dependency for WebSocket authentication since headers are not always available/standard in WS handshake 
    in all clients, but Query params are supported.
    """
    credentials_exception = WebSocketDisconnect(code=1008)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    from app import models
    user = db.query(models.User).filter(models.User.email == username).first()
    if user is None:
        raise credentials_exception
    return user

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    # Authenticate
    # We have to manually verify token here or use the dependency above.
    # Using the logic inline or via a helper is fine.
    # Note: Dependencies in websocket decorators are supported.
    
    user = None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            await websocket.close(code=1008)
            return
            
        from app import models
        user = db.query(models.User).filter(models.User.email == username).first()
        if user is None:
            await websocket.close(code=1008)
            return
            
        await manager.connect(websocket, user.id)
        
        try:
            while True:
                # Keep the connection alive. We can listen for client messages (e.g. "typing" status)
                data = await websocket.receive_text()
                # Echo or process if needed
                # await websocket.send_text(f"Message text was: {data}")
        except WebSocketDisconnect:
            manager.disconnect(websocket, user.id)
            
    except JWTError:
        await websocket.close(code=1008)
    except Exception as e:
        print(f"WebSocket Error: {e}")
        if user:
             manager.disconnect(websocket, user.id)
        else:
             try:
                 await websocket.close()
             except:
                 pass
