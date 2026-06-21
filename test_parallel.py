import time
from backend.portfolio_backtester import run_portfolio
from backend.history_manager import load_history
import concurrent.futures

def test():
    h = load_history()
    sids = [s['id'] for s in h[:6]]
    
    t = time.time()
    res = run_portfolio(sids, 1000, 'fixed_5')
    print("Sequential Time:", time.time() - t)

if __name__ == '__main__':
    test()
