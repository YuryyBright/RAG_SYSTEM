/**
 * websocket.js
 * Handles WebSocket connections for real-time updates in theme processing
 */

import { state } from "./state.js";
import { updateTaskUI } from "./ui.js";

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

    state.taskSocket.onopen = function () {
      //   state.reconnectAttempts = 0;
      //   // ✅ Safe to send after socket is open
      //   const testMessage = {
      //     command: "ping", // not "action"
      //     message: "Test WebSocket message",
      //     timestamp: new Date().toISOString(),
      //   };
      //   state.taskSocket.send(JSON.stringify(testMessage));
      //   console.log("Test message sent to server:", testMessage);
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
 * Avoids redundant subscriptions and assumes socket is ready when called
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
}

/**
 * Handle WebSocket messages
 * @param {Object} message - Message received from WebSocket
 */
export function handleWebSocketMessage(message) {
  // console.log("Received WebSocket message:", message);

  // Handle subscription confirmation
  if (message.type === "subscription") {
    // console.log(`Subscription status: ${message.status} for theme ${message.theme_id}`);

    // If subscription was successful, store the subscribed theme
    if (message.status === "success") {
      state.subscribedThemeId = message.theme_id;
    }
  }

  // Handle task updates
  if (message.type === "task_update" && message.data) {
    const taskData = message.data;

    // Only process updates for the current theme
    if (taskData.theme_id === state.currentThemeId) {
      // Update our task data
      state.processingTask = taskData;

      // Update UI based on task data
      updateTaskUI(taskData);

      // Import necessary modules dynamically to avoid circular dependencies
      import("./vectorDB.js").then(({ updateVectorDBStatusUI }) => {
        // Update vector DB status if it exists in the metadata
        if (taskData.metadata && taskData.metadata.vectorDBStatus) {
          state.vectorDBStatus = taskData.metadata.vectorDBStatus;
          updateVectorDBStatusUI();
        }
      });

      // If there are new logs, add them to the UI
      if (taskData.logs && taskData.logs.length > 0) {
        // Find logs that are not already in our state
        const existingLogs = new Set(state.processingLogs || []);
        const newLogs = taskData.logs.filter((log) => !existingLogs.has(log));

        // Add new logs to UI and state
        newLogs.forEach((log) => {
          $("#process-log-content").append(`<div>> ${log}</div>`);
          state.processingLogs = state.processingLogs || [];
          state.processingLogs.push(log);
        });

        // Auto-scroll to bottom if there are new logs
        if (newLogs.length > 0) {
          const logContainer = $("#process-log-content").parent();
          logContainer.scrollTop(logContainer[0].scrollHeight);
        }
      }
    }
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
  // We could pause long-running operations here or update status
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
