/* Profile: user info, WasteWise level (Explorer → Warrior → Champion), saved ideas,
   scan history, impact stats, achievements (demo-tolerant). */
document.addEventListener("DOMContentLoaded", async () => {
  if (!requireAuth()) return;
  await initPageAuth();

  try {
    const user = await ensureUser();
    const stats = await DEMO.statsOrDemo();

    // Account info.
    qs("#userName").textContent = user ? user.name : "Guest";
    qs("#userEmail").textContent = user ? user.email : "demo@wastewise.ai";
    qs("#userPoints").textContent = stats.points;
    qs("#userScans").textContent = (stats.items_reused + stats.items_recycled + stats.items_disposed) || 0;
    qs("#userJoined").textContent = "Member of WasteWise";

    // Level logic: Explorer (0–49) → Warrior (50–149) → Champion (150+).
    const points = stats.points || 0;
    let level = { name: "Waste Explorer", emoji: "🥉", min: 0, next: 50 };
    if (points >= 150) level = { name: "WasteWise Champion", emoji: "🥇", min: 150, next: null };
    else if (points >= 50) level = { name: "Waste Warrior", emoji: "🥈", min: 50, next: 150 };

    qs("#userLevel").textContent = level.name;
    qs("#levelEmoji").textContent = level.emoji;
    qs("#levelSub").textContent =
      level.next === null
        ? "Top of the leaderboard — extraordinary! 🎉"
        : `Keep going — ${level.next - points} XP to the next level.`;

    // Progress bar.
    const fill = qs("#levelFill");
    if (level.next === null) {
      fill.style.width = "100%";
      qs("#levelNums").textContent = `${points} XP · max level`;
    } else {
      const pct = Math.min(100, Math.round(((points - level.min) / (level.next - level.min)) * 100));
      fill.style.width = `${pct}%`;
      qs("#levelNums").textContent = `${points - level.min} / ${level.next - level.min} XP`;
    }

    // Impact stats.
    qs("#statsReused").textContent = stats.items_reused;
    qs("#statsRecycled").textContent = stats.items_recycled;
    qs("#statsDisposed").textContent = stats.items_disposed;
    qs("#statsDiverted").textContent = stats.waste_diverted;
    qs("#potentialValue").textContent = `₹${stats.value_created_total_min}–₹${stats.value_created_total_max}`;

    // Saved ideas (localStorage).
    const saved = getSavedIdeas();
    const savedEl = qs("#savedIdeas");
    if (saved.length) {
      savedEl.innerHTML = saved
        .map((i) => `<div class="recycler-item">
            <div class="rec-head"><span class="name">💡 ${escapeHtml(i.title)}</span></div>
            <p class="time-stamp">For: ${escapeHtml(i.waste_label || "your scanned item")}</p>
            <div class="rec-meta">
              <span class="badge badge-soft">${escapeHtml(i.difficulty || "Easy")}</span>
              <span class="badge badge-green">⏱ ${i.time_minutes || 20} min</span>
              ${i.value_min != null ? `<span class="badge badge-amber">₹${i.value_min}–₹${i.value_max}</span>` : ""}
              <button class="btn btn-outline btn-sm completeIdea" data-id="${escapeHtml(i.id)}" type="button">${i.completed ? "Completed" : "Mark done"}</button>
            </div>
          </div>`)
        .join("");
      qsa(".completeIdea", savedEl).forEach((button) => button.addEventListener("click", () => {
        const next = getSavedIdeas().map((idea) => idea.id === button.dataset.id ? { ...idea, completed: true } : idea);
        localStorage.setItem("ww_saved_ideas", JSON.stringify(next));
        button.textContent = "Completed";
        toast("Idea marked complete");
      }));
    }

    // Achievements.
    unlockAchievements(stats);

    const savedRecyclerEl = qs("#savedRecyclers");
    const savedRecyclers = getSavedRecyclers();
    if (savedRecyclers.length) savedRecyclerEl.innerHTML = savedRecyclers.map((r) => `<div class="recycler-item"><strong>${escapeHtml(r.name)}</strong><p class="time-stamp">${escapeHtml(r.address || r.district || "Tamil Nadu")}</p>${r.contact ? `<p class="time-stamp">${escapeHtml(r.contact)}</p>` : ""}</div>`).join("");

    qs("#loading").style.display = "none";
    qs("#content").style.display = "block";
  } catch (err) {
    qs("#loading").innerHTML = `<div class="empty"><p>${escapeHtml(err.message)}</p></div>`;
  }
});

function getSavedIdeas() {
  try {
    return JSON.parse(localStorage.getItem("ww_saved_ideas") || "[]");
  } catch {
    return [];
  }
}

function unlockAchievements(stats) {
  const list = qs("#achievements");
  const badges = {
    finder: { label: "Found a recycler", done: getSavedRecyclers().length >= 1 },
    maker: { label: "Saved an idea", done: getSavedIdeas().length >= 1 },
    first: { label: "♻️ First scan", done: (stats.items_reused + stats.items_recycled + stats.items_disposed) >= 1 },
    idea: { label: "💡 First idea", done: stats.items_reused >= 1 },
    diverter: { label: "🌱 10 items diverted", done: stats.waste_diverted >= 10 },
    points: { label: "🏅 50 points", done: stats.points >= 50 },
  };
  list.innerHTML = Object.values(badges)
    .map((b) => `<span class="ach${b.done ? "" : " locked"}">${b.done ? "✔ " : b.label}</span>`)
    .join("");
}

function getSavedRecyclers() {
  try {
    const saved = JSON.parse(localStorage.getItem("ww_saved_recyclers") || "[]");
    return Array.isArray(saved) ? saved : [];
  } catch { return []; }
}
