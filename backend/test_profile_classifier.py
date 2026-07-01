import sys
import os
from datetime import datetime, timedelta, timezone

# Add parent dir to path so we can import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.smart_money import classify_drop_profile

def test_sharp_pinnacle():
    print("\n[Test 1] Pinnacle Sharp Drop (Esperado: Sharps)")
    # Pinnacle, Premier League (E0), 24h antes, drop 8%
    commence_time = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    score, profile = classify_drop_profile(
        drop_pct=8.0,
        league_identifier="soccer_epl", # Tier Alta
        commence_time_str=commence_time,
        bookmaker_name="Pinnacle",
        match_entry=None,
        comp_key=None
    )
    print(f"Score: {score}% | Perfil: {profile}")
    assert profile == "Sharps", f"Esperado Sharps, obteve {profile}"
    assert score >= 60.0, f"Esperado score >= 60, obteve {score}"
    print("Test 1 OK!")

def test_square_recreative_no_consensus():
    print("\n[Test 2] Recreational Bookie Tipster/Square Drop (Esperado: Squares)")
    # BetMGM, Campeonato Norueguês (NORWAY_ELITESERIEN - Tier Média/Baixa), 1.5h antes, drop 6%, Pinnacle sem drop
    commence_time = (datetime.now(timezone.utc) + timedelta(hours=1.5)).isoformat()
    mock_match_entry = {
        'bookmakers': {
            'Pinnacle': {
                'h2h_home': {
                    'opening': 2.0,
                    'current': 2.0 # Sem queda na Pinnacle
                }
            }
        }
    }
    score, profile = classify_drop_profile(
        drop_pct=6.0,
        league_identifier="soccer_norway_eliteserien",
        commence_time_str=commence_time,
        bookmaker_name="BetMGM",
        match_entry=mock_match_entry,
        comp_key="h2h_home"
    )
    print(f"Score: {score}% | Perfil: {profile}")
    assert profile == "Squares", f"Esperado Squares, obteve {profile}"
    print("Test 2 OK!")

def test_sharp_recreative_with_consensus():
    print("\n[Test 3] Recreational Bookie with Pinnacle Consensus (Esperado: Sharps)")
    # Bet365, La Liga (SP1 - Tier Alta), 10h antes, drop 8.5%, Pinnacle também caiu
    commence_time = (datetime.now(timezone.utc) + timedelta(hours=10)).isoformat()
    mock_match_entry = {
        'bookmakers': {
            'Pinnacle': {
                'h2h_home': {
                    'opening': 2.00,
                    'current': 1.85 # Queda de ~8.1% na Pinnacle
                }
            }
        }
    }
    score, profile = classify_drop_profile(
        drop_pct=8.5,
        league_identifier="soccer_spain_la_liga",
        commence_time_str=commence_time,
        bookmaker_name="Bet365",
        match_entry=mock_match_entry,
        comp_key="h2h_home"
    )
    print(f"Score: {score}% | Perfil: {profile}")
    assert profile == "Sharps", f"Esperado Sharps, obteve {profile}"
    print("Test 3 OK!")

def test_historical_csv_fallback():
    print("\n[Test 4] Fallback Histórico CSV (Tier Alta vs Tier Baixa)")
    # Tier Alta (E0), drop 6%
    score_high, profile_high = classify_drop_profile(
        drop_pct=6.0,
        league_identifier="E0",
        commence_time_str="2026-06-30",
        bookmaker_name="Bet365",
        match_entry=None,
        comp_key=None
    )
    print(f"E0 (Alta) -> Score: {score_high}% | Perfil: {profile_high}")
    assert profile_high == "Sharps", f"Esperado Sharps, obteve {profile_high}"

    # Tier Baixa (OUTROS), drop 6%
    score_low, profile_low = classify_drop_profile(
        drop_pct=6.0,
        league_identifier="OUTROS",
        commence_time_str="2026-06-30",
        bookmaker_name="Bet365",
        match_entry=None,
        comp_key=None
    )
    print(f"OUTROS (Baixa) -> Score: {score_low}% | Perfil: {profile_low}")
    assert profile_low == "Squares", f"Esperado Squares, obteve {profile_low}"
    print("Test 4 OK!")

if __name__ == "__main__":
    print("Iniciando testes do classificador de perfil de drop...")
    test_sharp_pinnacle()
    test_square_recreative_no_consensus()
    test_sharp_recreative_with_consensus()
    test_historical_csv_fallback()
    print("\nTodos os testes passaram com sucesso!")
