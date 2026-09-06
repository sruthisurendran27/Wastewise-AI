/* WasteWise AI — shared navigation (bottom bar on mobile, top links on desktop). */
const NAV_ITEMS = [
  {
    key: "home",
    label: "Home",
    href: "index.html",
    icon: '<svg viewBox="0 0 24 24"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9"/></svg>',
  },
  {
    key: "scan",
    label: "Scan",
    href: "scan.html",
    icon: '<svg viewBox="0 0 24 24"><path d="M4 8V6a2 2 0 0 1 2-2h2"/><path d="M16 4h2a2 2 0 0 1 2 2v2"/><path d="M20 16v2a2 2 0 0 1-2 2h-2"/><path d="M8 20H6a2 2 0 0 1-2-2v-2"/><circle cx="12" cy="12" r="3"/></svg>',
  },
  {
    key: "create",
    label: "Ideas",
    href: "create.html",
    icon: '<svg viewBox="0 0 24 24"><path d="M9 18h6"/><path d="M10 21h4"/><path d="M12 3a6 6 0 0 0-4 10.4c.8.7 1 1.4 1 2.1V16h6v-.6c0-.7.2-1.4 1-2.1A6 6 0 0 0 12 3z"/></svg>',
  },
  {
    key: "nearby",
    label: "Nearby",
    href: "recycle.html",
    icon: '<svg viewBox="0 0 24 24"><path d="M12 21s-7-5.1-7-11a7 7 0 0 1 14 0c0 5.9-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>',
  },
  {
    key: "profile",
    label: "Profile",
    href: "profile.html",
    icon: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5"/></svg>',
  },
  {
    key: "history",
    label: "History",
    href: "history.html",
    icon: '<svg viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/><path d="M12 7v5l3 2"/></svg>',
  },
];

function initNav(activeKey) {
  const desktop = document.querySelector(".desktop-nav");
  if (desktop) {
    desktop.innerHTML = NAV_ITEMS.map(
      (n) =>
        `<a href="${n.href}" class="${n.key === activeKey ? "active" : ""}" ${n.key === activeKey ? 'aria-current="page"' : ""}>${n.icon}<span>${n.label}</span></a>`
    ).join("");
  }
  const bottom = document.getElementById("bottomNav");
  if (bottom) {
    bottom.innerHTML = NAV_ITEMS.map(
      (n) =>
        `<a href="${n.href}" class="${n.key === activeKey ? "active" : ""}" aria-label="${n.label}" ${n.key === activeKey ? 'aria-current="page"' : ""}>${n.icon}<span>${n.label}</span></a>`
    ).join("");
  }
}
