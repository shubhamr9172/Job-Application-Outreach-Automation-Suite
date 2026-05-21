// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "PING") {
    sendResponse({ success: true, message: "pong" });
  } else if (request.action === "SCRAPE_JOB") {
    try {
      const scrapedData = scrapeJobDetails();
      sendResponse(scrapedData);
    } catch (e) {
      sendResponse({ error: e.message });
    }
  } else if (request.action === "FILL_FORM") {
    try {
      const result = fillFormFields(request.profile);
      sendResponse({
        success: true,
        message: `Filled ${result.filledCount} fields. Highlighted ${result.highlightedZones} resume drop zones.`
      });
    } catch (e) {
      sendResponse({ success: false, message: e.message });
    }
  }
  return true;
});

function scrapeJobDetails() {
  const url = window.location.href;
  let title = "";
  let company = "";
  let location = "";
  let description = "";
  let source = "manual";

  if (url.includes("linkedin.com")) {
    source = "linkedin";
    // Title selectors
    const titleEl = document.querySelector(".job-details-jobs-unified-top-card__job-title, .jobs-unified-top-card__job-title, h1, .jobs-details-sidebar__title");
    title = titleEl ? titleEl.textContent : "";
    
    // Company selectors
    const companyEl = document.querySelector(".job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name a, .jobs-details-sidebar__company-link");
    company = companyEl ? companyEl.textContent : "";
    
    // Location selectors
    const locEl = document.querySelector(".job-details-jobs-unified-top-card__bullet, .jobs-unified-top-card__bullet, .jobs-unified-top-card__company-name + span");
    location = locEl ? locEl.textContent : "";
    
    // Description
    const descEl = document.querySelector(".jobs-description__content, .jobs-box__html-content, #job-details");
    description = descEl ? descEl.innerText : "";
    
  } else if (url.includes("naukri.com")) {
    source = "naukri";
    const titleEl = document.querySelector(".jd-header-title, h1, .title");
    title = titleEl ? titleEl.textContent : "";
    
    const companyEl = document.querySelector(".jd-header-comp-name a, .jd-header-comp-name, .companyName");
    company = companyEl ? companyEl.textContent : "";
    
    const locEl = document.querySelector(".location span, .loc, .locIcon + span");
    location = locEl ? locEl.textContent : "";
    
    const descEl = document.querySelector(".job-desc, .details, .jobDesc");
    description = descEl ? descEl.innerText : "";
    
  } else if (url.includes("indeed.com")) {
    source = "indeed";
    const titleEl = document.querySelector(".jobsearch-JobInfoHeader-title, h1, [data-testid='simCardJobTitle']");
    title = titleEl ? titleEl.textContent : "";
    
    const companyEl = document.querySelector("[data-company-name='true'], .jobsearch-CompanyInfoContainer, .jobsearch-InlineCompanyRating a");
    company = companyEl ? companyEl.textContent : "";
    
    const locEl = document.querySelector("#jobLocationSection, .jobsearch-JobInfoHeader-subtitle, [data-testid='jobsearch-JobInfoHeader-companyLocation']");
    location = locEl ? locEl.textContent : "";
    
    const descEl = document.querySelector("#jobDescriptionText");
    description = descEl ? descEl.innerText : "";
    
  } else if (url.includes("lever.co")) {
    source = "lever";
    const titleEl = document.querySelector(".posting-header h2");
    title = titleEl ? titleEl.textContent : "";
    
    const catEl = document.querySelector(".posting-categories .department, .posting-header .categories");
    company = catEl ? catEl.textContent : "";
    
    const locEl = document.querySelector(".posting-categories .location, .location");
    location = locEl ? locEl.textContent : "";
    
    const descEl = document.querySelector(".section.page-centered");
    description = descEl ? descEl.innerText : "";
    
  } else if (url.includes("greenhouse.io")) {
    source = "greenhouse";
    const titleEl = document.querySelector(".app-title, h1");
    title = titleEl ? titleEl.textContent : "";
    
    const compEl = document.querySelector(".company-name");
    company = compEl ? compEl.textContent : "";
    
    const locEl = document.querySelector(".location");
    location = locEl ? locEl.textContent : "";
    
    const descEl = document.querySelector("#content");
    description = descEl ? descEl.innerText : "";
  } else {
    // General fallback
    title = document.querySelector("h1, h2")?.textContent || document.title || "";
    description = document.querySelector("main, article, body")?.innerText || "";
  }

  // Helper cleanups
  title = title.trim().replace(/\s+/g, " ");
  
  // Clean company string (LinkedIn often appends rating, etc.)
  company = company.trim().replace(/\s+/g, " ");
  // LinkedIn rating filter if e.g. "Google 4.5"
  company = company.replace(/\d\.\d\s*$/, '').trim();
  
  location = location.trim().replace(/\s+/g, " ").replace(/^·\s*/, "").trim();
  
  // Extract first 400 chars of description
  description = description.trim().replace(/\s+/g, " ");
  if (description.length > 400) {
    description = description.substring(0, 400) + "...";
  }

  return {
    title,
    company,
    location,
    link: url,
    source,
    description
  };
}

// Set input value and trigger standard framework event listeners
function setInputValue(element, value) {
  if (!element) return;
  
  if (element.tagName === 'SELECT') {
    let found = false;
    // 1. Try exact match on option value
    for (let i = 0; i < element.options.length; i++) {
      if (element.options[i].value === value) {
        element.selectedIndex = i;
        found = true;
        break;
      }
    }
    // 2. Try case-insensitive substring match on option text or value
    if (!found) {
      const lowerVal = String(value).toLowerCase();
      for (let i = 0; i < element.options.length; i++) {
        const optText = element.options[i].text.toLowerCase();
        const optVal = element.options[i].value.toLowerCase();
        if (optText.includes(lowerVal) || optVal.includes(lowerVal)) {
          element.selectedIndex = i;
          found = true;
          break;
        }
      }
    }
  } else if (element.type === 'checkbox' || element.type === 'radio') {
    const valStr = String(value).toLowerCase();
    const shouldCheck = (valStr === 'true' || valStr === '1' || valStr === 'yes' || valStr === 'checked');
    element.checked = shouldCheck;
  } else {
    element.value = value;
  }
  
  // Dispatch input and change events for framework binding (React, Vue, Angular, etc.)
  element.dispatchEvent(new Event('input', { bubbles: true }));
  element.dispatchEvent(new Event('change', { bubbles: true }));
}

// Find label text associated with form input elements
function getLabelText(element) {
  if (element.id) {
    const label = document.querySelector(`label[for="${element.id}"]`);
    if (label) return label.textContent.trim();
  }
  const parentLabel = element.closest('label');
  if (parentLabel) return parentLabel.textContent.trim();

  const parent = element.parentElement;
  if (parent) {
    const clone = parent.cloneNode(true);
    const inputs = clone.querySelectorAll('input, select, textarea');
    inputs.forEach(i => i.remove());
    return clone.textContent.trim();
  }

  return "";
}

// Match input elements to profile fields using keyword heuristics
function matchFieldType(element, labelText) {
  const text = (
    labelText + " " +
    (element.placeholder || "") + " " +
    (element.name || "") + " " +
    (element.id || "")
  ).toLowerCase();

  // Exclusions: If the field is for other entities, do not autofill it with the candidate's name or contact info.
  // 1. Education
  if (text.includes("school") || text.includes("college") || text.includes("university") || 
      text.includes("degree") || text.includes("major") || text.includes("gpa") || 
      text.includes("education") || text.includes("graduation") || text.includes("study") || text.includes("schoolname")) {
    return null;
  }
  
  // 2. References / Managers
  if (text.includes("reference") || text.includes("referee") || text.includes("manager") || 
      text.includes("supervisor") || text.includes("colleague") || text.includes("coworker") || 
      text.includes("co-worker") || text.includes("friend")) {
    return null;
  }
  
  // 3. Projects / Files / Passwords
  if (text.includes("project") || text.includes("file") || text.includes("resume") || 
      text.includes("cv") || text.includes("upload") || text.includes("attachment") || 
      text.includes("cover letter") || text.includes("password") || text.includes("username")) {
    return null;
  }

  // 4. Middle Names / Other Names / Headings
  if (text.includes("middle name") || text.includes("middle_name") || text.includes("middle initial")) {
    return null;
  }

  // Now, classify field type based on prioritised keywords:
  
  // Email
  if (text.includes("email") || text.includes("e-mail")) {
    return "email";
  }

  // LinkedIn
  if (text.includes("linkedin") || text.includes("linked in") || text.includes("lnk.in")) {
    return "linkedin";
  }

  // GitHub
  if (text.includes("github") || text.includes("git hub")) {
    return "github";
  }

  // Portfolio / Website / Links
  if (text.includes("portfolio") || text.includes("website") || text.includes("personal site") || 
      text.includes("blog") || text.includes("personal link") || text.includes("homepage")) {
    return "portfolio";
  }

  // Company / Employer
  if (text.includes("company") || text.includes("employer") || text.includes("organization") || 
      text.includes("current firm") || text.includes("firm")) {
    return "company";
  }

  // Experience / Years
  if (text.includes("experience") || text.includes("years") || text.includes("yr")) {
    return "experience";
  }

  // Phone / Mobile
  if (text.includes("phone") || text.includes("mobile") || text.includes("contact") || 
      text.includes("tel") || text.includes("cell") || text.includes("phone number")) {
    return "phone";
  }

  // First Name
  if (text.includes("first name") || text.includes("given name") || text.includes("forename") || text.includes("fname")) {
    return "first_name";
  }

  // Last Name
  if (text.includes("last name") || text.includes("surname") || text.includes("family name") || text.includes("lname")) {
    return "last_name";
  }

  // Full Name (Check last as a fallback for any general "name" field)
  if (text.includes("full name") || text.includes("fullname") || text.includes("your name") || 
      text.includes("candidate name") || text.includes("applicant name") || 
      text.trim() === "name" || text.includes(" name")) {
    return "full_name";
  }

  return null;
}

// Highlight resume drop/upload zones
function highlightResumeDropZones() {
  let highlightedCount = 0;
  
  // Find all file inputs
  const fileInputs = document.querySelectorAll('input[type="file"]');
  fileInputs.forEach(input => {
    const container = input.closest('div, label, section') || input;
    applyHighlightStyle(container, "📎 Resume / CV Drop Zone");
    highlightedCount++;
  });

  // Find elements with text matching upload resume / cv patterns
  const allElements = document.querySelectorAll('div, label, span, section');
  allElements.forEach(el => {
    if (el.children.length > 5) return; // Skip large layout blocks
    const text = el.innerText || el.textContent || "";
    if (/\b(upload|drag|drop|attach)\b.*\b(resume|cv|c\.v\.)\b/i.test(text)) {
      applyHighlightStyle(el, "📎 Resume / CV Upload Area");
      highlightedCount++;
    }
  });

  return highlightedCount;
}

function applyHighlightStyle(element, label) {
  if (element.dataset.antigravityHighlighted) return;
  element.dataset.antigravityHighlighted = "true";

  element.style.border = "2px dashed #10b981";
  element.style.borderRadius = "8px";
  element.style.backgroundColor = "rgba(16, 185, 129, 0.05)";
  element.style.position = "relative";
  element.style.padding = "10px";

  const badge = document.createElement('div');
  badge.textContent = label;
  badge.style.position = "absolute";
  badge.style.top = "-12px";
  badge.style.left = "10px";
  badge.style.backgroundColor = "#10b981";
  badge.style.color = "white";
  badge.style.padding = "2px 8px";
  badge.style.borderRadius = "4px";
  badge.style.fontSize = "10px";
  badge.style.fontWeight = "bold";
  badge.style.zIndex = "9999";
  badge.style.pointerEvents = "none";
  element.appendChild(badge);
}

// Perform form autofill using candidate profile
function fillFormFields(profile) {
  let filledCount = 0;
  
  const nameParts = (profile.full_name || "").trim().split(/\s+/);
  const firstName = nameParts[0] || "";
  const lastName = nameParts.slice(1).join(" ") || "";

  const elements = document.querySelectorAll('input, textarea, select');
  
  elements.forEach(element => {
    if (element.type === 'hidden' || element.type === 'submit' || element.type === 'button') return;
    
    const labelText = getLabelText(element);
    const fieldType = matchFieldType(element, labelText);

    if (!fieldType) return;

    switch (fieldType) {
      case "email":
        if (profile.email) {
          setInputValue(element, profile.email);
          filledCount++;
        }
        break;
      case "phone":
        if (profile.phone) {
          setInputValue(element, profile.phone);
          filledCount++;
        }
        break;
      case "linkedin":
        if (profile.linkedin) {
          setInputValue(element, profile.linkedin);
          filledCount++;
        }
        break;
      case "github":
        if (profile.github) {
          setInputValue(element, profile.github);
          filledCount++;
        }
        break;
      case "portfolio":
        const portfolioVal = profile.portfolio || profile.website;
        if (portfolioVal) {
          setInputValue(element, portfolioVal);
          filledCount++;
        }
        break;
      case "company":
        if (profile.current_company) {
          setInputValue(element, profile.current_company);
          filledCount++;
        }
        break;
      case "experience":
        if (profile.experience_years) {
          setInputValue(element, profile.experience_years);
          filledCount++;
        }
        break;
      case "first_name":
        if (firstName) {
          setInputValue(element, firstName);
          filledCount++;
        }
        break;
      case "last_name":
        if (lastName) {
          setInputValue(element, lastName);
          filledCount++;
        }
        break;
      case "full_name":
        if (profile.full_name) {
          setInputValue(element, profile.full_name);
          filledCount++;
        }
        break;
    }
  });

  const highlightedZones = highlightResumeDropZones();

  return {
    filledCount,
    highlightedZones
  };
}
