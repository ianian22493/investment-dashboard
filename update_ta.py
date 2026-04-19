"""
update_ta.py - 每週技術分析教學自動更新腳本
每週一 08:00 UTC（台灣 16:00）由 GitHub Actions 執行
"""

import json, re
from datetime import datetime, timezone, timedelta

ROTATION = [
    {"symbol": "NVDA",  "name": "NVIDIA",          "market": "US", "sector": "AI 晶片",     "yf": "NVDA",     "desc": "全球 AI 運算龍頭，CUDA 生態系護城河極深，H 系列 GPU 供不應求"},
    {"symbol": "TSLA",  "name": "Tesla",            "market": "US", "sector": "電動車",      "yf": "TSLA",     "desc": "電動車品牌先驅，FSD 自駕與 Robotaxi 商業化是下一個成長引擎"},
    {"symbol": "MSFT",  "name": "Microsoft",        "market": "US", "sector": "雲端軟體",    "yf": "MSFT",     "desc": "Azure 雲端 + Copilot AI 整合，企業軟體市場地位最穩固的科技股之一"},
    {"symbol": "GOOGL", "name": "Alphabet",         "market": "US", "sector": "AI 搜尋",     "yf": "GOOGL",    "desc": "全球搜尋廣告霸主，Gemini AI 與 YouTube 廣告雙引擎驅動"},
    {"symbol": "AMZN",  "name": "Amazon",           "market": "US", "sector": "電商雲端",    "yf": "AMZN",     "desc": "AWS 雲端市占第一，電商物流護城河深，廣告業務快速成長"},
    {"symbol": "CELH",  "name": "Celsius Holdings", "market": "US", "sector": "健康飲料",    "yf": "CELH",     "desc": "北美成長最快的功能性飲料品牌，正積極拓展國際市場"},
    {"symbol": "MELI",  "name": "MercadoLibre",     "market": "US", "sector": "拉美電商",    "yf": "MELI",     "desc": "拉丁美洲的 Amazon + PayPal，Fintech 業務高速成長中"},
    {"symbol": "ONDS",  "name": "Ondas Holdings",   "market": "US", "sector": "無人機",      "yf": "ONDS",     "desc": "工業級無人機系統與鐵路自動化，防務訂單是主要催化劑"},
    {"symbol": "RBRK",  "name": "Rubrik",           "market": "US", "sector": "資安備份",    "yf": "RBRK",     "desc": "企業資料安全與雲端備份平台，Zero Trust 架構受市場重視"},
    {"symbol": "S",     "name": "SentinelOne",      "market": "US", "sector": "資安",        "yf": "S",        "desc": "AI 驅動端點安全平台，與 CrowdStrike 競爭最激烈的資安股"},
    {"symbol": "SMR",   "name": "NuScale Power",    "market": "US", "sector": "小型核電",    "yf": "SMR",      "desc": "小型模組化反應爐（SMR）先驅，AI 資料中心用電需求是最大催化劑"},
    {"symbol": "SOUN",  "name": "SoundHound AI",    "market": "US", "sector": "語音 AI",     "yf": "SOUN",     "desc": "車用語音 AI 商業化領先，NVIDIA 為策略投資方"},
    {"symbol": "TTD",   "name": "The Trade Desk",   "market": "US", "sector": "廣告科技",    "yf": "TTD",      "desc": "獨立程序化廣告平台龍頭，CTV 串流廣告成長最大受惠者"},
    {"symbol": "ZS",    "name": "Zscaler",          "market": "US", "sector": "零信任資安",  "yf": "ZS",       "desc": "雲端原生 SASE 安全架構龍頭，企業數位轉型的必要基礎建設"},
    {"symbol": "00692", "name": "富邦公司治理",      "market": "TW", "sector": "ETF",        "yf": "00692.TW", "desc": "追蹤公司治理評鑑優良企業，成分股品質穩定，適合長期持有領配息"},
    {"symbol": "00915", "name": "凱基優選高股息30",  "market": "TW", "sector": "ETF",        "yf": "00915.TW", "desc": "高股息 ETF，每月配息策略，適合需要穩定現金流的長期投資人"},
    {"symbol": "1104",  "name": "環泥",              "market": "TW", "sector": "水泥",       "yf": "1104.TW",  "desc": "台灣水泥龍頭之一，受惠公共建設投資與房市需求"},
    {"symbol": "2211",  "name": "長榮鋼",            "market": "TW", "sector": "鋼鐵",       "yf": "2211.TW",  "desc": "長榮集團旗下鋼材加工廠，與航運景氣連動程度高"},
    {"symbol": "2330",  "name": "台積電",            "market": "TW", "sector": "半導體",     "yf": "2330.TW",  "desc": "全球最先進晶片的唯一製造商，AI 時代最核心的科技基礎建設"},
    {"symbol": "2536",  "name": "宏普",              "market": "TW", "sector": "建設",       "yf": "2536.TW",  "desc": "台灣建設股，受央行利率政策與房市景氣影響明顯"},
    {"symbol": "2834",  "name": "臺企銀",            "market": "TW", "sector": "銀行",       "yf": "2834.TW",  "desc": "台灣政策性銀行，以中小企業放款為主要業務"},
    {"symbol": "3293",  "name": "鈺象",              "market": "TW", "sector": "電子零組件", "yf": "3293.TW",  "desc": "電子連接器製造，受 AI 伺服器供應鏈需求帶動"},
    {"symbol": "3661",  "name": "世芯-KY",           "market": "TW", "sector": "IC 設計",    "yf": "3661.TW",  "desc": "ASIC 客製化晶片設計領先者，AI / HPC 應用快速成長"},
    {"symbol": "3703",  "name": "欣陸",              "market": "TW", "sector": "建設",       "yf": "3703.TW",  "desc": "台灣建設與土地開發，業績受房市景氣影響明顯"},
    {"symbol": "4588",  "name": "玖鼎電力",          "market": "TW", "sector": "電力設備",   "yf": "4588.TW",  "desc": "電力設備製造商，受惠 AI 資料中心與電網升級帶來的用電需求"},
    {"symbol": "4707",  "name": "磐亞",              "market": "TW", "sector": "特用化學",   "yf": "4707.TW",  "desc": "特殊化學材料供應商，應用於電子與工業製造領域"},
]

US_TOTAL   = sum(1 for s in ROTATION if s["market"] == "US")
TW_TOTAL   = sum(1 for s in ROTATION if s["market"] == "TW")
TZ_TW      = timezone(timedelta(hours=8))
STATE_FILE = "ta_state.json"
INDEX_FILE = "index.html"


def load_state():
    with open(STATE_FILE) as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_next_stock(covered):
    for s in ROTATION:
        if s["symbol"] not in covered:
            return s
    return ROTATION[0]  # 全部介紹完，重新開始

def get_preview_name(current_symbol):
    idx = next((i for i, s in enumerate(ROTATION) if s["symbol"] == current_symbol), -1)
    if idx == -1 or idx + 1 >= len(ROTATION):
        return ROTATION[0]["symbol"]
    return ROTATION[idx + 1]["symbol"]

def get_progress_str(stock):
    if stock["market"] == "US":
        us_list = [s for s in ROTATION if s["market"] == "US"]
        idx = next(i for i, s in enumerate(us_list) if s["symbol"] == stock["symbol"])
        return f"美股 {idx+1}/{US_TOTAL}"
    else:
        tw_list = [s for s in ROTATION if s["market"] == "TW"]
        idx = next(i for i, s in enumerate(tw_list) if s["symbol"] == stock["symbol"])
        return f"台股 {idx+1}/{TW_TOTAL}"

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains  = [max(d, 0)      for d in deltas[-period:]]
    losses = [abs(min(d, 0)) for d in deltas[-period:]]
    avg_g  = sum(gains)  / period
    avg_l  = sum(losses) / period
    if avg_l == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_g / avg_l)), 1)

def fetch_indicators(stock):
    import yfinance as yf
    try:
        hist = yf.Ticker(stock["yf"]).history(period="3mo")
        if hist.empty or len(hist) < 20:
            print(f"  警告：{stock['symbol']} 資料不足")
            return None
        closes = list(hist["Close"])
        price  = round(closes[-1], 2)
        n60    = min(60, len(closes))
        ma5    = round(sum(closes[-5:]) / 5, 2)
        ma20   = round(sum(closes[-20:]) / 20, 2)
        ma60   = round(sum(closes[-n60:]) / n60, 2)
        # RSI 14 detailed breakdown
        period   = 14
        deltas   = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        changes  = deltas[-period:]
        up_days  = sum(1 for d in changes if d > 0)
        dn_days  = sum(1 for d in changes if d < 0)
        sum_g    = sum(max(d, 0)      for d in changes)
        sum_l    = sum(abs(min(d, 0)) for d in changes)
        avg_g    = sum_g / period
        avg_l    = sum_l / period
        rsi_rs   = round(avg_g / avg_l, 2) if avg_l > 0 else 999.0
        rsi      = round(100 - (100 / (1 + avg_g / avg_l)), 1) if avg_l > 0 else 100.0
        # MA5 detailed: last 5 trading days with dates
        dates     = [d.strftime("%m/%d") for d in hist.index]
        closes_5d = [(dates[-5+i], round(closes[-5+i], 2)) for i in range(5)]
        n252   = min(252, len(closes))
        low52  = round(min(closes[-n252:]), 2)
        high52 = round(max(closes[-n252:]), 2)
        rng    = high52 - low52
        w52pct = round(((price - low52) / rng * 100) if rng > 0 else 50, 1)
        s_sort = sorted(closes[-20:])
        h_sort = sorted(closes[-20:], reverse=True)
        return {
            "price": price, "ma5": ma5, "ma20": ma20, "ma60": ma60,
            "rsi": rsi, "low52": low52, "high52": high52, "w52pct": w52pct,
            "support1":    round(s_sort[2],    2),
            "support2":    round(low52 * 1.01, 2),
            "resistance1": round(h_sort[2],    2),
            "resistance2": round(high52 * 0.99, 2),
            # Detailed calculation data (for educational card)
            "closes_5d": closes_5d,
            "rsi_up":    up_days,
            "rsi_down":  dn_days,
            "rsi_sum_g": round(sum_g, 2),
            "rsi_sum_l": round(sum_l, 2),
            "rsi_avg_g": round(avg_g, 3),
            "rsi_avg_l": round(avg_l, 3),
            "rsi_rs":    rsi_rs,
        }
    except Exception as e:
        print(f"  錯誤：{stock['symbol']} 指標抓取失敗：{e}")
        return None

def fp(val, mkt):
    return f"${val:,.2f}" if mkt == "US" else f"{val:,.2f}"

def generate_ta_card(stock, ind, week_num, date_str):
    sym    = stock["symbol"]
    name   = stock["name"]
    sector = stock["sector"]
    desc   = stock["desc"]
    mkt    = stock["market"]
    p      = lambda v: fp(v, mkt)

    # MA5 calculation table HTML
    if ind.get("closes_5d"):
        _rows = "".join(
            f'<strong>{d}：</strong>{p(v)}<br>\n'
            for d, v in ind["closes_5d"]
        )
        _sum_5 = round(sum(v for _, v in ind["closes_5d"]), 2)
        ma5_calc_html = (
            f'<div class="ta-calc-box">\n'
            f'{_rows}'
            f'──────────────────────<br>\n'
            f'合計 {p(_sum_5)} ÷ 5 日 ＝ <strong style="color:#79c0ff">MA5 {p(ind["ma5"])}</strong>\n'
            f'</div>\n'
        )
    else:
        ma5_calc_html = ""

    # RSI calculation HTML
    if ind.get("rsi_avg_g") is not None:
        rsi_calc_html = (
            f'<div class="ta-calc-box">\n'
            f'上漲日：<strong>{ind["rsi_up"]} 天</strong>，合計漲幅 +{p(ind["rsi_sum_g"])}<br>\n'
            f'下跌日：<strong>{ind["rsi_down"]} 天</strong>，合計跌幅 −{p(ind["rsi_sum_l"])}<br>\n'
            f'────────────────────────────<br>\n'
            f'平均漲幅 = {p(ind["rsi_sum_g"])} ÷ 14 = <strong>+{p(ind["rsi_avg_g"])}</strong>（÷14，不是 ÷{ind["rsi_up"]}）<br>\n'
            f'平均跌幅 = {p(ind["rsi_sum_l"])} ÷ 14 = <strong>{p(ind["rsi_avg_l"])}</strong>（÷14，不是 ÷{ind["rsi_down"]}）<br>\n'
            f'RS = {p(ind["rsi_avg_g"])} ÷ {p(ind["rsi_avg_l"])} = <strong>{ind["rsi_rs"]}</strong><br>\n'
            f'RSI = 100 − 100 ÷ (1 + {ind["rsi_rs"]}) = <strong style="color:var(--red)">{ind["rsi"]}</strong>\n'
            f'</div>\n'
        )
    else:
        rsi_calc_html = ""

    # MA
    if ind["ma5"] > ind["ma20"] > ind["ma60"]:
        ma_b = "多頭排列"; ma_c = "status-bull"; sc = "sent-bull"; sl = "看多格局"
        ma_body = (f"5日線（{p(ind['ma5'])}）> 20日線（{p(ind['ma20'])}）> 60日線（{p(ind['ma60'])}），"
                   "三條均線同時向上，呈現<strong>多頭排列</strong>，短中長期趨勢全部偏多，是強勢股的典型特徵。")
        ma_tip = f"股價回測 20 日線（{p(ind['ma20'])}）不破，是多方持倉的確認訊號；跌破 60 日線（{p(ind['ma60'])}）且無力回升，才需重新評估方向。"
        st = "多頭排列（強勢）"
    elif ind["ma5"] < ind["ma20"] < ind["ma60"]:
        ma_b = "空頭排列"; ma_c = "status-bear"; sc = "sent-bear"; sl = "偏空格局"
        ma_body = (f"5日線（{p(ind['ma5'])}）< 20日線（{p(ind['ma20'])}）< 60日線（{p(ind['ma60'])}），"
                   "三條均線同時向下，呈現<strong>空頭排列</strong>，宜保守觀望，避免逆勢操作。")
        ma_tip = f"等股價站回 20 日線（{p(ind['ma20'])}）以上並持穩，才考慮布局；此前反彈往往只是賣點。"
        st = "空頭排列（弱勢）"
    else:
        ma_b = "盤整整理"; ma_c = "status-neut"; sc = "sent-neut"; sl = "觀察格局"
        ma_body = (f"5日（{p(ind['ma5'])}）、20日（{p(ind['ma20'])}）、60日（{p(ind['ma60'])}）三線糾結，"
                   "多空拉鋸，<strong>方向尚未明確</strong>，等待突破。")
        ma_tip = f"向上放量突破 20 日線（{p(ind['ma20'])}）偏多；跌破 60 日線（{p(ind['ma60'])}）偏空。"
        st = "盤整整理（觀察）"

    # RSI
    r = ind["rsi"]
    if r > 75:
        rsi_b = "強烈超買"; rsi_c = "status-bear"
        rsi_body = f"RSI 達 <strong>{r}</strong>，進入強烈超買區（&gt;75），短期漲幅過大，此時追高風險明顯增加。"
        rsi_tip = "等 RSI 回落至 60 以下再重新評估；已持有者可考慮分批減倉，鎖定部分利潤。"
    elif r > 60:
        rsi_b = "強勢健康"; rsi_c = "status-bull"
        rsi_body = f"RSI 為 <strong>{r}</strong>，處於 60–75 的健康偏多區間，「強勢但不過熱」的理想狀態。"
        rsi_tip = "這個區間是比較舒適的持有環境。若 RSI 在此整理後再度走高，往往是趨勢延續的訊號。"
    elif r > 45:
        rsi_b = "中性"; rsi_c = "status-neut"
        rsi_body = f"RSI 為 <strong>{r}</strong>，在 45–60 的中性區間，多空力道相當，股價可能正在整理，等待下一個方向選擇。"
        rsi_tip = "搭配均線方向判斷：均線多頭時 RSI 中性是整理後再攻的機會；均線空頭時往往只是反彈。"
    elif r > 30:
        rsi_b = "偏弱"; rsi_c = "status-neut"
        rsi_body = f"RSI 為 <strong>{r}</strong>，落在 30–45 的偏空區間，近期賣壓大於買盤，動能偏弱，不建議追跌。"
        rsi_tip = "若 RSI 在低位出現「底背離」（股價創低但 RSI 不創低），才是可能的轉折訊號。"
    else:
        rsi_b = "超賣"; rsi_c = "status-watch"
        rsi_body = f"RSI 為 <strong>{r}</strong>，進入超賣區（&lt;30）。超賣本身不是買進訊號，跌勢中 RSI 可長時間停留低位。"
        rsi_tip = "等 RSI 從低位回升並突破 35，且股價同步走強，才是比較安全的進場時機。"
    sr = f"{rsi_b}（{r}）"

    # 52週位置
    pct = ind["w52pct"]
    if pct > 80:
        pos = f"在 52 週區間的<strong>高位（{pct:.0f}%）</strong>，靠近歷史高點，代表市場對中長期前景有信心，但相對成本也較高。"
    elif pct > 20:
        pos = f"在 52 週區間的<strong>中段（{pct:.0f}%）</strong>，屬於相對合理的位置，無明顯追高或超跌的疑慮。"
    else:
        pos = f"在 52 週區間的<strong>低位（{pct:.0f}%）</strong>，接近年內低點，需判斷是超賣機會還是基本面惡化。"

    progress = get_progress_str(stock)
    next_sym = get_preview_name(sym)
    hist_summary = f"均線{st} · RSI {sr} · 52週位 {pct:.0f}%"

    card = (
        "    <!-- TA_CARD_START -->\n"
        "    <div class=\"ta-card\">\n"
        "      <div class=\"ta-header\">\n"
        "        <div class=\"ta-left\">\n"
        f"          <div class=\"ta-week-badge\">第 {week_num} 週</div>\n"
        f"          <div class=\"ta-ticker\">{sym} <span class=\"ta-name\">{name} · {sector}</span></div>\n"
        f"          <div class=\"ta-subtitle\">{desc}</div>\n"
        "        </div>\n"
        f"        <div class=\"ta-sentiment {sc}\">{sl}</div>\n"
        "      </div>\n"
        "      <div class=\"ta-indicators\">\n"
        "        <div class=\"ta-ind\">\n"
        "          <div class=\"ta-ind-header\">\n"
        "            <span class=\"ta-ind-icon\">📈</span>\n"
        "            <span class=\"ta-ind-name\">移動平均線 (MA)</span>\n"
        f"            <span class=\"ta-ind-status {ma_c}\">{ma_b}</span>\n"
        "          </div>\n"
        "          <div class=\"ta-ind-body\">\n"
        "            <strong>怎麼算？</strong>把過去 N 天的收盤價加總再除以 N。N 越大，線越平滑、越滯後。常用：5日（週線感）、20日（月線感）、60日（季線感）。<br><br>\n"
        f"            <strong>{sym} MA5 計算過程（最近 5 個交易日）：</strong><br>\n"
        f"{ma5_calc_html}"
        f"            <strong>各均線：</strong>MA5 <strong>{p(ind['ma5'])}</strong>、MA20 <strong>{p(ind['ma20'])}</strong>、MA60 <strong>{p(ind['ma60'])}</strong><br>\n"
        f"            {ma_body}\n"
        f"            <div class=\"ta-tip\">📌 <strong>操作參考：</strong>{ma_tip}</div>\n"
        "          </div>\n"
        "        </div>\n"
        "        <div class=\"ta-ind\">\n"
        "          <div class=\"ta-ind-header\">\n"
        "            <span class=\"ta-ind-icon\">⚡</span>\n"
        "            <span class=\"ta-ind-name\">相對強弱指數 (RSI)</span>\n"
        f"            <span class=\"ta-ind-status {rsi_c}\">{rsi_b}</span>\n"
        "          </div>\n"
        "          <div class=\"ta-ind-body\">\n"
        "            <strong>怎麼算？</strong>取最近 14 個交易日每日漲跌，分別算「14日平均漲幅」和「14日平均跌幅」——兩者都要除以 14，不管有幾天上漲、幾天下跌（這是關鍵！）。<br><br>\n"
        "            <strong>公式：</strong>RS = 平均漲幅 ÷ 平均跌幅，RSI = 100 − 100 ÷ (1 + RS)<br><br>\n"
        f"            <strong>{sym} 實際計算（近 14 個交易日）：</strong><br>\n"
        f"{rsi_calc_html}"
        f"            <strong>{sym} 現況：</strong>{rsi_body}\n"
        f"            <div class=\"ta-tip\">📌 <strong>實戰建議：</strong>{rsi_tip}</div>\n"
        "          </div>\n"
        "        </div>\n"
        "        <div class=\"ta-ind\">\n"
        "          <div class=\"ta-ind-header\">\n"
        "            <span class=\"ta-ind-icon\">🎯</span>\n"
        "            <span class=\"ta-ind-name\">52 週位置 ＆ 支撐壓力</span>\n"
        "            <span class=\"ta-ind-status status-watch\">關鍵位置</span>\n"
        "          </div>\n"
        "          <div class=\"ta-ind-body\">\n"
        "            <strong>52 週位置的意義：</strong>把過去一年的低點到高點當作座標系，現在股價落在哪個百分比，幫助判斷現在是「相對便宜」還是「相對昂貴」。<br><br>\n"
        f"            <strong>{sym} 現況：</strong>現價 {p(ind['price'])} 目前{pos}<br>\n"
        f"            52週低：{p(ind['low52'])} ／ 高：{p(ind['high52'])}<br><br>\n"
        f"            <strong>關鍵價位：</strong>支撐 {p(ind['support1'])}、{p(ind['support2'])}；壓力 {p(ind['resistance1'])}、{p(ind['resistance2'])}。\n"
        "            <div class=\"ta-tip\">📌 <strong>記住：</strong>支撐和壓力不是一條精確的線，而是一個「區間」。在支撐區附近出現止跌＋成交量縮小，才是比較有效的支撐訊號。</div>\n"
        "          </div>\n"
        "        </div>\n"
        "      </div>\n"
        "      <div class=\"ta-summary\">\n"
        f"        <div class=\"ta-summary-title\">🎯 本週總結：{sym} 怎麼看？</div>\n"
        "        <div class=\"ta-summary-body\">\n"
        f"          均線方向：<strong>{st}</strong> · RSI 動能：<strong>{sr}</strong> · 52週位置：<strong>{pct:.0f}%</strong><br><br>\n"
        "          <strong>學習重點：</strong>MA 看方向、RSI 看動能、52週位置看相對位階——這三個維度是技術分析最基礎的架構。每次看一支股票，先確認這三點，就能快速判斷現在是「順勢做多」、「等待整理」，還是「謹慎觀察」。\n"
        "        </div>\n"
        "      </div>\n"
        f"      <div class=\"ta-footer\">每週一更新 · {date_str} · {progress} · 下週：{next_sym}</div>\n"
        "    </div>\n"
        "    <!-- TA_CARD_END -->
"
    )
    return card, hist_summary


def generate_hist_row(entry_id, week_num, stock, date_str, summary, card_inner_html=''):
    """
    生成可展開的歷史紀錄項目。
    點擊最左該列可展開 / 收合完整分析內容。
    """
    sym  = stock["symbol"] if isinstance(stock, dict) else stock
    name = stock.get("name", sym) if isinstance(stock, dict) else sym

    # 展開區塊（包含該週完整分析內容）
    detail_html = (
        f'        <div class="ta-hist-detail" id="{entry_id}-detail">\n'
        f'{card_inner_html}\n'
        f'        </div>\n'
    ) if card_inner_html.strip() else ''

    return (
        f'      <div class="ta-hist-entry" id="{entry_id}">\n'
        f'        <div class="ta-hist-compact" onclick="toggleHistEntry(\'{entry_id}\')">\n'
        f'          <span class="ta-hist-week">第 {week_num} 週</span>\n'
        f'          <span class="ta-hist-ticker">{sym}</span>\n'
        f'          <span class="ta-hist-name">{name}</span>\n'
        f'          <span class="ta-hist-summary">{summary}</span>\n'
        f'          <span class="ta-hist-date">{date_str}</span>\n'
        f'          <span class="ta-hist-toggle" id="{entry_id}-toggle">▶</span>\n'
        f'        </div>\n'
        f'{detail_html}'
        f'      </div>'
    )


def update_html(new_card_html, hist_row_html):
    with open(INDEX_FILE, encoding="utf-8") as f:
        html = f.read()
    # 替換 ta-card
    old_pat = r'    <!-- TA_CARD_START -->.*?    <!-- TA_CARD_END -->'
    html = re.sub(old_pat, new_card_html, html, flags=re.DOTALL)
    # 插入歷史列（放在最前面）
    html = html.replace(
        '      <!-- HIST_ROWS_START -->',
        f'      <!-- HIST_ROWS_START -->\n{hist_row_html}'
    )
    # 移除「尚無歷史紀錄」提示
    html = re.sub(r'\s*<div class="ta-history-empty"[^>]*>.*?</div>', '', html, flags=re.DOTALL)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("  index.html 已更新")


def main():
    state    = load_state()
    next_stk = get_next_stock(state["covered"])
    week_num = state["week"] + 1
    date_str = datetime.now(TZ_TW).strftime("%Y/%m/%d")

    print(f"第 {week_num} 週：{next_stk['symbol']} {next_stk['name']}")

    ind = fetch_indicators(next_stk)
    if ind is None:
        print("無法取得指標，中止更新")
        return

    print(f"  價格 {ind['price']}，RSI {ind['rsi']}，52週位 {ind['w52pct']:.0f}%")

    new_card, hist_summary = generate_ta_card(next_stk, ind, week_num, date_str)

    # 取得舊卡片資訊（用於歷史列）
    with open(INDEX_FILE, encoding="utf-8") as f:
        old_html = f.read()
    m_week   = re.search(r'ta-week-badge">第 (\d+) 週', old_html)
    m_ticker = re.search(r'ta-ticker">(\S+) <span', old_html)
    m_date   = re.search(r'ta-footer">每週一更新 · (\d{4}/\d{2}/\d{2})', old_html)
    m_sent   = re.search(r'ta-sentiment\b[^>]+>([^<]+)', old_html)
    # 提取舊卡片完整內容（加進展開區塊）
    m_card   = re.search(r'<!-- TA_CARD_START -->(.*?)<!-- TA_CARD_END -->', old_html, flags=re.DOTALL)

    old_week     = int(m_week.group(1)) if m_week   else week_num - 1
    old_ticker   = m_ticker.group(1)    if m_ticker else "—"
    old_date     = m_date.group(1)      if m_date   else "—"
    old_summary  = m_sent.group(1).strip() if m_sent else "—"
    old_card_inner = m_card.group(1).strip() if m_card else ""
    old_stock = next((s for s in ROTATION if s["symbol"] == old_ticker),
                     {"symbol": old_ticker, "name": old_ticker})

    entry_id = f"hist-{old_week}"
    hist_row = generate_hist_row(entry_id, old_week, old_stock, old_date, old_summary, old_card_inner)
    update_html(new_card, hist_row)

    new_covered = state["covered"] + [next_stk["symbol"]]
    if len(new_covered) >= len(ROTATION):
        new_covered = []
    save_state({
        "week":         week_num,
        "covered":      new_covered,
        "last_updated": datetime.now(TZ_TW).strftime("%Y-%m-%d"),
    })
    print(f"完成！本週：{next_stk['symbol']}，下週：{get_preview_name(next_stk['symbol'])}")


if __name__ == "__main__":
    main()
