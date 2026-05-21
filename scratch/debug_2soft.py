from scrapling.fetchers import StealthyFetcher

url = "https://www.2softsolutions.com/"
page = StealthyFetcher.fetch(url, headless=True, timeout=15000)
if page:
    print(f"Status: {page.status}")
    print(f"URL: {page.url}")
    print(f"HTML Length: {len(page.text or '')}")
    
    # Print all links and text
    links = []
    for a in page.css("a"):
        href = a.attrib.get("href", "")
        text = (a.text or "").strip()
        links.append((href, text))
    
    print("\nAll links found:")
    for h, t in links[:50]:
        print(f"Href: '{h}', Text: '{t}'")
else:
    print("Failed to fetch page")
