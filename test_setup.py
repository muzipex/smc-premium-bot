import MetaTrader5 as mt5
import requests
import json

def test_setup():
    # Test MT5 connection
    if not mt5.initialize():
        print("❌ MT5 initialization failed")
        return False
    print("✅ MT5 initialized successfully")
    
    # Test login
    if not mt5.login(40463645, password="Watoop@222", server="Deriv-Demo"):
        print("❌ MT5 login failed")
        return False
    print("✅ MT5 login successful")
    
    # Test symbol access
    symbols = ["EURUSDm", "XAUUSDm", "USDJPYm", "Volatility 75 Index"]
    for symbol in symbols:
        if not mt5.symbol_select(symbol, True):
            print(f"❌ Symbol {symbol} not available")
            return False
        print(f"✅ Symbol {symbol} accessible")

    # Test Telegram
    TELEGRAM_TOKEN = "AAFjd5zloE8neWr2tzhkirk3uE4GvlArWSE"
    TELEGRAM_CHAT_ID = "7318697622"
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": "🤖 SMC Bot Test Message: Setup check successful!"
        }
        response = requests.post(url, data=json.dumps(payload), 
                               headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            print("✅ Telegram notifications working")
        else:
            print("❌ Telegram test failed")
            return False
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

    print("\n✅ All systems ready! Bot can be started.")
    return True

if __name__ == "__main__":
    test_setup()
