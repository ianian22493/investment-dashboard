"""
update_ta.py — 每週技術分析教學自動更新腳本
每週一 08:00 UTC（台灣 16:00）由 GitHub Actions 執行

課程設計：
  第 1–10 週：每週教一個技術分析工具
  第 11 週起：工具箱綜合分析（永久模式）
"""

import json, re
from datetime import datetime, timezone, timedelta

# ════════════════════════════════════════════════════════════════════
# 持倉輪替清單
# ════════════════════════════════════════════════════════════════════
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

# ════════════════════════════════════════════════════════════════════
# 教學課程（lesson_idx 0–9 學習期，10+ 工具箱永久模式）
# ════════════════════════════════════════════════════════════════════
CURRICULUM = [
    {"id": "ma",        "name": "移動平均線（MA）",      "icon": "📈"},
    {"id": "volume",    "name": "成交量分析",             "icon": "📊"},
    {"id": "macd",      "name": "MACD 趨勢轉折",          "icon": "🔄"},
    {"id": "bollinger", "name": "布林通道（波動率）",      "icon": "〰️"},
    {"id": "rsi_kd",    "name": "RSI ＋ KD 動能指標",    "icon": "⚡"},
    {"id": "candle",    "name": "K 線型態",               "icon": "🕯️"},
    {"id": "sr",        "name": "支撐與壓力",             "icon": "🎯"},
    {"id": "fibo",      "name": "費波納契回撤",           "icon": "🌀"},
    {"id": "rs",        "name": "相對強弱 vs 大盤",       "icon": "📍"},
    {"id": "atr",       "name": "ATR 與風險管理",         "icon": "🛡️"},
    {"id": "toolbox",   "name": "工具箱綜合分析",         "icon": "🔮"},
]

# ════════════════════════════════════════════════════════════════════
# 個股敘述（多空論點 / 關注焦點 / 催化劑）— 資料存於 narratives.json
# ════════════════════════════════════════════════════════════════════
with open("narratives.json", encoding="utf-8") as _f:
    NARRATIVES = json.load(_f)


# ════════════════════════════════════════════════════════════════════
# 工具函數
# ════════════════════════════════════════════════════════════════════
def fp(val, mkt):
    return f"${val:,.2f}" if mkt == "US" else f"{val:,.2f}"

def fmt_vol(v):
    if v >= 1_000_000: return f"{v/1_000_000:.1f}M"
    if v >= 1_000:     return f"{v/1_000:.0f}K"
    return str(v)

def load_state():
    with open(STATE_FILE) as f: return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f: json.dump(state, f, ensure_ascii=False, indent=2)

def get_next_stock(covered):
    for s in ROTATION:
        if s["symbol"] not in covered: return s
    return ROTATION[0]

def get_preview_name(current_symbol):
    idx = next((i for i, s in enumerate(ROTATION) if s["symbol"] == current_symbol), -1)
    if idx == -1 or idx + 1 >= len(ROTATION): return ROTATION[0]["symbol"]
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


# ════════════════════════════════════════════════════════════════════
# 技術指標計算
# ════════════════════════════════════════════════════════════════════
def calc_ema(prices, period):
    k = 2 / (period + 1)
    ema = [prices[0]]
    for p in prices[1:]:
        ema.append(p * k + ema[-1] * (1 - k))
    return ema

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0, {}
    deltas  = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    changes = deltas[-period:]
    up_days = sum(1 for d in changes if d > 0)
    dn_days = sum(1 for d in changes if d < 0)
    sum_g   = sum(max(d, 0) for d in changes)
    sum_l   = sum(abs(min(d, 0)) for d in changes)
    avg_g   = sum_g / period
    avg_l   = sum_l / period
    rs      = round(avg_g / avg_l, 2) if avg_l > 0 else 999.0
    rsi     = round(100 - (100 / (1 + avg_g / avg_l)), 1) if avg_l > 0 else 100.0
    detail  = {"up": up_days, "dn": dn_days,
               "sum_g": round(sum_g, 2), "sum_l": round(sum_l, 2),
               "avg_g": round(avg_g, 3), "avg_l": round(avg_l, 3), "rs": rs}
    return rsi, detail

def calc_kd(hist, period=9):
    highs  = list(hist["High"])
    lows   = list(hist["Low"])
    closes = list(hist["Close"])
    k, d   = 50.0, 50.0
    for i in range(period - 1, len(closes)):
        h9  = max(highs[i-period+1:i+1])
        l9  = min(lows[i-period+1:i+1])
        rng = h9 - l9
        rsv = ((closes[i] - l9) / rng * 100) if rng > 0 else 50.0
        k = k * 2/3 + rsv * 1/3
        d = d * 2/3 + k * 1/3
    return round(k, 1), round(d, 1)

def calc_atr(hist, period=14):
    highs  = list(hist["High"])
    lows   = list(hist["Low"])
    closes = list(hist["Close"])
    trs = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
           for i in range(1, len(closes))]
    return round(sum(trs[-period:]) / period, 2)

def identify_candle(o, h, l, c):
    body  = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    total = h - l
    if total == 0: return "十字線"
    bull = c > o
    if body < total * 0.1:
        return "十字線（多空猶豫，可能轉折）"
    if bull and lower > body * 2 and upper < body * 0.5:
        return "錘子線（下跌後出現，潛在底部反轉）"
    if not bull and upper > body * 2 and lower < body * 0.5:
        return "流星線（上漲後出現，潛在頂部反轉）"
    if bull and body > total * 0.7:
        return "長紅 K（強勁上漲，多方主導）"
    if not bull and body > total * 0.7:
        return "長黑 K（強勁下跌，空方主導）"
    return "一般 K 線"


# ════════════════════════════════════════════════════════════════════
# 一次性抓取全部所需指標
# ════════════════════════════════════════════════════════════════════
def fetch_indicators(stock):
    import yfinance as yf
    try:
        hist = yf.Ticker(stock["yf"]).history(period="6mo")
        if hist.empty or len(hist) < 30:
            print(f"  警告：{stock['symbol']} 資料不足")
            return None

        closes  = list(hist["Close"])
        volumes = list(hist["Volume"])
        dates   = [d.strftime("%m/%d") for d in hist.index]
        price   = round(closes[-1], 2)

        # ── MA ──
        n60  = min(60, len(closes))
        ma5  = round(sum(closes[-5:])  / 5,   2)
        ma20 = round(sum(closes[-20:]) / 20,  2)
        ma60 = round(sum(closes[-n60:]) / n60, 2)
        closes_5d = [(dates[-5+i], round(closes[-5+i], 2)) for i in range(5)]

        # ── RSI + KD ──
        rsi, rsi_detail = calc_rsi(closes)
        kd_k, kd_d      = calc_kd(hist)

        # ── Volume ──
        avg_vol = round(sum(volumes[-20:]) / 20)
        rel_vol = round(volumes[-1] / avg_vol, 2) if avg_vol > 0 else 1.0
        vol_5d  = [(dates[-5+i], volumes[-5+i]) for i in range(5)]
        # 判斷近 5 天量能趨勢
        vol_up = sum(1 for i in range(1, 5) if volumes[-5+i] > volumes[-5+i-1]) >= 3

        # ── MACD (12, 26, 9) ──
        ema12 = calc_ema(closes, 12)
        ema26 = calc_ema(closes, 26)
        off   = len(ema12) - len(ema26)
        macd_line = [ema12[i+off] - ema26[i] for i in range(len(ema26))]
        signal    = calc_ema(macd_line, 9)
        macd_val  = round(macd_line[-1], 3)
        sig_val   = round(signal[-1], 3)
        hist_val  = round(macd_val - sig_val, 3)
        hist_5    = [round(macd_line[-5+i] - signal[-5+i], 3) for i in range(5)]
        # 金叉/死叉判斷
        golden = (macd_line[-1] > signal[-1]) and (macd_line[-2] <= signal[-2])
        dead   = (macd_line[-1] < signal[-1]) and (macd_line[-2] >= signal[-2])

        # ── Bollinger (20, 2) ──
        ma20_v = sum(closes[-20:]) / 20
        std20  = (sum((c - ma20_v)**2 for c in closes[-20:]) / 20) ** 0.5
        bb_up  = round(ma20_v + 2*std20, 2)
        bb_lo  = round(ma20_v - 2*std20, 2)
        bb_w   = round((bb_up - bb_lo) / ma20_v * 100, 1)
        bb_pos = round((price - bb_lo) / (bb_up - bb_lo) * 100, 1) if (bb_up - bb_lo) > 0 else 50.0

        # ── ATR (14) ──
        atr     = calc_atr(hist)
        atr_pct = round(atr / price * 100, 2)

        # ── 52 週 ──
        n252   = min(252, len(closes))
        low52  = round(min(closes[-n252:]), 2)
        high52 = round(max(closes[-n252:]), 2)
        rng52  = high52 - low52
        w52pct = round(((price - low52) / rng52 * 100) if rng52 > 0 else 50, 1)

        # ── 支撐壓力 ──
        s_sort = sorted(closes[-20:])
        h_sort = sorted(closes[-20:], reverse=True)
        support1    = round(s_sort[2], 2)
        resistance1 = round(h_sort[2], 2)

        # ── 近 5 日 OHLC ──
        ohlc_5d = [{"date": dates[-5+i],
                    "open":  round(float(hist["Open"].iloc[-5+i]),  2),
                    "high":  round(float(hist["High"].iloc[-5+i]),  2),
                    "low":   round(float(hist["Low"].iloc[-5+i]),   2),
                    "close": round(float(hist["Close"].iloc[-5+i]), 2)}
                   for i in range(5)]

        # ── Fibonacci (3-month swing) ──
        n63      = min(63, len(closes))
        fib_high = round(max(closes[-n63:]), 2)
        fib_low  = round(min(closes[-n63:]), 2)
        fib_rng  = fib_high - fib_low
        fib_lvls = {
            "0%":    fib_high,
            "23.6%": round(fib_high - fib_rng * 0.236, 2),
            "38.2%": round(fib_high - fib_rng * 0.382, 2),
            "50%":   round(fib_high - fib_rng * 0.500, 2),
            "61.8%": round(fib_high - fib_rng * 0.618, 2),
            "100%":  fib_low,
        }

        # ── 相對強弱 vs SPY ──
        spy_hist = yf.Ticker("SPY").history(period="3mo")
        if not spy_hist.empty and len(spy_hist) >= 2:
            spy_ret = round((float(spy_hist["Close"].iloc[-1]) / float(spy_hist["Close"].iloc[0]) - 1) * 100, 1)
        else:
            spy_ret = None
        ret_3m    = round((closes[-1] / closes[-n63] - 1) * 100, 1) if n63 < len(closes) else None
        rs_vs_spy = round(ret_3m - spy_ret, 1) if (ret_3m is not None and spy_ret is not None) else None

        # ── 60 天圖表序列（收盤 + 滾動 MA）──
        n_chart = min(60, len(closes))
        chart_dates  = dates[-n_chart:]
        chart_closes = [round(c, 2) for c in closes[-n_chart:]]
        chart_ma5, chart_ma20, chart_ma60 = [], [], []
        for i in range(n_chart):
            idx = len(closes) - n_chart + i
            chart_ma5.append( round(sum(closes[idx-4 :idx+1])/5,  2) if idx >= 4  else None)
            chart_ma20.append(round(sum(closes[idx-19:idx+1])/20, 2) if idx >= 19 else None)
            chart_ma60.append(round(sum(closes[idx-59:idx+1])/60, 2) if idx >= 59 else None)

        return {
            "price": price,
            "ma5": ma5, "ma20": ma20, "ma60": ma60, "closes_5d": closes_5d,
            "rsi": rsi, "rsi_detail": rsi_detail,
            "kd_k": kd_k, "kd_d": kd_d,
            "vol": volumes[-1], "avg_vol": avg_vol, "rel_vol": rel_vol,
            "vol_5d": vol_5d, "vol_up": vol_up,
            "macd": macd_val, "signal": sig_val, "hist": hist_val,
            "hist_5": hist_5, "golden": golden, "dead": dead,
            "bb_up": bb_up, "bb_lo": bb_lo, "bb_w": bb_w, "bb_pos": bb_pos,
            "atr": atr, "atr_pct": atr_pct,
            "low52": low52, "high52": high52, "w52pct": w52pct,
            "support1": support1, "resistance1": resistance1,
            "ohlc_5d": ohlc_5d,
            "fib_high": fib_high, "fib_low": fib_low, "fib_lvls": fib_lvls,
            "ret_3m": ret_3m, "spy_ret": spy_ret, "rs_vs_spy": rs_vs_spy,
            # 圖表序列
            "chart_dates": chart_dates, "chart_closes": chart_closes,
            "chart_ma5": chart_ma5, "chart_ma20": chart_ma20, "chart_ma60": chart_ma60,
        }
    except Exception as e:
        print(f"  錯誤：{stock['symbol']} 指標抓取失敗：{e}")
        return None


# ════════════════════════════════════════════════════════════════════
# 各週教學內容生成器
# ════════════════════════════════════════════════════════════════════
def lesson_ma(stock, ind, p):
    sym = stock["symbol"]
    rows = "\n".join(f"{d}：<strong>{p(v)}</strong><br>" for d, v in ind["closes_5d"])
    s5   = round(sum(v for _, v in ind["closes_5d"]), 2)
    if ind["ma5"] > ind["ma20"] > ind["ma60"]:
        align = f"多頭排列（{p(ind['ma5'])} &gt; {p(ind['ma20'])} &gt; {p(ind['ma60'])}）——三條均線同時向上，是強勢股的典型特徵。"
        tip   = f"股價維持在 MA5（{p(ind['ma5'])}）上方，是短期偏多的確認訊號；跌破 MA60（{p(ind['ma60'])}）才需重新評估方向。"
    elif ind["ma5"] < ind["ma20"] < ind["ma60"]:
        align = f"空頭排列（{p(ind['ma5'])} &lt; {p(ind['ma20'])} &lt; {p(ind['ma60'])}）——三條均線同時向下，宜保守觀望，避免逆勢操作。"
        tip   = f"等股價站回 MA20（{p(ind['ma20'])}）以上並持穩，再考慮布局；此前反彈往往只是賣點。"
    else:
        align = f"均線糾結（MA5 {p(ind['ma5'])}、MA20 {p(ind['ma20'])}、MA60 {p(ind['ma60'])}）——多空方向未明，等待突破。"
        tip   = f"放量突破 MA20（{p(ind['ma20'])}）偏多；跌破 MA60（{p(ind['ma60'])}）偏空。"
    return (
        f'<div class="ta-ind">\n'
        f'  <div class="ta-ind-header"><span class="ta-ind-icon">📈</span>'
        f'<span class="ta-ind-name">本週教學：移動平均線（MA）</span></div>\n'
        f'  <div class="ta-ind-body">\n'
        f'    <strong>概念：</strong>把過去 N 天收盤價加總除以 N，消除每日雜訊，讓趨勢一目瞭然。N 越大越平滑、越滯後。常用 5日（週線感）、20日（月線感）、60日（季線感）。<br><br>\n'
        f'    <strong>MA5 實際計算（{sym} 最近 5 個交易日）：</strong>\n'
        f'    <div class="ta-calc-box">{rows}──────────────────<br>\n合計 {p(s5)} ÷ 5 日 ＝ <strong style="color:#79c0ff">MA5 = {p(ind["ma5"])}</strong></div>\n'
        f'    <strong>現況：</strong>{align}<br>\n'
        f'    <div class="ta-tip">📌 <strong>操作參考：</strong>{tip}</div>\n'
        f'  </div>\n</div>\n'
    )

def lesson_volume(stock, ind, p):
    sym   = stock["symbol"]
    rows  = "\n".join(f"{d}：<strong>{fmt_vol(v)}</strong>{'（高於均量）' if v > ind['avg_vol'] else '（低於均量）'}<br>" for d, v in ind["vol_5d"])
    price_trend = "上漲" if ind["ma5"] > ind["ma20"] else "下跌"
    if ind["rel_vol"] > 1.2 and price_trend == "上漲":
        signal = "放量上漲——多方積極進場，訊號偏多。"
    elif ind["rel_vol"] < 0.8 and price_trend == "上漲":
        signal = "縮量上漲——上漲力道不足，動能可能減弱，需警戒。"
    elif ind["rel_vol"] > 1.2 and price_trend == "下跌":
        signal = "放量下跌——空方主導，賣壓沉重，訊號偏空。"
    else:
        signal = "縮量下跌——賣壓趨於枯竭，跌勢可能減弱，但不代表反轉。"
    return (
        f'<div class="ta-ind">\n'
        f'  <div class="ta-ind-header"><span class="ta-ind-icon">📊</span>'
        f'<span class="ta-ind-name">本週教學：成交量分析</span></div>\n'
        f'  <div class="ta-ind-body">\n'
        f'    <strong>概念：</strong>成交量是市場「參與熱度」的溫度計。量能必須配合價格走勢才有意義——上漲要放量、下跌要縮量才是健康格局；上漲縮量或下跌放量都是警訊。<br><br>\n'
        f'    <strong>關鍵公式：</strong>相對量 = 今日成交量 ÷ 20日均量。&gt;1.5 代表異常放量，&lt;0.5 代表異常縮量。<br><br>\n'
        f'    <strong>{sym} 近 5 日成交量（20日均量 {fmt_vol(ind["avg_vol"])}）：</strong>\n'
        f'    <div class="ta-calc-box">{rows}──────────────────<br>\n今日相對量 = {fmt_vol(ind["vol"])} ÷ {fmt_vol(ind["avg_vol"])} = <strong style="color:#79c0ff">{ind["rel_vol"]}x</strong></div>\n'
        f'    <strong>現況：</strong>{signal}<br>\n'
        f'    <div class="ta-tip">📌 <strong>實戰口訣：</strong>量是價的先行指標。放量突破關鍵壓力，才是有效突破；縮量突破往往假突破。</div>\n'
        f'  </div>\n</div>\n'
    )

def lesson_macd(stock, ind, p):
    sym = stock["symbol"]
    hist_dir = "連續擴大" if ind["hist_5"][-1] > ind["hist_5"][0] else "連續縮小"
    h5_rows = " → ".join(f"{h:+.3f}" for h in ind["hist_5"])
    if ind["golden"]:
        cross = "⚡ <strong style='color:var(--green)'>本週出現金叉！</strong>MACD 線由下穿上突破訊號線——趨勢可能由空轉多，是較強烈的買入訊號。"
    elif ind["dead"]:
        cross = "⚡ <strong style='color:var(--red)'>本週出現死叉！</strong>MACD 線由上穿下跌破訊號線——趨勢可能由多轉空，需提高警覺。"
    elif ind["hist"] > 0:
        cross = f"MACD 柱狀圖為正（+{ind['hist']}），多方動能仍在，但需觀察是否持續{hist_dir}。"
    else:
        cross = f"MACD 柱狀圖為負（{ind['hist']}），空方動能主導，需觀察柱狀圖是否開始縮小（動能減弱）。"
    return (
        f'<div class="ta-ind">\n'
        f'  <div class="ta-ind-header"><span class="ta-ind-icon">🔄</span>'
        f'<span class="ta-ind-name">本週教學：MACD 趨勢轉折</span></div>\n'
        f'  <div class="ta-ind-body">\n'
        f'    <strong>概念：</strong>MACD 用兩條不同速度的均線之差，來捕捉趨勢的轉折時機。它由三個部分組成：<br>\n'
        f'    ・MACD 線 = EMA(12) − EMA(26)　　（快線 − 慢線）<br>\n'
        f'    ・訊號線 = EMA(9) of MACD 線　　（MACD 的均線）<br>\n'
        f'    ・柱狀圖 = MACD 線 − 訊號線　　（動能強弱的直觀呈現）<br><br>\n'
        f'    <strong>{sym} 實際數值：</strong>\n'
        f'    <div class="ta-calc-box">MACD 線 = <strong>{ind["macd"]:+.3f}</strong><br>\n訊號線 = <strong>{ind["signal"]:+.3f}</strong><br>\n柱狀圖 = <strong style="color:{"var(--green)" if ind["hist"] > 0 else "var(--red)"}">{ind["hist"]:+.3f}</strong><br>\n近 5 日柱狀圖趨勢：{h5_rows}</div>\n'
        f'    <strong>現況：</strong>{cross}<br>\n'
        f'    <div class="ta-tip">📌 <strong>金叉 / 死叉：</strong>MACD 線穿越訊號線時產生買賣訊號。金叉偏多、死叉偏空。搭配柱狀圖觀察動能強弱更可靠。</div>\n'
        f'  </div>\n</div>\n'
    )

def lesson_bollinger(stock, ind, p):
    sym = stock["symbol"]
    if ind["bb_pos"] > 85:
        pos_text = f"股價在布林上軌（{p(ind['bb_up'])}）附近（位置 {ind['bb_pos']}%），短期超買，需警戒回調。"
    elif ind["bb_pos"] < 15:
        pos_text = f"股價在布林下軌（{p(ind['bb_lo'])}）附近（位置 {ind['bb_pos']}%），短期超賣，可能出現反彈。"
    else:
        pos_text = f"股價在布林通道中段（位置 {ind['bb_pos']}%），無明顯超買或超賣。"
    squeeze = "目前帶寬偏窄（{:.1f}%），可能即將出現方向性突破。".format(ind['bb_w']) if ind['bb_w'] < 8 else f"帶寬 {ind['bb_w']:.1f}%，正常波動範圍。"
    return (
        f'<div class="ta-ind">\n'
        f'  <div class="ta-ind-header"><span class="ta-ind-icon">〰️</span>'
        f'<span class="ta-ind-name">本週教學：布林通道（波動率）</span></div>\n'
        f'  <div class="ta-ind-body">\n'
        f'    <strong>概念：</strong>布林通道以 MA20 為中軌，向上下各加減 2 個標準差，形成動態的「正常波動區間」。股價偶爾觸碰上下軌是正常的，但長時間持續突破通道外才需特別關注。<br><br>\n'
        f'    <strong>公式：</strong>上軌 = MA20 + 2×標準差，下軌 = MA20 − 2×標準差<br><br>\n'
        f'    <strong>{sym} 實際數值：</strong>\n'
        f'    <div class="ta-calc-box">上軌（壓力）= <strong>{p(ind["bb_up"])}</strong><br>\n中軌（MA20）= <strong>{p(ind["ma20"])}</strong><br>\n下軌（支撐）= <strong>{p(ind["bb_lo"])}</strong><br>\n帶寬（波動率指標）= <strong>{ind["bb_w"]:.1f}%</strong><br>\n現價位置 = <strong style="color:#79c0ff">{ind["bb_pos"]:.0f}%</strong>（0%=下軌，100%=上軌）</div>\n'
        f'    <strong>現況：</strong>{pos_text} {squeeze}<br>\n'
        f'    <div class="ta-tip">📌 <strong>帶寬收縮（Squeeze）：</strong>帶寬縮到極低時，代表市場即將選擇方向。此時放量突破上軌看多，放量跌破下軌看空。</div>\n'
        f'  </div>\n</div>\n'
    )

def lesson_rsi_kd(stock, ind, p):
    sym = stock["symbol"]
    rd  = ind.get("rsi_detail", {})
    kd_signal = "K 線在 D 線上方，短期動能偏多" if ind["kd_k"] > ind["kd_d"] else "K 線在 D 線下方，短期動能偏空"
    kd_zone = "超買區（>80），注意高位鈍化" if ind["kd_k"] > 80 else ("超賣區（<20），注意低位反彈訊號" if ind["kd_k"] < 20 else "中性區間")
    return (
        f'<div class="ta-ind">\n'
        f'  <div class="ta-ind-header"><span class="ta-ind-icon">⚡</span>'
        f'<span class="ta-ind-name">本週教學：RSI ＋ KD 動能指標</span></div>\n'
        f'  <div class="ta-ind-body">\n'
        f'    <strong>RSI 複習：</strong>衡量 14 日內買方 vs 賣方的力道比，範圍 0–100。&gt;70 超買，&lt;30 超賣。<br>\n'
        f'    <strong>KD 指標（台股投資人最愛用！）：</strong>比 RSI 更敏感，用 9 日最高最低價的相對位置來衡量動能。<br><br>\n'
        f'    <strong>KD 公式：</strong><br>\n'
        f'    ・RSV = (今日收盤 − 9日最低) ÷ (9日最高 − 9日最低) × 100<br>\n'
        f'    ・K = 前K × 2/3 + 今日RSV × 1/3　（K 線，較快）<br>\n'
        f'    ・D = 前D × 2/3 + 今日K × 1/3　（D 線，較慢，為 K 的移動平均）<br><br>\n'
        f'    <strong>{sym} 實際數值：</strong>\n'
        f'    <div class="ta-calc-box">RSI(14) = <strong style="color:{"var(--red)" if ind["rsi"] > 70 else ("var(--green)" if ind["rsi"] < 30 else "inherit")}">{ind["rsi"]}</strong>　（上漲 {rd.get("up","?")} 天，下跌 {rd.get("dn","?")} 天）<br>\nKD-K = <strong>{ind["kd_k"]}</strong>　KD-D = <strong>{ind["kd_d"]}</strong><br>\nKD 所在區間：<strong>{kd_zone}</strong></div>\n'
        f'    <strong>現況：</strong>{kd_signal}。RSI 與 KD 方向{"一致，訊號更可靠" if (ind["rsi"] > 50) == (ind["kd_k"] > ind["kd_d"]) else "背離，需謹慎"}。<br>\n'
        f'    <div class="ta-tip">📌 <strong>RSI vs KD：</strong>RSI 較平滑適合看趨勢，KD 較敏感適合抓短線高低點。KD 在 20 以下出現黃金交叉（K 上穿 D）是常見的底部買入訊號。</div>\n'
        f'  </div>\n</div>\n'
    )

def lesson_candle(stock, ind, p):
    sym = stock["symbol"]
    rows = ""
    for c in ind["ohlc_5d"]:
        o, h, l, cl = c["open"], c["high"], c["low"], c["close"]
        chg  = round(cl - o, 2)
        sign = "▲" if chg >= 0 else "▼"
        col  = "var(--green)" if chg >= 0 else "var(--red)"
        pat  = identify_candle(o, h, l, cl)
        rows += (f'{c["date"]}　開 {p(o)}　高 {p(h)}　低 {p(l)}　收 {p(cl)}'
                 f'　<span style="color:{col}">{sign}{abs(chg):.2f}</span>　<em>{pat}</em><br>\n')
    return (
        f'<div class="ta-ind">\n'
        f'  <div class="ta-ind-header"><span class="ta-ind-icon">🕯️</span>'
        f'<span class="ta-ind-name">本週教學：K 線型態</span></div>\n'
        f'  <div class="ta-ind-body">\n'
        f'    <strong>概念：</strong>每根 K 線包含四個資訊——開盤價（O）、最高價（H）、最低價（L）、收盤價（C）。實體（開收之間）代表主力意志，上下影線代表買賣攻防的戰場。<br><br>\n'
        f'    <strong>常見型態：</strong><br>\n'
        f'    ・<strong>長紅 K</strong>：收盤遠高於開盤，多方強勢主導<br>\n'
        f'    ・<strong>錘子線</strong>：下影線長（跌後被買回），出現在低位是底部訊號<br>\n'
        f'    ・<strong>流星線</strong>：上影線長（漲後遭賣壓），出現在高位是頂部訊號<br>\n'
        f'    ・<strong>十字線</strong>：開收幾乎相等，多空膠著，可能轉折<br><br>\n'
        f'    <strong>{sym} 近 5 日 K 線：</strong>\n'
        f'    <div class="ta-calc-box" style="font-size:11px;">{rows}</div>\n'
        f'    <div class="ta-tip">📌 <strong>使用原則：</strong>K 線型態要搭配量能和均線趨勢才有意義。孤立的一根 K 線意義有限；連續 2–3 根組成的型態（如吞噬形態、晨星 / 夜星）更可靠。</div>\n'
        f'  </div>\n</div>\n'
    )

def lesson_sr(stock, ind, p):
    sym = stock["symbol"]
    price = ind["price"]
    dist_sup  = round((price - ind["support1"]) / price * 100, 1)
    dist_res  = round((ind["resistance1"] - price) / price * 100, 1)
    return (
        f'<div class="ta-ind">\n'
        f'  <div class="ta-ind-header"><span class="ta-ind-icon">🎯</span>'
        f'<span class="ta-ind-name">本週教學：支撐與壓力</span></div>\n'
        f'  <div class="ta-ind-body">\n'
        f'    <strong>概念：</strong>支撐是「股價下跌時遇到買盤阻擋的區間」，壓力是「股價上漲時遇到賣壓的區間」。這些區間一旦突破，往往會互換角色（舊支撐變新壓力，舊壓力變新支撐）。<br><br>\n'
        f'    <strong>如何判斷？</strong><br>\n'
        f'    ・近期多次反彈的低點 → 支撐區<br>\n'
        f'    ・近期多次受阻的高點 → 壓力區<br>\n'
        f'    ・重要均線（MA20、MA60）→ 動態支撐壓力<br>\n'
        f'    ・整數關卡（$200、$150 等）→ 心理支撐壓力<br><br>\n'
        f'    <strong>{sym} 關鍵價位（來自近 20 日最低 / 最高分布）：</strong>\n'
        f'    <div class="ta-calc-box">現價 = <strong>{p(price)}</strong><br>\n近期壓力 = <strong>{p(ind["resistance1"])}</strong>　（距現價 +{dist_res}%）<br>\n近期支撐 = <strong>{p(ind["support1"])}</strong>　（距現價 −{dist_sup}%）<br>\n52週低點支撐 = <strong>{p(ind["low52"])}</strong><br>\n52週高點壓力 = <strong>{p(ind["high52"])}</strong></div>\n'
        f'    <div class="ta-tip">📌 <strong>實戰口訣：</strong>支撐和壓力是「區間」而非「精確的線」。在支撐區出現止跌 + 縮量，才是有效支撐；在壓力區出現放量突破，才是有效突破。</div>\n'
        f'  </div>\n</div>\n'
    )

def lesson_fibo(stock, ind, p):
    sym   = stock["symbol"]
    price = ind["price"]
    lvls  = ind["fib_lvls"]
    rows  = "\n".join(f'{k}　→　<strong>{p(v)}</strong>{"　← 現價附近" if abs(price - v) < abs(price * 0.02) else ""}<br>'
                      for k, v in lvls.items())
    return (
        f'<div class="ta-ind">\n'
        f'  <div class="ta-ind-header"><span class="ta-ind-icon">🌀</span>'
        f'<span class="ta-ind-name">本週教學：費波納契回撤</span></div>\n'
        f'  <div class="ta-ind-body">\n'
        f'    <strong>概念：</strong>費波納契數列（1,1,2,3,5,8,13…）中相鄰數之比趨近黃金比例 0.618。技術分析借用這些比例來預測股價回調或反彈後可能遇到的支撐壓力位。<br><br>\n'
        f'    <strong>用法：</strong>找一個明確的波段（從波段低點到波段高點），計算各比例位置。常用的回撤位是 38.2%、50%、61.8%——股價回調到這些位置往往會有支撐。<br><br>\n'
        f'    <strong>{sym} 費波納契回撤（3 個月波段：{p(ind["fib_low"])} → {p(ind["fib_high"])}）：</strong>\n'
        f'    <div class="ta-calc-box">{rows}──────────────────<br>\n現價 <strong style="color:#79c0ff">{p(price)}</strong></div>\n'
        f'    <div class="ta-tip">📌 <strong>黃金分割：</strong>61.8% 回撤位是最重要的費波支撐。若股價回撤超過 61.8% 仍無止跌，則波段結構可能已被破壞，需重新評估趨勢。</div>\n'
        f'  </div>\n</div>\n'
    )

def lesson_rs(stock, ind, p):
    sym    = stock["symbol"]
    ret3   = ind.get("ret_3m")
    spy3   = ind.get("spy_ret")
    rs     = ind.get("rs_vs_spy")
    ret3_s = f"{ret3:+.1f}%" if ret3 is not None else "N/A"
    spy3_s = f"{spy3:+.1f}%" if spy3 is not None else "N/A"
    rs_s   = f"{rs:+.1f}%" if rs is not None else "N/A"
    rs_col = "var(--green)" if (rs is not None and rs > 0) else "var(--red)"
    rs_txt = (f"過去 3 個月 {sym} 報酬 {ret3_s}，大盤（SPY）報酬 {spy3_s}，"
              f"{'跑贏大盤 ' + rs_s if rs and rs > 0 else '跑輸大盤 ' + rs_s}。")
    return (
        f'<div class="ta-ind">\n'
        f'  <div class="ta-ind-header"><span class="ta-ind-icon">📍</span>'
        f'<span class="ta-ind-name">本週教學：相對強弱 vs 大盤</span></div>\n'
        f'  <div class="ta-ind-body">\n'
        f'    <strong>概念：</strong>個股表現必須跟大盤（SPY / QQQ）比較才有意義。若大盤漲 10% 而個股只漲 3%，雖然「賺錢了」，但其實跑輸大盤——你的資金配置效率偏低。<br><br>\n'
        f'    <strong>相對強弱（RS）= 個股報酬 − 大盤報酬</strong><br>\n'
        f'    ・RS &gt; 0：跑贏大盤，選股有效，可繼續持有<br>\n'
        f'    ・RS &lt; 0：跑輸大盤，需評估是否繼續持有還是換股<br><br>\n'
        f'    <strong>{sym} 實際計算（近 3 個月）：</strong>\n'
        f'    <div class="ta-calc-box">{sym} 3 個月報酬 = <strong>{ret3_s}</strong><br>\nSPY（美國大盤）3 個月報酬 = <strong>{spy3_s}</strong><br>\n──────────────────────────<br>\n相對強弱（RS）= <strong style="color:{rs_col}">{rs_s}</strong></div>\n'
        f'    <strong>現況：</strong>{rs_txt}<br>\n'
        f'    <div class="ta-tip">📌 <strong>選股原則：</strong>長期跑贏大盤的股票往往有業績驅動；若一支股票持續跑輸，先找原因——是產業弱勢、個股問題，還是暫時落後後的均值回歸機會？</div>\n'
        f'  </div>\n</div>\n'
    )

def lesson_atr(stock, ind, p):
    sym    = stock["symbol"]
    price  = ind["price"]
    atr    = ind["atr"]
    atr_pct= ind["atr_pct"]
    sl_1x  = round(price - 1.5 * atr, 2)
    sl_2x  = round(price - 2.0 * atr, 2)
    # 以 1% 帳戶風險 + 2×ATR 停損計算部位
    risk_per_share = round(2 * atr, 2)
    shares_10k     = int(10000 * 0.01 / risk_per_share) if risk_per_share > 0 else 0
    return (
        f'<div class="ta-ind">\n'
        f'  <div class="ta-ind-header"><span class="ta-ind-icon">🛡️</span>'
        f'<span class="ta-ind-name">本週教學：ATR 與風險管理</span></div>\n'
        f'  <div class="ta-ind-body">\n'
        f'    <strong>概念：</strong>ATR（平均真實波動範圍）衡量股票「每天平均波動多少」，幫助你設定合理的停損點和部位大小。停損設太近容易被洗出場，設太遠虧損又太大——ATR 幫你找到平衡點。<br><br>\n'
        f'    <strong>公式：</strong>真實波動（TR）= max（高−低、｜高−昨收｜、｜低−昨收｜），ATR = 14 日平均 TR。<br><br>\n'
        f'    <strong>{sym} 實際數值：</strong>\n'
        f'    <div class="ta-calc-box">ATR(14) = <strong style="color:#79c0ff">{p(atr)}</strong>（約現價的 {atr_pct:.1f}%）<br>\n建議停損位（1.5×ATR）= <strong>{p(sl_1x)}</strong><br>\n建議停損位（2.0×ATR）= <strong>{p(sl_2x)}</strong><br>\n──────────────────────<br>\n部位試算：帳戶 10 萬元，承擔 1% 風險（1,000 元），<br>\n以 2×ATR（{p(risk_per_share)}）為停損，最多買 <strong>{shares_10k} 股</strong></div>\n'
        f'    <div class="ta-tip">📌 <strong>風險管理鐵律：</strong>單次交易最多承擔帳戶 1–2% 的資金風險。ATR 停損 + 部位計算讓你在「被證明錯誤之前」不會虧太多。</div>\n'
        f'  </div>\n</div>\n'
    )

def lesson_toolbox(stock, ind, p):
    """第 11 週起的工具箱綜合分析"""
    sym = stock["symbol"]
    # 評分系統
    score = 0
    signals = []
    if ind["ma5"] > ind["ma20"] > ind["ma60"]:
        score += 2; signals.append("✅ 均線多頭排列")
    elif ind["ma5"] < ind["ma20"] < ind["ma60"]:
        score -= 2; signals.append("❌ 均線空頭排列")
    else:
        signals.append("⚠️ 均線方向混沌")
    if 60 <= ind["rsi"] <= 75:
        score += 1; signals.append("✅ RSI 健康偏多（60–75）")
    elif ind["rsi"] > 75:
        signals.append(f"⚠️ RSI 超買警戒（{ind['rsi']}）")
    elif ind["rsi"] < 30:
        score -= 1; signals.append(f"⚠️ RSI 超賣（{ind['rsi']}）")
    if ind["hist"] > 0:
        score += 1; signals.append("✅ MACD 柱狀圖正值（動能向上）")
    else:
        score -= 1; signals.append("❌ MACD 柱狀圖負值（動能向下）")
    if ind["kd_k"] > ind["kd_d"] and ind["kd_k"] < 80:
        score += 1; signals.append("✅ KD 黃金交叉，K>D")
    elif ind["kd_k"] < ind["kd_d"] and ind["kd_k"] > 20:
        score -= 1; signals.append("❌ KD 死亡交叉，K<D")
    if ind["rel_vol"] > 1.2 and ind["ma5"] > ind["ma20"]:
        score += 1; signals.append(f"✅ 放量上漲（量比 {ind['rel_vol']}x）")
    elif ind["rel_vol"] > 1.2 and ind["ma5"] < ind["ma20"]:
        score -= 1; signals.append(f"❌ 放量下跌（量比 {ind['rel_vol']}x）")
    rs = ind.get("rs_vs_spy")
    if rs and rs > 5:
        score += 1; signals.append(f"✅ 跑贏大盤 +{rs}%")
    elif rs and rs < -5:
        score -= 1; signals.append(f"❌ 跑輸大盤 {rs}%")
    signals_html = "\n".join(f"<div>　{s}</div>" for s in signals)
    overall = ("積極看多" if score >= 4 else
               "偏多觀察" if score >= 2 else
               "中性觀望" if score >= 0 else
               "偏空謹慎" if score >= -2 else "積極看空")
    return (
        f'<div class="ta-ind">\n'
        f'  <div class="ta-ind-header"><span class="ta-ind-icon">🔮</span>'
        f'<span class="ta-ind-name">工具箱綜合分析</span></div>\n'
        f'  <div class="ta-ind-body">\n'
        f'    <strong>多維度評分（MA + RSI + KD + MACD + 量能 + 相對強弱）：</strong>\n'
        f'    <div class="ta-calc-box">{signals_html}<br>\n綜合評分 = <strong style="color:{"var(--green)" if score > 0 else ("var(--red)" if score < 0 else "inherit")}">{score:+d} 分</strong>　→　<strong>{overall}</strong></div>\n'
        f'    <div class="ta-tip">📌 <strong>說明：</strong>此評分系統僅供參考，每個維度等權計分（+1 多方訊號，−1 空方訊號）。評分越高代表技術面越多訊號共振偏多。</div>\n'
        f'  </div>\n</div>\n'
    )

LESSON_FN = {
    "ma":        lesson_ma,
    "volume":    lesson_volume,
    "macd":      lesson_macd,
    "bollinger": lesson_bollinger,
    "rsi_kd":    lesson_rsi_kd,
    "candle":    lesson_candle,
    "sr":        lesson_sr,
    "fibo":      lesson_fibo,
    "rs":        lesson_rs,
    "atr":       lesson_atr,
    "toolbox":   lesson_toolbox,
}


# ════════════════════════════════════════════════════════════════════
# 快照、敘述、情緒、結論生成器
# ════════════════════════════════════════════════════════════════════
def _snap(label, val, sub, cls=""):
    val_cls = f"ta-snap-val {cls}" if cls else "ta-snap-val"
    sub = sub.replace("<", "&lt;").replace(">", "&gt;")
    return (f'<div class="ta-snap-item"><div class="ta-snap-label">{label}</div>'
            f'<div class="{val_cls}">{val}</div>'
            f'<div class="ta-snap-sub">{sub}</div></div>')

def generate_snapshot(stock, ind, p):
    import json as _json
    mkt   = stock["market"]
    price = ind["price"]

    # ── 折線圖 HTML ──
    chart_id = f"taLineChart_{stock['symbol'].replace('-','')}"
    labels   = _json.dumps(ind.get("chart_dates",  []))
    c_closes = _json.dumps(ind.get("chart_closes", []))
    c_ma5    = _json.dumps(ind.get("chart_ma5",    []))
    c_ma20   = _json.dumps(ind.get("chart_ma20",   []))
    c_ma60   = _json.dumps(ind.get("chart_ma60",   []))
    chart_html = (
        f'<div class="ta-chart-wrap">'
        f'<canvas id="{chart_id}" height="160"></canvas>'
        f'<script>window.__taCharts=window.__taCharts||{{}};'
        f'window.__taCharts["{chart_id}"]={{type:"line",data:{{labels:{labels},datasets:['
        f'{{label:"收盤",data:{c_closes},borderColor:"rgba(200,200,220,.9)",borderWidth:1.5,pointRadius:0,tension:.3,fill:false,order:1}},'
        f'{{label:"MA5", data:{c_ma5}, borderColor:"#f0c040",borderWidth:1.5,pointRadius:0,tension:.3,fill:false,borderDash:[3,2],spanGaps:true,order:2}},'
        f'{{label:"MA20",data:{c_ma20},borderColor:"#56d364",borderWidth:1.5,pointRadius:0,tension:.3,fill:false,borderDash:[5,3],spanGaps:true,order:3}},'
        f'{{label:"MA60",data:{c_ma60},borderColor:"#f85149",borderWidth:1.5,pointRadius:0,tension:.3,fill:false,borderDash:[8,4],spanGaps:true,order:4}}'
        f']}},options:{{responsive:true,interaction:{{mode:"index",intersect:false}},'
        f'plugins:{{legend:{{display:true,position:"top",labels:{{color:"#8b949e",font:{{size:10}},boxWidth:16,padding:10}}}},'
        f'tooltip:{{backgroundColor:"rgba(22,27,34,.95)",titleColor:"#c9d1d9",bodyColor:"#8b949e",padding:8}}}},'
        f'scales:{{x:{{ticks:{{color:"#8b949e",maxTicksLimit:8,font:{{size:10}}}},grid:{{color:"rgba(139,148,158,.1)"}}}},'
        f'y:{{ticks:{{color:"#8b949e",font:{{size:10}}}},grid:{{color:"rgba(139,148,158,.1)"}}}}}}}};'
        f'</script></div>\n'
    )

    # ── 指標格子 ──
    items = []
    items.append(_snap("現價", p(price), f"52週 {ind['w52pct']}% 位置"))
    ma5c  = "snap-bull" if price > ind["ma5"]  else "snap-bear"
    ma20c = "snap-bull" if price > ind["ma20"] else "snap-bear"
    ma60c = "snap-bull" if price > ind["ma60"] else "snap-bear"
    items.append(_snap("MA5",  p(ind["ma5"]),  "↑ 站上" if price > ind["ma5"]  else "↓ 跌破", ma5c))
    items.append(_snap("MA20", p(ind["ma20"]), "↑ 站上" if price > ind["ma20"] else "↓ 跌破", ma20c))
    items.append(_snap("MA60", p(ind["ma60"]), "↑ 站上" if price > ind["ma60"] else "↓ 跌破", ma60c))
    rsic = "snap-bear" if ind["rsi"] > 70 else ("snap-bull" if ind["rsi"] < 30 else "")
    rsi_sub = "超買警戒" if ind["rsi"] > 70 else ("超賣區間" if ind["rsi"] < 30 else "健康區間" if ind["rsi"] > 50 else "偏弱區間")
    items.append(_snap("RSI(14)", str(ind["rsi"]), rsi_sub, rsic))
    kdc = "snap-bull" if ind["kd_k"] > ind["kd_d"] else "snap-bear"
    items.append(_snap("KD", f"K{ind['kd_k']}/D{ind['kd_d']}", "K>D 偏多" if ind["kd_k"] > ind["kd_d"] else "K<D 偏空", kdc))
    histc = "snap-bull" if ind["hist"] > 0 else "snap-bear"
    items.append(_snap("MACD柱", f"{ind['hist']:+.3f}", "動能向上" if ind["hist"] > 0 else "動能向下", histc))
    bbc = "snap-bear" if ind["bb_pos"] > 85 else ("snap-bull" if ind["bb_pos"] < 15 else "")
    items.append(_snap("布林位置", f"{ind['bb_pos']:.0f}%", "近上軌" if ind["bb_pos"] > 85 else ("近下軌" if ind["bb_pos"] < 15 else "中段"), bbc))
    items.append(_snap("ATR(14)", p(ind["atr"]), f"±{ind['atr_pct']:.1f}%/日"))
    rvc = "snap-bull" if ind["rel_vol"] > 1.2 else ("snap-bear" if ind["rel_vol"] < 0.6 else "")
    items.append(_snap("成交量比", f"{ind['rel_vol']}x", "放量" if ind["rel_vol"] > 1.2 else ("縮量" if ind["rel_vol"] < 0.6 else "正常"), rvc))
    rs = ind.get("rs_vs_spy")
    if rs is not None:
        rsc = "snap-bull" if rs > 0 else "snap-bear"
        items.append(_snap("vs大盤(3M)", f"{rs:+.1f}%", "跑贏" if rs > 0 else "跑輸", rsc))
    grid = "\n".join(items)
    return (
        f'<div class="ta-ind">\n'
        f'  <div class="ta-ind-header"><span class="ta-ind-icon">⚡</span>'
        f'<span class="ta-ind-name">技術面快照（全指標一覽）</span></div>\n'
        f'  {chart_html}'
        f'  <div class="ta-snap-grid">\n{grid}\n  </div>\n</div>\n'
    )

def _gemini_narrative(stock, ind):
    """用 Gemini API 生成動態多空論點（需環境變數 GEMINI_API_KEY）"""
    import os, re as _re
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        import time
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        mkt  = stock["market"]
        p    = lambda v: fp(v, mkt)
        ma_a = ("多頭排列" if ind["ma5"] > ind["ma20"] > ind["ma60"]
                else "空頭排列" if ind["ma5"] < ind["ma20"] < ind["ma60"]
                else "均線糾結")
        rsi_s = "超買" if ind["rsi"] > 70 else ("超賣" if ind["rsi"] < 30 else "健康")
        prompt = f"""你是專業投資分析師，為台灣投資人分析持股。
根據以下最新技術指標，用繁體中文生成投資脈絡分析。

股票：{stock['symbol']} / {stock['name']}（{stock['sector']}）
說明：{stock['desc']}

技術指標（本週實際數值）：
均線排列：{ma_a}（MA5 {p(ind['ma5'])} / MA20 {p(ind['ma20'])} / MA60 {p(ind['ma60'])}）
RSI：{ind['rsi']}（{rsi_s}）　MACD 柱：{ind['hist']:+.3f}　KD：K {ind['kd_k']} / D {ind['kd_d']}
布林位置：{ind['bb_pos']:.0f}%　52週位置：{ind['w52pct']}%

請輸出以下 7 行，不要任何其他文字：
多方1：[多方論點，25字內]
多方2：[多方論點，25字內]
多方3：[多方論點，25字內]
空方1：[空方風險，25字內]
空方2：[空方風險，25字內]
空方3：[空方風險，25字內]
本週關注：[本週最重要的關注焦點與催化劑，40字內]"""
        # 帶重試的呼叫（503 最多重試3次）
        response_text = None
        for attempt in range(3):
            try:
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_budget=0)
                    )
                )
                response_text = resp.text
                break
            except Exception as e:
                if "503" in str(e) and attempt < 2:
                    time.sleep(20 * (attempt + 1))
                else:
                    raise
        if response_text is None:
            return None
        lines = {}
        for line in response_text.strip().split('\n'):
            if '：' in line:
                k, v = line.split('：', 1)
                lines[k.strip()] = v.strip()
        bull  = [lines.get("多方1","—"), lines.get("多方2","—"), lines.get("多方3","—")]
        bear  = [lines.get("空方1","—"), lines.get("空方2","—"), lines.get("空方3","—")]
        watch = lines.get("本週關注", "—")
        print(f"  ✓ Gemini 敘述生成成功（{stock['symbol']}）")
        return bull, bear, watch
    except Exception as e:
        print(f"  ✗ Gemini 敘述失敗（{stock['symbol']}）：{e}，改用靜態備援")
        return None


def generate_narrative(stock, ind=None):
    # 優先嘗試 Gemini 動態生成
    if ind is not None:
        g = _gemini_narrative(stock, ind)
        if g:
            bull, bear, watch = g
            bull_rows = "\n".join(f'<div class="ta-bb-item">{b}</div>' for b in bull)
            bear_rows = "\n".join(f'<div class="ta-bb-item">{b}</div>' for b in bear)
            sym = stock["symbol"]
            return (
                f'<div class="ta-ind">\n'
                f'  <div class="ta-ind-header"><span class="ta-ind-icon">🏢</span>'
                f'<span class="ta-ind-name">個股脈絡：{sym} · {stock["sector"]}</span></div>\n'
                f'  <div class="ta-ind-body">\n'
                f'    <div style="font-size:12px;color:var(--text3);margin-bottom:8px;">{stock["desc"]}</div>\n'
                f'    <div style="font-size:10px;color:var(--blue);margin-bottom:8px;">🤖 由 Gemini AI 根據本週指標動態生成</div>\n'
                f'    <div class="ta-bb-grid">\n'
                f'      <div class="ta-bull-box"><div class="ta-bb-title">多方論點</div>{bull_rows}</div>\n'
                f'      <div class="ta-bear-box"><div class="ta-bb-title">空方風險</div>{bear_rows}</div>\n'
                f'    </div>\n'
                f'    <div class="ta-watch-box"><strong>本週關注：</strong>{watch}</div>\n'
                f'  </div>\n</div>\n'
            )
    # 靜態備援（Gemini 不可用時）
    sym  = stock["symbol"]
    narr = NARRATIVES.get(sym, {})
    bull = narr.get("bull", ["—"])
    bear = narr.get("bear", ["—"])
    watch = narr.get("watch", "—")
    cat   = narr.get("catalyst", "—")
    bull_rows = "\n".join(f'<div class="ta-bb-item">{b}</div>' for b in bull)
    bear_rows = "\n".join(f'<div class="ta-bb-item">{b}</div>' for b in bear)
    return (
        f'<div class="ta-ind">\n'
        f'  <div class="ta-ind-header"><span class="ta-ind-icon">🏢</span>'
        f'<span class="ta-ind-name">個股脈絡：{sym} · {stock["sector"]}</span></div>\n'
        f'  <div class="ta-ind-body">\n'
        f'    <div style="font-size:12px;color:var(--text3);margin-bottom:8px;">{stock["desc"]}</div>\n'
        f'    <div class="ta-bb-grid">\n'
        f'      <div class="ta-bull-box"><div class="ta-bb-title">多方論點</div>{bull_rows}</div>\n'
        f'      <div class="ta-bear-box"><div class="ta-bb-title">空方風險</div>{bear_rows}</div>\n'
        f'    </div>\n'
        f'    <div class="ta-watch-box"><strong>本週關注：</strong>{watch}<br><strong>催化劑：</strong>{cat}</div>\n'
        f'  </div>\n</div>\n'
    )

def get_sentiment(ind):
    score = 0
    if ind["ma5"] > ind["ma20"] > ind["ma60"]: score += 2
    elif ind["ma5"] < ind["ma20"] < ind["ma60"]: score -= 2
    if 55 <= ind["rsi"] <= 75: score += 1
    elif ind["rsi"] > 75: score += 0
    elif ind["rsi"] < 35: score -= 1
    if ind["hist"] > 0: score += 1
    else: score -= 1
    if ind["kd_k"] > ind["kd_d"]: score += 1
    else: score -= 1
    rs = ind.get("rs_vs_spy")
    if rs and rs > 3: score += 1
    elif rs and rs < -3: score -= 1
    if score >= 4:   return "sent-bull", "積極看多"
    if score >= 2:   return "sent-watch", "偏多觀察"
    if score >= 0:   return "sent-neut", "中性觀望"
    if score >= -2:  return "sent-watch", "偏空謹慎"
    return "sent-bear", "積極看空"


# ════════════════════════════════════════════════════════════════════
# 主卡片生成
# ════════════════════════════════════════════════════════════════════
def generate_ta_card(stock, ind, week_num, date_str, lesson):
    sym     = stock["symbol"]
    name    = stock["name"]
    sector  = stock["sector"]
    mkt     = stock["market"]
    p       = lambda v: fp(v, mkt)
    sc, sl  = get_sentiment(ind)
    progress = get_progress_str(stock)
    next_sym = get_preview_name(sym)

    lesson_html   = LESSON_FN[lesson["id"]](stock, ind, p)
    snapshot_html = generate_snapshot(stock, ind, p)
    narrative_html = generate_narrative(stock, ind)

    # 本週結論（基於技術面綜合）
    if ind["ma5"] > ind["ma20"] > ind["ma60"]:
        ma_note = "均線多頭排列，趨勢偏多"
    elif ind["ma5"] < ind["ma20"] < ind["ma60"]:
        ma_note = "均線空頭排列，趨勢偏空"
    else:
        ma_note = "均線方向混沌，等待整理"
    rsi_note = f"RSI {ind['rsi']}（{'超買警戒' if ind['rsi'] > 70 else '超賣區間' if ind['rsi'] < 30 else '健康區間'}）"
    macd_note = "MACD 動能向上" if ind["hist"] > 0 else "MACD 動能向下"
    rs = ind.get("rs_vs_spy")
    rs_note = f"vs 大盤 {rs:+.1f}%" if rs is not None else ""

    hist_summary = f"{sl} · {ma_note} · {rsi_note}"

    card = (
        "    <!-- TA_CARD_START -->\n"
        "    <div class=\"ta-card\">\n"
        "      <div class=\"ta-header\">\n"
        "        <div class=\"ta-left\">\n"
        f"          <div class=\"ta-week-badge\">第 {week_num} 週 · {lesson['icon']} {lesson['name']}</div>\n"
        f"          <div class=\"ta-ticker\">{sym} <span class=\"ta-name\">{name} · {sector}</span></div>\n"
        f"          <div class=\"ta-subtitle\">{stock['desc']}</div>\n"
        "        </div>\n"
        f"        <div class=\"ta-sentiment {sc}\">{sl}</div>\n"
        "      </div>\n"
        "      <div class=\"ta-indicators\">\n"
        f"{lesson_html}"
        f"{snapshot_html}"
        f"{narrative_html}"
        "        <div class=\"ta-summary\">\n"
        f"          <div class=\"ta-summary-title\">🎯 本週結論：{sym} 怎麼看？</div>\n"
        "          <div class=\"ta-summary-body\">\n"
        f"            {ma_note} · {rsi_note} · {macd_note}" + (f" · {rs_note}" if rs_note else "") + "<br><br>\n"
        f"            <strong>學習要點：</strong>今週介紹的「{lesson['name']}」是技術分析工具箱的重要一環。持續累積，等到 11 週後你就能同時使用所有工具做完整判斷。\n"
        "          </div>\n"
        "        </div>\n"
        "      </div>\n"
        f"      <div class=\"ta-footer\">每週一更新 · {date_str} · {progress} · 下週：{next_sym}</div>\n"
        "    </div>\n"
        "    <!-- TA_CARD_END -->\n"
    )
    return card, hist_summary


# ════════════════════════════════════════════════════════════════════
# 歷史紀錄列（可展開）
# ════════════════════════════════════════════════════════════════════
def generate_hist_row(entry_id, week_num, stock, date_str, summary, card_inner_html=''):
    sym  = stock["symbol"] if isinstance(stock, dict) else stock
    name = stock.get("name", sym) if isinstance(stock, dict) else sym
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


# ════════════════════════════════════════════════════════════════════
# HTML 更新
# ════════════════════════════════════════════════════════════════════
def update_html(new_card_html, hist_row_html):
    with open(INDEX_FILE, encoding="utf-8") as f:
        html = f.read()
    old_pat = r'    <!-- TA_CARD_START -->.*?    <!-- TA_CARD_END -->\n'
    html = re.sub(old_pat, new_card_html, html, flags=re.DOTALL)
    html = html.replace(
        '      <!-- HIST_ROWS_START -->',
        f'      <!-- HIST_ROWS_START -->\n{hist_row_html}'
    )
    html = re.sub(r'\s*<div class="ta-history-empty"[^>]*>.*?</div>', '', html, flags=re.DOTALL)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("  index.html 已更新")


# ════════════════════════════════════════════════════════════════════
# Backfill：為舊版歷史記錄補上折線圖
# ════════════════════════════════════════════════════════════════════
def _build_chart_html(sym, ind):
    import json as _json
    chart_id = f"taLineChart_{sym.replace('-', '')}_bf"
    labels   = _json.dumps(ind.get("chart_dates",  []))
    c_closes = _json.dumps(ind.get("chart_closes", []))
    c_ma5    = _json.dumps(ind.get("chart_ma5",    []))
    c_ma20   = _json.dumps(ind.get("chart_ma20",   []))
    c_ma60   = _json.dumps(ind.get("chart_ma60",   []))
    return (
        f'<div class="ta-chart-wrap">'
        f'<canvas id="{chart_id}" height="160"></canvas>'
        f'<script>window.__taCharts=window.__taCharts||{{}};'
        f'window.__taCharts["{chart_id}"]={{type:"line",data:{{labels:{labels},datasets:['
        f'{{label:"收盤",data:{c_closes},borderColor:"rgba(200,200,220,.9)",borderWidth:1.5,pointRadius:0,tension:.3,fill:false,order:1}},'
        f'{{label:"MA5", data:{c_ma5}, borderColor:"#f0c040",borderWidth:1.5,pointRadius:0,tension:.3,fill:false,borderDash:[3,2],spanGaps:true,order:2}},'
        f'{{label:"MA20",data:{c_ma20},borderColor:"#56d364",borderWidth:1.5,pointRadius:0,tension:.3,fill:false,borderDash:[5,3],spanGaps:true,order:3}},'
        f'{{label:"MA60",data:{c_ma60},borderColor:"#f85149",borderWidth:1.5,pointRadius:0,tension:.3,fill:false,borderDash:[8,4],spanGaps:true,order:4}}'
        f']}},options:{{responsive:true,interaction:{{mode:"index",intersect:false}},'
        f'plugins:{{legend:{{display:true,position:"top",labels:{{color:"#8b949e",font:{{size:10}},boxWidth:16,padding:10}}}},'
        f'tooltip:{{backgroundColor:"rgba(22,27,34,.95)",titleColor:"#c9d1d9",bodyColor:"#8b949e",padding:8}}}},'
        f'scales:{{x:{{ticks:{{color:"#8b949e",maxTicksLimit:8,font:{{size:10}}}},grid:{{color:"rgba(139,148,158,.1)"}}}},'
        f'y:{{ticks:{{color:"#8b949e",font:{{size:10}}}},grid:{{color:"rgba(139,148,158,.1)"}}}}}}}};'
        f'</script></div>\n  '
    )


def backfill_charts():
    """為歷史記錄中缺少折線圖的 TA 卡片補上 Chart.js 圖表"""
    with open(INDEX_FILE, encoding="utf-8") as f:
        html = f.read()

    # 找所有 hist-entry 的位置（倒序處理，避免字串位移）
    entry_pat = re.compile(r'<div class="ta-hist-entry" id="(hist-\d+)">')
    matches   = list(entry_pat.finditer(html))
    if not matches:
        print("無歷史記錄，無需 backfill")
        return

    modified = False
    for i in range(len(matches) - 1, -1, -1):
        m     = matches[i]
        eid   = m.group(1)
        start = m.start()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        block = html[start:end]

        if "ta-chart-wrap" in block:
            print(f"  {eid}: 已有圖表，略過")
            continue

        sym_m = re.search(r'class="ta-ticker">(\S+)\s*<span', block)
        if not sym_m:
            print(f"  {eid}: 找不到代號，略過")
            continue
        sym   = sym_m.group(1)
        stock = next((s for s in ROTATION if s["symbol"] == sym), None)
        if not stock:
            print(f"  {eid}: {sym} 不在輪替清單，略過")
            continue

        print(f"  {eid}: 為 {sym} 抓取數據...")
        ind = fetch_indicators(stock)
        if ind is None:
            print(f"  {eid}: 無法取得指標，略過")
            continue

        chart_html = _build_chart_html(sym, ind)

        # 在「技術面快照」的 ta-ind-header 後、ta-snap-grid 前插入圖表
        new_block = re.sub(
            r'(技術面快照（全指標一覽）</span></div>)\n(\s*<div class="ta-snap-grid">)',
            lambda mo: mo.group(1) + "\n  " + chart_html + mo.group(2),
            block,
            count=1
        )

        if new_block != block:
            html = html[:start] + new_block + html[end:]
            print(f"  {eid}: ✓ {sym} 圖表注入成功")
            modified = True
        else:
            print(f"  {eid}: ⚠ 找不到注入位置，略過")

    if modified:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        print("✅ index.html 已更新（backfill 完成）")
    else:
        print("✅ 所有歷史記錄均已有圖表，無需更新")


# ════════════════════════════════════════════════════════════════════
# 主程式
# ════════════════════════════════════════════════════════════════════
def main():
    import os
    if os.environ.get("BACKFILL_CHARTS") == "true":
        print("🔄 BACKFILL_CHARTS 模式：補生成歷史記錄圖表")
        backfill_charts()
        return

    state    = load_state()
    next_stk = get_next_stock(state["covered"])
    week_num = state["week"] + 1

    # 決定本週教學主題
    prev_idx    = state.get("lesson_idx", -1)
    lesson_idx  = min(prev_idx + 1, len(CURRICULUM) - 1)  # 10 以後永久停在 toolbox
    lesson      = CURRICULUM[lesson_idx]
    date_str    = datetime.now(TZ_TW).strftime("%Y/%m/%d")

    print(f"第 {week_num} 週：{next_stk['symbol']} {next_stk['name']}　教學主題：{lesson['name']}")

    ind = fetch_indicators(next_stk)
    if ind is None:
        print("無法取得指標，中止更新")
        return

    print(f"  價格 {ind['price']}，RSI {ind['rsi']}，KD {ind['kd_k']}/{ind['kd_d']}，MACD {ind['hist']:+.3f}")

    new_card, hist_summary = generate_ta_card(next_stk, ind, week_num, date_str, lesson)

    # 取得舊卡片資訊（存入歷史）
    with open(INDEX_FILE, encoding="utf-8") as f:
        old_html = f.read()
    m_week  = re.search(r'ta-week-badge">第 (\d+) 週', old_html)
    m_tick  = re.search(r'ta-ticker">(\S+) <span', old_html)
    m_date  = re.search(r'ta-footer">每週一更新 · (\d{4}/\d{2}/\d{2})', old_html)
    m_sent  = re.search(r'ta-sentiment\b[^>]+>([^<]+)', old_html)
    m_card  = re.search(r'<!-- TA_CARD_START -->(.*?)<!-- TA_CARD_END -->', old_html, flags=re.DOTALL)

    old_week     = int(m_week.group(1)) if m_week  else week_num - 1
    old_ticker   = m_tick.group(1)     if m_tick  else "—"
    old_date     = m_date.group(1)     if m_date  else "—"
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
        "lesson_idx":   lesson_idx,
        "last_updated": datetime.now(TZ_TW).strftime("%Y-%m-%d"),
    })
    print(f"完成！本週：{next_stk['symbol']}（{lesson['name']}），下週：{get_preview_name(next_stk['symbol'])}")


if __name__ == "__main__":
    main()
