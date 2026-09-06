/* Recycle page: geolocation + Leaflet map + filters + confirmation. */
document.addEventListener("DOMContentLoaded", async () => {
  requireAuth();
  await initPageAuth();

  const scanId = Journey.getScan();
  const hasScan = Boolean(scanId);
  const scanMaterial = sessionStorage.getItem("scan_material");

  const locationPrompt = qs("#locationPrompt");
  const recycleContent = qs("#recycleContent");
  const requestBtn = qs("#requestLocationBtn");
  const districtSelect = qs("#districtSelect");
  const viewDistrictBtn = qs("#viewDistrictBtn");
  const companyDetailsDialog = qs("#companyDetailsDialog");
  const companyDetailsBody = qs("#companyDetailsBody");
  const closeCompanyDetails = qs("#closeCompanyDetails");

  let map = null;
  let markersLayer = null;
  let routeLayer = null;
  let userMarker = null;
  let currentLocation = null;
  let selectedDistrict = "";
  let currentFilters = { material: "", facilityType: "" };

  function savedRecyclers() {
    try { return JSON.parse(localStorage.getItem("ww_saved_recyclers") || "[]"); } catch { return []; }
  }

  function isSavedRecycler(id) { return savedRecyclers().some((saved) => saved.id === id); }

  closeCompanyDetails.addEventListener("click", () => companyDetailsDialog.close());

  async function getMeta() {
    try {
      return await API.request("/recyclers/filters");
    } catch {
      return {
        materials: ["PET Plastic", "Paper", "Glass", "E-waste", "Metal"],
        types: ["Recycler", "Collection Centre", "Scrap Dealer"],
        districts: ["Chennai", "Coimbatore", "Madurai", "Kanyakumari", "Tenkasi"],
      };
    }
  }

  async function loadFilterChips() {
    const meta = await getMeta();
    const chipsWrap = qs("#filterChips");
    const materialChips = ["All", ...meta.materials].map((m, i) => {
      const btn = document.createElement("button");
      btn.className = "chip" + (i === 0 ? " active" : "");
      btn.textContent = m;
      btn.dataset.filter = i === 0 ? "all" : `material:${m}`;
      return btn;
    });
    const typeChips = meta.types.map((t) => {
      const btn = document.createElement("button");
      btn.className = "chip";
      btn.textContent = t;
      btn.dataset.filter = `type:${t}`;
      return btn;
    });
    chipsWrap.append(...materialChips, ...typeChips);

    chipsWrap.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        chipsWrap.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        applyChipFilter(chip.dataset.filter);
      });
    });

    (meta.districts || []).sort().forEach((district) => {
      const option = document.createElement("option");
      option.value = district;
      option.textContent = district;
      districtSelect.appendChild(option);
    });
  }

  function applyChipFilter(filter) {
    if (filter === "all") {
      currentFilters = { material: "", facilityType: "" };
    } else if (filter.startsWith("material:")) {
      currentFilters.material = filter.slice("material:".length);
      currentFilters.facilityType = "";
    } else if (filter.startsWith("type:")) {
      currentFilters.facilityType = filter.slice("type:".length);
      currentFilters.material = "";
    }
    if (currentLocation) loadRecyclers();
  }

  function loadRecyclers() {
    const params = new URLSearchParams({
      lat: currentLocation.lat,
      lng: currentLocation.lng,
      radius_km: "200",
    });
    if (selectedDistrict) params.set("district", selectedDistrict);
    if (currentFilters.material) params.set("material", currentFilters.material);
    if (currentFilters.facilityType) params.set("facility_type", currentFilters.facilityType);

    return API.request(`/recyclers/nearby?${params.toString()}`)
      .then(renderRecyclers)
      .catch((err) => {
        renderRecyclers([]);
        toast(err.message || "Could not load nearby recyclers.");
      });
  }

  function renderRecyclers(recyclers) {
    const listEl = qs("#recyclerList");
    listEl.innerHTML = "";

    if (!map) {
      map = L.map("map").setView([currentLocation.lat, currentLocation.lng], 13);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
      }).addTo(map);
    }
    setTimeout(() => map.invalidateSize(), 0);
    if (markersLayer) map.removeLayer(markersLayer);
    markersLayer = L.layerGroup().addTo(map);
    if (userMarker) map.removeLayer(userMarker);
    userMarker = L.circleMarker([currentLocation.lat, currentLocation.lng], {
      radius: 7, color: "#166534", fillColor: "#22c55e", fillOpacity: 0.9,
    }).addTo(map).bindPopup("You are here");

    if (!recyclers.length) {
      listEl.innerHTML = `<div class="empty">No matching collection points nearby.<br/>Try a wider area or clear the filters.</div>`;
      return;
    }

    const bounds = L.latLngBounds([]);
    recyclers.forEach((r, index) => {
      const item = document.createElement("div");
      item.className = "recycler-item";
      item.dataset.id = r.id;
      const destination = encodeURIComponent(`${r.name}, ${r.address || "Tamil Nadu, India"}`);
      // Spread records sharing an approximate city coordinate so every listing
      // remains visible; directions still use the company address.
      const mapLat = r.latitude + ((index % 5) - 2) * 0.002;
      const mapLng = r.longitude + (Math.floor(index / 5) - 1) * 0.002;
      bounds.extend([mapLat, mapLng]);

      const acceptsMy = (r.accepted_materials || []).some((m) =>
        scanMaterial ? m.toLowerCase().includes(scanMaterial.toLowerCase()) : true
      ) || Boolean(currentFilters.material);
      const serviceChips = (r.services || []).map((s) => {
        const icon = /reuse/i.test(s) ? "🔄" : /recycl/i.test(s) ? "♻️" : "📦";
        return `<span class="badge badge-soft">${icon} ${escapeHtml(s)}</span>`;
      }).join(" ");

      item.innerHTML = `
        <div class="rec-head">
          <span class="name">📍 ${escapeHtml(r.name)}</span>
          <span class="dist">${r.distance_km} km</span>
        </div>
        <div class="rec-meta">
          <span class="badge badge-blue">${escapeHtml(r.type)}</span>
          ${acceptsMy ? '<span class="badge badge-green">Accepts my waste</span>' : ""}
        </div>
        <p class="time-stamp" style="margin:6px 0">${escapeHtml(r.address || "")}</p>
        <div class="rec-services">${serviceChips}</div>
        ${r.opening ? `<p class="open-status">🕘 ${escapeHtml(r.opening)}</p>` : ""}
        ${r.contact ? `<p class="time-stamp">📞 ${escapeHtml(r.contact)}</p>` : ""}
        <div class="rec-actions">
          <button class="btn btn-outline btn-sm showRoute" type="button">Show route</button>
          <a class="btn btn-primary btn-sm" target="_blank" href="https://www.google.com/maps/dir/?api=1&destination=${r.latitude},${r.longitude}">🧭 Directions</a>
          <button class="btn btn-outline btn-sm viewDetails" data-id="${r.id}">View Details</button>
          <button class="btn btn-outline btn-sm saveRecycler" type="button">${isSavedRecycler(r.id) ? "Saved" : "Save"}</button>
        </div>`;

      const directionsLink = item.querySelector('a[href*="maps/dir"]');
      if (directionsLink) {
        directionsLink.href = `https://www.google.com/maps/dir/?api=1&destination=${destination}`;
        directionsLink.rel = "noopener";
      }

      item.querySelector(".showRoute").addEventListener("click", () => {
        showRoute(r);
      });

      item.querySelector(".viewDetails").addEventListener("click", () => {
        companyDetailsBody.innerHTML = `
          <h2>${escapeHtml(r.name)}</h2>
          <p class="time-stamp">${escapeHtml(r.type)} · ${escapeHtml(r.district || selectedDistrict || "Tamil Nadu")}</p>
          <p>${escapeHtml(r.address || "Address not listed")}</p>
          <p><strong>${r.distance_km} km</strong> from your current location</p>
          <p><strong>Accepted materials</strong><br/>${escapeHtml((r.accepted_materials || []).join(", ") || "Not listed")}</p>
          <p><strong>Services</strong><br/>${escapeHtml((r.services || []).join(", ") || "Not listed")}</p>
          <a class="btn btn-primary" target="_blank" rel="noopener" href="https://www.google.com/maps/dir/?api=1&destination=${destination}">Get directions</a>`;
        companyDetailsDialog.showModal();
        const routeButton = document.createElement("button");
        routeButton.className = "btn btn-outline";
        routeButton.type = "button";
        routeButton.textContent = "Show route in map";
        routeButton.addEventListener("click", () => { companyDetailsDialog.close(); showRoute(r); });
        companyDetailsBody.appendChild(routeButton);
      });

      item.querySelector(".saveRecycler").addEventListener("click", () => {
        const saved = savedRecyclers();
        const alreadySaved = isSavedRecycler(r.id);
        const next = alreadySaved ? saved.filter((entry) => entry.id !== r.id) : [...saved, { id: r.id, name: r.name, district: r.district, address: r.address, contact: r.contact }];
        localStorage.setItem("ww_saved_recyclers", JSON.stringify(next));
        item.querySelector(".saveRecycler").textContent = alreadySaved ? "Save" : "Saved";
        toast(alreadySaved ? "Removed from saved recyclers" : "Recycler saved");
      });

      const marker = L.marker([mapLat, mapLng]).addTo(markersLayer).bindPopup(
        `<strong>${escapeHtml(r.name)}</strong><br/>${r.distance_km} km<br/>${escapeHtml(r.type)}`
      );
      marker.on("click", () => {
        listEl.querySelectorAll(".recycler-item").forEach((el) => el.classList.remove("selected"));
        item.classList.add("selected");
      });

      listEl.appendChild(item);
    });
    if (bounds.isValid()) map.fitBounds(bounds.pad(0.2), { maxZoom: 13 });
  }

  async function showRoute(recycler) {
    if (!currentLocation) {
      toast("Choose a district and allow location access first.");
      return;
    }
    const routeUrl = `https://router.project-osrm.org/route/v1/driving/${currentLocation.lng},${currentLocation.lat};${recycler.longitude},${recycler.latitude}?overview=full&geometries=geojson`;
    try {
      const response = await fetch(routeUrl);
      if (!response.ok) throw new Error("Route service unavailable");
      const data = await response.json();
      const route = data.routes && data.routes[0];
      if (!route) throw new Error("No driving route found");

      if (routeLayer) map.removeLayer(routeLayer);
      routeLayer = L.geoJSON(route.geometry, {
        style: { color: "#cc0000", weight: 5, opacity: 0.85 },
      }).addTo(map);
      map.fitBounds(routeLayer.getBounds().pad(0.15));
      toast(`${(route.distance / 1000).toFixed(1)} km route · approximately ${Math.round(route.duration / 60)} min`);
    } catch (err) {
      toast(err.message || "Could not display the route.");
    }
  }

  function enableLocation(lat, lng) {
    currentLocation = { lat, lng };
    locationPrompt.style.display = "none";
    recycleContent.style.display = "block";
    if (!hasScan) qs("#scanReminder").style.display = "block";
    loadRecyclers();
  }

  districtSelect.addEventListener("change", () => {
    viewDistrictBtn.disabled = !districtSelect.value;
  });

  viewDistrictBtn.addEventListener("click", () => {
    selectedDistrict = districtSelect.value;
    requestUserLocation();
  });

  function requestUserLocation() {
    if (!selectedDistrict) {
      toast("Select your Tamil Nadu district first.");
      return;
    }
    if (!navigator.geolocation) {
      toast("Your browser does not support location services.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => enableLocation(pos.coords.latitude, pos.coords.longitude),
      () => {
        toast("Location permission is needed to find recyclers near you.");
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  }

  requestBtn.addEventListener("click", requestUserLocation);

  qs("#confirmRecycledBtn").addEventListener("click", async () => {
    if (!hasScan) {
      toast("Scan an item first, then confirm recycling.");
      return;
    }
    try {
      let result;
      if (DEMO.isDemo(scanId) || !navigator.onLine) {
        await new Promise((r) => setTimeout(r, 400));
        DEMO.localStats.add("recycled_item", 15);
        result = { points_earned: 15 };
      } else {
        result = await API.request(`/activity/recycled?scan_id=${scanId}`, { method: "POST" });
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

  loadFilterChips();
});

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
