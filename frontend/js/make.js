/* Make page: show the selected idea details, safety notes, and award "I Made This!" points.
   Falls back to demo idea awarding when the API is unavailable. */
document.addEventListener("DOMContentLoaded", async () => {
  requireAuth();
  await initPageAuth();

  const idea = Journey.getIdea();
  const scanId = Journey.getScan();
  if (!idea || !scanId) {
    window.location.href = "create.html";
    return;
  }

  const isDemo = DEMO.isDemo(scanId);

  // Render idea details.
  if (idea.is_best_match) qs("#bestBadge").style.display = "inline-block";
  qs("#ideaTitle").textContent = idea.title;
  qs("#diyEmblem").textContent = emojiFor(idea.title);

  const difficultyMap = { Easy: "⭐ Easy", Medium: "⭐⭐ Medium", Hard: "⭐⭐⭐ Hard" };
  const meta = [
    `<span class="badge badge-soft">${difficultyMap[idea.difficulty] || idea.difficulty}</span>`,
    `<span class="badge badge-green">⏱ ~${idea.time_minutes || 20} min</span>`,
    `<span class="badge badge-blue">🧰 ${escapeHtml(idea.extra_materials || "Minimal materials")}</span>`,
  ];
  qs("#ideaMeta").innerHTML = meta.join(" ");

  // Materials row.
  if (idea.extra_materials) {
    qs("#matRow").style.display = "flex";
    qs("#materialsText").textContent = idea.extra_materials;
  }

  const stepsList = qs("#stepsList");
  (idea.steps && idea.steps.length ? idea.steps : ["Clean the item.", "Prepare the materials.", "Assemble.", "Enjoy!"])
    .forEach((step) => {
      const li = document.createElement("li");
      li.textContent = step;
      stepsList.appendChild(li);
    });

  const valueText = qs("#valueText");
  if (idea.value_min != null && idea.value_max != null) {
    valueText.textContent = `₹${idea.value_min}–₹${idea.value_max}`;
  }
  qs("#usageTags").innerHTML = (idea.usage_tags && idea.usage_tags.length
    ? idea.usage_tags.map((t) => `<span class="badge badge-green">🛒 ${escapeHtml(t)}</span>`).join(" ")
    : `<span class="badge badge-green">🛒 Personal use</span>`);

  // Celebrate + award points (with confetti).
  const madeItBtn = qs("#madeItBtn");
  const celebration = qs("#celebration");

  madeItBtn.addEventListener("click", async () => {
    madeItBtn.disabled = true;
    madeItBtn.textContent = "Awarding points…";
    try {
      let result;
      if (isDemo || !navigator.onLine) {
        await new Promise((r) => setTimeout(r, 500));
        const stats = DEMO.localStats.add("made_item", 20, idea.value_min || 0, idea.value_max || 0);
        result = { points_earned: 20 };
        // Reflect in the topbar chip if present.
        const chip = document.getElementById("userChip");
        if (chip && API.getUser()) {
          API.setUser({ ...API.getUser(), points: stats.points });
          chip.textContent = `${API.getUser().name} | ${stats.points} PTS`;
        }
      } else {
        const params = new URLSearchParams({ scan_id: scanId });
        if (idea.value_min != null) params.set("value_min", idea.value_min);
        if (idea.value_max != null) params.set("value_max", idea.value_max);
        result = await API.request(`/activity/made?${params.toString()}`, { method: "POST" });
      }

      qs("#pointsEarnedText").textContent = `+${result.points_earned} WasteWise Points`;
      celebration.style.display = "block";
      madeItBtn.style.display = "none";
      launchConfetti();
      Journey.clear();
      celebration.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (err) {
      toast(err.message);
      madeItBtn.disabled = false;
      madeItBtn.textContent = "🎉  I Made This!";
      if (err.message.includes("already recorded")) {
        Journey.clear();
        window.location.href = "dashboard.html";
      }
    }
  });
});

function emojiFor(title) {
  const t = (title || "").toLowerCase();
  if (/planter|garden|plant|pot/.test(t)) return "🌱";
  if (/pen|holder|organis|pencil/.test(t)) return "🖊️";
  if (/lamp|light|decor/.test(t)) return "🕯️";
  if (/hanger|hook/.test(t)) return "🧷";
  return "✨";
}

/* Lightweight canvas confetti burst. */
function launchConfetti() {
  const colors = ["#22c55e", "#16a34a", "#f59e0b", "#86efac", "#4ade80"];
  const count = 80;
  const body = document.body;

  for (let i = 0; i < count; i++) {
    const piece = document.createElement("div");
    piece.className = "confetti";
    piece.style.left = `${Math.random() * 100}vw`;
    piece.style.background = colors[i % colors.length];
    piece.style.animationDelay = `${Math.random() * 0.4}s`;
    piece.style.setProperty("--drift", `${(Math.random() - 0.5) * 160}px`);
    body.appendChild(piece);
    setTimeout(() => piece.remove(), 2600);
  }
}
