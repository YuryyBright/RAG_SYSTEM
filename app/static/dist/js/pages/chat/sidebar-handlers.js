// Sidebar functionality handling with jQuery

export const SidebarHandlers = {
  // Initialize sidebar handlers
  init: function () {
    this.setupThemeSelection();
    this.setupChatHistoryHandlers();
    this.setupKeyboardShortcuts();
  },

  // Setup theme selection functionality
  setupThemeSelection: function () {
    $("#themesContainer").on("click", ".theme-pill", function () {
      $(".theme-pill", $("#themesContainer")).removeClass("badge-info").addClass("badge-secondary");
      $(this).removeClass("badge-secondary").addClass("badge-info");

      // Update active theme ID in ChatState
      window.ChatState.activeThemeId = parseInt($(this).data("theme-id"));

      if (window.ChatState.isRagMode) {
        alertify.success(`Theme switched to "${$(this).text().trim()}"`);
      }
    });
  },

  // Setup chat history interaction handlers
  setupChatHistoryHandlers: function () {
    // Chat history item click
    $("#chatHistoryList").on("click", ".chat-history-item", function () {
      const chatId = $(this).data("id");
      window.MessageHandlers.loadChat(chatId);

      // Update visual selection
      $(".chat-history-item").removeClass("active");
      $(this).addClass("active");
    });

    // Clear chat history button
    $("#clearHistoryBtn").on("click", function () {
      if (confirm("Are you sure you want to clear all chat history?")) {
        window.APIService.clearChatHistory()
          .then(() => {
            $("#chatHistoryList").empty();
            alertify.success("Chat history cleared");
            location.reload();
          })
          .catch(() => alertify.error("Failed to clear chat history"));
      }
    });

    // Add "New Chat" button if it doesn't exist
    if ($("#newChatBtn").length === 0) {
      const $newChatBtn = $(
        '<button id="newChatBtn" class="btn btn-sm btn-outline-primary mr-2"><i class="fas fa-plus mr-1"></i> New Chat</button>'
      );
      $newChatBtn.on("click", function () {
        location.reload();
      });
      $("#clearHistoryBtn").before($newChatBtn);
    }
  },

  // Setup keyboard shortcuts
  setupKeyboardShortcuts: function () {
    // Ctrl+Enter to submit message
    $("#messageInput").on("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        $("#chatForm").submit();
      }
    });

    // Enter vs Shift+Enter behavior
    $("#messageInput").on("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        $("#chatForm").submit();
      }
    });
  },
};
