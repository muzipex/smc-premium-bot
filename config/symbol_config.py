SYMBOL_MAPPINGS = {
    "EURUSDm": {  # Remove the 'm' suffix if using regular symbols
        "name": "EURUSDm",
        "pip_value": 0.0001,
        "min_lot": 0.01,
        "max_lot": 1.0,  # Reduced from 50.0
        "stop_loss_pips": 10,  # Reduced from 50
        "take_profit_pips": 20,  # Reduced from 100
        "commission": 0.0,
        "swap_long": -1.39,
        "swap_short": -0.89,
        "risk_reward_ratios": {
            "high_confidence": 3.0,  # >80% confidence
            "medium_confidence": 2.0, # 50-80% confidence
            "low_confidence": 1.5,   # <50% confidence
        },
        "max_spread": 3,  # Maximum allowed spread in pips
        "scalping": {
            "enabled": True,
            "sl_pips": 12,    # Balanced stop loss
            "tp_pips": 8,     # Smaller take profit for quick wins
            "max_spread": 1.5, # Tight spread requirement
            "min_margin_required": 50,
            "target_profit": 1.0  # $1 profit target (more conservative)
        },
        "max_positions": 3
    },
    "GBPUSDm": {
        "name": "GBPUSDm",
        "pip_value": 0.01,
        "min_lot": 0.01,
        "max_lot": 1.0,  # Reduced from 50.0
        "stop_loss_pips": 10,  # Reduced from 100
        "take_profit_pips": 20,  # Reduced from 200
        "commission": 0.0,
        "swap_long": -5.39,
        "swap_short": -4.89,
        "risk_reward_ratios": {
            "high_confidence": 4.0,
            "medium_confidence": 2.5,
            "low_confidence": 1.5,
        },
        "scalping": {
            "enabled": True,
            "sl_pips": 12,    # Balanced stop loss
            "tp_pips": 8,     # Smaller take profit for quick wins
            "max_spread": 1.5, # Tight spread requirement
            "min_margin_required": 50,
            "target_profit": 1.0  # $1 profit target (more conservative)
        },
        "max_positions": 3
    },
    "USDJPYm": {
        "name": "USDJPYm",
        "pip_value": 0.01,
        "min_lot": 0.01,
        "max_lot": 1.0,  # Reduced from 50.0
        "stop_loss_pips": 10,  # Reduced from 30
        "take_profit_pips": 20,  # Reduced from 60
        "commission": 0.0,
        "swap_long": -1.89,
        "swap_short": -0.89,
        "risk_reward_ratios": {
            "high_confidence": 3.0,
            "medium_confidence": 2.0,
            "low_confidence": 1.5,
        },
        "scalping": {
            "enabled": True,
            "sl_pips": 12,    # Balanced stop loss
            "tp_pips": 8,     # Smaller take profit for quick wins
            "max_spread": 1.5, # Tight spread requirement
            "min_margin_required": 50,
            "target_profit": 1.0  # $1 profit target (more conservative)
        }
    },
    "USDCADm": {
        "name": "USDCADm",
        "pip_value": 0.0001,
        "min_lot": 0.01,
        "max_lot": 1.0,  # Reduced from 50.0
        "stop_loss_pips": 10,  # Reduced from 200
        "take_profit_pips": 20,  # Reduced from 400
        "commission": 0.0,
        "swap_long": 0.0,
        "swap_short": 0.0,
        "risk_reward_ratios": {
            "high_confidence": 5.0,
            "medium_confidence": 3.0,
            "low_confidence": 2.0,
        },
        "scalping": {
            "enabled": True,
            "sl_pips": 12,    # Balanced stop loss
            "tp_pips": 8,     # Smaller take profit for quick wins
            "max_spread": 1.5, # Tight spread requirement
            "min_margin_required": 50,
            "target_profit": 1.0  # $1 profit target (more conservative)
        }
    }
}
