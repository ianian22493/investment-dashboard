"""
fetch_data.py — 投資儀表板資料抓取腳本
GitHub Actions 每天自動執行，抓取美股報價與匯率
輸出 data.json 供前端讀取（同源，無 CORS 問題）
（台股已移除，改用個人 APP 查看）
"""

import json
import requests
from datetime import datetime, timezone, timedelta

# ──────────────────────────────────────────
# 持倉清單（和 index.html 保持一致）
# ──────────────────────────────────────────
US_STOCKS = [
    "AMZN", "CELH", "GOOGL", "MELI", "MSFT", "NVDA",
    "ONDS", "RBRK", "S", "SMR", "SOUN", "TSLA", "TTD", "ZS",
]

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
# 匯率：open.er-api.com（允許跨域，無需金鑰）
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
        print(f"  ✗ JPY 匯率抓取失敗：{e}")
        return None


def fetch_usd_rate():
    print("💵 抓取 USD/TWD 匯率...")
    try:
        res  = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        res.raise_for_status()
        data = res.json()
        rate = data["rates"]["TWD"]
        print(f"  ✓ 1 USD = {rate:.4f} TWD")
        return round(rate, 4)
    except Exception as e:
        print(f"  ✗ USD 匯率抓取失敗：{e}")
        return None


# ──────────────────────────────────────────
# 主程式：組合並輸出 data.json
# ──────────────────────────────────────────
def main():
    us       = fetch_us()
    jpy_rate = fetch_jpy_rate()
    usd_rate = fetch_usd_rate()

    tz_tw      = timezone(timedelta(hours=8))
    updated_at = datetime.now(tz_tw).strftime("%Y-%m-%d %H:%M")

    output = {
        "updated_at": updated_at,
        "us":         us,
        "jpy_twd":    jpy_rate,
        "usd_twd":    usd_rate,   # 老婆基金美股市值換算用
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ data.json 已產生，更新時間：{updated_at}")


if __name__ == "__main__":
    main()
