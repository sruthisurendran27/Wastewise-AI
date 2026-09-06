/* Shared app shell: renders top nav + bottom nav, fills the user chip,
   wires logout, and reads the active page from <body data-page="...">. */
document.addEventListener("DOMContentLoaded", async () => {
  const page = document.body.dataset.page || "home";

  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) themeColor.setAttribute("content", "#111111");

  // Render navigation (bottom bar on mobile, top links on desktop).
  initNav(page);

  // Edition metadata for the editorial shell.
  const topbar = document.querySelector(".topbar");
  if (topbar && !topbar.querySelector(".topbar-meta")) {
    const meta = document.createElement("div");
    meta.className = "topbar-meta";
    meta.textContent = `Vol. 1 | ${new Date().toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    })} | Print Edition`;
    const brand = topbar.querySelector(".brand");
    if (brand && brand.nextSibling) {
      topbar.insertBefore(meta, brand.nextSibling);
    } else if (brand) {
      brand.insertAdjacentElement("afterend", meta);
    } else {
      topbar.prepend(meta);
    }
  }

  // Ensure we know who the user is (best-effort).
  await ensureUser();
  const user = API.getUser();

  // User chip in the top bar.
  const chip = document.getElementById("userChip");
  if (chip) {
    if (user) {
      chip.textContent = `${escapeHtml(user.name || "User")} | ${user.points ?? 0} PTS`;
      chip.style.display = "inline-flex";
    } else {
      chip.style.display = "none";
    }
  }

  // Logout button(s).
  const doLogout = (e) => {
    e.preventDefault();
    API.clearAuth();
    Journey.clear();
    window.location.href = "index.html";
  };
  const logoutTop = document.getElementById("logoutBtn");
  if (logoutTop) {
    if (user) logoutTop.style.display = "inline-block";
    logoutTop.addEventListener("click", doLogout);
  }
  const logoutMain = document.getElementById("logoutBtnMain");
  if (logoutMain) {
    if (user) logoutMain.style.display = "inline-flex";
    logoutMain.addEventListener("click", doLogout);
  }
});
