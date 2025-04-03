import MetaTrader5 as mt5
import pandas as pd
import time
import json
import requests
from datetime import datetime, timezone
from smc_patterns import SMCPatterns
from config.symbol_config import SYMBOL_MAPPINGS
from gui.bot_gui import TradingBotGUI
import threading
from gui.login_window import MT5LoginWindow
from ml_scalper import MLScalper

# Telegram Bot Setup
TELEGRAM_TOKEN = "7377915973:AAG99koT64MbDqvs6teMCX5WuGUKJJFpI44"
TELEGRAM_CHAT_ID = "7318697622"

# Trading Configurations
# Ensure these symbols exactly match what appears in Market Watch.
SYMBOLS = list(SYMBOL_MAPPINGS.keys())
TIMEFRAMES = [mt5.TIMEFRAME_M30, mt5.TIMEFRAME_H1, mt5.TIMEFRAME_H4]
RISK_PERCENTAGE = 20        # Risk per trade (1% of balance)
SESSION_FILTER = [(7, 17)] # Trade only during London & New York session (UTC)

class MT5SMCBot:
    def __init__(self, login, password, server):
        self.login = login
        self.password = password
        self.server = server
        self.active_positions = {}  # Track active positions by symbol
        self.smc_patterns = SMCPatterns()
        self.scalping_positions = {}  # Track scalping positions per symbol
        self.partial_tp_positions = {}  # Track positions with partial take profits
        self.gui = None
        self.selected_symbol = None  # Selected symbol from GUI
        self.risk_percentage = RISK_PERCENTAGE  # Risk percentage from GUI
        self.RISK_PERCENTAGE = RISK_PERCENTAGE    # Added for GUI access
        self.SYMBOL_MAPPINGS = SYMBOL_MAPPINGS    # Added to support GUI initialization
        self.bypass_margin_check = False  # Add this flag to bypass margin level check
        self.ml_scalper = MLScalper()
        self.last_training_time = datetime.now()

    def connect(self):
        try:
            if not mt5.initialize():
                print("MT5 initialization failed:", mt5.last_error())
                return False

            authorized = mt5.login(self.login, password=self.password, server=self.server)
            if authorized:
                print("Connected to MT5 successfully")
                return True
            else:
                print("MT5 login failed:", mt5.last_error())
                return False
        except Exception as e:
            print(f"Exception in connect: {e}")
            return False

    def log_message(self, message):
        print(message)
        if self.gui:
            try:
                self.gui.add_log(message)
            except Exception as e:
                print(f"Error adding log to GUI: {e}")

    def get_market_data(self, symbol, timeframe, count=50):
        try:
            # Ensure the symbol is selected in MT5
            if not mt5.symbol_select(symbol, True):
                print(f"Failed to select symbol: {symbol} - Error: {mt5.last_error()}")
                return None

            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
            if rates is None:
                print(f"Failed to fetch market data for {symbol} - Error: {mt5.last_error()}")
                return None

            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df
        except Exception as e:
            print(f"Exception in get_market_data: {e}")
            return None

    def has_active_position(self, symbol):
        try:
            positions = mt5.positions_get(symbol=symbol)
            self.active_positions[symbol] = bool(positions)
            return self.active_positions[symbol]
        except Exception as e:
            print(f"Exception in has_active_position: {e}")
            return False

    def detect_smc_trend(self, df):
        """Reversed SMC trend detection for counter-trend scalping"""
        try:
            # Get last 3 candles
            last_candles = df.tail(3)
            
            # Reverse the logic - sell on bullish setup, buy on bearish setup
            if (last_candles['close'].values[-1] > last_candles['open'].values[-1] and  # Bullish close
                last_candles['low'].values[-1] > last_candles['low'].values[-2]):       # Higher low
                return "SELL", 80  # Reverse signal
                
            if (last_candles['close'].values[-1] < last_candles['open'].values[-1] and  # Bearish close
                last_candles['high'].values[-1] < last_candles['high'].values[-2]):     # Lower high
                return "BUY", 80   # Reverse signal
                
            return None, 0
        except Exception as e:
            self.log_message(f"Error in detect_smc_trend: {e}")
            return None, 0

    def calculate_atr(self, df, period=14):
        try:
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift())
            low_close = abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            return true_range.rolling(period).mean().iloc[-1]
        except Exception as e:
            print(f"Exception in calculate_atr: {e}")
            return 0

    def calculate_lot_size(self, risk_percentage, symbol):
        try:
            account_info = mt5.account_info()
            if account_info is None:
                print("Account info not available")
                return 0
                
            symbol_config = SYMBOL_MAPPINGS[symbol]
            balance = account_info.balance
            risk_amount = (risk_percentage / 100) * balance
            stop_loss_pips = symbol_config['stop_loss_pips']

            # Base lot size calculation using symbol-specific settings
            base_lot = risk_amount / (stop_loss_pips * 10)
            
            # Apply symbol-specific limits
            lot_size = max(min(base_lot, symbol_config['max_lot']), symbol_config['min_lot'])
            
            # Adjust lot size based on ATR volatility
            df = self.get_market_data(symbol, mt5.TIMEFRAME_H1, 50)
            if df is not None:
                atr = self.calculate_atr(df)
                avg_atr = df['high'].mean() * 0.001  # 0.1% of average price
                volatility_factor = avg_atr / atr if atr > 0 else 1
                lot_size = lot_size * min(max(volatility_factor, 0.5), 1.5)
            
            return round(lot_size, 2)
        except Exception as e:
            print(f"Exception in calculate_lot_size: {e}")
            return 0

    def count_scalping_positions(self, symbol):
        try:
            positions = mt5.positions_get(symbol=symbol)
            if positions:
                return len([pos for pos in positions if "Scalp" in pos.comment])
            return 0
        except Exception as e:
            print(f"Exception in count_scalping_positions: {e}")
            return 0

    def close_position(self, symbol):
        """Close an open position for the given symbol"""
        try:
            position = mt5.positions_get(symbol=symbol)
            if not position:
                self.log_message(f"No position found for {symbol}")
                return False
                
            # Get the first position for this symbol
            pos = position[0]
            close_price = mt5.symbol_info_tick(symbol).bid if pos.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).ask
            
            # Prepare close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": pos.ticket,
                "symbol": symbol,
                "volume": pos.volume,
                "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "price": close_price,
                "deviation": 20,
                "magic": 123456,
                "comment": "Close position",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                # Send position closure update
                account_info = mt5.account_info()
                self.send_telegram_alert(
                    f"Position Closed: {symbol}\n"
                    f"Profit: ${pos.profit:.2f}\n"
                    f"New Balance: ${account_info.balance:.2f}\n"
                    f"New Equity: ${account_info.equity:.2f}"
                )
                self.log_message(f"Position closed for {symbol}")
                return True
            else:
                self.log_message(f"Error closing position: {result.comment}")
                return False
                
        except Exception as e:
            self.log_message(f"Error in close_position: {e}")
            return False

    def _execute_trade(self, symbol, trade_type, lot_size, sl_pips, tp_pips, confidence, is_scalping):
        try:
            tick = mt5.symbol_info_tick(symbol)
            symbol_config = SYMBOL_MAPPINGS[symbol]
            pip_value = symbol_config['pip_value']
            
            price = tick.ask if trade_type == "BUY" else tick.bid
            sl = price - sl_pips * pip_value if trade_type == "BUY" else price + sl_pips * pip_value
            tp = price + tp_pips * pip_value if trade_type == "BUY" else price - tp_pips * pip_value

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size,
                "type": mt5.ORDER_TYPE_BUY if trade_type == "BUY" else mt5.ORDER_TYPE_SELL,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 10,
                "magic": 123456,
                "comment": f"{'Scalp' if is_scalping else 'Trade'} {symbol} Conf:{confidence}%",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                self.send_telegram_alert(
                    f"{'Scalp' if is_scalping else 'Trade'} executed: {trade_type} {symbol}"
                    f"\nLot: {lot_size}\nConf: {confidence}%"
                    f"\nSL: {sl_pips} pips\nTP: {tp_pips} pips"
                )
        except Exception as e:
            print(f"Exception in _execute_trade: {e}")

    def send_telegram_alert(self, message):
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        try:
            requests.post(url, data=json.dumps(payload), headers={"Content-Type": "application/json"})
        except Exception as e:
            print("Failed to send Telegram alert:", e)
        self.log_message(message)

    def is_valid_session(self):
        try:
            now = datetime.now(timezone.utc)  # Use timezone-aware datetime
            # Don't trade 2 hours before weekend
            if now.weekday() == 4 and now.hour >= 20:  # Friday after 20:00 UTC
                return False
            # Don't trade on weekends
            if now.weekday() >= 5:  # Saturday and Sunday
                return False
            for start_hour, end_hour in SESSION_FILTER:
                if start_hour <= now.hour <= end_hour:
                    return True
            return False
        except Exception as e:
            print(f"Exception in is_valid_session: {e}")
            return False

    def run(self):
        if not self.connect():
            return False

        try:
            # Initialize GUI
            self.gui = TradingBotGUI(self)
        except Exception as e:
            print(f"GUI initialization error: {e}")
            return False

        try:
            # Start trading loop in separate thread
            self.trading_thread = threading.Thread(target=self.trading_loop, daemon=True)
            self.trading_thread.start()
            # Run GUI in main thread
            self.gui.run()
            return True
        except Exception as e:
            print(f"Error starting trading loop: {e}")
            return False

    def can_open_new_trade(self, symbol):
        """Modified position check without trade limits"""
        try:
            # Check total open positions
            all_positions = mt5.positions_get()
            if all_positions is None:
                return False
                
            # Calculate total risk exposure
            total_risk = 0
            account_info = mt5.account_info()
            if account_info is None:
                return False
                
            for pos in all_positions:
                if pos.profit < 0:
                    total_risk += abs(pos.profit)
            
            # Don't open new trades if total risk exceeds 5% of balance
            max_risk = account_info.balance * 0.05
            if total_risk > max_risk:
                self.log_message(f"Maximum risk reached: {total_risk:.2f} > {max_risk:.2f}")
                return False
                
            return True

        except Exception as e:
            self.log_message(f"Error in can_open_new_trade: {e}")
            return False

    def get_optimal_lot_size(self, symbol):
        """Calculate safer lot size based on balance"""
        try:
            account_info = mt5.account_info()
            if account_info is None:
                return 0.01

            # Use micro lots for small accounts
            if account_info.balance < 100:
                return 0.01
            elif account_info.balance < 500:
                return 0.02
            elif account_info.balance < 1000:
                return 0.05

            # Calculate lot size based on risk
            risk_amount = account_info.balance * 0.01  # 1% risk
            pip_value = self.SYMBOL_MAPPINGS[symbol]['pip_value']
            sl_pips = self.SYMBOL_MAPPINGS[symbol]['scalping']['sl_pips']
            
            # Calculate lot size
            lot_size = (risk_amount / (sl_pips * 10)) * 0.5  # 50% of calculated lot
            
            # Apply strict limits
            lot_size = min(lot_size, 0.5)  # Maximum 0.5 lot
            lot_size = max(lot_size, 0.01)  # Minimum 0.01 lot
            
            return round(lot_size, 2)
        except Exception as e:
            self.log_message(f"Error calculating lot size: {e}")
            return 0.01

    def place_trade(self, symbol, trade_type, lot_size, confidence=80):
        """Modified trade placement with better error handling"""
        try:
            # Basic checks
            if not mt5.initialize():
                self.log_message("MT5 not initialized")
                return False

            account_info = mt5.account_info()
            if not account_info:
                self.log_message("Unable to get account info")
                return False

            if account_info.margin_free < 50:
                self.log_message(f"Insufficient free margin (${account_info.margin_free:.2f})")
                return False

            # Get symbol info and verify
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                self.log_message(f"Failed to get symbol info for {symbol}")
                return False

            if not mt5.symbol_select(symbol, True):
                self.log_message(f"Failed to select {symbol}")
                return False

            # Get current price
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                self.log_message(f"Failed to get price tick for {symbol}")
                return False

            # Calculate price levels
            point = symbol_info.point
            pip_value = self.SYMBOL_MAPPINGS[symbol]['pip_value']
            stop_pips = 15
            target_pips = 10

            if trade_type == "BUY":
                price = tick.ask
                sl = price - (stop_pips * pip_value)
                tp = price + (target_pips * pip_value)
                order_type = mt5.ORDER_TYPE_BUY
            else:  # SELL
                price = tick.bid
                sl = price + (stop_pips * pip_value)
                tp = price - (target_pips * pip_value)
                order_type = mt5.ORDER_TYPE_SELL

            # Prepare trade request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(lot_size),
                "type": order_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 20,
                "magic": 123456,
                "comment": f"ML Signal {confidence:.1f}%",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }

            # Send order with retry
            for attempt in range(3):  # Try up to 3 times
                self.log_message(f"Sending order (attempt {attempt + 1})")
                result = mt5.order_send(request)
                
                if result and result.retcode != mt5.TRADE_RETCODE_DONE:
                    self.log_message(f"Order failed: {result.comment}")
                    time.sleep(0.1)  # Small delay before retry
                    continue
                    
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.log_message(f"Order executed: {trade_type} {symbol} at {price}")
                    self.send_telegram_alert(
                        f"Trade opened: {trade_type} {symbol}\n"
                        f"Price: {price}\nLot: {lot_size}\n"
                        f"SL: {sl}\nTP: {tp}\n"
                        f"Confidence: {confidence:.1f}%"
                    )
                    return True
                    
            self.log_message("All order attempts failed")
            return False

        except Exception as e:
            self.log_message(f"Error in place_trade: {str(e)}")
            return False

    def trading_loop(self):
        """Enhanced trading loop with learning-while-trading"""
        while True:
            try:
                if not self.gui.is_running:
                    time.sleep(1)
                    continue

                # Check for symbols
                for symbol in self.SYMBOL_MAPPINGS.keys():
                    try:
                        df = self.get_market_data(symbol, mt5.TIMEFRAME_M5, 100)
                        if df is None:
                            continue

                        # Get ML prediction first
                        ml_decision, ml_confidence = self.ml_scalper.predict(df)
                        
                        # Get SMC prediction if ML confidence is low
                        smc_decision = None
                        smc_confidence = 0
                        if ml_confidence < 60:
                            smc_decision, smc_confidence = self.smc_patterns.detect_premium_entry(df)
                        
                        self.log_message(f"Analysis for {symbol}:")
                        self.log_message(f"ML Signal: {ml_decision} ({ml_confidence:.1f}%)")
                        self.log_message(f"SMC Signal: {smc_decision} ({smc_confidence:.1f}%)")

                        # Trade decision logic
                        should_trade = False
                        final_decision = None
                        final_confidence = 0

                        # Use ML signal if confidence is good
                        if ml_decision and ml_confidence > 40:
                            should_trade = True
                            final_decision = ml_decision
                            final_confidence = ml_confidence
                        # Use SMC signal as backup
                        elif smc_decision and smc_confidence > 50:
                            should_trade = True
                            final_decision = smc_decision
                            final_confidence = smc_confidence
                        
                        if should_trade:
                            if not self.has_active_position(symbol) and self.can_open_new_trade(symbol):
                                lot_size = self.get_optimal_lot_size(symbol)
                                self.log_message(f"Opening trade for {symbol}: {final_decision} Lot: {lot_size}")
                                trade_result = self.place_trade(symbol, final_decision, lot_size, final_confidence)
                                if trade_result:
                                    self.log_message(f"Trade opened successfully for {symbol}")
                        
                        time.sleep(0.1)
                        
                    except Exception as e:
                        self.log_message(f"Error processing {symbol}: {str(e)}")
                    
                time.sleep(1)
                
            except Exception as e:
                self.log_message(f"Error in trading loop: {str(e)}")
                time.sleep(5)

    def detect_trend(self, df, lookback=20):
        """Ultra simple trend detection"""
        try:
            close = df['close'].values[-lookback:]
            sma = sum(close) / len(close)
            current_price = close[-1]
            
            if current_price > sma:
                return "BUY", min(((current_price/sma - 1) * 100), 100)
            elif current_price < sma:
                return "SELL", min(((sma/current_price - 1) * 100), 100)
            return None, 0
        except Exception as e:
            self.log_message(f"Error in detect_trend: {e}")
            return None, 0

if __name__ == "__main__":
    try:
        login_window = MT5LoginWindow()
        login_info = login_window.get_login_info()
        if login_info:
            bot = MT5SMCBot(
                login_info['login'],
                login_info['password'],
                login_info['server']
            )
            if not bot.run():  # Use the run method instead of separate initialization
                print("Failed to start bot")
        else:
            print("Login cancelled")
    except Exception as e:
        print(f"Application startup error: {e}")
    finally:
        try:
            mt5.shutdown()
        except:
            pass