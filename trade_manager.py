import MetaTrader5 as mt5
from datetime import datetime, timedelta
from config.settings import RISK_SETTINGS, SCALPING_SETTINGS

class TradeManager:
    def __init__(self, bot):
        self.bot = bot
        self.positions = {}
        self.tracked_positions = {}
        self.daily_stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'daily_profit': 0,
            'daily_loss': 0
        }

    def manage_positions(self):
        """Monitor and manage open positions"""
        try:
            positions = mt5.positions_get()
            if positions:
                for position in positions:
                    # Check scalping timeout
                    if "Scalp" in position.comment:
                        open_time = datetime.fromtimestamp(position.time)
                        if datetime.now() - open_time > timedelta(minutes=SCALPING_SETTINGS['timeout_minutes']):
                            self.bot.close_position(position.symbol)
                            continue

                    # Move to breakeven
                    if self.should_move_to_breakeven(position):
                        self.move_to_breakeven(position)

                    # Trailing stop
                    if self.should_update_trailing_stop(position):
                        self.update_trailing_stop(position)

        except Exception as e:
            self.bot.log_message(f"Error managing positions: {e}")

    def monitor_positions(self):
        """Monitor positions and send updates"""
        try:
            positions = mt5.positions_get()
            if positions:
                for position in positions:
                    # Check if position was just closed
                    if position.ticket not in self.tracked_positions:
                        continue
                        
                    current_profit = position.profit
                    last_profit = self.tracked_positions[position.ticket]['last_profit']
                    
                    # Position closed
                    if current_profit != last_profit:
                        account_info = mt5.account_info()
                        self.bot.send_telegram_alert(
                            f"Position Update for {position.symbol}\n"
                            f"Profit: ${position.profit:.2f}\n"
                            f"Account Balance: ${account_info.balance:.2f}\n"
                            f"Account Equity: ${account_info.equity:.2f}"
                        )
                        self.tracked_positions[position.ticket]['last_profit'] = current_profit
                        
            # Update tracked positions
            self.tracked_positions = {
                pos.ticket: {
                    'symbol': pos.symbol,
                    'last_profit': pos.profit
                } for pos in positions or []
            }
            
        except Exception as e:
            self.bot.log_message(f"Error monitoring positions: {e}")

    def should_move_to_breakeven(self, position):
        """Check if position should be moved to breakeven"""
        try:
            tick = mt5.symbol_info_tick(position.symbol)
            if not tick:
                return False

            profit_pips = (tick.bid - position.price_open) if position.type == 0 else (position.price_open - tick.ask)
            profit_pips /= self.bot.SYMBOL_MAPPINGS[position.symbol]['pip_value']

            return profit_pips >= SCALPING_SETTINGS['default_tp_pips'] * 0.5

        except Exception as e:
            self.bot.log_message(f"Error checking breakeven: {e}")
            return False

    def move_to_breakeven(self, position):
        """Move stop loss to entry price"""
        try:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "position": position.ticket,
                "sl": position.price_open
            }
            mt5.order_send(request)
        except Exception as e:
            self.bot.log_message(f"Error moving to breakeven: {e}")

    def update_daily_stats(self, trade_result):
        """Update daily trading statistics"""
        try:
            self.daily_stats['total_trades'] += 1
            if trade_result.profit > 0:
                self.daily_stats['winning_trades'] += 1
                self.daily_stats['daily_profit'] += trade_result.profit
            else:
                self.daily_stats['losing_trades'] += 1
                self.daily_stats['daily_loss'] += abs(trade_result.profit)

            # Check daily loss limit
            account_info = mt5.account_info()
            if account_info:
                daily_loss_pct = (self.daily_stats['daily_loss'] / account_info.balance) * 100
                if daily_loss_pct >= RISK_SETTINGS['max_daily_loss']:
                    self.bot.log_message("Daily loss limit reached - Stopping trading")
                    self.bot.gui.is_running = False

        except Exception as e:
            self.bot.log_message(f"Error updating stats: {e}")
