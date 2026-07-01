import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

# Add parent dir to path so we can import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.smart_money import _extract_steam_moves_from_df, SmartMoneyBacktester

def create_mock_df():
    # Criar um dataframe simulado com 5 partidas, com odds Bet365 e resultados
    data = {
        'Date': ['2026-06-01', '2026-06-02', '2026-06-03', '2026-06-04', '2026-06-05'],
        'HomeTeam': ['Flamengo', 'Palmeiras', 'Sao Paulo', 'Corinthians', 'Gremio'],
        'AwayTeam': ['Vasco', 'Santos', 'Santos', 'Vasco', 'Palmeiras'],
        'FTR': ['H', 'H', 'D', 'A', 'H'],
        'FTHG': [2, 3, 1, 0, 2],
        'FTAG': [0, 1, 1, 1, 1],
        'B365H': [2.20, 1.80, 2.00, 2.50, 2.10],
        'B365D': [3.30, 3.40, 3.20, 3.10, 3.20],
        'B365A': [3.10, 4.20, 3.60, 2.80, 3.30]
    }
    return pd.DataFrame(data)

def test_csv_latency():
    print("\n[Test 1] Testando latência na extração de CSV...")
    df = create_mock_df()
    
    # 1. Sem latência (0s)
    moves_no_latency = _extract_steam_moves_from_df(
        df=df,
        league_code='BRA',
        markets=['home', 'away', 'draw'],
        min_drop_pct=2.0,
        stake_value=10.0,
        start_date='2026-05-01',
        end_date='2026-07-01',
        latency_seconds=0
    )
    
    # 2. Com latência alta (120s)
    moves_with_latency = _extract_steam_moves_from_df(
        df=df,
        league_code='BRA',
        markets=['home', 'away', 'draw'],
        min_drop_pct=2.0,
        stake_value=10.0,
        start_date='2026-05-01',
        end_date='2026-07-01',
        latency_seconds=120
    )
    
    print(f"Total moves detectados: {len(moves_no_latency)}")
    assert len(moves_no_latency) == len(moves_with_latency)
    
    for m_no, m_lat in zip(moves_no_latency, moves_with_latency):
        if m_no['won']:
            print(f"Jogo: {m_no['match']} | Mercado: {m_no['market']}")
            print(f"  - Odd Original: {m_no['current_odd']}")
            print(f"  - Odd com Latência: {m_lat['executed_odd']}")
            print(f"  - Lucro Original: {m_no['profit']}")
            print(f"  - Lucro com Latência: {m_lat['profit']}")
            assert m_lat['executed_odd'] <= m_no['current_odd']
            assert m_lat['profit'] <= m_no['profit']
            
    print("Test 1 OK!")

def test_live_latency():
    print("\n[Test 2] Testando latência no backtest de alertas Live...")
    
    # Mock de carregamento de histórico de alertas
    mock_alerts = [
        {
            'date': '2026-06-30 12:00',
            'match': 'Flamengo vs Vasco',
            'league_code': 'BRA',
            'bookmaker': 'Bet365',
            'market': 'home',
            'opening_odd': 2.0,
            'current_odd': 1.70,
            'drop_pct': 17.6,
            'won': True,
            'resolved': True,
            'stake_value': 10.0,
            'source': 'live'
        }
    ]
    
    # Subclassificamos o backtester para usar nossos alertas mockados
    class MockBacktester(SmartMoneyBacktester):
        def _load_history_alerts(self):
            import copy
            return copy.deepcopy(mock_alerts)
            
        def _load_league_df(self, league_code, start_date):
            return pd.DataFrame() # Sem dados CSV
            
    # 1. Sem latência (0s)
    bt_no = MockBacktester()
    res_no = bt_no.scan_steam_moves(
        league_code='BRA',
        markets=['home'],
        latency_seconds=0
    )
    
    # 2. Com latência (60s)
    bt_lat = MockBacktester()
    res_lat = bt_lat.scan_steam_moves(
        league_code='BRA',
        markets=['home'],
        latency_seconds=60
    )
    
    # Filtra o nicho 'BRA|home'
    n_no = [r for r in res_no if r['code'] == 'BRA|home'][0]
    n_lat = [r for r in res_lat if r['code'] == 'BRA|home'][0]
    
    print(f"Nicho BRA|home:")
    print(f"  - Lucro Total Sem Latência: {n_no['net_profit']} (ROI: {n_no['roi']}%)")
    print(f"  - Lucro Total Com Latência (60s): {n_lat['net_profit']} (ROI: {n_lat['roi']}%)")
    
    assert n_lat['net_profit'] < n_no['net_profit']
    assert n_lat['roi'] < n_no['roi']
    print("Test 2 OK!")

if __name__ == "__main__":
    print("Iniciando testes da Simulação de Latência de Execução...")
    test_csv_latency()
    test_live_latency()
    print("\nTodos os testes de simulação de latência passaram com sucesso!")
