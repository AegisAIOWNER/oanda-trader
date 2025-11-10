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
from strategies import get_signal, get_signal_with_confidence

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

    def get_prices(self, instrument, count=50, granularity=GRANULARITY):
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

    def scan_pairs_for_signals(self):
        """Scan all configured pairs and return signals with confidence scores."""
        signals = []
        
        # Limit the number of pairs to scan based on config
        pairs_to_scan = INSTRUMENTS[:MAX_PAIRS_TO_SCAN]
        
        # Batch request optimization - collect all data first
        logging.info(f"Scanning {len(pairs_to_scan)} pairs for signals...")
        
        for instrument in pairs_to_scan:
            try:
                df = self.get_prices(instrument)
                
                if STRATEGY == 'advanced_scalp':
                    # Get signal with confidence and ATR
                    signal, confidence, atr = get_signal_with_confidence(
                        df, 
                        STRATEGY,
                        atr_period=ATR_PERIOD,
                        volume_ma_period=VOLUME_MA_PERIOD,
                        min_volume_ratio=MIN_VOLUME_RATIO
                    )
                else:
                    # Legacy strategy support
                    signal = get_signal(df, STRATEGY)
                    confidence = 1.0 if signal else 0.0
                    atr = 0.0
                
                if signal and confidence >= CONFIDENCE_THRESHOLD:
                    signals.append({
                        'instrument': instrument,
                        'signal': signal,
                        'confidence': confidence,
                        'atr': atr
                    })
                    logging.info(f"{instrument}: {signal} signal with confidence {confidence:.2f}")
                elif signal:
                    logging.info(f"{instrument}: {signal} signal rejected (confidence {confidence:.2f} < threshold {CONFIDENCE_THRESHOLD})")
                    
            except Exception as e:
                logging.error(f"Error scanning {instrument}: {e}")
                continue
        
        return signals
    
    def get_best_signal(self, signals):
        """Select the best signal based on confidence score."""
        if not signals:
            return None
        
        # Sort by confidence descending
        sorted_signals = sorted(signals, key=lambda x: x['confidence'], reverse=True)
        best = sorted_signals[0]
        
        logging.info(f"Best signal: {best['instrument']} {best['signal']} (confidence: {best['confidence']:.2f})")
        return best
    
    def calculate_atr_stops(self, atr, signal):
        """Calculate ATR-based stop loss and take profit."""
        if atr > 0:
            sl = atr * ATR_STOP_MULTIPLIER
            tp = atr * ATR_PROFIT_MULTIPLIER
            return sl, tp
        else:
            # Fallback to config defaults
            return STOP_LOSS_PIPS, TAKE_PROFIT_PIPS

    def run_cycle(self):
        # Check daily loss limit first
        current_balance = self.get_balance()
        daily_loss_pct = (self.daily_start_balance - current_balance) / self.daily_start_balance
        
        if daily_loss_pct > MAX_DAILY_LOSS_PERCENT / 100:
            logging.error(f"Daily loss limit reached ({daily_loss_pct*100:.2f}%), stopping.")
            return False
        
        # Check margin availability
        if not self.check_margin():
            logging.warning("Insufficient margin available, skipping this cycle.")
            return True
        
        # Scan all pairs for signals
        signals = self.scan_pairs_for_signals()
        
        if not signals:
            logging.info("No signals found in this cycle.")
            return True
        
        # Get the best signal (highest confidence)
        best_signal = self.get_best_signal(signals)
        
        if best_signal:
            instrument = best_signal['instrument']
            signal = best_signal['signal']
            atr = best_signal['atr']
            
            # Calculate ATR-based stops
            sl, tp = self.calculate_atr_stops(atr, signal)
            
            # Place order for the best signal only
            units = DEFAULT_UNITS
            logging.info(f"Placing order for {instrument}: {signal} with SL={sl:.4f}, TP={tp:.4f}")
            self.place_order(instrument, signal, units, sl, tp)
        
        return True

    def run(self, interval=CHECK_INTERVAL):
        while True:
            if not self.run_cycle():
                break
            time.sleep(interval)

if __name__ == '__main__':
    bot = OandaTradingBot()
    bot.run()