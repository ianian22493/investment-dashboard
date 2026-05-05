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
        import time
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)

        prompt = f"""你是為台灣移居者撰寫日本福岡不動產分析的專家。
目標讀者：台灣人，計畫 5–10 年內在福岡購買自住用中古或新築公寓，總預算約 3,000 萬日圓。
讀者目前在台灣工作，對預售屋（新築分讓マンション）特別有興趣，希望掌握各區預售屋動態。

本期分析：第 {period_num} 期・{district['name']}
重點地區：{district['areas']}
區域定位：{district['profile']}

請以繁體中文輸出一個 JSON 物件（不要任何其他文字，純 JSON），格式如下：
{{
  "summary": "區域一句話定位（20字內）",
  "feature": "區域特色描述，包含交通、生活機能、特色氛圍（50字內）",
  "spots": [
    {{"name": "具體地名或站名", "note": "推薦理由（20字內）", "price_70sqm": 2500}},
    {{"name": "具體地名或站名", "note": "推薦理由（20字內）", "price_70sqm": 2800}},
    {{"name": "具體地名或站名", "note": "推薦理由（20字內）", "price_70sqm": 3200}}
  ],
  "price_history": [
    {{"year": 2020, "avg_sqm": 42}},
    {{"year": 2021, "avg_sqm": 45}},
    {{"year": 2022, "avg_sqm": 49}},
    {{"year": 2023, "avg_sqm": 53}},
    {{"year": 2024, "avg_sqm": 57}}
  ],
  "presale_projects": [
    {{
      "name": "具體建案名稱或預計名稱",
      "location": "最近站名・徒步X分",
      "price_from": 2800,
      "price_to": 3500,
      "delivery": "20XX年XX月預定",
      "note": "建案特色簡述（25字內）",
      "status": "銷售中"
    }},
    {{
      "name": "具體建案名稱或預計名稱",
      "location": "最近站名・徒步X分",
      "price_from": 2400,
      "price_to": 3000,
      "delivery": "20XX年XX月預定",
      "note": "建案特色簡述（25字內）",
      "status": "即将登場"
    }}
  ],
  "presale_vs_resale": "該區預售屋目前比中古屋平均貴幾%，值不值得的簡短評估（40字內）",
  "pros": [
    "台灣人角度的優點1（25字內）",
    "台灣人角度的優點2（25字內）",
    "台灣人角度的優點3（25字內）"
  ],
  "risks": [
    "需注意風險1（25字內）",
    "需注意風險2（25字內）"
  ],
  "budget_advice": "針對預算 3,000 萬円 的具體建議，含預售屋建議（60字內）",
  "next_preview": "下一期預告一句話（15字內）"
}}

重要：
- price_70sqm、price_from、price_to 均為整數，單位是「萬円」（例：2800 表示 2,800 萬円）
- price_history 的 avg_sqm 為每平方公尺均價，單位是「萬円」（例：57 表示 57 萬円/㎡）
- presale_projects 盡量提供真實存在或合理預估的建案資訊，若該區近期無預售案可填預計資訊
- 所有價格以目前市場行情為基準，供參考用"""

        # 帶重試的呼叫（503 最多重試3次）
        text = None
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
                    time.sleep(20 * (attempt + 1))
                else:
                    raise
        if text is None:
            return None

        # 清除可能的 markdown code block 包裝
        text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^```\s*',     '', text, flags=re.MULTILINE)
        # 移除 Gemini 可能夾帶的引用標記（[1], [2] 等），這些會破壞 JSON
        text = re.sub(r'\[\d+\]', '', text)
        text = text.strip()

        # 取第一個 JSON 物件（防止前後有多餘文字）
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            text = m.group()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            print(f"  ⚠ JSON 解析失敗（{e}），重試一次（加強純 JSON 要求）...")
            for attempt2 in range(3):
                try:
                    resp2 = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt + "\n\n重要：只輸出純 JSON，不含任何引用標記、括號數字或額外說明。",
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
                    m2 = re.search(r'\{.*\}', t2, re.DOTALL)
                    if m2:
                        t2 = m2.group()
                    data = json.loads(t2)
                    break
                except Exception as e2:
                    if "503" in str(e2) and attempt2 < 2:
                        time.sleep(20 * (attempt2 + 1))
                    else:
                        raise
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

    # ── 推薦地段卡片 ──
    spots      = (analysis.get("spots") or [])[:3]
    spot_names = [s.get("name", "") for s in spots]
    spot_prices = [s.get("price_70sqm", 0) for s in spots]

    spots_html = ""
    for i, spot in enumerate(spots, 1):
        price_val = spot.get("price_70sqm", 0)
        price_display = f"{price_val:,}万円〜" if price_val else "—"
        spots_html += (
            f'\n    <div class="fk-spot">'
            f'\n      <div class="fk-spot-num">0{i}</div>'
            f'\n      <div class="fk-spot-name">{spot.get("name", "")}</div>'
            f'\n      <div class="fk-spot-note">{spot.get("note", "")}</div>'
            f'\n      <div class="fk-spot-price">{price_display}</div>'
            f'\n      <div class="fk-spot-type">70㎡ 參考價格</div>'
            f'\n    </div>'
        )

    # ── 預售屋項目卡片 ──
    presale_projects = analysis.get("presale_projects") or []
    presale_html = ""
    for proj in presale_projects[:3]:
        status     = proj.get("status", "")
        p_from     = proj.get("price_from", 0)
        p_to       = proj.get("price_to", 0)
        price_rng  = f"{p_from:,}〜{p_to:,} 萬円" if p_from and p_to else "—"
        status_cls = "fk-status-sale" if "銷售" in status else "fk-status-soon"
        presale_html += (
            f'\n      <div class="fk-presale-card">'
            f'\n        <div class="fk-presale-header">'
            f'\n          <span class="fk-presale-name">{proj.get("name", "")}</span>'
            f'\n          <span class="fk-presale-status {status_cls}">{status}</span>'
            f'\n        </div>'
            f'\n        <div class="fk-presale-loc">📍 {proj.get("location", "")}</div>'
            f'\n        <div class="fk-presale-price">💴 {price_rng}</div>'
            f'\n        <div class="fk-presale-delivery">🗓 交屋：{proj.get("delivery", "—")}</div>'
            f'\n        <div class="fk-presale-note">{proj.get("note", "")}</div>'
            f'\n      </div>'
        )

    presale_vs_resale = analysis.get("presale_vs_resale", "")

    # ── Chart.js 資料（JSON 字串嵌入 HTML）──
    import json as _json

    # 圖1：近5年房價走勢（折線圖）
    price_history  = analysis.get("price_history") or []
    hist_labels    = _json.dumps([str(h["year"]) for h in price_history])
    hist_data      = _json.dumps([h["avg_sqm"] for h in price_history])
    chart_trend_id = f"fkTrendChart{period_num}"

    # 圖2：推薦地段 70㎡ 價格比較（橫向柱狀圖）
    spot_labels_js = _json.dumps(spot_names)
    spot_data_js   = _json.dumps(spot_prices)
    chart_spot_id  = f"fkSpotChart{period_num}"

    # ── 優缺點 ──
    pros_html  = "\n".join(
        f'        <div class="fk-item">{p}</div>'
        for p in (analysis.get("pros") or [])
    )
    risks_html = "\n".join(
        f'        <div class="fk-item">{r}</div>'
        for r in (analysis.get("risks") or [])
    )

    next_preview = analysis.get("next_preview", "")

    # 用 list 組裝 HTML，避免混用隱式拼接與 + 運算子造成 SyntaxError
    parts = []
    parts.append("<!-- FK_CARD_START -->\n")
    parts.append(f'<div class="fk-report-wrap">\n')
    parts.append(
        f'  <div class="fk-header">\n'
        f'    <div>\n'
        f'      <div class="fk-edition">第 {period_num} 期</div>\n'
        f'      <div class="fk-district-name">{district["name"]}</div>\n'
        f'    </div>\n'
        f'    <div class="fk-header-date">{date_str}</div>\n'
        f'  </div>\n'
    )

    # 推薦地段卡片
    parts.append(f'  <div class="fk-spots-grid">{spots_html}\n  </div>\n')

    # 圖表區：走勢 + 地段比較
    parts.append(
        f'    <div class="fk-charts-row">\n'
        f'      <div class="fk-chart-box">\n'
        f'        <div class="fk-chart-title">📈 近5年均價走勢（萬円/㎡）</div>\n'
        f'        <canvas id="{chart_trend_id}" height="180"></canvas>\n'
        f'      </div>\n'
        f'      <div class="fk-chart-box">\n'
        f'        <div class="fk-chart-title">🏘 推薦地段 70㎡ 參考價（萬円）</div>\n'
        f'        <canvas id="{chart_spot_id}" height="180"></canvas>\n'
        f'      </div>\n'
        f'    </div>\n'
        f'    <script>\n'
        f'    (function(){{\n'
        f'      var tCtx = document.getElementById("{chart_trend_id}");\n'
        f'      if (tCtx) new Chart(tCtx, {{\n'
        f'        type: "line",\n'
        f'        data: {{ labels: {hist_labels}, datasets: [{{\n'
        f'          label: "均價（萬円/㎡）", data: {hist_data},\n'
        f'          borderColor: "#388bfd", backgroundColor: "rgba(56,139,253,0.12)",\n'
        f'          tension: 0.3, fill: true, pointRadius: 4, pointBackgroundColor: "#388bfd"\n'
        f'        }}]}},\n'
        f'        options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }},\n'
        f'          scales: {{ x: {{ ticks: {{ color: "#8b949e" }}, grid: {{ color: "rgba(139,148,158,0.15)" }} }},\n'
        f'                     y: {{ ticks: {{ color: "#8b949e" }}, grid: {{ color: "rgba(139,148,158,0.15)" }}, beginAtZero: false }} }} }}\n'
        f'      }});\n'
        f'      var sCtx = document.getElementById("{chart_spot_id}");\n'
        f'      if (sCtx) new Chart(sCtx, {{\n'
        f'        type: "bar",\n'
        f'        data: {{ labels: {spot_labels_js}, datasets: [{{\n'
        f'          label: "70㎡（萬円）", data: {spot_data_js},\n'
        f'          backgroundColor: ["rgba(56,139,253,0.7)","rgba(63,185,80,0.7)","rgba(210,153,34,0.7)"],\n'
        f'          borderRadius: 6\n'
        f'        }}]}},\n'
        f'        options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }},\n'
        f'          scales: {{ x: {{ ticks: {{ color: "#8b949e" }}, grid: {{ display: false }} }},\n'
        f'                     y: {{ ticks: {{ color: "#8b949e" }}, grid: {{ color: "rgba(139,148,158,0.15)" }},\n'
        f'                           min: Math.max(0, Math.min(...{spot_data_js}) - 500) }} }} }}\n'
        f'      }});\n'
        f'    }})();\n'
        f'    </script>\n'
    )

    # 預售屋專區（可選）
    if presale_html:
        parts.append(f'    <div class="fk-presale-section">\n')
        parts.append(f'      <div class="fk-section-label">🏗 預售屋動態</div>\n')
        parts.append(f'      <div class="fk-presale-grid">{presale_html}\n      </div>\n')
        if presale_vs_resale:
            parts.append(f'      <div class="fk-presale-note-row">💡 {presale_vs_resale}</div>\n')
        parts.append(f'    </div>\n')

    # AI 分析文字
    parts.append(
        f'  <div class="fk-ai-section">\n'
        f'    <div class="fk-ai-lead">{analysis.get("feature", "")}</div>\n'
        f'    <div class="fk-pros-cons">\n'
        f'      <div class="fk-pros">\n'
        f'        <div class="fk-pc-title">優勢</div>\n'
        f'{pros_html}\n'
        f'      </div>\n'
        f'      <div class="fk-cons">\n'
        f'        <div class="fk-pc-title">風險</div>\n'
        f'{risks_html}\n'
        f'      </div>\n'
        f'    </div>\n'
        f'    <div class="fk-budget-box"><strong>3,000万円 建議：</strong>{analysis.get("budget_advice", "—")}</div>\n'
        f'    <div class="fk-ai-footer">\n'
        f'      <span>🤖 由 Gemini AI 生成，房價僅供參考，實際行情請向仲介確認</span>\n'
    )
    if next_preview:
        parts.append(f'      <span class="fk-next">▶ 下期：{next_preview}</span>\n')
    parts.append(
        f'    </div>\n'
        f'  </div>\n'
        f'</div>\n'
    )
    parts.append("    <!-- FK_CARD_END -->")
    return "".join(parts)


# ════════════════════════════════════════════════════════════════════
# 更新 index.html
# ════════════════════════════════════════════════════════════════════
def update_index_html(fk_html):
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    # 把現有卡片存進 history
    old_m = re.search(r'<!-- FK_CARD_START -->(.*?)<!-- FK_CARD_END -->', html, re.DOTALL)
    if old_m:
        old_content = old_m.group(1).strip()
        period_m   = re.search(r'第 (\d+) 期', old_content)
        district_m = re.search(r'class="fk-district-name">([^<]+)<', old_content)
        date_m     = re.search(r'class="fk-header-date">([^<]+)<', old_content)
        if period_m and district_m:
            p_num  = period_m.group(1)
            d_name = district_m.group(1)
            d_date = date_m.group(1) if date_m else "—"
            eid    = f"fk-hist-{p_num}"
            hist_entry = (
                f'\n      <div class="fk-hist-entry" id="{eid}">\n'
                f'        <div class="fk-hist-compact" onclick="toggleFkHist(\'{eid}\')">\n'
                f'          <span class="fk-hist-edition">第 {p_num} 期</span>\n'
                f'          <span class="fk-hist-name">{d_name}</span>\n'
                f'          <span class="fk-hist-date">{d_date}</span>\n'
                f'          <span class="fk-hist-toggle" id="{eid}-toggle">▶</span>\n'
                f'        </div>\n'
                f'        <div class="fk-hist-detail" id="{eid}-detail">\n'
                f'{old_content}\n'
                f'        </div>\n'
                f'      </div>'
            )
            html = html.replace(
                '      <!-- FK_HIST_START -->',
                f'      <!-- FK_HIST_START -->{hist_entry}',
                1
            )

    # 替換本期卡片
    pattern = r'<!-- FK_CARD_START -->.*?<!-- FK_CARD_END -->'
    new_html, count = re.subn(pattern, lambda _: fk_html, html, flags=re.DOTALL)

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
