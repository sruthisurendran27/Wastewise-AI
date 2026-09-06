/* Cross-page session state for the current scan journey. */
const Journey = {
  setScan(id, path = "analyzed") {
    sessionStorage.setItem("scan_id", id);
    sessionStorage.setItem("chosen_path", path);
  },
  getScan() {
    return sessionStorage.getItem("scan_id");
  },
  setPath(path) {
    sessionStorage.setItem("chosen_path", path);
  },
  getPath() {
    return sessionStorage.getItem("chosen_path");
  },
  setIdea(ideaJson) {
    sessionStorage.setItem("chosen_idea", ideaJson);
  },
  getIdea() {
    try {
      return JSON.parse(sessionStorage.getItem("chosen_idea") || "null");
    } catch {
      return null;
    }
  },
  clear() {
    sessionStorage.removeItem("scan_id");
    sessionStorage.removeItem("chosen_path");
    sessionStorage.removeItem("chosen_idea");
  },
};