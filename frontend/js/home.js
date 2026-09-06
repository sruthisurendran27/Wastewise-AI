/* Home page: demo-entry strip + mini impact summary (demo-tolerant, publicly viewable). */
document.addEventListener("DOMContentLoaded", async () => {
  await initPageAuth();

  // Demo one-tap flow entry.
  const demoLink = qs("#demoModeLink");
  if (demoLink) {
    demoLink.addEventListener("click", (e) => {
      e.preventDefault();
      DEMO.start();
      window.location.href = "result.html";
    });
  }

  if (!API.getToken()) return;

  try {
    const stats = await DEMO.statsOrDemo();
    const user = API.getUser();
    qs("#miniStatsContent").innerHTML = `
      <div class="stat-grid">
        <div class="stat"><div class="value">${stats.points}</div><div class="label">Points</div></div>
        <div class="stat"><div class="value">${stats.items_reused}</div><div class="label">Items reused</div></div>
        <div class="stat"><div class="value">${stats.waste_diverted}</div><div class="label">Waste diverted</div></div>
        <div class="stat"><div class="value">₹${stats.value_created_total_min}–${stats.value_created_total_max}</div><div class="label">Value created</div></div>
      </div>
      <a href="dashboard.html">View my full dashboard →</a>`;
  } catch {
    qs("#miniStatsContent").innerHTML =
      '<p style="color:var(--ink-soft)">Sign in to track your impact.</p>';
  }
});