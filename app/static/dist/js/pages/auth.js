// Enhanced auth.js with improved session expiration and server-side session handling

/**
 * Handles authentication token storage, retrieval, and session management
 */
// === Timer & Retry Constants ===
const TOKEN_EXPIRY_THRESHOLD = 5 * 60 * 1000; // 5 minutes
const TWENTY_FOUR_HOURS = 24 * 60 * 60 * 1000; // 24 hours in ms
const SESSION_EXPIRY_24_HOURS = 24 * 60 * 60 * 1000; // 24 hours in ms
const MINUTES_DIVISOR = 24 * 60 * 60 * 1000; // 24 hours in ms
const INITIAL_RETRY_DELAY = 24 * 60 * 60 * 1000; // 24 hours in ms
const CSRF_RETRY_DELAY = 24 * 60 * 60 * 1000; // 24 hours in ms
const SESSION_RETRY_DELAY = 24 * 60 * 60 * 1000; // 24 hours in ms
const SESSION_VALIDATOR_INTERVAL = 24 * 60 * 60 * 1000; // 24 hours in ms
const DEFAULT_SESSION_EXPIRY = 24 * 60 * 60 * 1000; // 24 hours in ms
const AuthManager = {
  // Timer references
  sessionRefreshTimer: null,
  csrfRefreshTimer: null,
  // Max retry attempts for refresh operations
  maxRetries: 3,
  currentRetries: 0,

  /**
   * Store authentication token after login
   * @param {Object} response - Login response containing token data
   * @param {boolean} remember - Whether to remember the token across sessions
   */
  storeToken: function (response, remember) {
    // Store token data
    const tokenData = {
      accessToken: response.access_token,
      tokenType: response.token_type,
      expiresAt: response.expires_at,
      userId: response.user_id,
      username: response.username,
    };

    // Use localStorage for "remember me", sessionStorage otherwise
    const storage = remember ? localStorage : sessionStorage;
    storage.setItem("authToken", JSON.stringify(tokenData));

    // Schedule token refresh if expiration is provided
    if (response.expires_at) {
      this.setupTokenRefresh(new Date(response.expires_at));
    }
  },

  /**
   * Store session data after cookie-based login
   * @param {Object} response - Session response from login
   */
  storeSession: function (response) {
    if (response.csrf_token) {
      sessionStorage.setItem("csrfToken", response.csrf_token);
    }
    if (response.access_token) {
      sessionStorage.setItem("accessToken", response.access_token); // typo fixed
    }
    const userData = {
      userId: response.user_id,
      username: response.username,
      expiresAt: response.expires_at,
    };
    sessionStorage.setItem("userData", JSON.stringify(userData));
    if (response.expires_at) {
      this.setupSessionRefresh(new Date(response.expires_at));
    }
  },

  /**
   * Setup a timer to refresh the authentication token before it expires.
   * It clears any existing timers, calculates the appropriate time to refresh,
   * and sets a new timer to refresh the token.
   *
   * @param {Date} expiryDate - The expiration date of the current token
   */
  setupTokenRefresh: function (expiryDate) {
    if (!expiryDate) return;
    if (this.tokenRefreshTimer) clearTimeout(this.tokenRefreshTimer);

    const timeUntilExpiry = expiryDate.getTime() - Date.now();
    const refreshTime = Math.max(timeUntilExpiry * 0.8, TOKEN_EXPIRY_THRESHOLD);

    this.tokenRefreshTimer = setTimeout(() => {
      if (Date.now() < expiryDate.getTime()) {
        this.refreshToken();
      } else {
        this.handleSessionExpiration();
      }
    }, refreshTime);
  },

  /**
   * Setup a timer to refresh the session before it expires.
   * Similar to token refresh, it manages timers and schedules a session refresh.
   *
   * @param {Date} expiryDate - The expiration date of the current session
   */
  setupSessionRefresh: function (expiryDate) {
    if (!expiryDate) return;
    if (this.sessionRefreshTimer) clearTimeout(this.sessionRefreshTimer);

    const timeUntilExpiry = expiryDate.getTime() - Date.now();
    const refreshTime = Math.max(timeUntilExpiry * 0.8, TOKEN_EXPIRY_THRESHOLD);

    this.sessionRefreshTimer = setTimeout(() => {
      if (Date.now() < expiryDate.getTime()) {
        this.refreshSession();
      } else {
        this.handleSessionExpiration();
      }
    }, refreshTime);
  },

  /**
   * Refresh authentication token
   * @returns {Promise} Promise resolving when token is refreshed
   */
  refreshToken: function () {
    console.log("Refreshing authentication token");
    return $.ajax({
      url: "/api/auth/refresh-token",
      method: "POST",
      dataType: "json",
    })
      .then((response) => {
        // Reset retry counter on success
        this.currentRetries = 0;
        this.storeToken(response, this.isRemembered());
        console.log("Token refreshed successfully");
        return response;
      })
      .catch((error) => {
        console.error("Failed to refresh token:", error);

        // Check if backend session is invalid/deleted
        if (error.status === 401 || error.status === 403) {
          this.handleSessionExpiration();
        } else if (this.currentRetries < this.maxRetries) {
          // Try again after a delay if it's a server error
          this.currentRetries++;
          const retryDelay = INITIAL_RETRY_DELAY * this.currentRetries; // Increasing backoff
          console.log(`Retry ${this.currentRetries}/${this.maxRetries} in ${retryDelay / 1000}s`);
          setTimeout(() => this.refreshToken(), retryDelay);
        } else {
          // Max retries reached, force re-authentication
          console.log("Max retry attempts reached, session may be invalid");
          this.verifyServerSession();
        }
      });
  },

  /**
   * Refresh session cookie
   * @returns {Promise} Promise resolving when session is refreshed
   */
  refreshSession: function () {
    console.log("Refreshing session");
    return $.ajax({
      url: "/api/auth/refresh-session",
      method: "POST",
      headers: {
        "X-CSRF-Token": this.getCsrfToken(),
      },
      dataType: "json",
    })
      .then((response) => {
        // Reset retry counter on success
        this.currentRetries = 0;
        this.storeSession(response);
        console.log("Session refreshed successfully");
        return response;
      })
      .catch((error) => {
        console.error("Failed to refresh session:", error);

        // Check if backend session is invalid/deleted
        if (error.status === 401 || error.status === 403) {
          this.handleSessionExpiration();
        } else if (this.currentRetries < this.maxRetries) {
          // Try again after a delay if it's a server error
          this.currentRetries++;
          const retryDelay = INITIAL_RETRY_DELAY * this.currentRetries; // Increasing backoff
          console.log(`Retry ${this.currentRetries}/${this.maxRetries} in ${retryDelay / 1000}s`);
          setTimeout(() => this.refreshSession(), retryDelay);
        } else {
          // Max retries reached, verify server session
          console.log("Max retry attempts reached, verifying server session");
          this.verifyServerSession();
        }
      });
  },
  /**
   * Setup server session validator that checks periodically
   * This ensures we detect server-side session deletions even when frontends don't know
   */
  setupSessionValidator: function (interval = SESSION_VALIDATOR_INTERVAL) {
    // 5 minutes by default
    // Clear any existing validator
    if (this.sessionValidatorTimer) {
      clearInterval(this.sessionValidatorTimer);
    }

    // Set up periodic validation
    this.sessionValidatorTimer = setInterval(() => {
      // Only check if we think we're authenticated
      if (this.isAuthenticated()) {
        this.verifyServerSession().catch((error) => {
          console.error("Session validation failed:", error);
          // If server explicitly returns session_not_found error, clear auth immediately
          if (
            error?.responseJSON?.error === "session_not_found" ||
            error?.responseJSON?.detail === "Session not found"
          ) {
            console.warn("Server reported session not found, clearing auth data");
            this.handleSessionExpiration();
          }
        });
      }
    }, interval);

    console.log(`Session validator initialized with ${interval / 60000} minute interval`);
  },
  /**
   * Verify if the server-side session is still valid
   * Makes a direct call to /me endpoint to check authentication status
   */
  verifyServerSession: function () {
    console.log("Verifying server-side session");
    return $.ajax({
      url: "/api/auth/me",
      method: "GET",
      dataType: "json",
    })
      .then(() => {
        // Session is valid on server, try refreshing CSRF token
        console.log("Server session valid, refreshing CSRF token");
        this.currentRetries = 0;
        return this.refreshCsrfToken();
      })
      .catch((error) => {
        console.error("Server session verification failed:", error);

        // If server explicitly reports session not found
        if (error?.responseJSON?.error === "session_not_found" || error?.responseJSON?.detail === "Session not found") {
          console.warn("Server reported session not found, clearing auth data");
          this.handleSessionExpiration();
        }
        // Handle other auth errors
        else if (error.status === 401 || error.status === 403) {
          this.handleSessionExpiration();
        } else {
          // Server error but not auth-related, try one more time later
          setTimeout(() => this.verifyServerSession(), SESSION_RETRY_DELAY);
        }

        // Propagate the error
        return Promise.reject(error);
      });
  },
  /**
   * Refresh CSRF token
   * @returns {Promise} Promise resolving when token is refreshed
   */
  refreshCsrfToken: function () {
    console.log("Refreshing CSRF token");

    // If we are not even authenticated or we have no session/cookie, bail out early
    if (!this.isAuthenticated()) {
      console.warn("No valid session or token - skipping refreshCsrfToken()");
      return Promise.resolve(); // Do nothing
    }

    // If we’ve tried too many times, stop
    if (this.currentRetries >= this.maxRetries) {
      console.warn("Max CSRF refresh retries reached");
      this.verifyServerSession(); // Last-ditch check
      return Promise.resolve();
    }

    this.currentRetries++;

    // Notice we do NOT manually add X-CSRF-Token for this route:
    // In setupAjaxHeaders(), we skip it if URL contains /api/auth/refresh-csrf.
    return $.ajax({
      url: "/api/auth/refresh-csrf",
      method: "POST", // or GET, if that’s how your server is set up
      dataType: "json",
    })
      .then((response) => {
        this.currentRetries = 0;
        if (response.csrf_token) {
          sessionStorage.setItem("csrfToken", response.csrf_token);
          console.log("CSRF token refreshed successfully");
        }
        return response;
      })
      .catch((error) => {
        console.error("Failed to refresh CSRF token:", error);
        if (error.status === 401 || error.status === 403) {
          this.handleSessionExpiration();
        } else if (this.currentRetries < this.maxRetries) {
          // Try again after a delay
          setTimeout(() => this.refreshCsrfToken(), CSRF_RETRY_DELAY);
        } else {
          this.verifyServerSession();
        }
        return Promise.reject(error);
      });
  },

  /**
   * Handle session expiration consistently
   */
  handleSessionExpiration: function () {
    console.log("Handling session expiration - clearing all auth data");

    // Clear all local auth data
    this.clearAuth();

    // Make a backend call to actually logout and clear cookies
    // Use a simple fetch to avoid jQuery dependency issues after clearing auth
    fetch("/api/auth/logout", {
      method: "POST",
      headers: {
        "X-CSRF-Token": this.getCsrfToken() || "",
        "Content-Type": "application/json",
      },
      credentials: "same-origin", // Important for cookies
    })
      .catch((error) => {
        // Log but don't block the redirect process
        console.warn("Error during session cleanup:", error);
      })
      .finally(() => {
        // Check if we're already on the login page to avoid redirect loops
        if (!window.location.pathname.includes("/auth/login")) {
          // Redirect to login with expired session flag
          window.location.href = "/auth/login?session_expired=true";
        } else {
          // Just show a message if we're already on the login page
          alertify.error("Your session has expired. Please log in again.");
          // Reload page to clear any form state
          setTimeout(() => window.location.reload(), 2000);
        }
      });
  },

  /**yy
   * Get stored CSRF token
   * @returns {string|null} CSRF token or null if not found
   */
  getCsrfToken: function () {
    // Try sessionStorage first
    const sessionToken = sessionStorage.getItem("csrfToken");
    if (sessionToken) {
      return sessionToken;
    }

    // Fall back to cookie extraction (less reliable but works as backup)
    const csrfCookie = document.cookie.split("; ").find((row) => row.startsWith("X-CSRF-Token="));
    return csrfCookie ? decodeURIComponent(csrfCookie.split("=")[1]) : null;
  },

  /**
   * Get the stored authentication token
   * @returns {Object|null} Token data or null if not found
   */
  getToken: function () {
    // Try sessionStorage first, then localStorage
    let tokenData = sessionStorage.getItem("authToken");
    if (!tokenData) {
      tokenData = localStorage.getItem("authToken");
    }

    if (!tokenData) {
      return null;
    }

    const parsedToken = JSON.parse(tokenData);

    // Check if token is expired
    if (new Date(parsedToken.expiresAt) < new Date()) {
      console.log("Token expired during getToken check");
      this.removeToken();
      return null;
    }

    return parsedToken;
  },

  /**
   * Check if user chose "remember me" option
   * @returns {boolean} True if using localStorage (remembered)
   */
  isRemembered: function () {
    return localStorage.getItem("authToken") !== null;
  },

  /**
   * Get user data from session storage
   * @returns {Object|null} User data or null
   */
  getUserData: function () {
    const userData = sessionStorage.getItem("userData");
    if (!userData) return null;

    const parsedData = JSON.parse(userData);

    // Check if session data is expired
    if (parsedData.expiresAt && new Date(parsedData.expiresAt) < new Date()) {
      console.log("User session expired during getUserData check");
      this.removeUserData();
      return null;
    }

    return parsedData;
  },

  /**
   * Add authorization header to AJAX requests
   */
  setupAjaxHeaders: function () {
    // Global AJAX setup
    $.ajaxSetup({
      beforeSend: (xhr, settings) => {
        // 1) If it’s the refresh-CSRF endpoint, skip adding a CSRF token
        //    so we don’t cause infinite “token not found” loops.
        if (settings.url.includes("/api/auth/refresh-csrf")) {
          return;
        }

        // 2) Skip if it's login/logout to avoid messing with auth calls
        if (settings.url.includes("/api/auth/login") || settings.url.includes("/api/auth/logout")) {
          return;
        }

        // 3) Attach the Authorization header if we have an auth token
        const token = this.getToken();
        if (token) {
          xhr.setRequestHeader("Authorization", `${token.tokenType} ${token.accessToken}`);
        }

        // 4) If it's a non-GET method, attach CSRF only if we actually have one
        const unsafeMethods = ["POST", "PUT", "DELETE", "PATCH"];
        if (unsafeMethods.includes(settings.type.toUpperCase())) {
          const csrfToken = this.getCsrfToken();
          if (csrfToken) {
            xhr.setRequestHeader("X-CSRF-Token", csrfToken);
          } else {
            console.warn("CSRF token not found for non-GET request to", settings.url);
            // Possibly trigger a single attempt to request a token, or just log and move on
          }
        }
      },
    });

    // Add global error handler for ajax requests
    $(document).ajaxError((event, xhr, settings) => {
      // Skip handling for auth endpoints to avoid loops
      if (
        settings.url.includes("/api/auth/login") ||
        settings.url.includes("/api/auth/token") ||
        settings.url.includes("/api/auth/refresh")
      ) {
        return;
      }

      // Handle authorization errors
      if (xhr.status === 401) {
        console.log("401 Unauthorized response received");
        // Check if this is a persistent issue
        if (this.isAuthenticated()) {
          // We think we're authenticated but server disagrees
          // Verify server-side session directly
          this.verifyServerSession();
        } else {
          this.handleSessionExpiration();
        }
      }

      // Handle CSRF token errors
      else if (
        xhr.status === 403 &&
        (xhr.responseJSON?.error === "csrf_token_invalid" || xhr.responseJSON?.detail === "Invalid CSRF token")
      ) {
        console.log("CSRF token invalid, attempting refresh");
        this.refreshCsrfToken();
      }
    });
  },

  /**
   * Setup auto-refresh of session/token based on current auth method
   */
  setupAutoRefresh: function () {
    // Clear existing timers
    if (this.sessionRefreshTimer) {
      clearTimeout(this.sessionRefreshTimer);
      this.sessionRefreshTimer = null;
    }

    // Check which auth method is in use and set up appropriate refresh
    const token = this.getToken();
    if (token && token.expiresAt) {
      this.setupTokenRefresh(new Date(token.expiresAt));
    }

    const userData = this.getUserData();
    if (userData && userData.expiresAt) {
      this.setupSessionRefresh(new Date(userData.expiresAt));
    }
  },

  /**
   * Logout user and redirect to login
   */
  logout: function () {
    console.log("Logging out");
    // Send logout request to server
    $.ajax({
      url: "/api/auth/logout",
      method: "POST",
      headers: {
        "X-CSRF-Token": this.getCsrfToken(),
      },
    }).always(() => {
      // Clear tokens locally
      this.clearAuth();
      // Redirect to login page
      window.location.href = "/auth/login?logged_out=true";
    });
  },

  /**
   * Remove stored token and session data (for logout)
   */
  clearAuth: function () {
    this.removeToken();
    this.removeUserData();

    if (this.tokenRefreshTimer) {
      clearTimeout(this.tokenRefreshTimer);
      this.tokenRefreshTimer = null;
    }
    if (this.sessionRefreshTimer) {
      clearTimeout(this.sessionRefreshTimer);
      this.sessionRefreshTimer = null;
    }
    if (this.csrfRefreshTimer) {
      clearTimeout(this.csrfRefreshTimer);
      this.csrfRefreshTimer = null;
    }
    if (this.sessionValidatorTimer) {
      clearInterval(this.sessionValidatorTimer);
      this.sessionValidatorTimer = null;
    }
  },

  /**
   * Remove token data
   */
  removeToken: function () {
    sessionStorage.removeItem("authToken");
    localStorage.removeItem("authToken");
  },

  /**
   * Remove session-related data
   */
  removeUserData: function () {
    sessionStorage.removeItem("userData");
    sessionStorage.removeItem("csrfToken");
  },

  /**
   * Check if user is authenticated
   * @returns {boolean} True if authenticated
   */
  isAuthenticated: function () {
    // Check either token or session cookie based authentication
    return this.getToken() !== null || this.getUserData() !== null || document.cookie.includes("auth_session=");
  },

  /**
   * Check authentication status from server
   * @returns {Promise} Promise resolving to auth status
   */
  checkAuthStatus: function () {
    return $.ajax({
      url: "/api/auth/me",
      method: "GET",
      dataType: "json",
    })
      .then((userData) => {
        // If we're here, we got a successful response and we're authenticated
        // Update local user data if we have it
        if (userData && userData.id) {
          const storedUserData = {
            userId: userData.id,
            username: userData.username,
            // Set a short expiry since we don't know the real one
            expiresAt: new Date(Date.now() + DEFAULT_SESSION_EXPIRY).toISOString(),
          };
          sessionStorage.setItem("userData", JSON.stringify(storedUserData));
        }
        return true;
      })
      .catch((error) => {
        if (error.status === 401 || error.status === 403) {
          this.handleSessionExpiration();
        }
        return false;
      });
  },

  /**
   * Redirect to login if not authenticated
   */
  requireAuth: function () {
    if (!this.isAuthenticated()) {
      console.log("Not authenticated locally, checking with server");
      this.checkAuthStatus().then((authenticated) => {
        if (!authenticated) {
          this.handleSessionExpiration();
        } else {
          // We're authenticated on server but not locally, update local state
          console.log("Authenticated on server but not locally. Refreshing session state.");
          this.refreshSession();
        }
      });
    } else {
      // We think we're authenticated, set up refresh timers
      this.setupAutoRefresh();

      // Still verify with the server in the background
      this.checkAuthStatus().catch(() => {
        // If check fails, handled by the catch in checkAuthStatus
        console.log("Auth verification failed");
      });
    }
  },

  /**
   * Login user with API token
   * @param {string} email - User email
   * @param {string} password - User password
   * @param {boolean} remember - Whether to remember login
   * @returns {Promise} Login promise
   */
  loginWithToken: function (email, password, remember) {
    return $.ajax({
      url: "/api/auth/token",
      method: "POST",
      data: {
        username: email,
        password: password,
      },
      dataType: "json",
    }).then((response) => {
      this.storeToken(response, remember);
      return response;
    });
  },

  /**
   * Login user with cookie-based session
   * @param {string} email - User email
   * @param {string} password - User password
   * @param {boolean} remember - Whether to remember login
   * @returns {Promise} Login promise
   */
  loginWithSession: function (email, password, remember) {
    return $.ajax({
      url: "/api/auth/login",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({
        email: email,
        password: password,
        remember: remember,
      }),
      dataType: "json",
    }).then((response) => {
      this.storeSession(response);
      return response;
    });
  },

  /**
   * Initialize auth management
   */
  init: function () {
    // Setup AJAX interceptors
    this.setupAjaxHeaders();

    // Check and setup auto-refresh if needed
    if (this.isAuthenticated()) {
      this.setupAutoRefresh();
      // Add session validator to periodically check with server
      this.setupSessionValidator();
    }

    // Add URL parameter handler for session expired messages
    if (new URLSearchParams(window.location.search).has("session_expired")) {
      alertify.error("Your session has expired. Please log in again.");
    }

    console.log("AuthManager initialized");
  },
};

// Initialize auth management when page loads
$(document).ready(function () {
  AuthManager.init();

  // Check if current page requires authentication
  if ($("body").hasClass("requires-auth")) {
    AuthManager.requireAuth();
  }

  // Bind logout button
  $("#logoutBtn").on("click", function (e) {
    e.preventDefault();
    AuthManager.logout();
  });
});
