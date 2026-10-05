"""
update_news.py — 每週重大消息自動更新
每週一與技術分析一起執行。

作法（2026-10 改版）：
  1) 從免費的 Google News RSS 抓「真實」新聞標題（每檔持股），不依賴 Gemini 聯網搜尋。
  2) 把這些真實標題交給 Gemini（不使用 google_search grounding）挑選＋整理成卡片，
     並明確要求只能根據提供的標題、不得杜撰。
更新 index.html 的 <!-- NEWS_START --> ... <!-- NEWS_END --> 區塊。

改版原因：免費層的 Google Search grounding 幾乎已無額度（daily-brief 也長期退回無搜尋
模式），再多的免費 key 都解不了；改抓真實 RSS 來源可免費、穩定、且不會編造假新聞。
"""

import json, os, re, time, sys
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

import requests

from holdings import load_holdings

TZ_TW      = timezone(timedelta(hours=8))
INDEX_FILE = "index.html"
UA         = {"User-Agent": "Mozilla/5.0 (compatible; DashboardNewsBot/1.0)"}

# ── 所有持倉：一律從 portfolio.json 衍生（單一真相來源，見 holdings.py）──
_HOLD    = load_holdings()
HOLDINGS = {
    "TW": [s["symbol"] for s in _HOLD["tw"]],
    "US": [s["symbol"] for s in _HOLD["us"]],
}
# ── 持倉名稱對照（顯示用）──
NAMES = {s["symbol"]: s["name"] for s in _HOLD["us"] + _HOLD["tw"]}


# ════════════════════════════════════════════════════════════════════
# 1) 從 Google News RSS 抓真實標題
# ════════════════════════════════════════════════════════════════════
def _fetch_rss(query, hl, gl, ceid, limit=3):
    """抓單一查詢的 Google News RSS，回傳 [{title, pubDate, source}]。"""
    url = ("https://news.google.com/rss/search?q="
           + urllib.parse.quote(query)
           + f"&hl={hl}&gl={gl}&ceid={ceid}")
    out = []
    try:
        r = requests.get(url, timeout=15, headers=UA)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        for item in root.findall(".//item")[:limit]:
            title  = (item.findtext("title")   or "").strip()
            pub    = (item.findtext("pubDate")  or "").strip()
            source = (item.findtext("source")   or "").strip()
            if title:
                out.append({"title": title, "pubDate": pub, "source": source})
    except Exception as e:
        print(f"    ✗ RSS 失敗（{query}）：{e}")
    return out


def _month_from_pubdate(pub):
    """把 RSS pubDate（RFC822）轉成 YYYY/MM；失敗則回當月。"""
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return datetime.strptime(pub, fmt).strftime("%Y/%m")
        except Exception:
            pass
    return datetime.now(TZ_TW).strftime("%Y/%m")


def collect_headlines():
    """對每檔持股抓近期標題，回傳扁平清單。"""
    print("  📥 從 Google News RSS 抓真實標題...")
    heads = []
    jobs = ([(s["symbol"], s["name"], f'"{s["name"]}" 股票', "zh-TW", "TW", "TW:zh-Hant")
             for s in _HOLD["tw"]]
          + [(s["symbol"], s["name"], f'"{s["name"]}" stock', "en-US", "US", "US:en")
             for s in _HOLD["us"]])
    for code, name, q, hl, gl, ceid in jobs:
        for h in _fetch_rss(q, hl, gl, ceid, limit=3):
            heads.append({
                "ticker": code,
                "name":   name,
                "title":  h["title"],
                "month":  _month_from_pubdate(h["pubDate"]),
                "source": h["source"],
            })
        time.sleep(0.2)   # 對 Google News 禮貌一點
    print(f"  ✓ 共抓到 {len(heads)} 則真實標題（{len(jobs)} 檔持股）")
    return heads


# ════════════════════════════════════════════════════════════════════
# 2) Gemini 整理（不使用 grounding，只能根據提供的真實標題）
# ════════════════════════════════════════════════════════════════════
def _clean_json_text(text):
    text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*',     '', text, flags=re.MULTILINE)
    text = re.sub(r'\[\d+\]',     '', text)
    text = text.strip()
    m = re.search(r'\[.*\]', text, re.DOTALL)
    return m.group() if m else text


def organize_with_gemini(headlines):
    api_key = os.environ.get("GEMINI_API_KEY_DASH") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  ✗ 未找到 GEMINI_API_KEY，無法整理新聞")
        return None
    _src = "GEMINI_API_KEY_DASH(專屬)" if os.environ.get("GEMINI_API_KEY_DASH") else "GEMINI_API_KEY(共用·fallback)"
    print(f"  🔑 key 來源：{_src}（長度 {len(api_key)}）")

    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)

    today = datetime.now(TZ_TW).strftime("%Y-%m-%d")
    lines = [f"[{h['ticker']} {h['name']}] {h['title']}  ({h['source']}, {h['month']})"
             for h in headlines]
    headlines_text = "\n".join(lines)

    prompt = f"""今天是 {today}。以下是我持倉個股的「真實新聞標題」（來自 Google News，每行一則）：

{headlines_text}

請從上面這些真實標題中，挑出 5～8 則對我的持股最有實質影響的（財報、重大公告、分析師升降評、
政策、併購、重要產品或訂單等），依重要性排序。規則：
- 只能根據上面提供的標題，嚴禁自行編造或補上標題中沒有的事件、數字、評等。
- 同一事件有多則標題時合併成一則。
- 摘要只做「把標題用繁體中文說清楚」，不要杜撰具體數字或結論。

請輸出純 JSON 陣列，不含任何其他文字或 markdown：
[
  {{
    "ticker": "代碼（如 NVDA 或 2330）",
    "importance": "高、中、低 三選一",
    "title": "標題（25 字內，繁體中文）",
    "body": "內容摘要（60 字內，繁體中文，僅根據上面標題，不得杜撰數字）",
    "date": "YYYY/MM（用該標題旁括號內的月份）"
  }}
]"""

    text = None
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                ),   # ← 不使用 google_search grounding
            )
            text = resp.text.strip()
            break
        except Exception as e:
            es = str(e)
            if ("503" in es or "429" in es) and attempt < 2:
                wait = 30 * (attempt + 1)
                print(f"  ⏳ {es[:40]}...，{wait}s 後重試")
                time.sleep(wait)
            else:
                raise
    if text is None:
        return None

    try:
        items = json.loads(_clean_json_text(text))
    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON 解析失敗（{e}），重試一次純 JSON 模式...")
        resp = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt + "\n\n重要：只輸出純 JSON 陣列，不含任何其他文字。",
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            ),
        )
        items = json.loads(_clean_json_text(resp.text.strip()))

    # 後處理：date 不合法則補當月；ticker 去雜
    cur = datetime.now(TZ_TW).strftime("%Y/%m")
    for it in items:
        d = str(it.get("date", "")).strip()
        if not re.match(r"^\d{4}/\d{2}$", d):
            it["date"] = cur
    print(f"  ✓ 整理出 {len(items)} 則重大消息")
    return items


# ════════════════════════════════════════════════════════════════════
# HTML 生成
# ════════════════════════════════════════════════════════════════════
def build_news_html(items):
    """將新聞列表轉為 HTML，按月份分組"""
    by_month = {}
    for item in items:
        m = item.get("date", "")[:7]   # "YYYY/MM"
        by_month.setdefault(m, []).append(item)

    html = "\n"
    for month_key in sorted(by_month.keys(), reverse=True):
        month_label = month_key.replace("/", " / ")
        html += f'    <div style="font-size:11px;font-weight:700;color:var(--text3);letter-spacing:.06em;margin-bottom:10px;">{month_label}</div>\n'
        html += '    <div class="news-grid">\n\n'

        for item in by_month[month_key]:
            ticker     = item.get("ticker", "—")
            importance = item.get("importance", "中")
            title      = item.get("title", "")
            body       = item.get("body", "")
            date_str   = item.get("date", "")

            imp_class = {"高": "imp-high", "中": "imp-mid", "低": "imp-low"}.get(importance, "imp-mid")
            # 虧損持倉用紅色標籤
            tag_class = "tag-red" if ticker in ("TSLA", "3703") else ""
            tag_html  = f'<span class="news-tag{" " + tag_class if tag_class else ""}">{ticker}</span>'

            html += (
                f'      <div class="news-card">\n'
                f'        <div class="news-card-head">\n'
                f'          {tag_html}\n'
                f'          <span class="news-imp {imp_class}">{importance}</span>\n'
                f'        </div>\n'
                f'        <div class="news-title">{title}</div>\n'
                f'        <div style="font-size:12px;color:var(--text2);line-height:1.65;">\n'
                f'          {body}\n'
                f'        </div>\n'
                f'        <div class="news-meta">{date_str} · 來源 Google News 整理</div>\n'
                f'      </div>\n\n'
            )

        html += '    </div>\n\n'

    return html


# ════════════════════════════════════════════════════════════════════
# 更新 index.html
# ════════════════════════════════════════════════════════════════════
def update_index_html(news_html):
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    pattern  = r'<!-- NEWS_START -->.*?<!-- NEWS_END -->'
    new_block = f'<!-- NEWS_START -->\n{news_html}    <!-- NEWS_END -->'
    new_html, count = re.subn(pattern, new_block, html, flags=re.DOTALL)

    if count == 0:
        print("  ✗ 找不到 NEWS_START / NEWS_END 標記，無法更新")
        return False

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(new_html)
    return True


# ════════════════════════════════════════════════════════════════════
# 主程式
# ════════════════════════════════════════════════════════════════════
def main():
    print(f"📰 重大消息更新開始（{datetime.now(TZ_TW).strftime('%Y-%m-%d')}）")

    headlines = collect_headlines()
    if not headlines:
        # RSS 全數失敗＝真的有問題，要報錯讓使用者收到通知（不靜默略過）
        print("  ✗ 完全抓不到任何新聞標題（RSS 來源可能異常）")
        sys.exit(1)

    items = organize_with_gemini(headlines)
    if not items:
        print("  ✗ Gemini 整理失敗")
        sys.exit(1)

    if update_index_html(build_news_html(items)):
        print(f"  ✓ index.html 重大消息區塊已更新（{len(items)} 則，來源：真實 RSS）")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
