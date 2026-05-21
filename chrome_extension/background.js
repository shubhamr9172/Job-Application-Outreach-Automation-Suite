// Handle network request forwarding to bypass extension sandbox restrictions
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "ADD_JOB_EXTERNAL") {
    fetch("http://localhost:8000/api/jobs/external-add", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(request.data)
    })
    .then(res => {
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
      return res.json();
    })
    .then(data => {
      sendResponse({ success: true, data });
    })
    .catch(err => {
      sendResponse({ success: false, error: err.message });
    });
    return true; // Keeps the sendResponse channel open asynchronously
  }
});
