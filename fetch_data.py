"""
fetch_data.py — 投資儀表板資料抓取腳本
GitHub Actions 每天自動執行，抓取台股、美股、日幣匯率
並輸出 data.json 供前端讀取（同源，無 CORS 問題）
"""

import json
import requests
from datetime import datetime, timezone, timedelta

# ──────────────────────────────────────────
# 持倉清單（和 index.html 保持一致）
# ──────────────────────────────────────────
TW_STOCKS = [
    "00692", "00915", "1104", "2211", "2330",
    "2536", "2834", "3293", "3661", "3703", "4588", "4707",
]

US_STOCKS = [
    "AMZN", "CELH", "GOOGL", "MELI", "MSFT", "NVDA",
    "ONDS", "RBRK", "S", "SMR", "SOUN", "TSLA", "TTD", "ZS",
]

# ──────────────────────────────────────────
# 台股：TWSE 開放 API
# ──────────────────────────────────────────
def fetch_tw():
    print("📈 抓取台股資料...")
    result = {}
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        headers = {"Accept": "application/json"}
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        data = res.json()

        data_date = ""
        if data and data[0].get("Date"):
            raw = data[0]["Date"]
            yr = int(raw[:3]) + 1911
            mo, dy = raw[3:5], raw[5:7]
            data_date = f"{yr}-{mo}-{dy}"

        for item in data:
            code = item.get("Code", "")
            if code not in TW_STOCKS:
                continue
            try:
                price  = float(item["ClosingPrice"].replace(",", ""))
                change_str = item.get("Change", "0") or "0"
                change = float(change_str.replace(",", "").replace("+", ""))
                result[code] = {
                    "price":  price,
                    "change": change,
                    "date":   data_date,
                }
            except (ValueError, AttributeError):
                pass

        print(f"  ✓ 取得 {len(result)} 檔台股，資料日期：{data_date}")
    except Exception as e:
        print(f"  ✗ 台股抓取失敗：{e}")
    return result


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
                info = t.fast_info

                price  = getattr(info, "last_price",          None)
                prev   = getattr(info, "previous_close",      None)
                low52  = getattr(info, "fifty_two_week_low",  None)
                high52 = getattr(info, "fifty_two_week_high", None)

                if price is None or prev is None:
                    continue

                change = round(price - prev, 4)
                pct    = round((change / prev) * 100, 2) if prev else 0.0

                result[symbol] = {
                    "price":  round(price,  2),
                    "change": change,
                    "pct":    pct,
                    "low52":  round(low52,  2) if low52  else None,
                    "high52": round(high52, 2) if high52 else None,
                    "state":  "CLOSED",
                }
            except Exception as e:
                print(f"  ✗ {symbol} 失敗：{e}")

        print(f"  ✓ 取得 {len(result)} 檔美股")
    except Exception as e:
        print(f"  ✗ 美股整批失敗：{e}")
    return result


# ──────────────────────────────────────────
# 匯率：open.er-api.com
# ──────────────────────────────────────────
def fetch_jpy_rate():
    print("💴 抓取 JPY/TWD 匯率...")
    try:
        res  = requests.get("https://open.er-api.com/v6/latest/JPY", timeout=10)
        res.raise_for_status()
        data = res.json()
        rate = data["rates"]["TWD"]
        print(f"  ✓ 1 JPY = {rate:.4f} TWD")
        return round(rate, 6)
    except Exception as e:
        print(f"  ✗ 匯率抓取失敗：{e}")
        return None


# ──────────────────────────────────────────
# 主程式
# ──────────────────────────────────────────
def main():
    tw   = fetch_tw()
    us   = fetch_us()
    rate = fetch_jpy_rate()

    tz_tw      = timezone(timedelta(hours=8))
    updated_at = datetime.now(tz_tw).strftime("%Y-%m-%d %H:%M")

    output = {
        "updated_at": updated_at,
        "tw":         tw,
        "us":         us,
        "jpy_twd":    rate,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ data.json 已產生，更新時間：{updated_at}")


if __name__ == "__main__":
    main()
