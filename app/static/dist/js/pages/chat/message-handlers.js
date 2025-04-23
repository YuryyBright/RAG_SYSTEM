// =====================================================================
// message-handlers.js - IMPROVED VERSION
// =====================================================================

import { UIHandlers } from "./ui-handlers.js";

export const MessageHandlers = {
  // Send a message to the backend
  sendMessage(messageText, attachedFiles = [], customParameters = {}) {
    if (!messageText && (!attachedFiles || attachedFiles.length === 0)) {
      return Promise.reject(new Error("No message content or files provided"));
    }

    // Add user message to chat
    UIHandlers.addMessage(messageText, "user", false, attachedFiles);
    UIHandlers.elements.$messageInput.val("");

    // Show typing indicator
    UIHandlers.showTypingIndicator(true);

    // Prepare form data for files if any
    let requestData;
    let requestOptions = {
      headers: {
        "X-CSRF-TOKEN": document.querySelector('input[name="csrf_token"]')?.value || "",
      },
    };

    // Handle file attachments using FormData
    if (attachedFiles && attachedFiles.length > 0) {
      requestData = new FormData();
      requestData.append("message", messageText || "");
      requestData.append("rag_mode", window.ChatState.isRagMode ? "true" : "false");

      if (window.ChatState.isRagMode && window.ChatState.activeThemeId) {
        requestData.append("theme_id", window.ChatState.activeThemeId);
      }

      if (window.ChatState.conversationId) {
        requestData.append("conversation_id", window.ChatState.conversationId);
      }

      // Add model ID from ChatState
      if (window.ChatState.activeModelId) {
        requestData.append("model_id", window.ChatState.activeModelId);
      } else if (window.ChatState.models && window.ChatState.models.length > 0) {
        // Fallback to first model if none selected
        requestData.append("model_id", window.ChatState.models[0].id);
      }

      // Add advanced parameters
      Object.keys(customParameters).forEach((key) => {
        if (key !== "model") {
          // Exclude model to prevent conflicts
          requestData.append(key, customParameters[key]);
        }
      });

      // Add files
      attachedFiles.forEach((file) => {
        requestData.append("files", file);
      });

      requestOptions.method = "POST";
      requestOptions.body = requestData;
    } else {
      // JSON request for text-only
      requestData = {
        message: messageText || "",
        rag_mode: window.ChatState.isRagMode,
      };

      // Add conversation ID if present
      if (window.ChatState.conversationId) {
        requestData.conversation_id = window.ChatState.conversationId;
      }

      // Add theme if in RAG mode
      if (window.ChatState.isRagMode && window.ChatState.activeThemeId) {
        requestData.theme_id = window.ChatState.activeThemeId;
      }

      // Add model ID from ChatState
      if (window.ChatState.activeModelId) {
        requestData.model_id = window.ChatState.activeModelId;
      } else if (window.ChatState.models && window.ChatState.models.length > 0) {
        // Fallback to first model if none selected
        requestData.model_id = window.ChatState.models[0].id;
      }

      // Add advanced parameters, excluding 'model' to prevent conflicts
      Object.keys(customParameters).forEach((key) => {
        if (key !== "model") {
          requestData[key] = customParameters[key];
        }
      });

      requestOptions.method = "POST";
      requestOptions.headers["Content-Type"] = "application/json";
      requestOptions.body = JSON.stringify(requestData);
    }

    // Send message to backend
    return fetch("/api/conversations/chat", requestOptions)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Network response error: ${response.status} ${response.statusText}`);
        }
        return response.json();
      })
      .then((response) => {
        // Hide typing indicator
        UIHandlers.showTypingIndicator(false);

        // Add AI response to chat
        const responseText =
          typeof response.response === "string" ? response.response : response.response?.text || "[No response text]";

        UIHandlers.addMessage(responseText, "ai");

        // Update conversation ID if needed
        if (!window.ChatState.conversationId && response.conversation_id) {
          window.ChatState.conversationId = response.conversation_id;
        }

        // Scroll to bottom
        UIHandlers.scrollToBottom();

        return response;
      })
      .catch((error) => {
        // Hide typing indicator
        UIHandlers.showTypingIndicator(false);

        // Show error message
        UIHandlers.addMessage("Sorry, I encountered an error processing your request. Please try again.", "ai", true);
        console.error("Chat API error:", error);

        // Show toast error
        if (window.alertify) {
          alertify.error("Error sending message");
        } else {
          UIHandlers.showToast("Error sending message", "error");
        }

        // Scroll to bottom
        UIHandlers.scrollToBottom();

        throw error;
      });
  },

  // Load a specific chat
  loadChat(chatId) {
    if (!chatId) {
      UIHandlers.showToast("Invalid chat ID", "error");
      return Promise.reject(new Error("Invalid chat ID"));
    }

    return window.APIService.getChat(chatId)
      .then((response) => {
        if (response && response.messages && Array.isArray(response.messages)) {
          const container = UIHandlers.elements.$chatContainer;
          container.html(""); // Clear chat
          window.ChatState.conversationId = chatId;

          const BATCH_SIZE = 10;
          let currentIndex = 0;

          const renderBatch = () => {
            const fragment = document.createDocumentFragment();

            for (let i = 0; i < BATCH_SIZE && currentIndex < response.messages.length; i++, currentIndex++) {
              const msg = response.messages[currentIndex];
              const sender = msg.role === "user" ? "user" : "ai";
              const messageElement = createMessageElement(msg.content, sender, msg.created_at);
              fragment.appendChild(messageElement);
            }

            container[0].appendChild(fragment);

            if (currentIndex < response.messages.length) {
              requestAnimationFrame(renderBatch);
            } else {
              container.append(`
              <div class="typing-indicator" id="typingIndicator">
                <span></span><span></span><span></span>
              </div>
            `);
              UIHandlers.elements.$typingIndicator = $("#typingIndicator");
              UIHandlers.showTypingIndicator(false);
              UIHandlers.scrollToBottom();
            }
          };

          renderBatch(); // Start rendering

          // Update chat state
          if (response.settings && response.settings.rag_mode !== undefined) {
            window.ChatState.isRagMode = !!response.settings.rag_mode;
            UIHandlers.elements.$ragModeToggle.prop("checked", window.ChatState.isRagMode);
            UIHandlers.updateFileUploadVisibility(window.ChatState.isRagMode);
          }

          if (response.settings && response.settings.theme_id) {
            window.ChatState.activeThemeId = response.settings.theme_id;
            $(".theme-pill", $("#themesContainer")).removeClass("badge-info").addClass("badge-secondary");
            $(`.theme-pill[data-theme-id="${window.ChatState.activeThemeId}"]`, $("#themesContainer"))
              .removeClass("badge-secondary")
              .addClass("badge-info");
          }

          if (response.settings && response.settings.model_id) {
            window.ChatState.activeModelId = response.settings.model_id;
            $(".model-pill", $("#LLMContainer")).removeClass("badge-info").addClass("badge-secondary");
            $(`.model-pill[data-model-id="${window.ChatState.activeModelId}"]`, $("#LLMContainer"))
              .removeClass("badge-secondary")
              .addClass("badge-info");
          }

          UIHandlers.showToast("Chat loaded successfully", "success");
          return response;
        } else {
          throw new Error("Invalid chat data format");
        }
      })
      .catch((error) => {
        UIHandlers.showToast("Failed to load chat", "error");
        console.error("Failed to load chat:", error);
        throw error;
      });
  },
};

function createMessageElement(content, sender, createdAt = "Just now") {
  const isAI = sender === "ai";

  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${isAI ? "ai-message" : "user-message"}`;

  // Message info (avatar + sender)
  const infoDiv = document.createElement("div");
  infoDiv.className = "message-info";

  const avatarDiv = document.createElement("div");
  avatarDiv.className = "message-avatar";
  avatarDiv.textContent = isAI ? "AI" : "You";

  const senderDiv = document.createElement("div");
  senderDiv.className = "message-sender";
  senderDiv.textContent = isAI ? "Powerfull AI Assistant" : "You";

  infoDiv.appendChild(avatarDiv);
  infoDiv.appendChild(senderDiv);

  // Message content
  const contentDiv = document.createElement("div");
  contentDiv.className = "message-content";
  content.split("\n").forEach((line) => {
    const p = document.createElement("p");
    p.textContent = line;
    contentDiv.appendChild(p);
  });

  // Message time
  const timeDiv = document.createElement("div");
  timeDiv.className = "message-time";
  timeDiv.textContent = new Date(createdAt).toLocaleTimeString();

  // Message actions
  const actionsDiv = document.createElement("div");
  actionsDiv.className = "message-actions";

  const copyBtn = document.createElement("button");
  copyBtn.className = "message-action-btn copy-btn";
  copyBtn.innerHTML = `<i class="fas fa-copy"></i> Copy`;
  copyBtn.onclick = () => navigator.clipboard.writeText(content);

  const regenBtn = document.createElement("button");
  regenBtn.className = "message-action-btn regenerate-btn";
  regenBtn.innerHTML = `<i class="fas fa-redo-alt"></i> Regenerate`;
  regenBtn.onclick = () => {
    if (window.UIHandlers.handleRegenerate) {
      window.UIHandlers.handleRegenerate(content);
    } else {
      console.warn("No regenerate handler defined.");
    }
  };

  actionsDiv.appendChild(copyBtn);
  if (isAI) actionsDiv.appendChild(regenBtn);

  // Final assembly
  messageDiv.appendChild(infoDiv);
  messageDiv.appendChild(contentDiv);
  messageDiv.appendChild(timeDiv);
  messageDiv.appendChild(actionsDiv);

  return messageDiv;
}
