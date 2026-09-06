/* Camera helpers: getUserMedia capture with canvas snapshot and teardown. */
function initCamera(videoEl) {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    return Promise.reject(new Error("Camera not supported in this browser."));
  }
  return navigator.mediaDevices
    .getUserMedia({ video: { facingMode: "environment" }, audio: false })
    .then((stream) => {
      videoEl.srcObject = stream;
      return videoEl.play().then(() => stream);
    });
}

function capturePhoto(videoEl, canvasEl) {
  canvasEl.width = videoEl.videoWidth || 1280;
  canvasEl.height = videoEl.videoHeight || 720;
  const ctx = canvasEl.getContext("2d");
  ctx.drawImage(videoEl, 0, 0, canvasEl.width, canvasEl.height);
  return new Promise((resolve) => {
    canvasEl.toBlob((blob) => resolve(blob), "image/jpeg", 0.9);
  });
}

function stopCamera(stream) {
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
  }
}