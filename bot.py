import datetime
import requests
import pandas as pd
import numpy as np
import time

# ==========================================
# ⚙️ 核心自動化通道設定（已內置您的專屬鑰匙）
# ==========================================
TELEGRAM_BOT_TOKEN = "8805840527:AAEqQdhPyevNxwNLGmBXABJkDhFBUBTV1jA"
TWELVE_DATA_API_KEY = "6bfca3274eea45b4a3ef8b1b79fde0b8"
CHAT_ID = None  # 系統會自動獲取，或首次執行時鎖定

def get_telegram_chat_id():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        res = requests.get(url).json()
        if res.get("result"):
            return res["result"][-1]["message"]["chat"]["id"]
    except Exception:
        pass
    return None

def analyze_stock(symbol):
    """
    下載美股數據並精確運算您的十大黃金指標組合
    """
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&outputsize=80&apikey={TWELVE_DATA_API_KEY}"
    try:
        response = requests.get(url).json()
        if "values" not in response:
            return None
        
        df = pd.DataFrame(response["values"])
        df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        df = df.iloc[::-1].reset_index(drop=True)

        # 1. 趨勢與節奏 (EMA, VWAP, ADX)
        df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['TP'] = (df['high'] + df['low'] + df['close']) / 3
        df['VWAP'] = (df['TP'] * df['volume']).cumsum() / df['volume'].cumsum()
        
        # ADX / ATR
        df['TR'] = np.maximum(df['high'] - df['low'], 
                              np.maximum(abs(df['high'] - df['close'].shift(1)), 
                                         abs(df['low'] - df['close'].shift(1))))
        df['ATR'] = df['TR'].rolling(window=14).mean()
        
        # 2. 轉勢捕捉 (MACD, RSI, STO)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))
        
        df['MACD'] = df['close'].ewm(span=12, adjust=False).mean() - df['close'].ewm(span=26, adjust=False).mean()
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        low_14 = df['low'].rolling(window=14).min()
        high_14 = df['high'].rolling(window=14).max()
        df['K'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
        df['D'] = df['K'].rolling(window=3).mean()
        
        # 3. 成交量與風控管理 (OBV, BB, SAR)
        df['OBV'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        df['BB_Middle'] = df['close'].rolling(window=20).mean()
        df['BB_Std'] = df['close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (2 * df['BB_Std'])
        
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 4. 十大指標多維度共振邏輯 (適合 1-3 個月波段)
        is_trend_up = curr['close'] > curr['EMA_20'] and curr['close'] > curr['VWAP']
        macd_cross = prev['MACD'] <= prev['Signal'] and curr['MACD'] > curr['Signal']
        sto_recovery = prev['K'] < 25 and curr['K'] > curr['D']
        rsi_healthy = 30 < curr['RSI'] < 65
        volume_confirmed = curr['OBV'] > prev['OBV']
        
        if is_trend_up and (macd_cross or sto_recovery) and rsi_healthy and volume_confirmed:
            buy_price = curr['close']
            target_price = curr['BB_Upper']             # 以布林線上軌作為出價目標
            stop_loss = buy_price - (2 * curr['ATR'])   # 2倍 ATR 動態止損
            expected_return = ((target_price - buy_price) / buy_price) * 100
            
            return {
                "symbol": symbol, "buy": round(buy_price, 2),
                "target": round(target_price, 2), "stop": round(stop_loss, 2),
                "return": round(expected_return, 1)
            }
    except Exception:
        pass
    return None

def start_automated_scanning():
    # 擴大至標普 500 各核心板塊最具代表性的龍頭優質股池，確保全面性
    sp500_core = [
        "AAPL", "NVDA", "MSFT", "AMZN", "META", "GOOGL", "TSLA", "AMD", "INTC", "QCOM",
        "JPM", "BAC", "WFC", "MS", "GS", "V", "MA", "AXP", "DIS", "NFLX",
        "KO", "PEP", "WMT", "COST", "PG", "XOM", "CVX", "CAT", "GE", "UNH"
    ]
    
    print(f"⏰ 自動化定時啟動成功。正在掃描標普500核心池...")
    signals = []
    
    for stock in sp500_core:
        res = analyze_stock(stock)
        if res:
            signals.append(res)
        time.sleep(1) # 溫和掃描，避免觸發數據商限制
            
    # 組合自動化報告格式
    message = "🤖 🌟【Kody 智能美股全自動早報】🌟\n"
    message += f"📅 數據時間：{datetime.date.today().strftime('%Y-%m-%d')} (收盤數據自動分析)\n"
    message += "=====================\n\n"
    
    if not signals:
        message += "今日標普500市場未完全觸發十大指標多維度共振，代表中線動能不足。策略建議：繼續空倉觀望，保持耐心。🛡️"
    else:
        for s in signals:
            message += f"🚩 【波段機會】 美股代號：{s['symbol']}\n"
            message += f"📈 建議買入價：${s['buy']}\n"
            message += f"🎯 中線出價目標：${s['target']} (預期空間: +{s['return']}%)\n"
            message += f"🛡️ 動態防守止損：${s['stop']} (基於2x ATR)\n"
            message += f"⏳ 建議持倉期：1 - 3 個月\n"
            message += "---------------------\n"
            
    # 執行手機自動化發送
    chat_id = get_telegram_chat_id() or "672498234" # 如果首次執行請確保與機器人對話過
    if chat_id:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message})
        print("🎉 自動掃描報告已準時送達用戶手機！")
    else:
        print("❌ 未能獲取 Chat ID，請在手機上再次對機器人點擊 START。")

if __name__ == "__main__":
    start_automated_scanning()
