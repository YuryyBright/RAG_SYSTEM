// =====================================================================
// sidebar-handlers.js - IMPROVED VERSION
// =====================================================================

export const SidebarHandlers = {
  // Initialize sidebar handlers
  init: function () {
    this.setupThemeSelection();
    this.setupChatHistoryHandlers();
    this.setupKeyboardShortcuts();
    this.initializeNewChatButton();
  },

  // Setup theme selection functionality
  setupThemeSelection: function () {
    $("#themesContainer")
      .off("click")
      .on("click", ".theme-pill", function () {
        $(".theme-pill", $("#themesContainer")).removeClass("badge-info").addClass("badge-secondary");
        $(this).removeClass("badge-secondary").addClass("badge-info");

        // Update active theme ID in ChatState
        const newThemeId = parseInt($(this).data("theme-id"), 10);
        const previousThemeId = window.ChatState.activeThemeId;
        window.ChatState.activeThemeId = newThemeId;

        if (window.ChatState.isRagMode && newThemeId !== previousThemeId) {
          if (window.alertify) {
            alertify.success(`Theme switched to "${$(this).text().trim()}"`);
          } else if (window.UIHandlers) {
            window.UIHandlers.showToast(`Theme switched to "${$(this).text().trim()}"`, "success");
          }
        }
      });
  },

  // Setup chat history interaction handlers
  setupChatHistoryHandlers: function () {
    // Chat history item click
    $("#chatHistoryList")
      .off("click")
      .on("click", ".chat-history-item", function () {
        const chatId = $(this).data("id");

        if (!chatId) {
          console.error("Chat history item clicked without a valid ID");
          return;
        }

        window.MessageHandlers.loadChat(chatId).catch((err) => {
          console.error("Error loading chat:", err);
        });

        // Update visual selection
        $(".chat-history-item").removeClass("active");
        $(this).addClass("active");
      });

    // Clear chat history button
    $("#clearHistoryBtn")
      .off("click")
      .on("click", function () {
        if (confirm("Are you sure you want to clear all chat history?")) {
          window.APIService.clearChatHistory()
            .then(() => {
              $("#chatHistoryList").empty();
              if (window.alertify) {
                alertify.success("Chat history cleared");
              } else if (window.UIHandlers) {
                window.UIHandlers.showToast("Chat history cleared", "success");
              }
              location.reload();
            })
            .catch((error) => {
              console.error("Failed to clear chat history:", error);
              if (window.alertify) {
                alertify.error("Failed to clear chat history");
              } else if (window.UIHandlers) {
                window.UIHandlers.showToast("Failed to clear chat history", "error");
              }
            });
        }
      });
  },

  // Initialize New Chat button
  initializeNewChatButton: function () {
    // Add "New Chat" button if it doesn't exist
    if ($("#newChatBtn").length === 0) {
      const $clearHistoryBtn = $("#clearHistoryBtn");
      if ($clearHistoryBtn.length) {
        const $newChatBtn = $(
          '<button id="newChatBtn" class="btn btn-sm btn-outline-primary mr-2"><i class="fas fa-plus mr-1"></i> New Chat</button>'
        );
        $newChatBtn.on("click", function () {
          // Reset conversation
          window.ChatState.conversationId = null;

          // Clear chat container
          if (window.UIHandlers && window.UIHandlers.elements.$chatContainer) {
            window.UIHandlers.elements.$chatContainer.html("");

            // Add typing indicator back
            window.UIHandlers.elements.$chatContainer.append(`
              <div class="typing-indicator" id="typingIndicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            `);

            // Update typing indicator reference
            window.UIHandlers.elements.$typingIndicator = $("#typingIndicator");
            window.UIHandlers.showTypingIndicator(false);
          }

          // Clear message input
          if (window.UIHandlers && window.UIHandlers.elements.$messageInput) {
            window.UIHandlers.elements.$messageInput.val("").focus();
          }

          // Show toast
          if (window.UIHandlers) {
            window.UIHandlers.showToast("Started a new chat", "success");
          }
        });
        $clearHistoryBtn.before($newChatBtn);
      }
    }
  },

  // Setup keyboard shortcuts
  setupKeyboardShortcuts: function () {
    // Ctrl+Enter to submit message
    $("#messageInput")
      .off("keydown.ctrlEnter")
      .on("keydown.ctrlEnter", function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
          e.preventDefault();
          $("#chatForm").submit();
        }
      });

    // Enter vs Shift+Enter behavior
    $("#messageInput")
      .off("keydown.enter")
      .on("keydown.enter", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          $("#chatForm").submit();
        }
      });
  },
};
