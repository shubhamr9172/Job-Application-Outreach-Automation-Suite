import json
import urllib.request
import urllib.error

def main():
    url = "http://localhost:8000/api/jobs/analyze"
    
    # We will use one of the existing links in jobs_tracker.json so it updates it,
    # or a mock link which will create a new manual entry.
    payload = {
        "link": "https://apply.workable.com/keywords-intl1/j/E8B1526F94",
        "jd_text": """
Role: AI Engineer
Company: Keywords Studios
Location: Remote (India)

About the role:
We are seeking an experienced AI Engineer to join our global technology division. You will build and deploy generative AI applications, agentic workflows, and high-performance Retrieval-Augmented Generation (RAG) systems.

Key Responsibilities:
- Design, build, and optimize stateful multi-agent workflows using LangGraph and LangChain.
- Develop and maintain semantic search layers and vector indexing with Qdrant and ChromaDB.
- Set up automated LLM evaluation frameworks using DeepEval and Ragas to track retrieval accuracy and hallucination rates.
- Deploy SLM/LLM microservices using vLLM on GCP (Google Kubernetes Engine) and optimize prompt templates for cost and latency.
- Collaborate with product teams to integrate AI models into user-facing web applications.

Requirements:
- 3+ years of software engineering experience in Python.
- Proven experience building RAG systems and using LLM/SLM APIs (Gemini, Claude, or OpenAI).
- Strong hands-on knowledge of LangGraph, LangChain, or similar agentic frameworks.
- Experience with Vector Databases (Qdrant, Pinecone, or ChromaDB).
- Hands-on experience with LLM evaluation methods and observability tools (LangSmith or Arize Phoenix).
- Experience with containerization (Docker, Kubernetes) and cloud platforms (GCP preferred).
- Excellent communication and English skills.
"""
    }
    
    headers = {"Content-Type": "application/json; charset=utf-8"}
    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode("utf-8"), 
        headers=headers, 
        method="POST"
    )
    
    print("[*] Sending analyze request to server...")
    try:
        with urllib.request.urlopen(req) as res:
            response_data = res.read().decode("utf-8")
            response_json = json.loads(response_data)
            print("[OK] Server responded with success!")
            print(f"Status Success: {response_json.get('success')}")
            job = response_json.get("job", {})
            print(f"Title: {job.get('title')}")
            print(f"Company: {job.get('company')}")
            print(f"Suitability Score: {job.get('suitability_score')}/100")
            print(f"Matching Skills: {job.get('matching_skills')}")
            print(f"Missing Skills: {job.get('missing_skills')}")
            print(f"Resume Suggestions Count: {len(job.get('resume_suggestions', []))}")
            print("\nDraft Cover Letter (first 150 chars):")
            print(job.get("cover_letter", "")[:150] + "...")
            print("\nStudy Plan (first 150 chars):")
            print(job.get("study_plan", "")[:150] + "...")
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP Error: {e.code} - {e.reason}")
        print(e.read().decode("utf-8"))
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")

if __name__ == "__main__":
    main()
