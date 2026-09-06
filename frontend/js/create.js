/* Create page: fetch AI-generated DIY ideas with tag chips + Save Idea. */
document.addEventListener("DOMContentLoaded", async () => {
  requireAuth();
  await initPageAuth();

  const scanId = Journey.getScan();
  if (!scanId) {
    window.location.href = "index.html";
    return;
  }

  const loading = qs("#loading");
  const ideasList = qs("#ideasList");
  const noIdeas = qs("#noIdeas");
  const errorBox = qs("#errorBox");
  const isDemo = DEMO.isDemo(scanId);

  function difficultyText(d) {
    const map = { Easy: "Easy", Medium: "Medium", Hard: "Hard" };
    return map[d] || d;
  }

  // Save helpers (localStorage-backed so Profile can list them).
  function getSaved() {
    try {
      return JSON.parse(localStorage.getItem("ww_saved_ideas") || "[]");
    } catch {
      return [];
    }
  }
  function isSaved(id) {
    return getSaved().some((i) => i.id === id);
  }

  function renderIdea(idea, idx) {
    const best = idx === 0;
    const card = document.createElement("div");
    card.className = `idea-card${best ? " best" : ""}`;

    const tagChips = (idea.tags && idea.tags.length ? idea.tags : []).map((t) =>
      `<span class="badge badge-amber">${escapeHtml(t)}</span>`
    ).join("");
    const valueRange =
      idea.value_min != null && idea.value_max != null
        ? `<div class="idea-value">💰 ₹${idea.value_min}–₹${idea.value_max}</div>`
        : "";

    card.innerHTML = `
      <div class="idea-top">
        <span class="badge badge-soft">${difficultyText(idea.difficulty)}</span>
        <span class="badge badge-green">⏱ ~${idea.time_minutes || 20} min</span>
        <span class="badge badge-blue">🧰 ${escapeHtml(idea.extra_materials || "Minimal")}</span>
      </div>
      <h4>${emojiFor(idea.title)} ${escapeHtml(idea.title)}</h4>
      <div class="idea-tags">${tagChips}${best ? '<span class="badge badge-amber">🥇 Best Match</span>' : ""}</div>
      ${valueRange}
      <div class="idea-actions">
        <button class="btn btn-primary btn-sm viewHowTo" data-index="${idx}">View How-To</button>
        <button class="btn btn-outline btn-sm saveIdea" data-index="${idx}">${isSaved(idea.id) ? "✓ Saved" : "Save Idea"}</button>
      </div>`;

    card.querySelector(".viewHowTo").addEventListener("click", (e) => {
      e.stopPropagation();
      Journey.setIdea(JSON.stringify(idea));
      window.location.href = "make.html";
    });
    card.querySelector(".saveIdea").addEventListener("click", (e) => {
      e.stopPropagation();
      const saved = getSaved();
      if (isSaved(idea.id)) {
        const next = saved.filter((i) => i.id !== idea.id);
        localStorage.setItem("ww_saved_ideas", JSON.stringify(next));
        card.querySelector(".saveIdea").textContent = "Save Idea";
        toast("Removed from saved ideas");
      } else {
        saved.push({ id: idea.id, title: idea.title, waste_label: data.label, difficulty: idea.difficulty, time_minutes: idea.time_minutes, value_min: idea.value_min, value_max: idea.value_max, saved_at: new Date().toISOString(), completed: false });
        localStorage.setItem("ww_saved_ideas", JSON.stringify(saved));
        card.querySelector(".saveIdea").textContent = "✓ Saved";
        toast("🔖 Idea saved");
      }
    });

    return card;
  }

  try {
    let data;
    if (isDemo) {
      data = { label: "Plastic Bottle", ideas: DEMO.ideas };
    } else {
      data = await API.request(`/scan/${scanId}/ideas`);
    }

    loading.style.display = "none";
    qs("#ideaSubtitle").textContent = `Ideas for your ${data.label || "waste"} — tap one to see the full how-to.`;

    if (!data.ideas || data.ideas.length === 0) {
      noIdeas.style.display = "block";
      return;
    }

    data.ideas.forEach((idea, i) => {
      ideasList.appendChild(renderIdea(idea, i));
    });
  } catch (err) {
    loading.style.display = "none";
    errorBox.style.display = "block";
    errorBox.textContent = err.message || "Could not generate ideas. Please try again.";
  }
});

function emojiFor(title) {
  const t = (title || "").toLowerCase();
  if (/planter|garden|plant|pot/.test(t)) return "🌱";
  if (/pen|holder|organis|pencil/.test(t)) return "🖊️";
  if (/lamp|light|decor/.test(t)) return "🕯️";
  if (/hanger|hook/.test(t)) return "🧷";
  return "✨";
}
