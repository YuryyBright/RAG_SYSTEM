// Message handling functionality

const MessageHandlers = {
  // Send a message to the backend
  sendMessage(messageText, attachedFiles = [], customParameters = {}) {
    if (!messageText && attachedFiles.length === 0) return;

    // Add user message to chat
    UIHandlers.addMessage(messageText, "user", false, attachedFiles);
    UIHandlers.elements.messageInput.value = "";

    // Show typing indicator
    UIHandlers.showTypingIndicator(true);

    // Prepare form data for files if any
    let requestData;
    let requestOptions = {
      headers: {
        "X-CSRF-TOKEN": document.querySelector('input[name="csrf_token"]').value
      }
    };

    if (attachedFiles.length > 0) {
      requestData = new FormData();
      requestData.append('message', messageText);
      requestData.append('rag_mode', ChatState.isRagMode);

      if (ChatState.isRagMode) {
        requestData.append('theme_id', ChatState.activeThemeId);
      }

      if (ChatState.conversationId) {
        requestData.append('conversation_id', ChatState.conversationId);
      }

      // Add advanced parameters
      Object.keys(customParameters).forEach(key => {
        requestData.append(key, customParameters[key]);
      });

      // Add files
      attachedFiles.forEach(file => {
        requestData.append('files', file);
      });

      requestOptions.method = 'POST';
      requestOptions.body = requestData;

    } else {
      // JSON request for text-only
      requestData = {
        message: messageText,
        rag_mode: ChatState.isRagMode,
        conversation_id: ChatState.conversationId
      };

      // Add theme if in RAG mode
      if (ChatState.isRagMode) {
        requestData.theme_id = ChatState.activeThemeId;
      }

      // Add advanced parameters
      Object.assign(requestData, customParameters);

      requestOptions.method = 'POST';
      requestOptions.headers['Content-Type'] = 'application/json';
      requestOptions.body = JSON.stringify(requestData);
    }

    // Send message to backend
    return fetch('/api/v1/chat', requestOptions)
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(response => {
        // Hide typing indicator
        UIHandlers.showTypingIndicator(false);

        // Add AI response to chat
        UIHandlers.addMessage(response.response, "ai");

        // Update conversation ID if needed
        if (!ChatState.conversationId && response.conversation_id) {
          ChatState.conversationId = response.conversation_id;
        }

        // Scroll to bottom
        UIHandlers.scrollToBottom();

        return response;
      })
      .catch(error => {
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
    return APIService.getChat(chatId)
      .then(response => {
        if (response.messages && response.messages.length > 0) {
          // Clear current chat
          UIHandlers.elements.chatContainer.innerHTML = "";

          // Set conversation ID
          ChatState.conversationId = chatId;

          // Add messages
          response.messages.forEach(msg => {
            const sender = msg.role === "user" ? "user" : "ai";
            UIHandlers.addMessage(msg.content, sender);
          });

          // Add typing indicator back
          UIHandlers.elements.chatContainer.insertAdjacentHTML('beforeend', `
            <div class="typing-indicator" id="typingIndicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          `);

          // Update typing indicator reference
          UIHandlers.elements.typingIndicator = document.getElementById('typingIndicator');

          // Hide typing indicator
          UIHandlers.showTypingIndicator(false);

          // Set RAG mode if applicable
          if (response.settings && response.settings.rag_mode !== undefined) {
            ChatState.isRagMode = response.settings.rag_mode;
            UIHandlers.elements.ragModeToggle.checked = ChatState.isRagMode;
            UIHandlers.updateFileUploadVisibility(ChatState.isRagMode);
          }

          // Set theme if applicable
          if (response.settings && response.settings.theme_id) {
            ChatState.activeThemeId = response.settings.theme_id;
            document.querySelectorAll('.theme-pill').forEach(pill => {
              pill.classList.remove("badge-info");
              pill.classList.add("badge-secondary");
            });
            document.querySelector(`.theme-pill[data-theme-id="${ChatState.activeThemeId}"]`)?.classList.add("badge-info");
          }

          alertify.success("Chat loaded successfully");
        }
      })
      .catch(() => {
        alertify.error("Failed to load chat");
      });
  }
};

// Export the module
window.MessageHandlers = MessageHandlers;