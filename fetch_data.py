"""
fetch_data.py — 投資儀表板資料抓取腳本
GitHub Actions 每天自動執行，抓取美股報價與永豐銀行匯率
輸出 data.json 供前端讀取（同源，無 CORS 問題）
"""

import json
import re
import requests
from datetime import datetime, timezone, timedelta

# ──────────────────────────────────────────
# 持倉清單（和 index.html 保持一致）
# ──────────────────────────────────────────
US_STOCKS = [
    "AMZN", "CELH", "GOOGL", "MELI", "MSFT", "NVDA",
    "ONDS", "RBRK", "S", "SOUN", "TSLA", "ZS",
]

# 美股持倉：代號 → 股數（需與 index.html WIFE_SHARES 保持一致）
# 2026-04-23：SMR 1股 $12.54 賣出；TTD 3股 $23.50 賣出；CELH +1股 $33.00 買入（均價 $34.00，共 5 股）
# 2026-05-01：CELH +1股 $32.10 買入（共 6 股）
US_POSITIONS = {
    "AMZN": 2, "CELH": 6, "GOOGL": 6.00049, "MELI": 1, "MSFT": 5,
    "NVDA": 4.00006, "ONDS": 7, "RBRK": 9, "S": 1,
    "SOUN": 10, "TSLA": 11, "ZS": 11,
}

# ──────────────────────────────────────────
# 美股：yfinance
# ──────────────────────────────────────────
def fetch_us():
    print("📈 抓取美股資料...")
    result = {}
    try:
        import yfinance as yf
        tickers = yf.Tickers(" ".join(US_STOCKS))

        for symbol in US_STOCKS:
            try:
                t    = tickers.tickers[symbol]
                info = t.fast_info   # 比 .info 快很多，不會觸發慢速爬蟲

                price = getattr(info, "last_price",      None)
                prev  = getattr(info, "previous_close",  None)

                if price is None or prev is None:
                    continue

                change = round(price - prev, 4)
                pct    = round((change / prev) * 100, 2) if prev else 0.0

                result[symbol] = {
                    "price":  round(price, 2),
                    "change": change,
                    "pct":    pct,
                    "state":  "CLOSED",
                }
            except Exception as e:
                print(f"  ✗ {symbol} 失敗：{e}")

        print(f"  ✓ 取得 {len(result)} 檔美股")
    except Exception as e:
        print(f"  ✗ 美股整批失敗：{e}")
    return result


# ──────────────────────────────────────────
# 匯率：永豐銀行牌告匯率（掛牌買入 / 賣出）
# 大戶換匯時請電話詢問最新優惠匯率，此為牌告參考價
# ──────────────────────────────────────────
def fetch_sinopac_jpy():
    """
    從永豐銀行 API 抓取 JPY/TWD 牌告匯率，傳回 (buy, sell)
    buy  = 銀行買入日幣（你賣出日幣時拿到的 TWD）
    sell = 銀行賣出日幣（你買入日幣時付出的 TWD） ← 存款/換匯用這個
    大戶實際優惠匯率通常比牌告 sell 略低（約 0.001–0.003 TWD）
    """
    print("💴 抓取永豐銀行 JPY/TWD 牌告匯率...")
    try:
        url = (
            "https://mma.sinopac.com/ws/share/rate/ws_exchange.ashx"
            "?exchangeType=REMIT&Cross=genREMITResult"
        )
        headers = {"User-Agent": "Mozilla/5.0 (compatible; DashboardBot/1.0)"}
        # verify=False：永豐 mma.sinopac.com 憑證缺少 Subject Key Identifier，
        # 新版 OpenSSL 會驗證失敗，但此為已知官方 API，安全性可接受
        import urllib3; urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        res = requests.get(url, timeout=10, headers=headers, verify=False)
        res.raise_for_status()

        # JSONP 格式：genREMITResult({...})
        text  = res.text
        match = re.search(r'genREMITResult\s*\((.*)\)\s*;?\s*$', text, re.DOTALL)
        if not match:
            raise ValueError("無法解析 JSONP 格式，原始回應：" + text[:200])

        data = json.loads(match.group(1))

        # 永豐 JSONP 實際結構：
        #   頂層是 list，第一個元素是 dict，鍵值：
        #     TitleInfo: 報價時間說明字串
        #     QueryDate: 查詢時間
        #     SubInfo:   匯率資料 list
        #                每筆：DataValue1=幣別名稱, DataValue2=銀行買入,
        #                      DataValue3=銀行賣出, DataValue4=幣別代碼
        d = data[0] if isinstance(data, list) else data
        rate_list = d.get("SubInfo", d.get("Result", []))

        jpy_buy = jpy_sell = None
        for item in (rate_list or []):
            ccy = str(item.get("DataValue4", "")).strip()
            if ccy == "JPY":
                try:
                    jpy_buy  = float(item["DataValue2"])
                    jpy_sell = float(item["DataValue3"])
                except (KeyError, ValueError):
                    pass
                break

        if jpy_buy is None or jpy_sell is None:
            raise ValueError(f"找不到 JPY 欄位，rate_list 筆數：{len(rate_list or [])}")

        print(f"  ✓ 永豐 JPY 買入:{jpy_buy:.4f}  賣出:{jpy_sell:.4f} TWD")
        return round(jpy_buy, 6), round(jpy_sell, 6)

    except Exception as e:
        print(f"  ✗ 永豐匯率失敗：{e}，改用備用 API")
        try:
            res  = requests.get("https://open.er-api.com/v6/latest/JPY", timeout=10)
            rate = round(res.json()["rates"]["TWD"], 6)
            # 估算牌告買賣差（約 ±1.8%）
            return round(rate * 0.982, 6), round(rate * 1.018, 6)
        except Exception as e2:
            print(f"  ✗ 備用 API 也失敗：{e2}")
            return None, None


def fetch_usd_rate():
    print("💵 抓取 USD/TWD 匯率...")
    try:
        res  = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        res.raise_for_status()
        rate = res.json()["rates"]["TWD"]
        print(f"  ✓ 1 USD = {rate:.4f} TWD")
        return round(rate, 4)
    except Exception as e:
        print(f"  ✗ USD 匯率抓取失敗：{e}")
        return None


# ──────────────────────────────────────────
# 主程式：組合並輸出 data.json
# ──────────────────────────────────────────
def main():
    us                = fetch_us()
    jpy_buy, jpy_sell = fetch_sinopac_jpy()
    usd_rate          = fetch_usd_rate()

    tz_tw      = timezone(timedelta(hours=8))
    now_tw     = datetime.now(tz_tw)
    updated_at = now_tw.strftime("%Y-%m-%d %H:%M")
    today_str  = now_tw.strftime("%Y-%m-%d")

    # ── 讀取現有 data.json（保留手動欄位 + 歷史紀錄）
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            old = json.load(f)
    except Exception:
        old = {}

    # 手動欄位（只能由使用者透過 Claude 更新）
    jpy_savings          = old.get("jpy_savings", 600_000)
    jpy_monthly_estimate = old.get("jpy_monthly_estimate", 50_000)
    jpy_taisho_discount  = old.get("jpy_taisho_discount", 0.0006)  # 大戶優惠：牌告賣出 - 此值

    # 匯率歷史：今日記一筆，保留最近 60 天
    history = old.get("jpy_rate_history", [])
    if jpy_sell is not None:
        history = [h for h in history if h.get("date") != today_str]  # 移除同日舊筆
        history.append({
            "date": today_str,
            "buy":  jpy_buy,
            "sell": jpy_sell,
        })
        history = sorted(history, key=lambda h: h["date"])[-60:]  # 只保留最近 60 天

    # 美股組合歷史：今日記一筆，保留最近 90 天
    us_value_usd = sum(US_POSITIONS[t] * us[t]["price"]
                       for t in US_POSITIONS if t in us and us[t].get("price"))
    us_value_twd = round(us_value_usd * (usd_rate or 32.0))

    port_history = old.get("portfolio_history", [])
    if us_value_twd > 0:
        port_history = [h for h in port_history if h.get("date") != today_str]
        port_history.append({
            "date":  today_str,
            "us":    us_value_twd,
            "total": us_value_twd,
        })
        port_history = sorted(port_history, key=lambda h: h["date"])[-90:]

    output = {
        "updated_at":           updated_at,
        "us":                   us,
        "jpy_twd":              jpy_sell,           # 向後相容（舊 JS 仍讀這個）
        "jpy_buy":              jpy_buy,
        "jpy_sell":             jpy_sell,
        "jpy_savings":          jpy_savings,        # 手動更新：告知 Claude 最新餘額
        "jpy_monthly_estimate": jpy_monthly_estimate,  # 手動更新：每月大概存多少
        "jpy_taisho_discount":  jpy_taisho_discount,       # 手動更新：大戶優惠折扣（牌告賣出 - 此值）
        "jpy_rate_history":     history,            # 自動累積，供走勢分析使用
        "usd_twd":              usd_rate,
        "portfolio_history":    port_history,       # 每日美股市値（自動累積）
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ data.json 已產生，更新時間：{updated_at}")
    print(f"   JPY 歷史紀錄：{len(history)} 筆")
    print(f"   日幣存款：¥{jpy_savings:,}（手動欄位，如需更新請告知 Claude）")
    print(f"   投組歷史：{len(port_history)} 筆｜今日美股 NT${us_value_twd:,.0f}")


if __name__ == "__main__":
    main()
