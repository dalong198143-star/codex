"""图片分析工具 — 通过 qwen-vl-plus 识别图片内容。

用法:
  python analyze_image.py <图片路径> [提问]

自动检测本地代理(:1234)是否运行，若运行则走代理，否则直连 DashScope。
"""
import sys
import base64
import os
import requests

# ── 配置 ──────────────────────────────────────────────────────────
LOCAL_PROXY = os.environ.get("CODEX_PROXY_URL", "http://127.0.0.1:1234/v1")
LOCAL_KEY = os.environ.get("LITELLM_MASTER_KEY", "sk-litellm-master-2026")
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

# 沙箱内有系统代理 127.0.0.1:9 导致出站失败，跳过它
NO_PROXY_CFG = {"http": "", "https": ""}


# ── 工具函数 ───────────────────────────────────────────────────────

def _mime_from_ext(path: str) -> str:
    ext = os.path.splitext(path)[1].lower().replace(".", "")
    return {"jpg": "jpeg", "jpeg": "jpeg", "png": "png",
            "webp": "webp", "gif": "gif"}.get(ext, "png")


def _build_body(image_path: str, question: str) -> dict:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    mime = _mime_from_ext(image_path)
    return {
        "model": "qwen-vl-plus",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": question},
            {"type": "image_url", "image_url": {
                "url": f"data:image/{mime};base64,{b64}"
            }},
        ]}],
    }


def _proxy_alive() -> bool:
    """检查本地代理(:1234)是否在运行"""
    try:
        r = requests.get("http://127.0.0.1:1234/health", timeout=3)
        return r.ok
    except Exception:
        return False


def analyze(image_path: str, question: str | None = None) -> str:
    """用 qwen-vl-plus 分析图片，自动选择代理或直连。"""
    if not question:
        question = "请用中文详细描述这张图片的内容"

    body = _build_body(image_path, question)

    if _proxy_alive():
        # ── 走本地代理 ──
        resp = requests.post(
            f"{LOCAL_PROXY}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {LOCAL_KEY}"},
            timeout=120,
        )
    else:
        # ── 直连 DashScope（跳过系统代理） ──
        resp = requests.post(
            DASHSCOPE_URL,
            json=body,
            headers={"Authorization": f"Bearer {os.environ['DASHSCOPE_API_KEY']}"},
            proxies=NO_PROXY_CFG,
            timeout=120,
        )

    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python analyze_image.py <图片路径> [提问]")
        sys.exit(1)

    path = sys.argv[1]
    question = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.isfile(path):
        print(f"错误: 文件不存在 — {path}")
        sys.exit(1)

    try:
        result = analyze(path, question)
        print(result)
    except Exception as e:
        print(f"分析失败: {e}")
        sys.exit(1)
