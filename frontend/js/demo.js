/* Demo mode · a fully client-side Plastic Bottle journey for SIH presentations.
   Activated via "See how it works" on Home. Used only when the live backend/AI
   is unavailable, so the whole flow can still be demonstrated. */
const DEMO = {
  SCAN_ID: "__demo__",

  isDemo(scanId) {
    return scanId === this.SCAN_ID;
  },

  scan: {
    id: "__demo__",
    image_url: null,
    ai_result: {
      label: "Plastic Bottle",
      material: "PET Plastic",
      category: "Recyclable",
      condition: "Reusable",
      requires_special_handling: false,
      confidence: 0.94,
      raw_model_text: "Demo mode canned classification",
    },
    final_label: "Plastic Bottle",
    category: "Recyclable",
    requires_special_handling: false,
    status: "completed",
    created_at: new Date().toISOString(),
  },

  ideas: [
    {
      id: "self-watering-planter",
      title: "Self-Watering Planter",
      difficulty: "Easy",
      time_minutes: 20,
      extra_materials: "String, soil, seeds",
      is_best_match: true,
      tags: ["Best Match", "Eco-Friendly"],
      steps: [
        "Clean the bottle thoroughly and remove the label.",
        "Cut the bottle in half and keep both pieces.",
        "Thread a cotton string through the bottle cap.",
        "Fill the top half with soil and seeds, then invert it into the water reservoir.",
        "Place it near sunlight — your planter waters itself.",
      ],
      value_min: 30,
      value_max: 80,
      usage_tags: ["Personal use", "Gift", "Hydroponics"],
    },
    {
      id: "pineapple-pen-holder",
      title: "Pineapple Pen Holder",
      difficulty: "Easy",
      time_minutes: 10,
      extra_materials: "Colour paper, scissors",
      is_best_match: false,
      tags: ["Easy", "High Value"],
      steps: [
        "Clean the bottle and cut it to half height.",
        "Wrap it in yellow paper and add a leafy green top.",
        "Draw a pineapple grid with a marker.",
        "Use it as a bright desk organiser.",
      ],
      value_min: 15,
      value_max: 45,
      usage_tags: ["Personal use", "Sell"],
    },
    {
      id: "vertical-garden-unit",
      title: "Vertical Garden Unit",
      difficulty: "Medium",
      time_minutes: 35,
      extra_materials: "Rope, soil, small plants",
      is_best_match: false,
      tags: ["Eco-Friendly"],
      steps: [
        "Clean the bottles and cut a side opening in each.",
        "Poke hanging holes near the top and bottom.",
        "String the bottles along a wall or balcony rail.",
        "Add soil and a small plant to every pocket.",
      ],
      value_min: 80,
      value_max: 180,
      usage_tags: ["Personal use", "Decor"],
    },
  ],

  recyclers: [
    { id: "d-r1", name: "EcoGreen Recyclers", type: "Recycler", latitude: 12.9716, longitude: 77.5946, distance_km: 1.2, address: "Koramangala, Bengaluru", accepted_materials: ["PET Plastic", "Plastic", "Paper", "Glass"], services: ["Recycling", "Scrap collection"], contact: "+91 98765 43210" },
    { id: "d-r2", name: "GreenPoint Reuse Hub", type: "Collection Centre", latitude: 12.9784, longitude: 77.6062, distance_km: 2.5, address: "Indiranagar, Bengaluru", accepted_materials: ["PET Plastic", "Plastic", "E-waste", "Cloth"], services: ["Reuse", "Recycling"], contact: "+91 91234 56780" },
    { id: "d-r3", name: "City Scrap Depot", type: "Scrap Dealer", latitude: 12.9600, longitude: 77.5800, distance_km: 3.1, address: "Wilson Garden, Bengaluru", accepted_materials: ["PET Plastic", "Metal", "Paper"], services: ["Scrap collection", "Buyback"], contact: "+91 90000 12345" },
  ],

  guide: {
    waste_type: "General Hazardous",
    hazard_level: "Low",
    instructions: [
      "When in doubt, keep hazardous items separate from recyclables.",
      "Search for your ward's nearest designated collection point.",
      "Never burn or crush pressurised or e-waste items.",
    ],
    special_collection_required: true,
    notes: "Fallback guidance shown in demo mode.",
  },

  start() {
    // Demo works without a real account: seed a guest session so the whole
    // journey (scan → result → create → nearby → impact) works offline.
    if (!API.getToken()) {
      localStorage.setItem(API.TOKEN_KEY, "__demo__");
      localStorage.setItem(
        API.USER_KEY,
        JSON.stringify({ id: "demo", name: "Demo User", email: "demo@wastewise.ai", points: 0 })
      );
    }
    Journey.setScan(this.SCAN_ID);
    sessionStorage.setItem("demo_scan", JSON.stringify(this.scan));
  },

  getScan() {
    try {
      return JSON.parse(sessionStorage.getItem("demo_scan") || "null");
    } catch {
      return null;
    }
  },

  /* Small local ledger so demo earned points still work if the server is down. */
  localStats: {
    key: "ww_demo_stats",
    get() {
      try {
        return JSON.parse(localStorage.getItem(this.key) || "null");
      } catch {
        return null;
      }
    },
    add(actionType, points, valueMin = 0, valueMax = 0) {
      const s = this.get() || {
        points: 0, items_reused: 0, items_recycled: 0, items_disposed: 0,
        waste_diverted: 0, value_created_total_min: 0, value_created_total_max: 0,
        recent_activities: [],
      };
      s.points += points;
      s.waste_diverted += 1;
      if (actionType === "made_item") {
        s.items_reused += 1;
        s.value_created_total_min += valueMin;
        s.value_created_total_max += valueMax;
      } else if (actionType === "recycled_item") {
        s.items_recycled += 1;
      } else {
        s.items_disposed += 1;
      }
      const descriptions = {
        made_item: "Made something new from waste 💡",
        recycled_item: "Recycled an item ♻️",
        disposed_item: "Disposed of an item responsibly 🗑️",
      };
      s.recent_activities.unshift({
        id: `d-${Date.now()}`,
        action_type: actionType,
        points_earned: points,
        description: descriptions[actionType] || actionType,
        created_at: new Date().toISOString(),
      });
      if (s.recent_activities.length > 10) s.recent_activities.length = 10;
      localStorage.setItem(this.key, JSON.stringify(s));
      return s;
    },
  },

  /* Return real dashboard stats when reachable, otherwise the local demo ledger. */
  async statsOrDemo() {
    try {
      return await API.request("/dashboard");
    } catch {
      const st = this.localStats.get();
      return (
        st || {
          points: 0, items_reused: 0, items_recycled: 0, items_disposed: 0,
          waste_diverted: 0, value_created_total_min: 0, value_created_total_max: 0,
          recent_activities: [],
        }
      );
    }
  },
};