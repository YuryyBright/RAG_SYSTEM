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

    state.taskSocket.onopen = function () {
      console.log("WebSocket connection established successfully!");
      $("#connection-status").removeClass("badge-warning badge-danger").addClass("badge-success").text("Connected");
      $("#connection-error").addClass("d-none");
      state.reconnectAttempts = 0; // Reset counter on successful connectio

      state.taskSocket.send(JSON.stringify({ command: "ping" }));
      console.log("Ping sent to server");

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
      $("#connection-status").removeClass("badge-success").addClass("badge-warning").text("Disconnected");
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
// Improve the attemptReconnect function
export function attemptReconnect() {
  if (state.reconnectAttempts >= state.maxReconnectAttempts) {
    console.error("Maximum reconnection attempts reached");
    addLogMessage("Lost connection to server. Please refresh the page.");
    $("#connection-error").removeClass("d-none").text("Connection lost. Please refresh the page to continue.");
    return;
  }

  state.reconnectAttempts++;
  const delay = state.reconnectDelay * Math.pow(1.5, state.reconnectAttempts - 1); // Exponential backoff

  console.log(`Attempting to reconnect (${state.reconnectAttempts}/${state.maxReconnectAttempts}) in ${delay}ms...`);
  addLogMessage(`Connection lost. Reconnecting (attempt ${state.reconnectAttempts})...`);

  setTimeout(() => {
    initializeWebSocketConnection();
  }, delay);
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

    state.taskSocket.send(JSON.stringify(unsubscribeMsg));
    console.log(`Unsubscribed from theme ${state.subscribedThemeId}`);
  }

  // Now send the subscription
  const subscribeMsg = {
    command: "subscribe",
    theme_id: themeId,
  };

  state.taskSocket.send(JSON.stringify(subscribeMsg));
  state.subscribedThemeId = themeId; // optimistic update
  console.log(`Subscribed to theme ${themeId}`);
}

/**
 * Handle WebSocket messages
 * @param {Object} message - Message received from WebSocket
 */
export function handleWebSocketMessage(message) {
  // Log all messages for debugging
  console.log("Received WebSocket message:", message);

  if (message.type === "subscription") {
    if (message.status === "success") {
      state.subscribedThemeId = message.theme_id;
      console.log(`Successfully subscribed to theme ${message.theme_id}`);
    }
    return;
  }

  if (message.type === "task_update" && message.data) {
    const taskData = message.data;

    // Only process updates for the current theme (if theme_id is provided)
    if (message.theme_id && message.theme_id !== state.currentThemeId) {
      console.log(`Ignoring update for different theme: ${message.theme_id}`);
      return;
    }

    // Update global state
    state.processingTask = taskData;

    // Update task UI with latest data
    updateTaskUI(taskData);

    // Process step-specific updates
    processStepUpdate(taskData);
  }
}

/**
 * Update processing status based on details
 */
function processStepUpdate(taskData) {
  const progress = taskData.progress || 0;
  const step = taskData.current_step;

  // Map steps to vectorDB status fields
  const stepStatusMapping = {
    READING: { step: 0, status: "dataIngestion" },
    CHUNKING: { step: 1, status: "textChunking" },
    EMBEDDING: { step: 2, status: "generateEmbeddings" },
  };

  // Mark current step as in_progress and previous steps as completed
  Object.keys(stepStatusMapping).forEach((stepNum) => {
    const statusField = stepStatusMapping[stepNum];
    if (parseInt(stepNum) < step) {
      state.vectorDBStatus[statusField] = "completed";
    } else if (parseInt(stepNum) === step) {
      state.vectorDBStatus[statusField] = "in_progress";
    }
  });

  // Add log message based on step
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

  // Update the UI
  updateVectorDBStatusUI();

  // Update progress bar
  $("#process-progress").css("width", `${progress}%`);

  // Handle task completion
  if (taskData.status === "completed") {
    // Mark all steps as completed when the task is done
    Object.keys(state.vectorDBStatus).forEach((key) => {
      state.vectorDBStatus[key] = "completed";
    });

    addLogMessage("Processing completed successfully!");
    updateVectorDBStatusUI();

    // Enable finish button
    $("#finish-btn").prop("disabled", false);
  }
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
