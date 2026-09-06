document.addEventListener("DOMContentLoaded", async () => {
  if (!requireAuth()) return;
  await initPageAuth();
  const list = qs("#historyList");
  let scans = [];
  try { scans = await API.request("/scans"); }
  catch (err) { list.innerHTML = `<div class="empty">${escapeHtml(err.message)}</div>`; }

  function render(filter = "all") {
    const visible = filter === "all" ? scans : scans.filter((s) => s.category === filter);
    list.innerHTML = visible.length ? visible.map((s) => {
      const date = new Date(s.created_at).toLocaleDateString(undefined, {day: "numeric", month: "short", year: "numeric"});
      return `<article class="history-item"><div><span class="eyebrow">${escapeHtml(date)}</span><h3>${escapeHtml(s.final_label)}</h3><p class="time-stamp">${escapeHtml(s.ai_result?.material || "Material unknown")}</p></div><div class="history-actions"><span class="badge badge-green">${escapeHtml(s.category)}</span><a class="btn btn-outline btn-sm" href="result.html" data-scan="${escapeHtml(s.id)}">View result</a></div></article>`;
    }).join("") : `<div class="empty"><p>No scans found.</p><a class="btn btn-primary" href="scan.html">Scan waste</a></div>`;
    qsa("[data-scan]", list).forEach((link) => link.addEventListener("click", () => Journey.setScan(link.dataset.scan)));
  }
  qsa(".history-filters .chip").forEach((chip) => chip.addEventListener("click", () => { qsa(".history-filters .chip").forEach((c) => c.classList.remove("active")); chip.classList.add("active"); render(chip.dataset.filter); }));
  render(); qs("#loading").style.display = "none"; list.style.display = "grid";
});
