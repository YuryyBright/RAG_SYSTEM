/**
 * Enhanced request helper with automatic retries for auth issues
 */
const RequestHelper = {
  /**
   * Make an authenticated API request with automatic retry on auth failure
   * @param {Object} options - Request options
   * @param {string} options.url - Request URL
   * @param {string} options.method - HTTP method (GET, POST, etc.)
   * @param {Object} options.data - Request payload
   * @param {boolean} options.retry - Whether to retry on auth failure
   * @returns {Promise} - Promise resolving to response data
   */
  request: function (options) {
    const { url, method = "GET", data, retry = true } = options;

    // Create a unique request ID to track retries
    const requestId = Date.now().toString();

    return this._makeRequest(url, method, data, requestId, retry);
  },

  /**
   * Internal method to make the actual request with retry logic
   */
  _makeRequest: function (url, method, data, requestId, canRetry, retryCount = 0) {
    const ajaxSettings = {
      url: url,
      method: method,
      dataType: "json",
      cache: false,
    };

    // Add data if provided
    if (data) {
      if (method === "GET") {
        ajaxSettings.data = data;
      } else {
        ajaxSettings.contentType = "application/json";
        ajaxSettings.data = JSON.stringify(data);
      }
    }

    return $.ajax(ajaxSettings).catch((error) => {
      // Handle authentication errors with retry
      if (canRetry && retryCount < 1 && (error.status === 401 || error.status === 403)) {
        console.log(`Auth error on request ${requestId}, attempting to refresh session`);

        // Try to refresh the authentication
        return this._refreshAuth()
          .then(() => {
            console.log(`Retrying request ${requestId} after auth refresh`);
            // Retry the original request with retry disabled to prevent loops
            return this._makeRequest(url, method, data, requestId, false, retryCount + 1);
          })
          .catch((refreshError) => {
            console.error("Auth refresh failed:", refreshError);
            // Re-throw the original error
            throw error;
          });
      }

      // For other errors or if retry fails, just propagate the error
      throw error;
    });
  },

  /**
   * Refresh authentication before retrying
   */
  _refreshAuth: function () {
    // Check which auth method we're using
    if (AuthManager.getToken()) {
      return AuthManager.refreshToken();
    } else {
      return AuthManager.refreshSession();
    }
  },

  /**
   * Convenience method for GET requests
   */
  get: function (url, data) {
    return this.request({ url, method: "GET", data });
  },

  /**
   * Convenience method for POST requests
   */
  post: function (url, data) {
    return this.request({ url, method: "POST", data });
  },

  /**
   * Convenience method for PUT requests
   */
  put: function (url, data) {
    return this.request({ url, method: "PUT", data });
  },

  /**
   * Convenience method for DELETE requests
   */
  delete: function (url) {
    return this.request({ url, method: "DELETE" });
  },
};
