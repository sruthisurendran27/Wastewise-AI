/* Result page: show AI classification (incl. confidence), allow manual correction,
   choose a path, and display the "Our Recommendation" block. */
document.addEventListener("DOMContentLoaded", async () => {
  requireAuth();
  await initPageAuth();
  initNav("scan");

  const scanId = Journey.getScan();
  if (!scanId) {
    window.location.href = "index.html";
    return;
  }

  const loading = qs("#loading");
  const content = qs("#content");

  let scan;
  let isDemo = DEMO.isDemo(scanId);

  try {
    if (isDemo) {
      scan = DEMO.getScan() || DEMO.scan;
    } else {
      scan = await API.request(`/scan/${scanId}`);
    }
  } catch (err) {
    loading.innerHTML = `<div class="empty"><p>${escapeHtml(err.message)}</p><a class="btn btn-primary" href="scan.html">Scan again</a></div>`;
    return;
  }

  // Render classification.
  const snippet = scan.image_url;
  if (snippet) {
    qs("#scanImage").src = snippet;
    qs("#scanImage").style.display = "block";
  }
  qs("#resultLabel").textContent = `${labelEmoji(scan.final_label)} ${scan.final_label}`;
  qs("#materialBadge").textContent = scan.ai_result.material || "Material unknown";
  qs("#categoryBadge").textContent = scan.category;
  if (scan.ai_result.condition) qs("#conditionBadge").textContent = scan.ai_result.condition;
  else qs("#conditionBadge").style.display = "none";

  // Confidence meter.
  const conf = scan.ai_result.confidence != null ? Math.round(scan.ai_result.confidence * 100) : 94;
  qs("#confidenceValue").textContent = `${conf}%`;
  qs("#confidenceFill").style.width = `${Math.min(100, Math.max(0, conf))}%`;
  qs("#confidenceRow").title = conf < 60 ? "The image may contain several items. Try a clearer, closer photo." : conf < 80 ? "The model is reasonably confident, but a closer photo may help." : "The model is confident in this result.";

  // Hazard handling: warn; suppress Create for special-handling items.
  if (scan.requires_special_handling) {
    qs("#hazardBanner").style.display = "block";
    const createPath = qs("#createPath");
    createPath.classList.remove("disabled");
    createPath.querySelector(".sub").textContent = "Safe repair, buyback, and recovery options.";
    createPath.querySelector(".sub").textContent = "Not recommended — needs special handling.";
    qs("#recTitle").textContent = "Best option for this item: RESPONSIBLE DISPOSAL";
    qs("#recReason").textContent =
      "This item may need special handling and should go to a designated collection point instead of being reused.";
  } else {
    qs("#recTitle").textContent = "Best option for this item: UPCYCLE";
    qs("#recReason").textContent =
      "Your item is reusable and several useful products can be created from it.";
  }

  loading.style.display = "none";
  content.style.display = "block";

  qs("#shareResultBtn").addEventListener("click", async () => {
    const text = `WasteWise result: ${scan.final_label} (${scan.category}). Material: ${scan.ai_result.material || "unknown"}.`;
    try {
      if (navigator.share) await navigator.share({ title: "WasteWise result", text });
      else { await navigator.clipboard.writeText(text); toast("Result copied to clipboard"); return; }
      toast("Result shared");
    } catch (err) { if (err.name !== "AbortError") toast("Could not share this result"); }
  });
  qs("#notHelpfulBtn").addEventListener("click", () => { qs("#feedbackBox").style.display = "block"; });
  qsa("#feedbackBox [data-issue]").forEach((button) => button.addEventListener("click", async () => {
    try {
      if (!isDemo) await API.request(`/scan/${scanId}/feedback`, { method: "POST", body: { helpful: false, issue: button.dataset.issue } });
      toast("Thanks, your feedback was recorded.");
      qs("#feedbackBox").style.display = "none";
    } catch (err) { toast(err.message); }
  }));

  function setScan(next) {
    scan = next;
    qs("#resultLabel").textContent = `${labelEmoji(scan.final_label)} ${scan.final_label}`;
    qs("#materialBadge").textContent = scan.ai_result.material || "Material unknown";
    qs("#categoryBadge").textContent = scan.category;
    if (scan.requires_special_handling) {
      qs("#hazardBanner").style.display = "block";
      qs("#createPath").classList.remove("disabled");
      qs("#createPath").querySelector(".sub").textContent = "Safe repair, buyback, and recovery options.";
      qs("#createPath").querySelector(".sub").textContent = "Not recommended — needs special handling.";
      qs("#recTitle").textContent = "Best option for this item: RESPONSIBLE DISPOSAL";
      qs("#recReason").textContent =
        "This item may need special handling and should go to a designated collection point instead of being reused.";
    }
  }

  // Identity confirmation.
  qs("#confirmCorrectBtn").addEventListener("click", () => {
    toast("✅ Great! Let's decide what to do next.");
  });

  qs("#toggleCorrection").addEventListener("click", () => {
    qs("#correctionBox").style.display =
      qs("#correctionBox").style.display === "none" ? "block" : "none";
  });

  qs("#submitCorrection").addEventListener("click", async () => {
    const label = qs("#correctionLabel").value.trim();
    if (!label) {
      toast("Please enter the correct waste name.");
      return;
    }
    try {
      let updated;
      if (isDemo) {
        updated = { ...scan };
        updated.final_label = label;
        updated.ai_result.label = label;
        updated.ai_result.material = label;
        updated.ai_result.category = qs("#correctionCategory").value;
        updated.category = qs("#correctionCategory").value;
      } else {
        updated = await API.request(`/scan/${scanId}/correct`, {
          method: "PATCH",
          body: { label, category: qs("#correctionCategory").value },
        });
      }
      setScan(updated);
      qs("#correctionBox").style.display = "none";
      toast("✅ Result updated");
    } catch (err) {
      toast(err.message);
    }
  });

  // Record chosen path when a path card is clicked.
  qsa("a.path-action").forEach((link) => {
    link.addEventListener("click", () => {
      const href = link.getAttribute("href") || "";
      if (href.includes("create")) Journey.setPath("create");
      else if (href.includes("recycle")) Journey.setPath("recycle");
      else if (href.includes("dispose")) Journey.setPath("dispose");
    });
  });
});

function labelEmoji(label) {
  const l = (label || "").toLowerCase();
  if (/bottle|jar|glass|can|beverage/.test(l)) return "🧴";
  if (/paper|cardboard|box|news/.test(l)) return "📦";
  if (/bag|plastic/.test(l)) return "🛍️";
  if (/can|metal|aluminium|tin/.test(l)) return "🥫";
  if (/food|organic|peel|fruit|veg/.test(l)) return "🍌";
  return "♻️";
}
