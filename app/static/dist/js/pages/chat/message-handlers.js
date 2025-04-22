// Message related functionality
import { UIHandlers } from './ui-handlers.js';

export const MessageHandlers = {
  // Send a message to the backend
  sendMessage(messageText, attachedFiles = [], customParameters = {}) {
    if (!messageText && attachedFiles.length === 0) return;

    // Add user message to chat
    UIHandlers.addMessage(messageText, "user", false, attachedFiles);
    UIHandlers.elements.$messageInput.val("");

    // Show typing indicator
    UIHandlers.showTypingIndicator(true);

    // Prepare form data for files if any
    let requestData;
    let requestOptions = {
      headers: {
        "X-CSRF-TOKEN": document.querySelector('input[name="csrf_token"]').value,
      },
    };

    if (attachedFiles.length > 0) {
      requestData = new FormData();
      requestData.append("message", messageText);
      requestData.append("rag_mode", window.ChatState.isRagMode);

      if (window.ChatState.isRagMode) {
        requestData.append("theme_id", window.ChatState.activeThemeId);
      }

      if (window.ChatState.conversationId) {
        requestData.append("conversation_id", window.ChatState.conversationId);
      }

      // Add model ID directly from ChatState
      if (window.ChatState.activeModelId) {
        requestData.append("model_id", window.ChatState.activeModelId);
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
        message: messageText,
        rag_mode: window.ChatState.isRagMode,
        conversation_id: window.ChatState.conversationId,
      };

      // Add theme if in RAG mode
      if (window.ChatState.isRagMode) {
        requestData.theme_id = window.ChatState.activeThemeId;
      }

      // Add model ID directly from ChatState
      if (window.ChatState.activeModelId) {
        requestData.model_id = window.ChatState.activeModelId;
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
    return fetch("/api/v1/chat", requestOptions)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((response) => {
        // Hide typing indicator
        UIHandlers.showTypingIndicator(false);

        // Add AI response to chat
        UIHandlers.addMessage(response.response, "ai");

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
        alertify.error("Error sending message");

        // Scroll to bottom
        UIHandlers.scrollToBottom();

        throw error;
      });
  },

  // Load a specific chat
  loadChat(chatId) {
    return window.APIService.getChat(chatId)
      .then((response) => {
        if (response.messages && response.messages.length > 0) {
          // Clear current chat
          UIHandlers.elements.$chatContainer.html("");

          // Set conversation ID
          window.ChatState.conversationId = chatId;

          // Add messages
          response.messages.forEach((msg) => {
            const sender = msg.role === "user" ? "user" : "ai";
            UIHandlers.addMessage(msg.content, sender);
          });

          // Add typing indicator back
          UIHandlers.elements.$chatContainer.append(`
            <div class="typing-indicator" id="typingIndicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          `);

          // Update typing indicator reference
          UIHandlers.elements.$typingIndicator = $("#typingIndicator");

          // Hide typing indicator
          UIHandlers.showTypingIndicator(false);

          // Set RAG mode if applicable
          if (response.settings && response.settings.rag_mode !== undefined) {
            window.ChatState.isRagMode = response.settings.rag_mode;
            UIHandlers.elements.$ragModeToggle.prop("checked", window.ChatState.isRagMode);
            UIHandlers.updateFileUploadVisibility(window.ChatState.isRagMode);
          }

          // Set theme if applicable
          if (response.settings && response.settings.theme_id) {
            window.ChatState.activeThemeId = response.settings.theme_id;
            $(".theme-pill", $("#themesContainer")).removeClass("badge-info").addClass("badge-secondary");
            $(`.theme-pill[data-theme-id="${window.ChatState.activeThemeId}"]`, $("#themesContainer")).addClass("badge-info");
          }

          // Set model if applicable
          if (response.settings && response.settings.model_id) {
            window.ChatState.activeModelId = response.settings.model_id;
            $(".theme-pill", $("#LLMContainer")).removeClass("badge-info").addClass("badge-secondary");
            $(`.theme-pill[data-model-id="${window.ChatState.activeModelId}"]`, $("#LLMContainer")).addClass("badge-info");
          }

          alertify.success("Chat loaded successfully");
        }
      })
      .catch(() => {
        alertify.error("Failed to load chat");
      });
  },
};