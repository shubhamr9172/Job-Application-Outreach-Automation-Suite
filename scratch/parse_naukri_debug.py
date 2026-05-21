import re
import html

html_path = "d:/SR/Main Projects/Resume Details/naukri_debug_content.html"

try:
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
except Exception as e:
    print(f"Failed to read file: {e}")
    content = ""

if content:
    print(f"HTML loaded successfully. Length: {len(content)}")
    
    # Check if there is text indicating a block or captchas
    suspicious_words = ["captcha", "robot", "block", "security", "unusual traffic", "verify you are a human", "distil", "cloudflare", "access denied"]
    for w in suspicious_words:
        if w in content.lower():
            print(f"Suspicious word found: '{w}'")
            
    # Check page title
    title_match = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
    if title_match:
        print(f"Title: {title_match.group(1).strip()}")
    else:
        print("No title tag found.")
        
    # Check if page is just a redirect / empty or has actual content
    # Let's extract some clean text and classes
    # Find all class attributes
    classes = re.findall(r'class=["\']([^"\']+)["\']', content)
    unique_classes = set()
    for c in classes:
        for single_class in c.split():
            unique_classes.add(single_class)
            
    print(f"Number of unique classes: {len(unique_classes)}")
    sorted_classes = sorted(list(unique_classes))
    # Print sample classes
    print("Sample classes (first 50):", sorted_classes[:50])
    
    # Check if there are class names starting with "rec" or containing "card"
    rec_classes = [c for c in unique_classes if "rec" in c.lower() or "card" in c.lower() or "comp" in c.lower()]
    print("Recruiter/Card/Company related classes:", rec_classes)

    # Let's find matches for keywords in text
    print("\nSearch for agency/recruiter text context:")
    text_blocks = re.findall(r'([^<>\n]{0,50}(?:recruitment|agency|staffing|placement|recruiter|company)[^<>\n]{0,50})', content, re.IGNORECASE)
    print(f"Matches count: {len(text_blocks)}")
    for i, block in enumerate(text_blocks[:15]):
        print(f"{i+1}: {block.strip()}")
        
    # Let's find some URLs / links
    links = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', content, re.DOTALL | re.IGNORECASE)
    print(f"\nTotal links: {len(links)}")
    for i, (href, text) in enumerate(links[:20]):
        clean_text = re.sub(r'<[^>]+>', '', text).strip()
        clean_text = re.sub(r'\s+', ' ', clean_text)
        print(f"{i+1}: Href: '{href}' | Text: '{clean_text}'")

