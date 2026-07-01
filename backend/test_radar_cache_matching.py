"""
Teste reproduzivel do matching de cache do Radar Smart Money (pos-correcao).

Replica FIELMENTE a logica das duas pontas apos a correcao:

  PONTA A (escrita no Lab / renderSteamTable, app.js):
      backtestCache[r.code] = {...}
      r.code vem do backend /scan_steam_moves como "<league_code>|<market>"
      (ex.: "BRA|home") - market minusculo, canonico.

  PONTA B (leitura no Ao Vivo / renderLiveSteamTable, app.js):
      league_code vem do backend via map_sport_to_league_code() (canonico)
      normMkt = canonicalMarketCode(item.market) (home/away/draw/over25/under25)
      cacheKey = `${item.league_code}|${normMkt}`

Objetivo: garantir chave gravada == chave lida em TODOS os casos, inclusive
ligas fora do mapa (fallback 'OUTROS') e variacoes de rotulo de mercado.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.live_odds_tracker import map_sport_to_league_code, UNMAPPED_LEAGUE_CODE


def lab_cache_key(league_code, market_canonical):
    return f"{league_code}|{market_canonical}"


def canonical_market_code(market_raw):
    """Replica fiel de canonicalMarketCode() do app.js."""
    if not market_raw:
        return ''
    m = ''.join(ch for ch in str(market_raw).lower() if ch.isalnum())
    if m == 'home':
        return 'home'
    if m == 'away':
        return 'away'
    if m == 'draw':
        return 'draw'
    if m.startswith('over'):
        return 'over25'
    if m.startswith('under'):
        return 'under25'
    return m


def live_cache_key(sport_key, market_raw):
    league_code = map_sport_to_league_code(sport_key)
    return f"{league_code}|{canonical_market_code(market_raw)}"


def check(sport_key, market_from_backend, lab_league_code, lab_market_canonical):
    key_written = lab_cache_key(lab_league_code, lab_market_canonical)
    key_read = live_cache_key(sport_key, market_from_backend)
    return key_written, key_read, key_written == key_read


if __name__ == '__main__':
    print("=" * 78)
    print(" TESTE DE MATCHING DE CACHE - Radar Smart Money (Lab -> Ao Vivo)")
    print(" (pos-correcao: funcao canonica unica de liga + mercado)")
    print("=" * 78)

    scenarios = [
        ("Brasileirao / Home  (liga MAPEADA)",            "soccer_brazil_campeonato",      "HOME",      "BRA",    "home"),
        ("Premier League / Home (liga MAPEADA)",          "soccer_epl",                    "HOME",      "E0",     "home"),
        ("La Liga / Draw (liga MAPEADA)",                 "soccer_spain_la_liga",          "DRAW",      "SP1",    "draw"),
        ("Serie A / Over 2.5 (backend manda OVER25)",     "soccer_italy_serie_a",          "OVER25",    "I1",     "over25"),
        ("Eredivisie / Under (variacao UNDER 2.5)",       "soccer_netherlands_eredivisie", "UNDER 2.5", "N1",     "under25"),
        ("Copa do Mundo / Home (liga NAO mapeada)",       "soccer_fifa_world_cup",         "HOME",      "OUTROS", "home"),
        ("Liga obscura / Away (NAO mapeada)",             "soccer_random_league_xyz",      "AWAY",      "OUTROS", "away"),
    ]

    all_ok = True
    for desc, sk, mkt_live, lab_lc, lab_mkt in scenarios:
        kw, kr, ok = check(sk, mkt_live, lab_lc, lab_mkt)
        all_ok = all_ok and ok
        status = "[OK] MATCH" if ok else "[X] NAO BATE"
        print(f"\n{desc}")
        print(f"   Lab grava   : '{kw}'")
        print(f"   Ao Vivo le  : '{kr}'")
        print(f"   {status}")

    print("\n" + "=" * 78)
    print(" SUB-TESTE: canonicalMarketCode aceita todas as variacoes de rotulo")
    variations = ['OVER25', 'OVER 2.5', 'OVER_2.5', 'over 2.5', 'Over2.5',
                  'UNDER25', 'UNDER 2.5', 'HOME', 'Home', 'home', 'DRAW']
    for raw in variations:
        print(f"   '{raw:<12}' -> '{canonical_market_code(raw)}'")

    print("=" * 78)
    print(f"\nUNMAPPED_LEAGUE_CODE (fallback compartilhado) = '{UNMAPPED_LEAGUE_CODE}'")
    print(f"\nRESULTADO GERAL: {'TODOS OS NICHOS BATEM' if all_ok else 'HA NICHOS QUE NAO BATEM -> filtro esconde drops'}")
    sys.exit(0 if all_ok else 1)
