"""
update_news.py — 每週重大消息自動更新
每週一與技術分析一起執行。
使用 Gemini + Google Search 搜尋所有持倉近兩週重大消息，
更新 index.html 的 <!-- NEWS_START --> ... <!-- NEWS_END --> 區塊。
"""

import json, os, re, time
from datetime import datetime, timezone, timedelta

TZ_TW      = timezone(timedelta(hours=8))
INDEX_FILE = "index.html"

# ── 所有持倉（用於 Gemini 搜尋範圍）──
HOLDINGS = {
    "TW": ["00692", "00915", "1104", "2211", "2330", "2536", "2834",
           "3293", "3661", "3703", "4588", "4707"],
    "US": ["AMZN", "CELH", "GOOGL", "MELI", "MSFT", "NVDA",
           "ONDS", "RBRK", "S", "SOUN", "TSLA", "ZS"],
}

# ── 持倉名稱對照（顯示用）──
NAMES = {
    "00692": "富邦公司治理", "00915": "凱基優選高股息30",
    "1104":  "環泥",         "2211":  "長榮鋼",
    "2330":  "台積電",       "2536":  "宏普",
    "2834":  "臺企銀",       "3293":  "鈺象",
    "3661":  "世芯-KY",      "3703":  "欣陸",
    "4588":  "玖鼎電力",     "4707":  "磐亞",
    "AMZN":  "Amazon",       "CELH":  "Celsius",
    "GOOGL": "Alphabet",     "MELI":  "MercadoLibre",
    "MSFT":  "Microsoft",    "NVDA":  "NVIDIA",
    "ONDS":  "Ondas",        "RBRK":  "Rubrik",
    "S":     "SentinelOne",
    "SOUN":  "SoundHound",   "TSLA":  "Tesla",
    "ZS":    "Zscaler",
}


# ════════════════════════════════════════════════════════════════════
# Gemini 呼叫
# ════════════════════════════════════════════════════════════════════
def fetch_news_from_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  ✗ 未找到 GEMINI_API_KEY，跳過重大消息更新")
        return None

    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)

    tw_list = "、".join(HOLDINGS["TW"])
    us_list = "、".join(HOLDINGS["US"])
    today   = datetime.now(TZ_TW).strftime("%Y-%m-%d")

    prompt = f"""今天是 {today}。你是投資分析師，協助台灣個人投資者追蹤持倉動態。

我的持倉：
- 台股：{tw_list}
- 美股：{us_list}

請搜尋這些持倉近兩週內的重大消息（財報發布、重大公告、分析師升降評、政策影響、重要產品發布等），
挑選 5～8 則最值得關注的，依重要性排序。

重要：只選有實質影響的消息，不要選無關緊要的小新聞。

請輸出純 JSON 陣列，不含任何其他文字或 markdown：
[
  {{
    "ticker": "代碼（如 NVDA 或 2330）",
    "importance": "高、中、低 三選一",
    "title": "標題（25 字內，繁體中文）",
    "body": "內容摘要（60 字內，繁體中文，說明事件與影響）",
    "date": "YYYY/MM"
  }}
]"""

    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )
            text = resp.text.strip()
            break
        except Exception as e:
            if "503" in str(e) and attempt < 2:
                wait = 20 * (attempt + 1)
                print(f"  ⏳ 503 繁忙，{wait}s 後重試...")
                time.sleep(wait)
            else:
                raise
    else:
        return None

    # 清理 markdown / 引用標記
    text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*',     '', text, flags=re.MULTILINE)
    text = re.sub(r'\[\d+\]',     '', text)
    text = text.strip()

    # 取第一個 JSON 陣列
    m = re.search(r'\[.*\]', text, re.DOTALL)
    if m:
        text = m.group()

    try:
        items = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON 解析失敗（{e}），重試（純 JSON 模式）...")
        for attempt2 in range(3):
            try:
                resp2 = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt + "\n\n重要：只輸出純 JSON 陣列，不含任何引用標記、括號數字或其他文字。",
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        thinking_config=types.ThinkingConfig(thinking_budget=0)
                    )
                )
                t2 = resp2.text.strip()
                t2 = re.sub(r'^```json\s*', '', t2, flags=re.MULTILINE)
                t2 = re.sub(r'^```\s*',     '', t2, flags=re.MULTILINE)
                t2 = re.sub(r'\[\d+\]',     '', t2)
                t2 = t2.strip()
                m2 = re.search(r'\[.*\]', t2, re.DOTALL)
                if m2:
                    t2 = m2.group()
                items = json.loads(t2)
                break
            except Exception as e2:
                if "503" in str(e2) and attempt2 < 2:
                    time.sleep(20 * (attempt2 + 1))
                else:
                    raise

    print(f"  ✓ 取得 {len(items)} 則重大消息")
    return items


# ════════════════════════════════════════════════════════════════════
# HTML 生成
# ════════════════════════════════════════════════════════════════════
def build_news_html(items):
    """將新聞列表轉為 HTML，按月份分組"""
    # 按月份分組
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
            name       = NAMES.get(ticker, "")

            imp_class = {"高": "imp-high", "中": "imp-mid", "低": "imp-low"}.get(importance, "imp-mid")
            # 虧損持倉用紅色標籤
            tag_class = "tag-red" if ticker in ("TSLA", "2536", "4588", "3703") else ""
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
                f'        <div class="news-meta">{date_str} 整理</div>\n'
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

    items = fetch_news_from_gemini()
    if items is None:
        print("  ✗ 無法取得消息，保留現有內容")
        return

    news_html = build_news_html(items)

    if update_index_html(news_html):
        print(f"  ✓ index.html 重大消息區塊已更新（{len(items)} 則）")
    else:
        print("  ✗ 更新失敗，請手動確認 NEWS_START/END 標記")


if __name__ == "__main__":
    main()
