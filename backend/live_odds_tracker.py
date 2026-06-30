import os
import json
import requests
from datetime import datetime, timedelta, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
TRACKER_FILE = os.path.join(DATA_DIR, 'live_odds_tracker.json')

API_KEY = '26ced02b008e91c1acdea04181df12ff'
SPORT = 'upcoming'
REGIONS = 'eu,uk,us'
MARKETS = 'h2h,spreads,totals'

def load_tracker_data():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(TRACKER_FILE):
        return {}
    try:
        with open(TRACKER_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_tracker_data(data):
    try:
        with open(TRACKER_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving live odds tracker: {e}")


SPORT_LEAGUE_MAP = {
    'soccer_epl': 'E0',
    'soccer_spain_la_liga': 'SP1',
    'soccer_italy_serie_a': 'I1',
    'soccer_germany_bundesliga': 'D1',
    'soccer_france_ligue_one': 'F1',
    'soccer_brazil_campeonato': 'BRA',
    'soccer_usa_mls': 'USA',
    'soccer_japan_j_league': 'JPN',
    'soccer_sweden_allsvenskan': 'SWEDEN_ALLSVENSKAN',
    'soccer_norway_eliteserien': 'NORWAY_ELITESERIEN'
}

def add_alert_to_history(alert_data):
    history_file = os.path.join(DATA_DIR, 'live_steam_moves_history.json')
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except Exception:
            history = []
            
    unique_id = f"{alert_data['match']}_{alert_data['bookmaker']}_{alert_data['market']}"
    for item in history:
        if item.get('unique_id') == unique_id:
            return
            
    alert_data['unique_id'] = unique_id
    history.append(alert_data)
    
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[Live Odds Tracker] Erro ao salvar histórico de alertas: {e}")

def cleanup_old_matches(data):
    now = datetime.now(timezone.utc)
    to_delete = []
    for match_id, match_data in data.items():
        try:
            commence_time = datetime.fromisoformat(match_data['commence_time'].replace('Z', '+00:00'))
            # If match started more than 12 hours ago, remove it
            if now > commence_time + timedelta(hours=12):
                to_delete.append(match_id)
        except:
            to_delete.append(match_id)
            
    for md in to_delete:
        del data[md]

def normalize_market_key(market_key, outcome_name, home_team, away_team):
    # Converts API market structure to our standard names
    if market_key == 'h2h':
        if outcome_name == home_team: return 'home'
        elif outcome_name == away_team: return 'away'
        else: return 'draw'
    elif market_key == 'totals':
        if outcome_name.lower() == 'over': return 'over25' # Simplified
        elif outcome_name.lower() == 'under': return 'under25'
    elif market_key == 'spreads':
        if outcome_name == home_team: return 'home_spread'
        elif outcome_name == away_team: return 'away_spread'
    return outcome_name

def fetch_and_update_live_odds():
    print("[Live Odds Tracker] Iniciando varredura The Odds API...")
    url = f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={API_KEY}&regions={REGIONS}&markets={MARKETS}'
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print(f"[Live Odds Tracker] API Error: {response.text}")
            return
            
        matches = response.json()
        data = load_tracker_data()
        cleanup_old_matches(data)
        
        updated_count = 0
        new_count = 0
        
        now_str = datetime.now(timezone.utc).isoformat()
        
        for match in matches:
            match_id = match['id']
            home_team = match['home_team']
            away_team = match['away_team']
            sport_key = match['sport_key']
            commence_time = match['commence_time']
            
            # Skip non-soccer for simplicity if we only want soccer
            if 'soccer' not in sport_key.lower():
                continue
                
            if match_id not in data:
                data[match_id] = {
                    'title': f"{home_team} vs {away_team}",
                    'sport': sport_key,
                    'commence_time': commence_time,
                    'bookmakers': {}
                }
                new_count += 1
                
            match_entry = data[match_id]
            
            for bookie in match.get('bookmakers', []):
                bookie_name = bookie['title']
                if bookie_name not in match_entry['bookmakers']:
                    match_entry['bookmakers'][bookie_name] = {}
                    
                bookie_entry = match_entry['bookmakers'][bookie_name]
                
                for market in bookie.get('markets', []):
                    market_key = market['key'] # h2h, totals, spreads
                    
                    for outcome in market.get('outcomes', []):
                        outcome_name = outcome['name']
                        price = outcome['price']
                        
                        norm_market = normalize_market_key(market_key, outcome_name, home_team, away_team)
                        
                        # Use a composite key for market + outcome
                        # e.g., "h2h_home", "totals_over", "spreads_home_spread"
                        comp_key = f"{market_key}_{norm_market}"
                        
                        if comp_key not in bookie_entry:
                            bookie_entry[comp_key] = {
                                'market_type': market_key,
                                'outcome_name': outcome_name,
                                'norm_market': norm_market,
                                'opening': price,
                                'current': price,
                                'last_updated': now_str,
                                'telegram_sent': False
                            }
                        else:
                            # Update current price
                            if bookie_entry[comp_key]['current'] != price:
                                bookie_entry[comp_key]['current'] = price
                                bookie_entry[comp_key]['last_updated'] = now_str
                                updated_count += 1
                                
                                # Telegram & History Smart Money Check
                                opening = bookie_entry[comp_key]['opening']
                                if opening > 1.0 and price > 0.0 and price < opening:
                                    drop_pct = ((opening / price) - 1.0) * 100
                                    if drop_pct >= 5.0:
                                        try:
                                            from backend.smart_money import calculate_confidence_score
                                            sport_key = match_entry.get('sport', '')
                                            score, confidence_level, tier_name = calculate_confidence_score(drop_pct, sport_key)
                                            
                                            commence_time = match_entry.get('commence_time', '')
                                            try:
                                                from datetime import datetime, timezone
                                                dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                                                dt_local = dt.astimezone()
                                                date_str = dt_local.strftime('%d/%m %H:%M')
                                            except:
                                                date_str = commence_time
                                                
                                            # Map to internal league code
                                            mapped_league = SPORT_LEAGUE_MAP.get(sport_key, 'OUTROS')
                                            
                                            # Build historical alert entry
                                            alert_entry = {
                                                'date': date_str,
                                                'match': match_entry.get('title', 'Desconhecido'),
                                                'league_code': mapped_league,
                                                'bookmaker': bookie_name,
                                                'market': norm_market,
                                                'opening_odd': opening,
                                                'current_odd': price,
                                                'drop_pct': round(drop_pct, 1),
                                                'confidence_score': score,
                                                'confidence_level': confidence_level,
                                                'won': None,
                                                'profit': 0.0,
                                                'stake_value': 10.0,
                                                'resolved': False
                                            }
                                            add_alert_to_history(alert_entry)
                                            
                                            # Send Telegram alert if not sent yet
                                            if not bookie_entry[comp_key].get('telegram_sent', False):
                                                from backend.telegram_bot import send_telegram_message, format_telegram_smart_money_tip
                                                msg = format_telegram_smart_money_tip(
                                                    match_entry.get('title', 'Desconhecido'),
                                                    date_str,
                                                    bookie_name,
                                                    norm_market.upper(),
                                                    opening,
                                                    price,
                                                    drop_pct,
                                                    confidence_score=score,
                                                    confidence_level=confidence_level,
                                                    liquidity_tier=tier_name
                                                )
                                                send_telegram_message(msg)
                                                bookie_entry[comp_key]['telegram_sent'] = True
                                                print(f"[Live Odds Tracker] Telegram alert sent and saved in history for {match_entry.get('title')} ({drop_pct:.1f}%)")
                                        except Exception as e:
                                            print(f"[Live Odds Tracker] Erro ao registrar alerta/telegram: {e}")
                                
        save_tracker_data(data)
        print(f"[Live Odds Tracker] Finalizado. {new_count} novos jogos. {updated_count} odds atualizadas.")
        
        # Resolves any completed matches in historical alerts
        resolve_historical_steam_results()
        
    except Exception as e:
        print(f"[Live Odds Tracker] Exceção durante varredura: {e}")

def resolve_historical_steam_results():
    print("[Live Odds Tracker] Iniciando resolução de resultados de Smart Money...")
    history_file = os.path.join(DATA_DIR, 'live_steam_moves_history.json')
    if not os.path.exists(history_file):
        return
        
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except Exception:
        return
        
    updated = False
    loaded_dfs = {}
    
    from backend.data_loader import load_league_data
    import pandas as pd
    
    for item in history:
        if item.get('resolved', False) or item.get('won') is not None:
            continue
            
        date_str = item.get('date', '')
        try:
            now = datetime.now()
            dt_parts = date_str.split(' ')
            day_month = dt_parts[0].split('/')
            hour_min = dt_parts[1].split(':')
            match_dt = datetime(
                year=now.year,
                month=int(day_month[1]),
                day=int(day_month[0]),
                hour=int(hour_min[0]),
                minute=int(hour_min[1])
            )
            # If match started less than 3 hours ago, skip
            if datetime.now() < match_dt + timedelta(hours=3):
                continue
        except:
            continue
            
        lcode = item.get('league_code')
        if not lcode or lcode == 'OUTROS':
            item['won'] = False
            item['profit'] = -item.get('stake_value', 10.0)
            item['resolved'] = True
            updated = True
            continue
            
        if lcode not in loaded_dfs:
            try:
                df = load_league_data(lcode, start_date='2020-08-01')
                loaded_dfs[lcode] = df
            except Exception:
                loaded_dfs[lcode] = None
                
        df = loaded_dfs[lcode]
        if df is None or df.empty:
            continue
            
        teams = item.get('match', '').split(' vs ')
        if len(teams) != 2:
            continue
        home_target = teams[0].lower()
        away_target = teams[1].lower()
        
        match_row = None
        for _, row in df.iterrows():
            h_local = str(row.get('HomeTeam', '')).lower()
            a_local = str(row.get('AwayTeam', '')).lower()
            
            if (h_local in home_target or home_target in h_local) and (a_local in away_target or away_target in a_local):
                match_row = row
                break
                
        if match_row is not None:
            ftr = match_row.get('FTR')
            market = item.get('market', '').lower()
            stake = item.get('stake_value', 10.0)
            current_odd = item.get('current_odd', 1.0)
            
            won = False
            if market == 'home' and ftr == 'H': won = True
            elif market == 'draw' and ftr == 'D': won = True
            elif market == 'away' and ftr == 'A': won = True
            
            item['won'] = won
            item['profit'] = (current_odd - 1.0) * stake if won else -stake
            item['resolved'] = True
            updated = True
            print(f"[Live Odds Tracker] Alerta resolvido: {item.get('match')} | Mercado: {market} | Resultado: {ftr} | Ganhou? {won}")
            
    if updated:
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Live Odds Tracker] Erro ao salvar histórico resolvido: {e}")

if __name__ == '__main__':
    fetch_and_update_live_odds()
