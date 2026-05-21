from scrapling.fetchers import StealthyFetcher

url = "https://www.2softsolutions.com/"
page = StealthyFetcher.fetch(url, headless=True, timeout=15000)
if page:
    print(f"page.url: {page.url}")
    print(f"page.status: {page.status}")
    print(f"page.body length: {len(page.body or b'')}")
    print(f"page.html_content type: {type(page.html_content)}, length: {len(str(page.html_content or ''))}")
    
    # Try calling get_all_text
    try:
        all_text = page.get_all_text()
        print(f"page.get_all_text() length: {len(all_text or '')}")
        print("First 200 chars of all_text:", all_text[:200] if all_text else "None")
    except Exception as e:
        print("page.get_all_text() failed:", e)
        
    # Let's see if str(page.html_content) or page.body.decode() contains the HTML
    html = str(page.html_content) if page.html_content else ""
    if not html and page.body:
        html = page.body.decode('utf-8', errors='ignore')
    print(f"Combined HTML length: {len(html)}")
else:
    print("Failed to fetch page")
