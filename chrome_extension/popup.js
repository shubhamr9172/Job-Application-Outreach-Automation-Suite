document.addEventListener('DOMContentLoaded', () => {
  const loader = document.getElementById('loader');
  const mainForm = document.getElementById('mainForm');
  const autofillBtn = document.getElementById('autofillBtn');
  const responseMessage = document.getElementById('responseMessage');

  // Form Fields
  const titleInput = document.getElementById('jobTitle');
  const companyInput = document.getElementById('jobCompany');
  const locationInput = document.getElementById('jobLocation');
  const sourceInput = document.getElementById('jobSource');
  const linkInput = document.getElementById('jobLink');
  const descInput = document.getElementById('jobDesc');
  const statusSelect = document.getElementById('jobStatus');
  const notesInput = document.getElementById('jobNotes');

  let serverOnline = false;
  let candidateProfile = null;

  // 1. Check if backend server is online
  checkServerConnection();

  // 2. Query the active tab and extract job details
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs || tabs.length === 0) {
      showError("No active tab found.");
      return;
    }

    const activeTab = tabs[0];

    // Check if it's a standard web page
    if (!activeTab.url || activeTab.url.startsWith("chrome://") || activeTab.url.startsWith("about:") || activeTab.url.startsWith("edge://")) {
      showManualEntry("Not a supported job posting webpage. You can enter details manually.");
      linkInput.value = activeTab.url || "";
      return;
    }

    ensureContentScript(activeTab.id, (success) => {
      if (!success) {
        showManualEntry("Cannot access this page. Please enter details manually.");
        return;
      }

      chrome.tabs.sendMessage(activeTab.id, { action: "SCRAPE_JOB" }, (response) => {
        if (chrome.runtime.lastError || !response) {
          showManualEntry("Failed to read page details. Please enter manually.");
        } else {
          populateFields(response);
        }
      });
    });
  });

  // Check connection to server
  function checkServerConnection() {
    fetch("http://localhost:8000/api/config")
      .then(res => {
        if (res.ok) {
          serverStatus.textContent = "Server Online";
          serverStatus.className = "status-indicator online";
          serverOnline = true;
          saveBtn.classList.remove('disabled');
          return res.json();
        } else {
          setServerOffline();
        }
      })
      .then(config => {
        if (config && config.profile) {
          candidateProfile = config.profile;
          autofillBtn.classList.remove('disabled');
          autofillBtn.disabled = false;
        }
      })
      .catch(() => {
        setServerOffline();
      });
  }

  function setServerOffline() {
    serverStatus.textContent = "Server Offline";
    serverStatus.className = "status-indicator offline";
    serverOnline = false;
    saveBtn.classList.add('disabled');
    autofillBtn.classList.add('disabled');
    autofillBtn.disabled = true;
  }

  // Ensure content script is loaded on the tab
  function ensureContentScript(tabId, callback) {
    chrome.tabs.sendMessage(tabId, { action: "PING" }, (resp) => {
      if (chrome.runtime.lastError || !resp) {
        chrome.scripting.executeScript({
          target: { tabId: tabId },
          files: ['content.js']
        }, () => {
          if (chrome.runtime.lastError) {
            callback(false);
          } else {
            callback(true);
          }
        });
      } else {
        callback(true);
      }
    });
  }

  function populateFields(data) {
    loader.style.display = 'none';
    mainForm.style.display = 'block';

    titleInput.value = data.title || "";
    companyInput.value = data.company || "";
    locationInput.value = data.location || "";
    sourceInput.value = data.source || "manual";
    linkInput.value = data.link || "";
    descInput.value = data.description || "";
  }

  function showManualEntry(msg) {
    loader.style.display = 'none';
    mainForm.style.display = 'block';
    
    sourceInput.value = "manual";
    
    responseMessage.textContent = msg;
    responseMessage.className = "response-message error";
    setTimeout(() => {
      responseMessage.style.display = 'none';
    }, 5000);
  }

  function showError(msg) {
    loader.style.display = 'none';
    responseMessage.textContent = msg;
    responseMessage.className = "response-message error";
  }

  // Handle Save
  saveBtn.addEventListener('click', () => {
    if (!serverOnline) {
      responseMessage.textContent = "Start the python server first (python dashboard_server.py).";
      responseMessage.className = "response-message error";
      return;
    }

    const payload = {
      title: titleInput.value.trim(),
      company: companyInput.value.trim(),
      location: locationInput.value.trim(),
      source: sourceInput.value.trim() || "extension",
      link: linkInput.value.trim(),
      description: descInput.value.trim(),
      status: statusSelect.value,
      notes: notesInput.value.trim()
    };

    if (!payload.title || !payload.link) {
      responseMessage.textContent = "Title and URL are required.";
      responseMessage.className = "response-message error";
      return;
    }

    saveBtn.classList.add('disabled');
    saveBtn.textContent = "Saving...";

    // Send save command to background service worker (to bypass CORS)
    chrome.runtime.sendMessage({
      type: "ADD_JOB_EXTERNAL",
      data: payload
    }, (response) => {
      saveBtn.classList.remove('disabled');
      saveBtn.textContent = "Save to Dashboard";

      if (chrome.runtime.lastError || !response || !response.success) {
        const errMsg = response ? response.error : (chrome.runtime.lastError?.message || "Unknown error");
        responseMessage.textContent = "Save Failed: " + errMsg;
        responseMessage.className = "response-message error";
      } else {
        responseMessage.textContent = response.data.message || "Saved successfully!";
        responseMessage.className = "response-message success";
        
        // Disable button to prevent double submits
        saveBtn.classList.add('disabled');
        saveBtn.disabled = true;
      }
    });
  });

  // Handle Auto-fill click
  autofillBtn.addEventListener('click', () => {
    if (!serverOnline || !candidateProfile) {
      responseMessage.textContent = "Cannot auto-fill: Server offline or profile not found.";
      responseMessage.className = "response-message error";
      responseMessage.style.display = "block";
      return;
    }

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs || tabs.length === 0) return;
      const activeTab = tabs[0];

      autofillBtn.classList.add('disabled');
      autofillBtn.disabled = true;
      autofillBtn.querySelector('span').textContent = "⚡ Auto-filling Form...";
      responseMessage.style.display = 'none';

      ensureContentScript(activeTab.id, (success) => {
        if (!success) {
          autofillBtn.classList.remove('disabled');
          autofillBtn.disabled = false;
          autofillBtn.querySelector('span').textContent = "⚡ Auto-fill Application Form";
          showManualEntry("Cannot inject autofill script on this page.");
          return;
        }

        chrome.tabs.sendMessage(activeTab.id, {
          action: "FILL_FORM",
          profile: candidateProfile
        }, (response) => {
          autofillBtn.classList.remove('disabled');
          autofillBtn.disabled = false;
          autofillBtn.querySelector('span').textContent = "⚡ Auto-fill Application Form";

          if (chrome.runtime.lastError || !response || !response.success) {
            const errMsg = response ? response.message : (chrome.runtime.lastError?.message || "Communication failed.");
            responseMessage.textContent = "Auto-fill Error: " + errMsg;
            responseMessage.className = "response-message error";
            responseMessage.style.display = 'block';
          } else {
            responseMessage.textContent = response.message || "Auto-fill complete!";
            responseMessage.className = "response-message success";
            responseMessage.style.display = 'block';
            setTimeout(() => {
              responseMessage.style.display = 'none';
            }, 5000);
          }
        });
      });
    });
  });
});
