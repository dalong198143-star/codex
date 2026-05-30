"""采集层 — 多源数据采集

当前实现的源（v2.0）:
  - bing: Bing 网页搜索（HTML 解析）
  - google_news: Google News RSS
  - rss: 9 个 RSS/Feed 专业源（DataCenterDynamics/LightReading/SubmarineNetworks 等）

安全设计:
  - 每个采集器独立 try/catch，失败不阻塞全局
  - 三层兜底（Bing → Google News → RSS）
"""

from .bing import bing_search
from .google_news import google_news_search