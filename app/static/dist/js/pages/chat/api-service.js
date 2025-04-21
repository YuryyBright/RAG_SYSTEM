// API Service for handling backend communication

const APIService = {
  // Load available themes
  loadThemes() {
    return fetch("/api/v1/themes")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((response) => {
        if (response.themes && response.themes.length > 0) {
          const themesContainer = document.getElementById("themesContainer");
          themesContainer.innerHTML = "";

          // Add themes to container
          response.themes.forEach((theme, index) => {
            const badgeClass = index === 0 ? "badge-info" : "badge-secondary";
            themesContainer.insertAdjacentHTML(
              "beforeend",
              `
              <div class="badge ${badgeClass} theme-pill m-1 p-2" data-theme-id="${theme.id}">
                ${theme.name}
              </div>
            `
            );
          });
        }
        return response.themes;
      });
  },

  // Load chat history
  loadChatHistory() {
    return fetch("/api/v1/chat/history")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((response) => {
        if (response.history && response.history.length > 0) {
          const chatHistoryList = document.getElementById("chatHistoryList");
          chatHistoryList.innerHTML = "";

          // Add history items
          response.history.forEach((chat) => {
            const timeAgo = UIHandlers.formatTimeAgo(new Date(chat.created_at));
            chatHistoryList.insertAdjacentHTML(
              "beforeend",
              `
              <li class="list-group-item d-flex justify-content-between align-items-center chat-history-item" 
                  data-id="${chat.id}">
                <span>${chat.title || "Chat Session"}</span>
                <span class="badge badge-primary badge-pill">${timeAgo}</span>
              </li>
            `
            );
          });
        }
        return response.history;
      });
  },

  // Get a specific chat
  getChat(chatId) {
    return fetch(`/api/v1/chat/${chatId}`).then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    });
  },

  // Clear chat history
  clearChatHistory() {
    return fetch("/api/v1/chat/history", {
      method: "DELETE",
      headers: {
        "X-CSRF-TOKEN": document.querySelector('input[name="csrf_token"]').value,
      },
    }).then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    });
  },
};

// Export the module
window.APIService = APIService;
