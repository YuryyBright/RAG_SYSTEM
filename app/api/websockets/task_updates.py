# app/api/websockets/task_updates.py
import datetime
import json
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect, Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from starlette.websockets import WebSocketState

from api.dependencies.task_dependencies import get_task_repository
from infrastructure.repositories.repository.task_repository import TaskRepository
from config import settings
from application.services.auth_service import AuthService
from utils.security import COOKIE_NAME

router = APIRouter()
from utils.logger_util import get_logger

logger = get_logger(__name__)
engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class TaskUpdateManager:
    """
    A Singleton WebSocket manager that handles task updates across multiple clients.
    Manages active user connections and theme subscriptions.
    """
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            logger.info("Creating a new TaskUpdateManager instance (Singleton)")
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.active_connections: Dict[str, Set[WebSocket]] = {}
            self.theme_subscriptions: Dict[str, Set[str]] = {}
            self._initialized = True  # Prevents reinitialization on next instantiation

    async def connect(self, websocket: WebSocket, user_id: str):
        """Register a new WebSocket connection for a user."""
        logger.info(f"Connecting user {user_id} to WebSocket.")
        self.active_connections.setdefault(user_id, set()).add(websocket)
        logger.debug(f"Current active connections: {self.active_connections}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection for a user."""
        logger.info(f"Disconnecting user {user_id} from WebSocket.")
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.debug(f"Active connections after disconnect: {self.active_connections}")

    async def subscribe_to_theme(self, user_id: str, theme_id: str):
        """Subscribe a user to a theme to receive updates."""
        self.theme_subscriptions.setdefault(theme_id, set()).add(user_id)
        logger.info(f"User {user_id} subscribed to theme {theme_id}.")

    async def unsubscribe_from_theme(self, user_id: str, theme_id: str):
        """Unsubscribe a user from a theme."""
        if theme_id in self.theme_subscriptions:
            self.theme_subscriptions[theme_id].discard(user_id)
            if not self.theme_subscriptions[theme_id]:
                del self.theme_subscriptions[theme_id]
            logger.info(f"User {user_id} unsubscribed from theme {theme_id}.")

    async def broadcast_task_update(self, task_data: dict):
        """Broadcast a task update to relevant users."""
        theme_id = task_data.get("theme_id")
        user_id = task_data.get("user_id")

        if not user_id:
            logger.warning("Broadcast aborted: task update missing user_id.")
            return

        await self.send_to_user(user_id, task_data)

        if theme_id and theme_id in self.theme_subscriptions:
            for subscribed_user_id in self.theme_subscriptions[theme_id]:
                if subscribed_user_id != user_id:
                    await self.send_to_user(subscribed_user_id, task_data)

    async def send_to_user(self, user_id: str, data: dict):
        """Send data to all active WebSocket connections of a user."""
        if user_id not in self.active_connections:
            logger.info(f"No active connections for user {user_id}.")
            return

        message = json.dumps(data)
        disconnected = set()

        for websocket in self.active_connections[user_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(message)
                    logger.info(f"Message sent to user {user_id}.")
                else:
                    logger.warning(f"WebSocket not connected for user {user_id}, marking for cleanup.")
                    disconnected.add(websocket)
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                disconnected.add(websocket)

        for websocket in disconnected:
            self.active_connections[user_id].discard(websocket)

        if not self.active_connections[user_id]:
            del self.active_connections[user_id]

# Create a singleton instance - should be imported, not instantiated elsewhere
task_update_manager = TaskUpdateManager()


async def get_task_update_manager():
    """Dependency to get the task update manager singleton."""
    # This will always return the same instance
    return task_update_manager


@router.websocket("/ws/tasks")
async def handle_task_websocket(
        websocket: WebSocket,
        task_repository: TaskRepository = Depends(get_task_repository),
):
    """
    Handle task updates, subscriptions, and retrieval via a WebSocket connection.
    """
    # Accept the WebSocket connection immediately upon entry
    await websocket.accept()

    # Add debug logging
    session = AsyncSessionLocal()  # create the session here.

    # Get the singleton manager
    manager = task_update_manager  # Use the singleton directly - don't instantiate
    logger.info(f"WebSocket handler using TaskUpdateManager instance ID: {id(manager)}")

    # Extract session ID with proper debugging
    session_id = websocket.cookies.get(COOKIE_NAME) or websocket.query_params.get("token")
    logger.debug(f"Extracted session ID: {session_id}")

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
            elif command == "ping":
                logger.info('User ping socket connection')
                # Send ping response
                await websocket.send_json({
                    "type": "ping",
                    "status": "success",
                    "timestamp": datetime.datetime.utcnow().isoformat()
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
                    #
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

    except WebSocketDisconnect:
        # Handle client disconnecting intentionally
        logger.info(f"WebSocket disconnected for user {current_user.id}")
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