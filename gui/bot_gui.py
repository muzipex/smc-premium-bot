import tkinter as tk
from tkinter import ttk, font
import threading
from datetime import datetime, timezone, timedelta
import pytz  # Add this import
import MetaTrader5 as mt5
import requests
import tempfile
import os
import queue
import time

class TradingBotGUI:
    def __init__(self, bot):
        # Add timezone setup
        self.timezone = pytz.timezone('UTC')  # Use UTC for consistency
        # Initialize queues and variables first
        self.log_queue = queue.Queue()  # Ensure log_queue is initialized
        self.is_running = False
        self.bot = bot
        self.root = tk.Tk()
        self.root.title("SMC Premium Trading Bot")
        self.root.geometry("1000x700")
        
        # Setup tags for treeview
        self.setup_treeview_tags()
        
        # Initialize variables before any UI creation
        self.selected_symbol = tk.StringVar()
        self.risk_var = tk.IntVar(value=20)  # Default risk
        self.scalping_var = tk.BooleanVar(value=True)
        self.confidence_var = tk.IntVar(value=60)
        
        try:
            # Configure style
            self.style = ttk.Style(self.root)
            self.current_theme = "dark"
            self.set_dark_theme()
            
            # Set default font
            default_font = ('Segoe UI', 10)
            title_font = ('Segoe UI', 16, 'bold')
            self.root.option_add('*Font', default_font)
            
            # Create UI components
            self.create_header(title_font)
            self.create_account_info()
            self.create_positions_table()
            self.create_log_area()
            
            # Set initial symbol selection
            if hasattr(self.bot, 'SYMBOL_MAPPINGS'):
                symbols = list(self.bot.SYMBOL_MAPPINGS.keys())
                if symbols:
                    self.selected_symbol.set(symbols[0])
            
            # Center window
            self.center_window()
            
            # Schedule update loop
            self.root.after(1000, self.update_loop)
            
            # Add periodic log processing
            self.root.after(100, self.process_logs)
        except Exception as e:
            print(f"GUI init error: {e}")

    def setup_treeview_tags(self):
        """Setup color tags for treeview"""
        self.style = ttk.Style()
        self.style.map('Treeview',
            foreground=[('selected', '#ffffff')],
            background=[('selected', '#0066cc')]
        )
        
        # Add tags for profit/loss colors
        self.style.configure("profit.Treeview", foreground="#00ff00")
        self.style.configure("loss.Treeview", foreground="#ff0000")

    def create_header(self, title_font):
        header = ttk.Frame(self.root)
        header.pack(fill=tk.X, padx=10, pady=10)
        
        # Create title with system font
        title_frame = tk.Frame(header, bg="#1e1e1e", bd=2, relief="ridge")
        title_frame.pack(side=tk.LEFT, padx=5)
        title_label = tk.Label(title_frame, 
                             text="SMC PREMIUM BOT", 
                             font=title_font,
                             bg="#1e1e1e",
                             fg="#00ff00",
                             padx=10,
                             pady=5)
        title_label.pack()
        
        # Create modern controls frame
        controls_frame = ttk.Frame(header)
        controls_frame.pack(side=tk.LEFT, padx=20)
        
        # Symbol Selection Dropdown
        symbols = list(self.bot.SYMBOL_MAPPINGS.keys())
        self.selected_symbol = tk.StringVar(value=symbols[0])  # Default to first symbol
        symbol_label = ttk.Label(controls_frame, text="Select Symbol:")
        symbol_label.pack(side=tk.LEFT, padx=5)
        symbol_dropdown = ttk.Combobox(controls_frame, textvariable=self.selected_symbol, values=symbols, state='readonly')
        symbol_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Start/Stop Button
        self.start_stop_button = ttk.Button(controls_frame, text="Start Bot", command=self.toggle_bot)
        self.start_stop_button.pack(side=tk.LEFT, padx=5)
        
        # Risk Percentage Slider
        risk_label = ttk.Label(controls_frame, text="Risk %:")
        risk_label.pack(side=tk.LEFT, padx=5)
        self.risk_var = tk.IntVar(value=self.bot.RISK_PERCENTAGE)
        self.risk_slider = tk.Scale(controls_frame, from_=1, to=50, orient=tk.HORIZONTAL, variable=self.risk_var, length=100)
        self.risk_slider.pack(side=tk.LEFT, padx=5)
        
        # Stylish scalping toggle
        self.scalping_var = tk.BooleanVar(value=True)
        scalping_frame = tk.Frame(controls_frame, bg="#2d2d2d", bd=1, relief="raised")
        scalping_frame.pack(side=tk.LEFT, padx=10)
        self.scalping_toggle = tk.Checkbutton(scalping_frame, 
                                            text="SCALPING MODE",
                                            variable=self.scalping_var,
                                            bg="#2d2d2d",
                                            fg="#00ff00",
                                            selectcolor="#1e1e1e",
                                            activebackground="#2d2d2d",
                                            activeforeground="#00ff00",
                                            command=self.update_settings)
        self.scalping_toggle.pack(padx=5, pady=2)
        
        # Modern confidence slider
        confidence_frame = tk.Frame(controls_frame, bg="#2d2d2d", bd=1, relief="raised")
        confidence_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(confidence_frame, 
                text="CONFIDENCE THRESHOLD",
                bg="#2d2d2d",
                fg="#00ff00").pack(padx=5, pady=2)
        self.confidence_var = tk.IntVar(value=60)
        confidence_scale = tk.Scale(confidence_frame,
                                  from_=0,
                                  to=100,
                                  variable=self.confidence_var,
                                  orient=tk.HORIZONTAL,
                                  bg="#2d2d2d",
                                  fg="#00ff00",
                                  troughcolor="#1e1e1e",
                                  activebackground="#00ff00",
                                  length=150,
                                  command=self.update_settings)
        confidence_scale.pack(padx=5, pady=2)
        
        # Animated status indicator
        self.status_frame = tk.Frame(header, bg="#1e1e1e")
        self.status_frame.pack(side=tk.RIGHT)
        self.status_label = tk.Label(self.status_frame,
                                   text="◉ DISCONNECTED",
                                   font=('Consolas', 10),
                                   bg="#1e1e1e",
                                   fg="#ff0000")
        self.status_label.pack()
        
        # Theme Toggle Button
        self.theme_button = ttk.Button(header, text="Toggle Theme", command=self.toggle_theme)
        self.theme_button.pack(side=tk.RIGHT, padx=5)

        # Add Daily Stats Display
        stats_frame = tk.Frame(controls_frame, bg="#2d2d2d", bd=1, relief="raised")
        stats_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(stats_frame, text="TODAY'S STATS", bg="#2d2d2d", fg="#00ff00").pack(padx=5, pady=2)
        
        self.wins_label = tk.Label(stats_frame, text="Wins: 0", bg="#2d2d2d", fg="#00ff00")
        self.wins_label.pack()
        self.losses_label = tk.Label(stats_frame, text="Losses: 0", bg="#2d2d2d", fg="#ff0000")
        self.losses_label.pack()
        self.winrate_label = tk.Label(stats_frame, text="Win Rate: 0%", bg="#2d2d2d", fg="#ffffff")
        self.winrate_label.pack()

        # Add Market Hours Indicator
        market_frame = tk.Frame(header, bg="#2d2d2d", bd=1, relief="raised")
        market_frame.pack(side=tk.RIGHT, padx=5)
        self.london_label = tk.Label(market_frame, text="LONDON: CLOSED", bg="#2d2d2d", fg="#ff0000")
        self.london_label.pack(pady=1)
        self.ny_label = tk.Label(market_frame, text="NEW YORK: CLOSED", bg="#2d2d2d", fg="#ff0000")
        self.ny_label.pack(pady=1)

        # Add bypass margin check toggle
        bypass_frame = tk.Frame(controls_frame, bg="#2d2d2d", bd=1, relief="raised")
        bypass_frame.pack(side=tk.LEFT, padx=10)
        self.bypass_margin_var = tk.BooleanVar(value=self.bot.bypass_margin_check)
        bypass_toggle = tk.Checkbutton(bypass_frame,
                                        text="BYPASS MARGIN CHECK",
                                        variable=self.bypass_margin_var,
                                        bg="#2d2d2d",
                                        fg="#00ff00",
                                        selectcolor="#1e1e1e",
                                        activebackground="#2d2d2d",
                                        activeforeground="#00ff00",
                                        command=self.update_bypass_margin_check)
        bypass_toggle.pack(padx=5, pady=2)

    def update_bypass_margin_check(self):
        """Update the bypass margin check flag in the bot"""
        self.bot.bypass_margin_check = self.bypass_margin_var.get()

    def create_account_info(self):
        info_frame = ttk.LabelFrame(self.root, text="ACCOUNT METRICS")
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Create modern metric displays
        metrics_frame = tk.Frame(info_frame, bg="#1e1e1e")
        metrics_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Balance display with border
        balance_frame = tk.Frame(metrics_frame, bg="#2d2d2d", bd=1, relief="raised")
        balance_frame.pack(side=tk.LEFT, expand=True, padx=5)
        tk.Label(balance_frame, text="BALANCE", bg="#2d2d2d", fg="#00ff00").pack()
        self.balance_label = tk.Label(balance_frame, text="$0.00", 
                                    bg="#2d2d2d", fg="#ffffff",
                                    font=('Consolas', 12, 'bold'))
        self.balance_label.pack(pady=2)

        # Similar frames for equity and profit
        equity_frame = tk.Frame(metrics_frame, bg="#2d2d2d", bd=1, relief="raised")
        equity_frame.pack(side=tk.LEFT, expand=True, padx=5)
        tk.Label(equity_frame, text="EQUITY", bg="#2d2d2d", fg="#00ff00").pack()
        self.equity_label = tk.Label(equity_frame, text="$0.00",
                                   bg="#2d2d2d", fg="#ffffff",
                                   font=('Consolas', 12, 'bold'))
        self.equity_label.pack(pady=2)

        profit_frame = tk.Frame(metrics_frame, bg="#2d2d2d", bd=1, relief="raised")
        profit_frame.pack(side=tk.LEFT, expand=True, padx=5)
        tk.Label(profit_frame, text="PROFIT", bg="#2d2d2d", fg="#00ff00").pack()
        self.profit_label = tk.Label(profit_frame, text="$0.00",
                                   bg="#2d2d2d", fg="#ffffff",
                                   font=('Consolas', 12, 'bold'))
        self.profit_label.pack(pady=2)

    def create_positions_table(self):
        positions_frame = ttk.LabelFrame(self.root, text="Active Positions")
        positions_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Enhanced columns with more trading info
        columns = ('Symbol', 'Type', 'Volume', 'Entry', 'Current', 'SL', 'TP', 'Profit', 
                  'Pips', 'Duration', 'Spread', 'Mode')
        self.positions_tree = ttk.Treeview(positions_frame, columns=columns, show='headings')
        
        # Column configurations
        widths = {
            'Symbol': 80, 'Type': 60, 'Volume': 60, 'Entry': 80, 'Current': 80,
            'SL': 80, 'TP': 80, 'Profit': 80, 'Pips': 60, 'Duration': 80,
            'Spread': 60, 'Mode': 70
        }
        for col in columns:
            self.positions_tree.heading(col, text=col, command=lambda c=col: self.sort_positions(c))
            self.positions_tree.column(col, width=widths.get(col, 80))

        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(positions_frame, orient=tk.VERTICAL, command=self.positions_tree.yview)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.positions_tree.configure(yscrollcommand=y_scrollbar.set)
        
        self.positions_tree.pack(fill=tk.BOTH, expand=True)

        # Add right-click menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Close Position", command=self.close_selected_position)
        self.positions_tree.bind("<Button-3>", self.show_context_menu)

        # Add position controls
        controls_frame = ttk.Frame(positions_frame)
        controls_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(controls_frame, text="Close All", command=self.close_all_positions).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Close Profits", command=self.close_profit_positions).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Break Even", command=self.move_to_breakeven).pack(side=tk.LEFT, padx=5)

    def show_context_menu(self, event):
        item = self.positions_tree.identify_row(event.y)
        if item:
            self.positions_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def close_selected_position(self):
        selected = self.positions_tree.selection()
        if selected:
            item = selected[0]
            symbol = self.positions_tree.item(item)['values'][0]
            self.bot.close_position(symbol)

    def create_log_area(self):
        log_frame = ttk.LabelFrame(self.root, text="Bot Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(log_frame, height=8)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Clear Log Button
        self.clear_log_button = ttk.Button(log_frame, text="Clear Log", command=self.clear_log)
        self.clear_log_button.pack(pady=5)

    def update_account_info(self):
        if not mt5.initialize():
            return
            
        account_info = mt5.account_info()
        if account_info:
            self.balance_label.config(text=f"${account_info.balance:.2f}")
            self.equity_label.config(text=f"${account_info.equity:.2f}")
            self.profit_label.config(text=f"${account_info.profit:.2f}")
            
            if account_info.profit > 0:
                self.profit_label.config(fg="#00ff00")
            elif account_info.profit < 0:
                self.profit_label.config(fg="#ff0000")

    def update_positions_table(self):
        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)
            
        positions = mt5.positions_get()
        if positions:
            for pos in positions:
                # Calculate pips and duration
                current_tick = mt5.symbol_info_tick(pos.symbol)
                if current_tick:
                    pip_value = self.bot.SYMBOL_MAPPINGS[pos.symbol]['pip_value']
                    pips = (current_tick.bid - pos.price_open) / pip_value if pos.type == 0 else (pos.price_open - current_tick.ask) / pip_value
                    duration = datetime.now() - datetime.fromtimestamp(pos.time)
                    spread = (current_tick.ask - current_tick.bid) / pip_value
                    
                    values = (
                        pos.symbol,
                        "BUY" if pos.type == 0 else "SELL",
                        pos.volume,
                        f"{pos.price_open:.5f}",
                        f"{current_tick.bid:.5f}" if pos.type == 0 else f"{current_tick.ask:.5f}",
                        f"{pos.sl:.5f}",
                        f"{pos.tp:.5f}",
                        f"${pos.profit:.2f}",
                        f"{pips:.1f}",
                        str(duration).split('.')[0],
                        f"{spread:.1f}",
                        "Scalp" if "Scalp" in pos.comment else "Normal"
                    )
                    
                    # Color based on profit/loss
                    tag = 'profit' if pos.profit > 0 else 'loss'
                    self.positions_tree.insert('', tk.END, values=values, tags=(tag,))

        self.update_daily_stats()

    def update_daily_stats(self):
        """Update daily trading statistics"""
        closed_positions = mt5.history_deals_get(
            datetime.now().replace(hour=0, minute=0, second=0),
            datetime.now()
        )
        
        if closed_positions:
            wins = len([pos for pos in closed_positions if pos.profit > 0])
            losses = len([pos for pos in closed_positions if pos.profit < 0])
            total = wins + losses
            winrate = (wins / total * 100) if total > 0 else 0
            
            self.wins_label.config(text=f"Wins: {wins}")
            self.losses_label.config(text=f"Losses: {losses}")
            self.winrate_label.config(text=f"Win Rate: {winrate:.1f}%")

    def update_market_hours(self):
        """Update market session indicators with proper timezone handling"""
        try:
            # Get current UTC time
            now = datetime.now(self.timezone)
            
            # London (7:00-16:00 UTC)
            london_active = 7 <= now.hour < 16 and now.weekday() < 5
            self.london_label.config(
                text="LONDON: OPEN" if london_active else "LONDON: CLOSED",
                fg="#00ff00" if london_active else "#ff0000"
            )
            
            # New York (13:00-22:00 UTC)
            ny_active = 13 <= now.hour < 22 and now.weekday() < 5
            self.ny_label.config(
                text="NEW YORK: OPEN" if ny_active else "NEW YORK: CLOSED",
                fg="#00ff00" if ny_active else "#ff0000"
            )
        except Exception as e:
            self.add_log(f"Error updating market hours: {e}")

    def add_log(self, message):
        """Thread-safe logging with timezone"""
        try:
            timestamp = datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M:%S %Z")
            formatted_message = f"{timestamp} - {message}"
            
            # Add to queue for GUI
            self.log_queue.put(formatted_message)
            
            # Print to console as backup
            print(formatted_message)
        except Exception as e:
            print(f"Logging error: {e}")
            print(message)  # Fallback

    def _write_log(self, message):
        """Actually write the message to the log text widget"""
        try:
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)  # Auto-scroll to bottom
            
            # Limit log size to last 1000 lines
            num_lines = int(self.log_text.index('end-1c').split('.')[0])
            if num_lines > 1000:
                self.log_text.delete('1.0', f'{num_lines-1000}.0')
        except Exception as e:
            print(f"Error writing to log: {e}")

    def process_logs(self):
        """Process any pending log messages in the queue"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self._write_log(message)
        except queue.Empty:
            pass
        finally:
            # Schedule next check
            self.root.after(100, self.process_logs)

    def update_loop(self):
        """Fixed update loop with better error handling"""
        try:
            if not self.root.winfo_exists():
                return

            # Check MT5 connection
            if not mt5.initialize():
                self.status_label.config(text="◉ DISCONNECTED", fg="#ff0000")
                return

            # Update account info
            account_info = mt5.account_info()
            if account_info:
                self.status_label.config(text="◉ CONNECTED", fg="#00ff00")
                self.update_account_info()
                self.update_positions_table()
                self.update_market_hours()

        except Exception as e:
            self.add_log(f"GUI update error: {e}")
        finally:
            if self.root.winfo_exists():
                self.root.after(1000, self.update_loop)

    def run(self):
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"Error in GUI mainloop: {e}")
        
    def toggle_bot(self):
        try:
            if not mt5.initialize():
                self.add_log("Cannot start bot - MT5 not connected")
                return

            self.is_running = not self.is_running
            if self.is_running:
                self.start_stop_button.config(text="Stop Bot")
                self.add_log("Bot started - Trading configured pairs")
                # Update bot settings from GUI
                self.bot.RISK_PERCENTAGE = self.risk_var.get()
                self.bot.scalping_enabled = self.scalping_var.get()
                self.bot.confidence_threshold = self.confidence_var.get()
            else:
                self.start_stop_button.config(text="Start Bot")
                self.add_log("Bot stopped")
                
        except Exception as e:
            self.add_log(f"Error toggling bot: {e}")
            self.is_running = False
            self.start_stop_button.config(text="Start Bot")

    def update_settings(self, *args):
        """Update bot settings when GUI controls change"""
        try:
            self.bot.RISK_PERCENTAGE = self.risk_var.get()
            self.bot.scalping_enabled = self.scalping_var.get()
            self.bot.confidence_threshold = self.confidence_var.get()
            self.add_log(f"Settings updated - Risk: {self.risk_var.get()}%, Scalping: {self.scalping_var.get()}")
        except Exception as e:
            self.add_log(f"Error updating settings: {e}")

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)
        
    def toggle_theme(self):
        if self.current_theme == "dark":
            self.set_light_theme()
            self.current_theme = "light"
        else:
            self.set_dark_theme()
            self.current_theme = "dark"

    def set_dark_theme(self):
        self.style.configure(".", font=('Segoe UI', 9))
        self.style.configure("TFrame", background="#1e1e1e")
        self.style.configure("TLabel", background="#1e1e1e", foreground="#00ff00")
        self.style.configure("TLabelframe", background="#1e1e1e", foreground="#00ff00")
        self.style.configure("TLabelframe.Label", background="#1e1e1e", foreground="#00ff00")
        self.style.configure("Treeview", 
                           background="#2d2d2d", 
                           foreground="#ffffff", 
                           fieldbackground="#2d2d2d")
        self.style.configure("Treeview.Heading", 
                           background="#3d3d3d", 
                           foreground="#00ff00")
        self.root.configure(bg="#1e1e1e")
        
    def set_light_theme(self):
        self.style.configure(".", font=('Segoe UI', 9))
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", foreground="#000000")
        self.style.configure("TLabelframe", background="#f0f0f0", foreground="#000000")
        self.style.configure("TLabelframe.Label", background="#f0f0f0", foreground="#000000")
        self.style.configure("Treeview", 
                           background="#ffffff", 
                           foreground="#000000", 
                           fieldbackground="#ffffff")
        self.style.configure("Treeview.Heading", 
                           background="#d0d0d0", 
                           foreground="#000000")
        self.root.configure(bg="#f0f0f0")

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def sort_positions(self, column):
        """Sort position table by column"""
        items = [(self.positions_tree.set(item, column), item) for item in self.positions_tree.get_children('')]
        items.sort()
        
        for index, (_, item) in enumerate(items):
            self.positions_tree.move(item, '', index)

    def close_all_positions(self):
        """Close all open positions with error handling"""
        try:
            positions = mt5.positions_get()
            if positions:
                for pos in positions:
                    success = self.bot.close_position(pos.symbol)
                    if success:
                        self.add_log(f"Closed position for {pos.symbol}")
                    else:
                        self.add_log(f"Failed to close position for {pos.symbol}")
        except Exception as e:
            self.add_log(f"Error closing all positions: {e}")

    def close_profit_positions(self):
        """Close all positions in profit"""
        positions = mt5.positions_get()
        if positions:
            for pos in positions:
                if pos.profit > 0:
                    self.bot.close_position(pos.symbol)

    def move_to_breakeven(self):
        """Move stop loss to entry for all positions in profit"""
        positions = mt5.positions_get()
        if positions:
            for pos in positions:
                if pos.profit > 0:
                    request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "symbol": pos.symbol,
                        "position": pos.ticket,
                        "sl": pos.price_open
                    }
                    mt5.order_send(request)
