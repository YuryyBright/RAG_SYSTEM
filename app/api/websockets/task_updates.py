# app/api/websockets/task_updates.py
import json
from typing import Dict, List, Optional, Set, Annotated, Union
import asyncio
from fastapi import WebSocket, WebSocketDisconnect, Depends, Cookie, APIRouter, Query, WebSocketException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from starlette import status
from starlette.websockets import WebSocketState

from api.middleware_auth import get_current_active_user
from app.infrastructure.database.repository.task_repository import TaskRepository
from app.api.dependencies import get_task_repository
from config import settings
from core.entities.user import User
from core.services.auth_service import AuthService
from infrastructure.database.repository import get_async_db, get_websocket_db
from utils.security import COOKIE_NAME

router = APIRouter()
from utils.logger_util import get_logger

logger = get_logger(__name__)
engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class TaskUpdateManager:
    """
    WebSocket connection manager for task updates.
    Broadcasts task updates to connected clients.
    """

    def __init__(self):
        # Map of user_id -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map of theme_id -> Set of user_ids interested in that theme
        self.theme_subscriptions: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a new WebSocket client."""
        # await websocket.accept() #Remove this line.

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a WebSocket client."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)

            # Clean up if no more connections for this user
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def subscribe_to_theme(self, user_id: str, theme_id: str):
        """Subscribe a user to theme updates."""
        if theme_id not in self.theme_subscriptions:
            self.theme_subscriptions[theme_id] = set()

        self.theme_subscriptions[theme_id].add(user_id)

    async def unsubscribe_from_theme(self, user_id: str, theme_id: str):
        """Unsubscribe a user from theme updates."""
        if theme_id in self.theme_subscriptions:
            self.theme_subscriptions[theme_id].discard(user_id)

            # Clean up if no more subscriptions for this theme
            if not self.theme_subscriptions[theme_id]:
                del self.theme_subscriptions[theme_id]

    async def broadcast_task_update(self, task_data: dict):
        """Broadcast task update to all connected clients who need to know."""
        theme_id = task_data.get("theme_id")
        user_id = task_data.get("user_id")

        # Always send to the task owner
        await self.send_to_user(user_id, task_data)

        # Also send to anyone subscribed to the theme (if applicable)
        if theme_id and theme_id in self.theme_subscriptions:
            for subscribed_user_id in self.theme_subscriptions[theme_id]:
                if subscribed_user_id != user_id:  # Skip if already sent to this user
                    await self.send_to_user(subscribed_user_id, task_data)

    async def send_to_user(self, user_id: str, data: dict):
        """Send a message to all connections of a specific user."""
        if user_id not in self.active_connections:
            return

        # Convert to JSON string
        message = json.dumps(data)

        # Keep track of disconnected websockets to remove later
        disconnected = set()

        # Send to all connections for this user
        for websocket in self.active_connections[user_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message)
            except Exception:
                disconnected.add(websocket)

        # Clean up disconnected websockets
        for websocket in disconnected:
            self.active_connections[user_id].discard(websocket)

        # Clean up if no more connections for this user
        if not self.active_connections[user_id]:
            del self.active_connections[user_id]


# Create a singleton instance
task_update_manager = TaskUpdateManager()


async def get_task_update_manager():
    """Dependency to get the task update manager."""
    return task_update_manager



@router.websocket("/ws/tasks")
async def handle_task_websocket(
        websocket: WebSocket,
        task_repository: TaskRepository = Depends(get_task_repository),
):
    """
    Handle task updates, subscriptions, and retrieval via a WebSocket connection.

    This endpoint allows clients to:
    1. Subscribe to a specific theme (via "subscribe" command).
    2. Unsubscribe from a specific theme (via "unsubscribe" command).
    3. Retrieve tasks for a given theme or all user tasks (via "get_tasks" command).

    WebSocket connection flow:
    - The client must provide a session/token either through a cookie or query parameter.
    - The session/token is used to identify the user via AuthService.
    - If the token is invalid/expired, the connection is closed with an error code.
    - Once authenticated, the user is connected, and can send commands in JSON format:
        {
            "command": "<subscribe|unsubscribe|get_tasks>",
            "theme_id": "..."
        }
    - The server responds with JSON messages as needed (e.g. subscription confirmation,
      unsubscribing notification, or sending tasks).
    - If the connection is closed, or any exception arises, we attempt to cleanly disconnect.
    """
    # Accept the WebSocket connection immediately upon entry

    await websocket.accept()
    # Add debug logging
    session = AsyncSessionLocal()  # create the session here.
    # Get the manager
    manager = await get_task_update_manager()
    # Extract session ID with proper debugging
    session_id = websocket.cookies.get(COOKIE_NAME) or websocket.query_params.get("token")
    logger.debug(f"Extracted session ID: {session_id}")
    # Get the manager responsible for orchestrating WebSocket connections and updates

    # Extract session from cookie or query params
    session_id: Optional[str] = (
            websocket.cookies.get(COOKIE_NAME) or websocket.query_params.get("token")
    )
    if not session_id:
        await websocket.close(code=4001, reason="Missing token or session")
        return

    # Attempt to validate and load the current user from the session
    auth_service = AuthService(session)
    current_user = await auth_service.get_user_by_session_id(session_id)
    if not current_user:
        await websocket.close(code=4001, reason="Invalid or expired token/session")
        return

    # Register this WebSocket connection with the manager
    await manager.connect(websocket, current_user.id)

    try:
        while True:
            # Wait to receive a JSON message from the client
            data = await websocket.receive_json()
            command = data.get("command")

            # Handle different commands from the client
            if command == "subscribe":
                logger.info('User subscribe to task updates')
                theme_id = data.get("theme_id")
                if theme_id is not None:
                    # Subscribe the user to the given theme
                    await manager.subscribe_to_theme(current_user.id, theme_id)
                    await websocket.send_json({
                        "type": "subscription",
                        "status": "success",
                        "theme_id": theme_id
                    })

            elif command == "unsubscribe":
                theme_id = data.get("theme_id")
                if theme_id is not None:
                    # Unsubscribe the user from the given theme
                    await manager.unsubscribe_from_theme(current_user.id, theme_id)
                    await websocket.send_json({
                        "type": "subscription",
                        "status": "unsubscribed",
                        "theme_id": theme_id
                    })

            elif command == "get_tasks":
                theme_id = data.get("theme_id")
                if theme_id:
                    # Retrieve tasks for a specific theme, but ensure only the user's tasks
                    tasks = await task_repository.get_theme_tasks(theme_id)
                    tasks = [t for t in tasks if t.user_id == current_user.id]
                else:
                    # Retrieve all tasks for the current user
                    tasks = await task_repository.get_user_tasks(current_user.id)

                # Send each task back to the client
                for task in tasks:
                    await websocket.send_json({
                        "type": "task_update",
                        "data": task.to_dict()  # or however you serialize your task
                    })
            elif command == "get_task_status":
                task_id = data.get("task_id")
                if task_id:
                    task = await task_repository.get_by_id(task_id)
                    if task and task.user_id == current_user.id:
                        await websocket.send_json({
                            "type": "task_status",
                            "data": task.to_dict()
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Task not found or access denied"
                        })
            # You can add more commands as needed...

    except WebSocketDisconnect:
        # Handle client disconnecting intentionally
        manager.disconnect(websocket, current_user.id)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, current_user.id)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    finally:
        await session.close()  # close the session.
