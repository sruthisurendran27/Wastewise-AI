/* Dashboard: impact ring, stats, period cards, recent activity (demo-tolerant). */
document.addEventListener("DOMContentLoaded", async () => {
  requireAuth();
  await initPageAuth();

  try {
    const stats = await DEMO.statsOrDemo();

    // Values.
    qs("#pointsValue").textContent = stats.points;
    qs("#statReused").textContent = stats.items_reused;
    qs("#statRecycled").textContent = stats.items_recycled;
    qs("#statDisposed").textContent = stats.items_disposed;
    qs("#statDiverted").textContent = stats.waste_diverted;
    qs("#valueCreatedText").textContent = `₹${stats.value_created_total_min}–₹${stats.value_created_total_max}`;

    // Chips.
    qs("#ptReused").textContent = `♻️ ${stats.items_reused}`;
    qs("#ptRecycled").textContent = `♻️ ${stats.items_recycled}`;
    qs("#ptDiverted").textContent = `🌱 ${stats.waste_diverted}`;

    // Period cards — derive from recent activity timestamps when available.
    const now = new Date();
    const weekAgo = now.getTime() - 7 * 24 * 3600 * 1000;
    const monthAgo = now.getTime() - 30 * 24 * 3600 * 1000;
    let week = 0;
    let month = 0;
    (stats.recent_activities || []).forEach((a) => {
      const t = new Date(a.created_at).getTime();
      if (t >= weekAgo) week += 1;
      if (t >= monthAgo) month += 1;
    });
    qs("#weekDiverted").textContent = week;
    qs("#monthDiverted").textContent = month;

    // Circular progress ring (diverted as a share of a 50-item goal, min 1 for line).
    const total = stats.waste_diverted || 0;
    const pct = Math.min(100, Math.round((total / 50) * 100));
    const ring = qs("#ringFg");
    const C = 2 * Math.PI * 52;
    ring.style.strokeDasharray = C;
    ring.style.strokeDashoffset = C * (1 - pct / 100);
    qs("#divertPct").textContent = `${pct}%`;

    // Recent activity list.
    const listEl = qs("#activityList");
    if (stats.recent_activities && stats.recent_activities.length) {
      listEl.innerHTML = stats.recent_activities
        .map((a) => {
          const date = new Date(a.created_at).toLocaleDateString(undefined, {
            day: "numeric", month: "short",
          });
          return `<div class="recycler-item">
            <div>${escapeHtml(a.description)} <span class="badge badge-green">+${a.points_earned} pts</span></div>
            <span class="time-stamp">${date}</span>
          </div>`;
        })
        .join("");
    }

    const savedIdeas = getSavedIdeas();
    const savedIdeasEl = qs("#savedIdeasDashboard");
    if (savedIdeas.length) {
      savedIdeasEl.innerHTML = savedIdeas
        .slice(0, 3)
        .map((idea) => `
          <div class="recycler-item">
            <div class="rec-head">
              <span class="name">${escapeHtml(idea.title)}</span>
              <span class="dist">${escapeHtml(idea.difficulty || "Easy")}</span>
            </div>
            <p class="time-stamp">For: ${escapeHtml(idea.waste_label || "your scanned item")}</p>
            <div class="rec-meta">
              <span class="badge badge-soft">${idea.time_minutes || 20} min</span>
              ${idea.value_min != null ? `<span class="badge badge-amber">Rs ${idea.value_min}-${idea.value_max}</span>` : ""}
            </div>
          </div>`)
        .join("");
    }

    // Refresh topbar chip.
    if (API.getUser()) {
      const user = API.getUser();
      user.points = stats.points;
      API.setUser(user);
      const chip = document.getElementById("userChip");
      if (chip) chip.textContent = `${escapeHtml(user.name || "User")} | ${stats.points} PTS`;
    }

    qs("#loading").style.display = "none";
    qs("#content").style.display = "block";
  } catch (err) {
    qs("#loading").innerHTML = `<div class="empty"><p>${escapeHtml(err.message)}</p></div>`;
  }
});

function getSavedIdeas() {
  try {
    const saved = JSON.parse(localStorage.getItem("ww_saved_ideas") || "[]");
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
