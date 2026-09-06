/* Shared API helper: attaches auth token, wraps fetch, parses errors. */
const API = {
  TOKEN_KEY: "wastewise_token",
  USER_KEY: "wastewise_user",

  getToken() {
    return localStorage.getItem(this.TOKEN_KEY);
  },

  setToken(token) {
    localStorage.setItem(this.TOKEN_KEY, token);
  },

  getUser() {
    try {
      return JSON.parse(localStorage.getItem(this.USER_KEY) || "null");
    } catch {
      return null;
    }
  },

  setUser(user) {
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
  },

  clearAuth() {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
  },

  async request(path, { method = "GET", body, headers = {}, isFormData = false } = {}) {
    const opts = { method, headers: { ...headers } };
    const token = this.getToken();
    if (token) opts.headers["Authorization"] = `Bearer ${token}`;

    if (body) {
      if (isFormData) {
        opts.body = body;
      } else {
        opts.headers["Content-Type"] = "application/json";
        opts.body = JSON.stringify(body);
      }
    }

    let resp;
    try {
      resp = await fetch(`/api${path}`, opts);
    } catch (err) {
      throw new Error("Network error. Is the server running?");
    }

    let data = null;
    try {
      data = await resp.json();
    } catch {
      data = null;
    }

    if (!resp.ok) {
      const detail = data && data.detail ? data.detail : `Request failed (${resp.status})`;
      // Demo mode has a fake token; don't bounce those users to login.
      if (resp.status === 401 && token !== "__demo__" && path !== "/auth/login") {
        this.clearAuth();
        if (!window.location.pathname.endsWith("login.html")) {
          window.location.href = "login.html";
        }
      }
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  },
};

function toast(message) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2600);
}

function qs(selector, root = document) {
  return root.querySelector(selector);
}

function qsa(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

/* Escape text for safe injection into innerHTML. */
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str == null ? "" : String(str);
  return div.innerHTML;
}