/* Scan page: manage camera/upload flow and submit the photo for classification. */
document.addEventListener("DOMContentLoaded", () => {
  requireAuth();
  initPageAuth();

  const video = qs("#camera");
  const canvas = qs("#snapshot");
  const startBtn = qs("#startCameraButton");
  const captureBtn = qs("#captureButton");
  const fileInput = qs("#fileInput");
  const preview = qs("#preview");
  const analyzeBtn = qs("#analyzeButton");
  const scanActions = qs("#scanActions");
  const analyzing = qs("#analyzing");
  const errorBox = qs("#errorBox");
  const modeHint = qs("#modeHint");

  let stream = null;
  let currentBlob = null;

  function showError(msg) {
    errorBox.textContent = msg;
    errorBox.style.display = "block";
  }

  function hideError() {
    errorBox.style.display = "none";
  }

  /* --- Explicit demo mode: one-tap Plastic Bottle journey without an API --- */
  if (window.location.hash === "#demo") {
    DEMO.start();
    goToResult();
  }

  function goToResult() {
    window.location.href = "result.html";
  }

  function setBusy(busy) {
    analyzing.style.display = busy ? "block" : "none";
    scanActions.style.display = busy ? "none" : "block";
  }

  // If user came from home with ?mode=upload, default to upload prompt.
  if (new URLSearchParams(window.location.search).get("mode") === "upload") {
    startBtn.classList.add("btn-outline");
    modeHint.textContent = "Choose a photo of your waste from your gallery.";
  }

  startBtn.addEventListener("click", () => {
    initCamera(video)
      .then((s) => {
        stream = s;
        video.style.display = "block";
        video.classList.add("live");
        qs(".scan-placeholder").style.display = "none";
        startBtn.style.display = "none";
        captureBtn.style.display = "inline-flex";
      })
      .catch((err) => {
        showError(err.message);
        // Fall back to upload control.
        fileInput.click();
      });
  });

  captureBtn.addEventListener("click", async () => {
    try {
      currentBlob = await capturePhoto(video, canvas);
      stopCamera(stream);
      stream = null;
      video.style.display = "none";
      captureBtn.style.display = "none";
      startBtn.style.display = "none";
      qs(".scan-placeholder").style.display = "none";
      preview.src = URL.createObjectURL(currentBlob);
      preview.style.display = "block";
      scanActions.style.display = "block";
    } catch (err) {
      showError(err.message);
    }
  });

  fileInput.addEventListener("change", () => {
    const file = fileInput.files && fileInput.files[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      showError("Please choose an image file (JPG, PNG, WebP).");
      return;
    }
    if (stream) {
      stopCamera(stream);
      stream = null;
      video.style.display = "none";
      captureBtn.style.display = "none";
    }
    currentBlob = file;
    qs(".scan-placeholder").style.display = "none";
    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";
    scanActions.style.display = "block";
  });

  analyzeBtn.addEventListener("click", async () => {
    if (!currentBlob) return;
    if (!navigator.onLine) {
      showError("You are offline. Connect to the internet to classify this uploaded image.");
      return;
    }
    setBusy(true);
    hideError();
    try {
      const form = new FormData();
      form.append("file", currentBlob, "waste.jpg");
      const scan = await API.request("/scan", {
        method: "POST",
        body: form,
        isFormData: true,
      });
      Journey.setScan(scan.id);
      goToResult();
    } catch (err) {
      // Keep live failures visible. The demo is only entered explicitly or offline;
      // silently replacing a real result makes every failed scan look identical.
      setBusy(false);
      showError(err.message || "Classification failed. Please try again.");
    }
  });
});
