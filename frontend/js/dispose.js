/* Dispose page: show curated responsible-handling guidance + confirmation points.
   Falls back to demo guide when the server is unavailable. */
document.addEventListener("DOMContentLoaded", async () => {
  if (!requireAuth()) return;
  await initPageAuth();

  const scanId = Journey.getScan();
  const loading = qs("#loading");
  const content = qs("#content");
  const errorBox = qs("#errorBox");
  const isDemo = DEMO.isDemo(scanId);

  let wasteType = "General Hazardous";
  let currentScan = null;
  if (scanId) {
    try {
      let scan;
      if (isDemo) scan = DEMO.getScan() || DEMO.scan;
      else scan = await API.request(`/scan/${scanId}`);
      currentScan = scan;
      const label = `${scan.final_label || ""} ${scan.ai_result?.material || ""} ${scan.category || ""}`.toLowerCase();
      qs("#hazardWarning").style.display = scan.requires_special_handling ? "block" : "none";

      const map = [
        [/battery|batter|lithium|cell/i, "Battery"],
        [/e-?waste|electronic|circuit|phone|mobile|smartphone|charger|laptop|computer|wire|cable/i, "E-waste"],
        [/bulb|tube|cfl|fluorescent|led/i, "CFL/LED Bulb"],
        [/paint|chemical|solvent|cleaner|oil|aerosol|spray|pesticide|insecticide/i, "Chemical/Paint"],
        [/syringe|needle|sharps|medical|medicine|pill|medication/i, "Medical/Sharps"],
        [/aerosol|spray can|deodorant/i, "Aerosol Can"],
      ];
      for (const [re, type] of map) {
        if (re.test(label)) {
          wasteType = type;
          break;
        }
      }
    } catch {
      /* fall through to general guidance */
    }
  }

  try {
    let data;
    if (isDemo) {
      data = { guides: [DEMO.guide] };
    } else {
      data = await API.request(`/disposal?waste_type=${encodeURIComponent(wasteType)}`);
    }
    const guide = data.guides && data.guides[0];
    if (!guide) throw new Error("No guidance found for this item.");

    const hazardBadge =
      guide.hazard_level === "High"
        ? '<span class="badge badge-red">High hazard</span>'
        : guide.hazard_level === "Medium"
        ? '<span class="badge badge-amber">Medium hazard</span>'
        : '<span class="badge badge-green">Low hazard</span>';

    qs("#guideCard").innerHTML = `
      <h3>${escapeHtml(guide.waste_type)}</h3>
      <p>${hazardBadge} ${guide.special_collection_required ? '<span class="badge badge-blue">Special collection may be required</span>' : ""}</p>
      <ol class="steps">
        ${guide.instructions.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}
      </ol>
      ${guide.notes ? `<p class="time-stamp">💡 ${escapeHtml(guide.notes)}</p>` : ""}`;

    if (currentScan?.requires_special_handling || guide.hazard_level === "High" || guide.special_collection_required) {
      qs("#safetyChecklist").style.display = "block";
      qs("#safetyChecklist").innerHTML = `<h3>Safety checklist</h3><label><input type="checkbox"> Keep it separate from regular waste</label><label><input type="checkbox"> Do not burn, puncture, or dismantle it</label><label><input type="checkbox"> Use an authorised collection point</label>`;
    }

    loading.style.display = "none";
    content.style.display = "block";
  } catch (err) {
    loading.style.display = "none";
    errorBox.style.display = "block";
    qs("#errorMsg").textContent = err.message;
  }

  qs("#confirmDisposedBtn").addEventListener("click", async () => {
    if (!scanId) {
      toast("Scan an item first, then confirm disposal.");
      return;
    }
    try {
      let result;
      if (isDemo || !navigator.onLine) {
        await new Promise((r) => setTimeout(r, 400));
        DEMO.localStats.add("disposed_item", 10);
        result = { points_earned: 10 };
      } else {
        result = await API.request(`/activity/disposed?scan_id=${scanId}`, { method: "POST" });
      }
      toast(`🎉 +${result.points_earned} WasteWise Points`);
      Journey.clear();
      setTimeout(() => (window.location.href = "dashboard.html"), 900);
    } catch (err) {
      toast(err.message);
      if (err.message.includes("already recorded")) {
        Journey.clear();
        window.location.href = "dashboard.html";
      }
    }
  });
});

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
