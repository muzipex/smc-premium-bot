ML_SETTINGS = {
    'training': {
        'min_samples': 1000,
        'train_interval_hours': 24,
        'validation_split': 0.2,
        'min_validation_score': 0.6
    },
    'prediction': {
        'min_confidence': 70,
        'volume_threshold': 1.0,
        'rsi_overbought': 70,
        'rsi_oversold': 30
    },
    'features': {
        'price_windows': [5, 10, 20],
        'volume_windows': [5, 10],
        'momentum_window': 4,
        'volatility_window': 10,
        'bollinger_window': 20,
        'bollinger_std': 2
    }
}
