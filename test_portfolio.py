import sys
import traceback
from backend.portfolio_backtester import run_portfolio
from backend.history_manager import load_history

try:
    history = load_history()
    if history:
        strat_id = history[0]['id']
        res = run_portfolio([strat_id], 1000.0, 'fixed_3')
        if "error" in res:
            print("Error returned:", res["error"])
        else:
            print("Success")
    else:
        print("No history found")
except Exception as e:
    traceback.print_exc()
