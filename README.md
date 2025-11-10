# Oanda Trading Bot

A scalable auto trading bot for Oanda.

## Setup

1. Create venv: `python -m venv venv`
2. Activate: `venv\Scripts\activate`
3. Install: `pip install -r requirements.txt`
4. Set env vars or edit config.py
5. Run: `python bot.py` or `python cli.py start`

## Features

- Rate limiting compliance
- Margin checks
- Multiple instruments
- Configurable strategies
- Backtesting
- CLI interface

## Security

Do not commit credentials. Use .env file.