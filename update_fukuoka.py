"""
update_fukuoka.py — 每兩週二福岡房市 AI 分析
由 GitHub Actions 每週二觸發，但腳本內部節流為兩週一次。
使用 Gemini API 生成福岡各區不動產分析，更新 index.html 的福岡房市區塊。

分析輪轉（每期一區，循環）：
  第1期：中央區（天神・大濠）
  第2期：早良區（西新・藤崎）
  第3期：博多區（博多站周邊）
  第4期：東区（香椎・千早）
  第5期：南区（大橋・野間）
  第6期：城南区（七隈・別府）
  第7期：西区・糸島市（姪浜・前原）
  第8期：福岡市購屋指南（全市綜合 + 外國人注意事項）
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta

TZ_TW      = timezone(timedelta(hours=8))
STATE_FILE = "fukuoka_state.json"
INDEX_FILE = "index.html"

# ════════════════════════════════════════════════════════════════════
# 區域輪轉清單
# ════════════════════════════════════════════════════════════════════
DISTRICTS = [
    {
        "id":      "chuo",
        "name":    "中央區",
        "areas":   "天神・大濠公園・六本松・薬院",
        "profile": "福岡精華地段，天神商圈步行可達，生活機能頂級",
    },
    {
        "id":      "sawara",
        "name":    "早良區",
        "areas":   "西新・藤崎・百道・室見",
        "profile": "性價比首選，地鐵直達天神 10 分鐘，文教區環境優",
    },
    {
        "id":      "hakata",
        "name":    "博多區",
        "areas":   "博多站・千代・東比恵・住吉",
        "profile": "新幹線交通樞紐，商業設施集中，租金收益率較高",
    },
    {
        "id":      "higashi",
        "name":    "東区",
        "areas":   "香椎・千早・貝塚・名島",
        "profile": "市區邊緣，房價相對低，適合首購族，未來開發潛力",
    },
    {
        "id":      "minami",
        "name":    "南区",
        "areas":   "大橋・井尻・野間・花畑",
        "profile": "住宅環境寧靜，文教設施密集，適合有小孩的家庭",
    },
    {
        "id":      "jonan",
        "name":    "城南区",
        "areas":   "七隈・別府・長尾・友泉亭",
        "profile": "七隈線沿線，大學城氛圍，年輕族群聚集，生活便利",
    },
    {
        "id":      "nishi",
        "name":    "西区・糸島市",
        "areas":   "姪浜・今宿・前原・加布里",
        "profile": "海濱生活，遠離塵囂，自然環境好，移居者高人氣區",
    },
    {
        "id":      "summary",
        "name":    "福岡市購屋指南",
        "areas":   "全市綜合比較・外國人購屋注意事項・資金規劃",
        "profile": "綜合整理，協助做出最適合自己的購屋決策",
    },
]


# ════════════════════════════════════════════════════════════════════
# 狀態管理
# ════════════════════════════════════════════════════════════════════
def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"period": 0, "last_updated": "2000-01-01", "district_idx": 0}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def should_run_today(state):
    """距上次執行需超過 13 天（允許排程時間小誤差）"""
    last = state.get("last_updated", "2000-01-01")
    try:
        last_dt = datetime.strptime(last, "%Y-%m-%d").replace(tzinfo=TZ_TW)
        return (datetime.now(TZ_TW) - last_dt).days >= 13
    except Exception:
        return True


# ════════════════════════════════════════════════════════════════════
# Gemini API — 生成分析內容
# ════════════════════════════════════════════════════════════════════
def generate_with_gemini(district, period_num):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  ✗ 未找到 GEMINI_API_KEY，跳過 AI 分析")
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""你是為台灣移居者撰寫日本福岡不動產分析的專家。
目標讀者：台灣人，計畫 5–10 年內在福岡購買自住用中古公寓，總預算約 3,000 萬日圓。
讀者目前在台灣工作，會不定期前往福岡看房，希望了解各區特性後再決定目標區域。

本期分析：第 {period_num} 期・{district['name']}
重點地區：{district['areas']}
區域定位：{district['profile']}

請以繁體中文輸出一個 JSON 物件（不要任何其他文字，純 JSON），格式如下：
{{
  "summary": "區域一句話定位（20字內）",
  "feature": "區域特色描述，包含交通、生活機能、特色氛圍（50字內）",
  "spots": [
    {{"name": "具體地名或站名", "note": "推薦理由（20字內）", "price": "70㎡約X,XXX萬円"}},
    {{"name": "具體地名或站名", "note": "推薦理由（20字內）", "price": "70㎡約X,XXX萬円"}},
    {{"name": "具體地名或站名", "note": "推薦理由（20字內）", "price": "70㎡約X,XXX萬円"}}
  ],
  "pros": [
    "台灣人角度的優點1（25字內）",
    "台灣人角度的優點2（25字內）",
    "台灣人角度的優點3（25字內）"
  ],
  "risks": [
    "需注意風險1（25字內）",
    "需注意風險2（25字內）"
  ],
  "budget_advice": "針對預算 3,000 萬円 的具體建議（60字內）",
  "next_preview": "下一期預告一句話（15字內）"
}}"""

        response = model.generate_content(prompt)
        text = response.text.strip()

        # 清除可能的 markdown code block 包裝
        text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^```\s*',     '', text, flags=re.MULTILINE)
        text = text.strip()

        data = json.loads(text)
        print(f"  ✓ Gemini 分析生成成功（{district['name']}）")
        return data

    except Exception as e:
        print(f"  ✗ Gemini 分析失敗：{e}")
        return None


# ════════════════════════════════════════════════════════════════════
# HTML 生成
# ════════════════════════════════════════════════════════════════════
def build_fk_html(district, analysis, date_str, period_num):
    """生成福岡 section 的完整 HTML（放在 FK_CARD_START/END 之間）"""

    if analysis is None:
        # Gemini 失敗時顯示簡單佔位
        return (
            "<!-- FK_CARD_START -->\n"
            "    <div style=\"text-align:center;padding:36px;color:var(--text3)\">\n"
            "      <div style=\"font-size:36px;margin-bottom:12px\">🏠</div>\n"
            f"      <div style=\"font-size:15px;font-weight:700;margin-bottom:8px\">第 {period_num} 期：{district['name']}</div>\n"
            "      <div style=\"font-size:12px\">AI 分析暫時不可用，請稍後再試</div>\n"
            "    </div>\n"
            "    <!-- FK_CARD_END -->"
        )

    ym = date_str[:7].replace('-', '/')

    # 地點卡片
    spots_html = ""
    for spot in (analysis.get("spots") or [])[:3]:
        spots_html += (
            f'\n      <div class="fk-card">'
            f'\n        <div class="fk-tag">{spot.get("note", "")}</div>'
            f'\n        <div class="fk-title">{spot.get("name", "")}</div>'
            f'\n        <div class="fk-body">{district["name"]} · 推薦地段</div>'
            f'\n        <div class="fk-price">{spot.get("price", "—")}</div>'
            f'\n        <div class="fk-date">{ym}</div>'
            f'\n      </div>'
        )

    # 優缺點
    pros_html  = "\n".join(
        f'        <div class="highlight-item">✅ {p}</div>'
        for p in (analysis.get("pros") or [])
    )
    risks_html = "\n".join(
        f'        <div class="highlight-item">⚠️ {r}</div>'
        for r in (analysis.get("risks") or [])
    )

    next_preview = analysis.get("next_preview", "")

    return (
        "<!-- FK_CARD_START -->\n"
        f'    <div class="fk-period-badge">第 {period_num} 期・{district["name"]}・{date_str}</div>\n'
        f'    <div class="fk-grid">{spots_html}\n    </div>\n'
        f'    <div class="report-card">\n'
        f'      <div class="report-header">\n'
        f'        <div class="report-title">🤖 AI 分析：{district["name"]} / {district["areas"]}</div>\n'
        f'        <div class="report-date">{ym}</div>\n'
        f'      </div>\n'
        f'      <div class="report-body">\n'
        f'        <p>{analysis.get("feature", "")}</p>\n'
        f'        <div class="highlight-box">\n'
        f'          <strong>適合台灣人的優點：</strong>\n'
        f'{pros_html}\n'
        f'          <strong style="margin-top:8px;display:block">需注意的風險：</strong>\n'
        f'{risks_html}\n'
        f'        </div>\n'
        f'        <p><strong>預算 3,000 萬円 建議：</strong>{analysis.get("budget_advice", "—")}</p>\n'
        + (f'        <p style="color:var(--text3);font-size:12px;margin-top:12px">▶ 下期預告：{next_preview}</p>\n' if next_preview else '')
        + '        <p style="color:var(--text3);font-size:11px;margin-top:8px">🤖 由 Gemini AI 根據訓練資料生成，房價僅供參考，實際行情請向仲介確認</p>\n'
        f'      </div>\n'
        f'    </div>\n'
        "    <!-- FK_CARD_END -->"
    )


# ════════════════════════════════════════════════════════════════════
# 更新 index.html
# ════════════════════════════════════════════════════════════════════
def update_index_html(fk_html):
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    pattern = r'<!-- FK_CARD_START -->.*?<!-- FK_CARD_END -->'
    new_html, count = re.subn(pattern, fk_html, html, flags=re.DOTALL)

    if count == 0:
        print("  ✗ 找不到 FK_CARD_START / FK_CARD_END 標記，無法更新")
        return False

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(new_html)
    return True


# ════════════════════════════════════════════════════════════════════
# 主程式
# ════════════════════════════════════════════════════════════════════
def main():
    state    = load_state()
    now_tw   = datetime.now(TZ_TW)
    today    = now_tw.strftime("%Y-%m-%d")

    if not should_run_today(state):
        last = state.get("last_updated", "—")
        try:
            days = (now_tw - datetime.strptime(last, "%Y-%m-%d").replace(tzinfo=TZ_TW)).days
        except Exception:
            days = 0
        print(f"  ⏭ 距上次更新僅 {days} 天，兩週節流生效，跳過本次執行")
        return

    district_idx = state.get("district_idx", 0) % len(DISTRICTS)
    period_num   = state.get("period", 0) + 1
    district     = DISTRICTS[district_idx]

    print(f"🏠 第 {period_num} 期福岡房市分析：{district['name']}（{district['areas']}）")

    analysis = generate_with_gemini(district, period_num)
    fk_html  = build_fk_html(district, analysis, today, period_num)

    if update_index_html(fk_html):
        print(f"  ✓ index.html 福岡區塊已更新")
    else:
        print(f"  ✗ 更新失敗，請手動確認 FK_CARD_START/END 標記")
        return

    # 更新狀態
    state["period"]       = period_num
    state["last_updated"] = today
    state["district_idx"] = (district_idx + 1) % len(DISTRICTS)
    save_state(state)
    next_district = DISTRICTS[state["district_idx"]]["name"]
    print(f"  ✓ 狀態已儲存，下期分析：{next_district}（約兩週後）")


if __name__ == "__main__":
    main()
