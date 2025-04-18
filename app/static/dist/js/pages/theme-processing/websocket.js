/**
 * websocket.js
 * Improved WebSocket connection for real-time updates in theme processing
 */

import { state } from "./state.js";
import { updateTaskUI, addLogMessage } from "./ui.js";
import { updateVectorDBStatusUI } from "./vectorDB.js";

/**
 * Wait until WebSocket is connected before executing a callback
 * @param {function} callback - Function to run once the socket is connected
 * @param {number} interval - Interval in ms to check connection (default: 100ms)
 */
export function waitForSocketConnection(callback, interval = 100) {
  if (state.taskSocket && state.taskSocket.readyState === WebSocket.OPEN) {
    callback();
  } else {
    setTimeout(() => {
      waitForSocketConnection(callback, interval);
    }, interval);
  }
}

/**
 * Initialize WebSocket connection for real-time updates
 */
export function initializeWebSocketConnection() {
  // Close any existing connection
  if (state.taskSocket && state.taskSocket.readyState !== WebSocket.CLOSED) {
    state.taskSocket.close();
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/tasks`;
  try {
    state.taskSocket = new WebSocket(wsUrl);
    console.log("WebSocket initialized:", wsUrl); // <-- add this
    state.taskSocket.onopen = function () {
      // Process any pending subscription
      if (state.pendingSubscription) {
        subscribeToThemeUpdates(state.pendingSubscription);
        state.pendingSubscription = null;
      } else if (state.currentThemeId) {
        // Subscribe to the current theme if available
        subscribeToThemeUpdates(state.currentThemeId);
      }
    };

    state.taskSocket.onmessage = function (event) {
      const message = JSON.parse(event.data);
      console.log("Received WebSocket message:", message); // <-- add this
      handleWebSocketMessage(message);
    };

    state.taskSocket.onclose = function (event) {
      console.log("WebSocket closed", event);
      if (event.code !== 1000) attemptReconnect();
    };

    state.taskSocket.onerror = function (error) {
      console.error("WebSocket error:", error);
    };
  } catch (error) {
    console.error("WebSocket init failed:", error);
    attemptReconnect();
  }
}

/**
 * Attempt to reconnect WebSocket after connection lost
 */
export function attemptReconnect() {
  if (state.reconnectAttempts >= state.maxReconnectAttempts) {
    console.error("Maximum reconnection attempts reached");
    alertify.error("Lost connection to server. Please refresh the page.");
    return;
  }

  state.reconnectAttempts++;

  console.log(`Attempting to reconnect (${state.reconnectAttempts}/${state.maxReconnectAttempts})...`);

  setTimeout(() => {
    initializeWebSocketConnection();
  }, state.reconnectDelay);
}

/**
 * Subscribe to theme updates via WebSocket
 * @param {string} themeId
 */
export function subscribeToThemeUpdates(themeId) {
  if (!themeId) {
    console.warn("No theme ID provided for subscription.");
    return;
  }

  // Avoid duplicate subscription
  if (state.subscribedThemeId === themeId) {
    console.log(`Already subscribed to theme ${themeId}`);
    return;
  }

  // Optionally unsubscribe previous
  if (state.subscribedThemeId && state.subscribedThemeId !== themeId) {
    const unsubscribeMsg = {
      command: "unsubscribe",
      theme_id: state.subscribedThemeId,
    };
    waitForSocketConnection(() => {
      state.taskSocket.send(JSON.stringify(unsubscribeMsg));
      console.log(`Unsubscribed from theme ${state.subscribedThemeId}`);
    });
  }

  // Now send the subscription
  const subscribeMsg = {
    command: "subscribe",
    theme_id: themeId,
  };

  waitForSocketConnection(() => {
    state.taskSocket.send(JSON.stringify(subscribeMsg));
    state.subscribedThemeId = themeId; // optimistic update
    console.log(`Subscribed to theme ${themeId}`);
  });
}

/**
 * Handle WebSocket messages
 * @param {Object} message - Message received from WebSocket
 */
export function handleWebSocketMessage(message) {
  if (message.type === "subscription") {
    if (message.status === "success") {
      state.subscribedThemeId = message.theme_id;
    }
    return;
  }

  if (message.type === "task_update" && message.data) {
    const taskData = message.data;

    if (message.theme_id !== state.currentThemeId) return; // <-- Fix here

    state.processingTask = taskData;
    updateTaskUI(taskData);

    const progress = taskData.progress || 0;
    const step = taskData.current_step;

    let stepDescription = "";

    switch (step) {
      case 0:
        stepDescription = `Reading files (${progress}%)`;
        break;
      case 1:
        stepDescription = `Chunking text (${progress}%)`;
        break;
      case 2:
        stepDescription = `Generating embeddings (${progress}%)`;
        break;
      case 3:
        stepDescription = `Storing vectors (${progress}%)`;
        break;
      default:
        stepDescription = `Processing (${progress}%)`;
    }

    addLogMessage(stepDescription);

    // Update the live progress bar
    $("#process-progress").css("width", `${progress}%`);

    // Update vector DB status UI
    if (taskData.metadata && taskData.metadata.vectorDBStatus) {
      state.vectorDBStatus = taskData.metadata.vectorDBStatus;
      updateVectorDBStatusUI();
    }
  }
}

/**
 * Update processing status based on details
 */
function updateProcessingStatus(details) {
  // Update state based on processing stage
  if (details.stage === "reading") {
    state.vectorDBStatus.dataIngestion = "in_progress";
    addLogMessage(`Reading files: ${details.progress}% complete`);
  } else if (details.stage === "chunking") {
    state.vectorDBStatus.dataIngestion = "completed";
    state.vectorDBStatus.textChunking = "in_progress";
    addLogMessage(`Chunking text: ${details.progress}% complete. Created ${details.chunksCreated || 0} chunks.`);
  } else if (details.stage === "embedding") {
    state.vectorDBStatus.textChunking = "completed";
    state.vectorDBStatus.generateEmbeddings = "in_progress";
    addLogMessage(
      `Generating embeddings: ${details.progress}% complete. Processed ${details.embeddingsCreated || 0} embeddings.`
    );
  } else if (details.stage === "storing") {
    state.vectorDBStatus.generateEmbeddings = "completed";
    state.vectorDBStatus.storeVectors = "in_progress";
    addLogMessage(`Storing vectors: ${details.progress}% complete`);
  } else if (details.stage === "completed") {
    state.vectorDBStatus.storeVectors = "completed";
    addLogMessage(
      `Processing completed. Total chunks: ${details.totalChunks}, total embeddings: ${details.totalEmbeddings}`
    );
  }

  // Update the UI
  updateVectorDBStatusUI();
}
/**
 * Handle page visibility change to manage WebSocket connection
 */
export function handleWindowFocus() {
  // If the WebSocket is closed, try to reconnect
  if (state.taskSocket && state.taskSocket.readyState === WebSocket.CLOSED) {
    console.log("Window gained focus, reconnecting WebSocket...");
    initializeWebSocketConnection();
  }

  // Also refresh task status if we have an active task
  if (state.processingTask && state.processingTask.id) {
    import("./task.js").then(({ refreshTaskStatus }) => {
      refreshTaskStatus(state.processingTask.id);
    });
  }
}

/**
 * Handle window blur event (user navigated away)
 */
export function handleWindowBlur() {
  console.log("Window lost focus");
}

/**
 * Handle before unload event to warn if there's an active task
 * @param {Event} e - BeforeUnload event
 * @returns {string|undefined} Warning message if there's an active task
 */
export function handleBeforeUnload(e) {
  // Only show warning if there's an active task
  if (state.processingTask && ["pending", "in_progress"].includes(state.processingTask.status)) {
    const message = "You have an active processing task. Are you sure you want to leave?";
    e.returnValue = message;
    return message;
  }
}
