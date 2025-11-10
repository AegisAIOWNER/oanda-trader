import oandapyV20
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.positions as positions
import pandas as pd
import time
import logging
from datetime import datetime
from config import *
from strategies import get_signal

class OandaTradingBot:
    def __init__(self):
        self.api = oandapyV20.API(access_token=API_KEY, environment=ENVIRONMENT)
        self.account_id = ACCOUNT_ID
        self.last_request_time = time.time()
        self.daily_pnl = 0.0
        self.daily_start_balance = self.get_balance()
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def _rate_limited_request(self, endpoint):
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = current_time
        try:
            return self.api.request(endpoint)
        except Exception as e:
            if '429' in str(e):
                logging.warning("Rate limit hit, sleeping longer.")
                time.sleep(RATE_LIMIT_DELAY * 2)
                return self._rate_limited_request(endpoint)
            raise

    def get_balance(self):
        r = accounts.AccountSummary(accountID=self.account_id)
        response = self._rate_limited_request(r)
        return float(response['account']['balance'])

    def check_margin(self):
        r = accounts.AccountSummary(accountID=self.account_id)
        response = self._rate_limited_request(r)
        margin_available = float(response['account']['marginAvailable'])
        balance = float(response['account']['balance'])
        return margin_available > (balance * MARGIN_BUFFER)

    def get_prices(self, instrument, count=50, granularity='H1'):
        params = {'count': count, 'granularity': granularity}
        r = pricing.PricingCandles(instrument=instrument, params=params)
        response = self._rate_limited_request(r)
        candles = response['candles']
        data = []
        for c in candles:
            if c['complete']:
                data.append({
                    'time': c['time'],
                    'open': float(c['mid']['o']),
                    'high': float(c['mid']['h']),
                    'low': float(c['mid']['l']),
                    'close': float(c['mid']['c']),
                    'volume': int(c['volume'])
                })
        return pd.DataFrame(data)

    def place_order(self, instrument, side, units, sl_pips=None, tp_pips=None):
        if not self.check_margin():
            logging.warning(f"Insufficient margin for {instrument}, skipping.")
            return
        data = {
            'order': {
                'instrument': instrument,
                'units': units if side == 'BUY' else -units,
                'type': 'MARKET',
                'timeInForce': 'FOK'
            }
        }
        if sl_pips:
            data['order']['stopLossOnFill'] = {'distance': str(sl_pips)}
        if tp_pips:
            data['order']['takeProfitOnFill'] = {'distance': str(tp_pips)}
        r = orders.OrderCreate(accountID=self.account_id, data=data)
        response = self._rate_limited_request(r)
        logging.info(f"Order placed for {instrument}: {response}")
        return response

    def run_cycle(self):
        for instrument in INSTRUMENTS:
            df = self.get_prices(instrument)
            signal = get_signal(df, STRATEGY)
            if signal:
                units = DEFAULT_UNITS
                sl = STOP_LOSS_PIPS if signal == 'BUY' else None  # Adjust for sell
                tp = TAKE_PROFIT_PIPS if signal == 'BUY' else None
                self.place_order(instrument, signal, units, sl, tp)
        # Daily loss check
        current_balance = self.get_balance()
        if (self.daily_start_balance - current_balance) / self.daily_start_balance > MAX_DAILY_LOSS_PERCENT / 100:
            logging.error("Daily loss limit reached, stopping.")
            return False
        return True

    def run(self, interval=3600):
        while True:
            if not self.run_cycle():
                break
            time.sleep(interval)

if __name__ == '__main__':
    bot = OandaTradingBot()
    bot.run()