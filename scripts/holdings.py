"""
holdings.py — 持股單一真相來源

所有持股（美股 / 台股）一律從 investment-ai 的 portfolio.json 衍生，
不再於各腳本、index.html 硬編碼，避免多份清單 drift。

  來源：https://raw.githubusercontent.com/ianian22493/investment-ai/main/data/portfolio.json
  （又瑄在另一個對話即時維護、每日刷價；此檔為公開 raw，故免 token）

隱私保護：portfolio.json 含現金 / 月薪 / 房產 / 房貸等敏感欄位，
本模組「只」萃取代號 / 名稱 / 股數 / 產業 / 策略，其餘一律不取、不外流。

用法：
    from holdings import load_holdings
    h = load_holdings()          # {'us': [...], 'tw': [...], '_updated': '...'}
    us_symbols = [s["symbol"] for s in h["us"]]
"""

import json
import os
import urllib.request

PORTFOLIO_URL = (
    "https://raw.githubusercontent.com/ianian22493/"
    "investment-ai/main/data/portfolio.json"
)
CACHE_FILE = "holdings.json"   # 成功抓取後寫入，作為離線 fallback

# ── 個股教學卡補充描述（portfolio.json 無此欄，選填；無則回退產業字串）──
DESC_OVERRIDES = {
    "NVDA":  "全球 AI 運算龍頭，CUDA 生態系護城河極深，H 系列 GPU 供不應求",
    "TSLA":  "電動車品牌先驅，FSD 自駕與 Robotaxi 商業化是下一個成長引擎",
    "MSFT":  "Azure 雲端 + Copilot AI 整合，企業軟體市場地位最穩固的科技股之一",
    "GOOGL": "全球搜尋廣告霸主，Gemini AI 與 YouTube 廣告雙引擎驅動",
    "AMZN":  "AWS 雲端市占第一，電商物流護城河深，廣告業務快速成長",
    "CELH":  "北美成長最快的功能性飲料品牌，正積極拓展國際市場",
    "CAVA":  "美式地中海料理連鎖，展店快速的餐飲成長股，同店銷售動能強勁",
    "ONDS":  "工業級無人機系統與鐵路自動化，防務訂單是主要催化劑",
    "RBRK":  "企業資料安全與雲端備份平台，Zero Trust 架構受市場重視",
    "S":     "AI 驅動端點安全平台，與 CrowdStrike 競爭最激烈的資安股",
    "SOUN":  "車用語音 AI 商業化領先，NVIDIA 為策略投資方",
    "ZS":    "雲端原生 SASE 安全架構龍頭，企業數位轉型的必要基礎建設",
    "DRAM":  "追蹤記憶體與儲存晶片產業的 ETF，受惠 AI 帶動 HBM / DRAM 需求",
    "00675L": "富邦臺灣加權指數 2 倍槓桿 ETF，放大大盤漲跌，適合波段操作",
    "00685L": "群益臺灣加權指數 2 倍槓桿 ETF，追蹤大盤 2 倍報酬",
    "00692":  "追蹤公司治理評鑑優良企業，成分股品質穩定，適合長期持有領配息",
    "00915":  "高股息 ETF，每月配息策略，適合需要穩定現金流的長期投資人",
    "1104":  "台灣水泥龍頭之一，受惠公共建設投資與房市需求",
    "1736":  "全球健身器材龍頭，品牌與通路兼具，健身與復健需求長期成長",
    "2211":  "長榮集團旗下鋼材加工廠，與航運景氣連動程度高",
    "2308":  "全球電源供應器與散熱方案龍頭，AI 伺服器電源與資料中心受惠股",
    "2330":  "全球最先進晶片的唯一製造商，AI 時代最核心的科技基礎建設",
    "2834":  "台灣政策性銀行，以中小企業放款為主要業務",
    "3293":  "電子遊戲機台與線上遊戲營運，海內外博弈娛樂需求穩定成長",
    "3546":  "老牌遊戲廠（宇峻奧汀），毛利率高，新作與 IP 授權挹注業績",
    "3703":  "台灣建設與土地開發，業績受房市景氣影響明顯",
    "6442":  "光纖連接器與光通訊元件，資料中心與電信網路建置需求帶動",
    "6534":  "農業生技，與國際大廠專屬合作，毛利高、EPS 創高",
    "8299":  "NAND Flash 控制晶片與儲存方案龍頭，受惠 AI 儲存需求成長",
}


# ── AI 曝險分層（美股儀表板用；core=本業 AI / adjacent=AI 受惠 / none=非 AI）──
# 分類可調整，改這裡即可，前端會自動跟著變。
AI_TIER = {
    "NVDA": "core", "MSFT": "core", "GOOGL": "core", "SOUN": "core",
    "AMZN": "adjacent", "TSLA": "adjacent", "ONDS": "adjacent", "S": "adjacent",
    "ZS": "adjacent", "RBRK": "adjacent", "DRAM": "adjacent",
    "CELH": "none", "CAVA": "none",
}

# ── 產業別覆寫（美股 portfolio.json 無 sector 欄；台股沿用 portfolio.json）──
SECTOR_OVERRIDES = {
    "NVDA": "AI 晶片",   "TSLA": "電動車",     "MSFT": "雲端軟體",
    "GOOGL": "AI 搜尋",  "AMZN": "電商雲端",   "CELH": "健康飲料",
    "CAVA": "餐飲連鎖",  "ONDS": "無人機",     "RBRK": "資安備份",
    "S": "資安",         "SOUN": "語音 AI",    "ZS": "零信任資安",
    "DRAM": "ETF",
}


def _is_etf(ticker, name, ptype):
    if ptype in ("ETF", "leveraged_ETF"):
        return True
    return "ETF" in (name or "").upper()


def fetch_portfolio(timeout=15):
    """抓取遠端 portfolio.json（原始完整內容）"""
    req = urllib.request.Request(
        PORTFOLIO_URL, headers={"User-Agent": "YuzuFinanceBot/1.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _normalize(pf):
    """把 portfolio.json 轉成「純持股」結構（不含任何隱私欄位）"""
    us = []
    for s in pf.get("us_stocks", []):
        t = s.get("ticker")
        if not t:
            continue
        us.append({
            "symbol":   t,
            "name":     s.get("name", t),
            "market":   "US",
            "sector":   SECTOR_OVERRIDES.get(t) or s.get("sector") or "美股",
            "is_etf":   _is_etf(t, s.get("name"), s.get("type")),
            "yf":       t,
            "shares":   s.get("shares", 0),
            "strategy": s.get("strategy", "long"),
            "ai":       AI_TIER.get(t, "none"),
            "desc":     DESC_OVERRIDES.get(t, s.get("sector") or s.get("name", t)),
        })

    tw = []
    for s in pf.get("tw_stocks", []):
        c = s.get("code")
        if not c:
            continue
        tw.append({
            "symbol":   c,
            "name":     s.get("name", c),
            "market":   "TW",
            "sector":   s.get("sector") or "台股",
            "is_etf":   _is_etf(c, s.get("name"), s.get("type")),
            "yf":       f"{c}.TW",
            "shares":   s.get("shares", 0),
            "strategy": s.get("strategy", "long"),
            "desc":     DESC_OVERRIDES.get(c, s.get("sector") or s.get("name", c)),
        })

    return {
        "us": us,
        "tw": tw,
        "_updated": pf.get("_price_refreshed") or pf.get("_updated"),
    }


def load_holdings(write_cache=False):
    """
    取得正規化持股。優先抓遠端 portfolio.json；失敗則回退本地 holdings.json。
    write_cache=True 時（僅 fetch_data.py 呼叫）把結果寫入 holdings.json 供離線 fallback。
    """
    try:
        pf = fetch_portfolio()
        result = _normalize(pf)
        print(f"  ✓ 持股來源 portfolio.json（{len(result['us'])} 美股 / "
              f"{len(result['tw'])} 台股，更新 {result['_updated']}）")
        if write_cache:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        return result
    except Exception as e:
        print(f"  ✗ 抓取 portfolio.json 失敗：{e}，改用本地 {CACHE_FILE}")
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        raise RuntimeError(
            "無法取得持股：遠端 portfolio.json 與本地 holdings.json 皆不可用"
        ) from e


if __name__ == "__main__":
    h = load_holdings(write_cache=True)
    print(json.dumps(h, ensure_ascii=False, indent=2))
