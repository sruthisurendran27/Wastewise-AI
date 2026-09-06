/* Auth helpers: login/register forms, protected-page guard, logout, topbar render. */

function requireAuth() {
  if (!API.getToken()) {
    window.location.href = "login.html";
    return false;
  }
  return true;
}

async function ensureUser() {
  if (!API.getUser() && API.getToken()) {
    try {
      const me = await API.request("/auth/me");
      API.setUser({
        id: me.id,
        name: me.name,
        email: me.email,
        points: me.points,
      });
    } catch {
      /* token invalid; guard will handle */
    }
  }
  return API.getUser();
}

function renderTopbar(user) {
  if (!user) return;
  // New topbars expose #userChip (rendered by shell.js); also support legacy <nav>.
  const chip = document.getElementById("userChip");
  if (chip) {
    chip.textContent = `${user.name || "User"} | ${user.points ?? 0} PTS`;
    chip.style.display = "inline-flex";
    return;
  }
  const topbar = qs(".topbar");
  if (!topbar) return;
  const nav = topbar.querySelector("nav");
  if (nav) {
    const el = document.createElement("span");
    el.className = "user-chip";
    el.textContent = `${user.name} | ${user.points ?? 0} PTS`;
    nav.appendChild(el);
  }
}

async function initPageAuth() {
  const user = await ensureUser();
  renderTopbar(user);
}
