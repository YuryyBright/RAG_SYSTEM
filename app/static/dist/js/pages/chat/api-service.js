// API Service for handling backend communication (jQuery version)

export const APIService = {
  // Load available themes
  loadThemes() {
    return $.ajax({
      url: "/api/themes",
      method: "GET",
      dataType: "json",
    })
      .then((response) => {
        if (response && response.length > 0) {
          const $themesContainer = $("#themesContainer");
          $themesContainer.empty();

          // Add themes to container
          response.forEach((theme, index) => {
            const badgeClass = index === 0 ? "badge-info" : "badge-secondary";
            $themesContainer.append(`
            <div class="badge ${badgeClass} theme-pill m-1 p-2" data-theme-id="${theme.id}">
              ${theme.name}
            </div>
          `);
          });
        }
        return response.themes;
      })
      .catch((error) => {
        console.error("Error loading themes:", error);
        throw new Error("Network response was not ok");
      });
  },

  // Load chat history
  loadChatHistory() {
    return $.ajax({
      url: "/api/conversations/history",
      method: "GET",
      dataType: "json",
    })
      .then((response) => {
        if (response.history && response.history.length > 0) {
          const $chatHistoryList = $("#chatHistoryList");
          $chatHistoryList.empty();

          // Add history items
          response.history.forEach((chat) => {
            const timeAgo = UIHandlers.formatTimeAgo(new Date(chat.created_at));
            $chatHistoryList.append(`
            <li class="list-group-item d-flex justify-content-between align-items-center chat-history-item" 
                data-id="${chat.id}">
              <span>${chat.title || "Chat Session"}</span>
              <span class="badge badge-primary badge-pill">${timeAgo}</span>
            </li>
          `);
          });
        }
        return response.history;
      })
      .catch((error) => {
        console.error("Error loading chat history:", error);
        throw new Error("Network response was not ok");
      });
  },

  // Get a specific chat
  getChat(chatId) {
    return $.ajax({
      url: `/api/v1/chat/${chatId}`,
      method: "GET",
      dataType: "json",
    }).catch((error) => {
      console.error("Error loading chat:", error);
      throw new Error("Network response was not ok");
    });
  },

  // Load models
  loadModels() {
    return $.ajax({
      url: "/api/v1/models",
      method: "GET",
      dataType: "json",
    })
      .then((data) => data.models)
      .catch((error) => {
        console.error("Failed to load models:", error);
        throw new Error("Failed to load models");
      });
  },

  // Clear chat history
  clearChatHistory() {
    return $.ajax({
      url: "/api/v1/chat/history",
      method: "DELETE",
      dataType: "json",
    }).catch((error) => {
      console.error("Error clearing chat history:", error);
      throw new Error("Network response was not ok");
    });
  },
};
