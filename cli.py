import click
from bot import OandaTradingBot
from backtest import backtest

@click.group()
def cli():
    pass

@cli.command()
def start():
    """Start the trading bot."""
    bot = OandaTradingBot()
    bot.run()

@cli.command()
@click.option('--instrument', default='EUR_USD')
def backtest(instrument):
    """Run backtest for an instrument."""
    # Load data and run
    pass

if __name__ == '__main__':
    cli()