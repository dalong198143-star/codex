import sys; sys.path.insert(0, r"D:\maozhua\Codex\codex\scripts")
from monitor.engine.classifier import classify_multi

tests = [
    "Venture capital funding for AI startups reached $50 billion in 2026",
    "TSMC announces new 2nm chip fabrication plant in Arizona",
    "OpenAI releases new open source LLM foundation model",
    "NVIDIA GPU stock market surge after data center demand",
    "Fintech IPO market shows strong recovery in Q2 2026",
    "Microsoft invests $10 billion in cloud computing infrastructure",
    "DE-CIX Frankfurt reports record traffic growth",
]
for t in tests:
    r = classify_multi(t)
    print(f"  [{r['primary'] or 'NONE':>8}] {r['keywords'][:3]}  |  {t[:50]}")
