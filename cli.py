import click
import pandas as pd
from bot import OandaTradingBot
from backtest import backtest as run_backtest, walk_forward_analysis
from ml_predictor import MLPredictor
from database import TradeDatabase
import logging

@click.group()
def cli():
    """Oanda Trading Bot CLI - Enhanced with ML, Multi-timeframe, and Advanced Features."""
    pass

@cli.command()
@click.option('--enable-ml/--no-ml', default=False, help='Enable ML predictions')
@click.option('--enable-multiframe/--no-multiframe', default=True, help='Enable multi-timeframe analysis')
@click.option('--position-sizing', default='fixed_percentage', 
              type=click.Choice(['fixed_percentage', 'kelly_criterion']),
              help='Position sizing method')
def start(enable_ml, enable_multiframe, position_sizing):
    """Start the trading bot with configurable features."""
    click.echo(f"Starting trading bot...")
    click.echo(f"  ML Predictions: {enable_ml}")
    click.echo(f"  Multi-timeframe: {enable_multiframe}")
    click.echo(f"  Position Sizing: {position_sizing}")
    
    bot = OandaTradingBot(
        enable_ml=enable_ml,
        enable_multiframe=enable_multiframe,
        position_sizing_method=position_sizing
    )
    bot.run()

@cli.command()
@click.option('--instrument', default='EUR_USD', help='Trading instrument')
@click.option('--strategy', default='advanced_scalp', help='Strategy to backtest')
@click.option('--cash', default=10000.0, help='Initial portfolio value')
def backtest(instrument, strategy, cash):
    """Run backtest for an instrument with enhanced metrics."""
    click.echo(f"Running backtest for {instrument} using {strategy} strategy...")
    
    # Note: In production, you would load real historical data here
    # For now, we'll create sample data
    import numpy as np
    np.random.seed(42)
    n = 500
    base_price = 1.1000
    
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n, freq='5min')
    prices = base_price + np.cumsum(np.random.randn(n) * 0.0001)
    
    data = pd.DataFrame({
        'open': prices + np.random.randn(n) * 0.00005,
        'high': prices + abs(np.random.randn(n) * 0.0001),
        'low': prices - abs(np.random.randn(n) * 0.0001),
        'close': prices,
        'volume': np.random.randint(100, 1000, n)
    }, index=dates)
    
    result = run_backtest(instrument, data, strategy, cash)
    
    click.echo("\nBacktest completed successfully!")
    click.echo(f"Review the results above for detailed metrics.")

@cli.command()
@click.option('--instrument', default='EUR_USD', help='Trading instrument')
@click.option('--strategy', default='advanced_scalp', help='Strategy to test')
@click.option('--train-period', default=252, help='Training period in bars')
@click.option('--test-period', default=63, help='Testing period in bars')
def walkforward(instrument, strategy, train_period, test_period):
    """Run walk-forward analysis for robust strategy testing."""
    click.echo(f"Running walk-forward analysis for {instrument}...")
    
    # Create sample data
    import numpy as np
    np.random.seed(42)
    n = 1000
    base_price = 1.1000
    
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n, freq='5min')
    prices = base_price + np.cumsum(np.random.randn(n) * 0.0001)
    
    data = pd.DataFrame({
        'open': prices + np.random.randn(n) * 0.00005,
        'high': prices + abs(np.random.randn(n) * 0.0001),
        'low': prices - abs(np.random.randn(n) * 0.0001),
        'close': prices,
        'volume': np.random.randint(100, 1000, n)
    }, index=dates)
    
    result = walk_forward_analysis(
        instrument, data, strategy, 
        train_period, test_period
    )
    
    if result:
        click.echo("\nWalk-forward analysis completed!")
    else:
        click.echo("\nWalk-forward analysis failed - check logs for details.")

@cli.command()
@click.option('--min-samples', default=200, help='Minimum samples for training')
def train_ml(min_samples):
    """Train the ML model on historical data."""
    click.echo(f"Training ML model...")
    
    db = TradeDatabase()
    predictor = MLPredictor()
    
    # Get training data from database
    df = db.get_training_data(min_samples=min_samples)
    
    if len(df) < min_samples:
        click.echo(f"Insufficient data for training. Have {len(df)}, need {min_samples}")
        click.echo("Run the bot for a while to collect more data.")
        return
    
    # Train model
    metrics = predictor.train(df, database=db)
    
    if metrics:
        click.echo("\nML Model Training Complete!")
        click.echo(f"  Accuracy: {metrics['accuracy']:.4f}")
        click.echo(f"  Precision: {metrics['precision']:.4f}")
        click.echo(f"  Recall: {metrics['recall']:.4f}")
        click.echo(f"  F1 Score: {metrics['f1']:.4f}")
        click.echo(f"  Training Samples: {metrics['training_samples']}")
    else:
        click.echo("ML model training failed.")
    
    db.close()

@cli.command()
@click.option('--days', default=30, help='Number of days to analyze')
def stats(days):
    """Display trading performance statistics."""
    click.echo(f"Trading Statistics (Last {days} days)")
    click.echo("="*60)
    
    db = TradeDatabase()
    metrics = db.get_performance_metrics(days=days)
    
    if not metrics or metrics.get('total_trades', 0) == 0:
        click.echo("No trading data available.")
        db.close()
        return
    
    click.echo(f"Total Trades: {metrics['total_trades']}")
    click.echo(f"Winning Trades: {metrics['winning_trades']}")
    click.echo(f"Losing Trades: {metrics['losing_trades']}")
    click.echo(f"Win Rate: {metrics['win_rate']*100:.2f}%")
    click.echo(f"Total Profit: ${metrics['total_profit']:.2f}")
    click.echo(f"Average Win: ${metrics['average_profit']:.2f}")
    click.echo(f"Average Loss: ${metrics['average_loss']:.2f}")
    click.echo(f"Largest Win: ${metrics['largest_win']:.2f}")
    click.echo(f"Largest Loss: ${metrics['largest_loss']:.2f}")
    click.echo("="*60)
    
    db.close()

if __name__ == '__main__':
    cli()