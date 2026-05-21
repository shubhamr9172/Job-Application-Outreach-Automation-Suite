from scrapling.fetchers import StealthyFetcher

url = "https://www.2softsolutions.com/"
page = StealthyFetcher.fetch(url, headless=True, timeout=15000)
if page:
    print("Page object properties:")
    for prop in dir(page):
        if not prop.startswith("_"):
            print(f"- {prop}: {type(getattr(page, prop))}")
    
    # Try to see where the text/html content is
    # e.g., page.content, page.text, page.raw, etc.
    try:
        print(f"page.content (type: {type(page.content)})")
    except Exception as e:
        print("page.content failed:", e)
        
    try:
        print(f"page.text length: {len(page.text or '')}")
    except Exception as e:
        print("page.text failed:", e)
        
    try:
        # Check if we can get full page text via selector
        body_text = page.css('html').text
        print(f"page.css('html').text length: {len(body_text or '')}")
        print("First 200 chars of body_text:", body_text[:200] if body_text else "None")
    except Exception as e:
        print("page.css('html').text failed:", e)
else:
    print("Failed to fetch page")
