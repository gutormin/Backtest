import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# ─────────────────────────────────────────────
#  LIQUIDEZ E CONFIANÇA
# ─────────────────────────────────────────────

def estimate_liquidity_tier(league_identifier: str):
    """
    Estima a liquidez da liga baseado em sua sigla/nome.
    Retorna (tier_name, weight) onde:
    - tier_name: 'Alta', 'Média', 'Baixa'
    - weight: 1.0, 0.7, 0.4
    """
    if not league_identifier:
        return 'Baixa', 0.4
    lid = league_identifier.lower().strip()

    # Tier 1 - Alta Liquidez (Peso 1.0)
    t1_keys = [
        'e0', 'sp1', 'i1', 'd1', 'f1', 'bra',
        'premier_league', 'la_liga', 'serie_a', 'bundesliga', 'ligue1',
        'campeonato_brasileiro', 'brazil_serie_a'
    ]
    is_t1 = any(k in lid for k in t1_keys)
    if is_t1:
        if 'bundesliga2' in lid or 'bundesliga_2' in lid or 'serie_b' in lid or 'segunda' in lid:
            pass
        else:
            return 'Alta', 1.0

    # Tier 2 - Média Liquidez (Peso 0.7)
    t2_keys = [
        'e1', 'sp2', 'i2', 'd2', 'f2', 'n1', 'b1', 'p1', 't1', 'usa', 'jpn',
        'championship', 'segunda', 'serie_b', 'bundesliga2', 'bundesliga_2',
        'ligue2', 'eredivisie', 'primeira_liga', 'belgium_first_division',
        'super_league', 'mls', 'j_league', 'japan_j_league',
        'netherlands_eredivisie', 'portugal_primeira_liga', 'turkey_super_league'
    ]
    if any(k in lid for k in t2_keys):
        return 'Média', 0.7

    # Tier 3 - Baixa Liquidez (Peso 0.4)
    return 'Baixa', 0.4


def calculate_confidence_score(drop_pct: float, league_identifier: str):
    """
    Calcula um score de confiança de 0 a 100 com base no drop de odds e na liquidez da liga.
    Ligas de alta liquidez exigem menos variação para serem de alta confiança.
    Ligas de baixa liquidez exigem variações violentas para mitigar ruídos de baixo volume.
    Retorna (score, confidence_level, liquidity_tier)
    """
    tier_name, weight = estimate_liquidity_tier(league_identifier)
    if drop_pct <= 0:
        return 0.0, 'Baixa', tier_name

    if tier_name == 'Alta':
        score = min(100.0, 35.0 + (drop_pct * 12.0))
    elif tier_name == 'Média':
        score = min(100.0, 15.0 + (drop_pct * 8.0))
    else:  # Baixa
        score = min(100.0, drop_pct * 5.0)

    if score >= 75.0:
        confidence_level = 'Alta'
    elif score >= 45.0:
        confidence_level = 'Média'
    else:
        confidence_level = 'Baixa'

    return round(score, 1), confidence_level, tier_name


def classify_drop_profile(
    drop_pct: float,
    league_identifier: str,
    commence_time_str: str,
    bookmaker_name: str,
    match_entry: dict = None,
    comp_key: str = None
):
    """
    Classifica se o movimento de odds foi provocado por Sharps (dinheiro inteligente)
    ou Squares (público geral/tipster followers).
    Retorna (sharpness_score, profile_type)
    """
    score = 0.0

    # 1. Origem e Consenso (Máx: 35 pontos)
    if bookmaker_name.lower() == 'pinnacle':
        score += 35.0
    else:
        pinnacle_dropped = False
        has_pinnacle = False
        if match_entry and 'bookmakers' in match_entry:
            pinnacle_data = match_entry['bookmakers'].get('Pinnacle')
            if pinnacle_data and comp_key in pinnacle_data:
                has_pinnacle = True
                p_entry = pinnacle_data[comp_key]
                p_open = p_entry.get('opening', 0.0)
                p_curr = p_entry.get('current', 0.0)
                if p_open > 1.0 and p_curr > 0.0 and p_curr < p_open:
                    p_drop = ((p_open / p_curr) - 1.0) * 100
                    if p_drop >= 4.0:
                        pinnacle_dropped = True
        
        if pinnacle_dropped:
            score += 25.0
        elif has_pinnacle:
            score += 0.0
        else:
            score += 12.0

    # 2. Antecedência (Máx: 25 pontos)
    if match_entry is None:
        diff_hours = 12.0  # fallback para histórico CSV
    else:
        try:
            dt_commence = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
            dt_now = datetime.now(timezone.utc)
            diff_hours = (dt_commence - dt_now).total_seconds() / 3600.0
        except Exception:
            diff_hours = 4.0

    if diff_hours >= 12.0:
        score += 25.0
    elif diff_hours >= 6.0:
        score += 18.0
    elif diff_hours >= 3.0:
        score += 10.0
    else:
        score += 0.0

    # 3. Liquidez da Liga (Máx: 25 pontos)
    tier_name, _ = estimate_liquidity_tier(league_identifier)
    if tier_name == 'Alta':
        score += 25.0
    elif tier_name == 'Média':
        score += 12.0
    else:
        score += 0.0

    # 4. Magnitude da Queda (Máx: 15 pontos)
    if drop_pct >= 10.0:
        score += 15.0
    elif drop_pct >= 7.5:
        score += 10.0
    elif drop_pct >= 5.0:
        score += 5.0

    profile_type = 'Sharps' if score >= 60.0 else 'Squares'
    return round(score, 1), profile_type


# ─────────────────────────────────────────────
#  SCANNER HISTÓRICO DE STEAM MOVES
# ─────────────────────────────────────────────

def _calc_fair_odds(prob: float) -> float:
    """Converte probabilidade em odd justa (sem margem)."""
    if prob <= 0 or prob >= 1:
        return np.nan
    return round(1.0 / prob, 4)


def _extract_steam_moves_from_df(
    df: pd.DataFrame,
    league_code: str,
    markets: list,
    min_drop_pct: float,
    stake_value: float,
    start_date: str,
    end_date: str,
    latency_seconds: int = 0
) -> list:
    """
    Detecta steam moves históricos implícitos em um DataFrame de resultados.

    Estratégia:
      - Usa modelo Dixon-Coles simplificado (frequências históricas por time) para estimar
        a probabilidade justa de cada mercado.
      - Compara a odd justa com a odd Bet365 disponível no CSV.
      - Se a odd Bet365 está ACIMA da odd justa em >= min_drop_pct%, interpreta como
        sinal de que o mercado ainda não absorveu a informação (steam move implícito).
      - Se a odd B365 está ABAIXO da justa → odd já foi comprimida (steam move tardio / sem sinal).

    Retorna lista de dicts compatíveis com o formato live_steam_moves_history.json.
    """
    if df is None or df.empty:
        return []

    # Filtrar por data
    try:
        df = df.copy()
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Date'])
        df = df[(df['Date'] >= pd.to_datetime(start_date)) &
                (df['Date'] <= pd.to_datetime(end_date))]
    except Exception:
        pass

    if df.empty:
        return []

    # Calcular frequências históricas por time (todos os jogos disponíveis no DF)
    # Usamos lambdas de gols para estimar probabilidades via Poisson
    try:
        home_goals_avg = df['FTHG'].mean()
        away_goals_avg = df['FTAG'].mean()
        if pd.isna(home_goals_avg) or pd.isna(away_goals_avg):
            home_goals_avg, away_goals_avg = 1.5, 1.2
    except Exception:
        home_goals_avg, away_goals_avg = 1.5, 1.2

    # Pre-calcular ataque/defesa por time (Dixon-Coles simplificado)
    team_attack = {}
    team_defense = {}
    for _, row in df.iterrows():
        h, a = str(row.get('HomeTeam', '')), str(row.get('AwayTeam', ''))
        fthg = row.get('FTHG', np.nan)
        ftag = row.get('FTAG', np.nan)
        if pd.isna(fthg) or pd.isna(ftag):
            continue
        team_attack[h] = team_attack.get(h, []) + [fthg]
        team_defense[a] = team_defense.get(a, []) + [fthg]
        team_attack[a] = team_attack.get(a, []) + [ftag]
        team_defense[h] = team_defense.get(h, []) + [ftag]

    def get_team_lambda(home_team, away_team):
        """Retorna (lambda_h, lambda_a) esperados para o jogo."""
        h_att = np.mean(team_attack.get(home_team, [home_goals_avg]))
        h_def = np.mean(team_defense.get(home_team, [away_goals_avg]))
        a_att = np.mean(team_attack.get(away_team, [away_goals_avg]))
        a_def = np.mean(team_defense.get(away_team, [home_goals_avg]))

        home_bias = 1.15  # vantagem de jogar em casa
        lh = max(0.3, h_att * (a_def / max(away_goals_avg, 0.01)) * home_bias)
        la = max(0.3, a_att * (h_def / max(home_goals_avg, 0.01)))
        return lh, la

    def poisson_prob(lam, k):
        from math import exp, factorial
        try:
            return (lam ** k) * exp(-lam) / factorial(k)
        except Exception:
            return 0.0

    def calc_match_probs(lh, la, max_goals=8):
        """Retorna (p_home, p_draw, p_away) via Poisson bivariado."""
        p_home = p_draw = p_away = 0.0
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                p = poisson_prob(lh, i) * poisson_prob(la, j)
                if i > j:
                    p_home += p
                elif i == j:
                    p_draw += p
                else:
                    p_away += p
        total = p_home + p_draw + p_away
        if total <= 0:
            return 1/3, 1/3, 1/3
        return p_home / total, p_draw / total, p_away / total

    steam_moves = []

    for _, row in df.iterrows():
        home_team = str(row.get('HomeTeam', ''))
        away_team = str(row.get('AwayTeam', ''))
        ftr = row.get('FTR')
        date_val = row.get('Date')

        try:
            date_str = date_val.strftime('%Y-%m-%d') if hasattr(date_val, 'strftime') else str(date_val)
        except Exception:
            date_str = str(date_val)

        # Odds Bet365 disponíveis no CSV
        b365h = row.get('B365H', np.nan)
        b365d = row.get('B365D', np.nan)
        b365a = row.get('B365A', np.nan)
        b365o = row.get('B365>2.5', np.nan)
        b365u = row.get('B365<2.5', np.nan)

        # Calcular probabilidades via Poisson
        try:
            lh, la = get_team_lambda(home_team, away_team)
            p_home, p_draw, p_away = calc_match_probs(lh, la)
            p_over25 = 1 - sum(
                poisson_prob(lh, i) * poisson_prob(la, j)
                for i in range(3) for j in range(3) if i + j < 3
            )
            p_under25 = 1 - p_over25
        except Exception:
            continue

        # Mapa: mercado → (prob_modelo, odd_bookie, resultado_vencedor)
        market_map = {
            'home':    (p_home,    b365h, 'H'),
            'draw':    (p_draw,    b365d, 'D'),
            'away':    (p_away,    b365a, 'A'),
            'over25':  (p_over25,  b365o, 'O'),
            'under25': (p_under25, b365u, 'U'),
        }

        for mkt in markets:
            if mkt not in market_map:
                continue

            prob_model, bookie_odd, winner_code = market_map[mkt]
            if pd.isna(bookie_odd) or bookie_odd <= 1.0 or prob_model <= 0:
                continue

            fair_odd = _calc_fair_odds(prob_model)
            if pd.isna(fair_odd) or fair_odd <= 1.0:
                continue

            # Steam move implícito: bookie_odd > fair_odd significa que o mercado
            # ainda não comprimiu a odd — dinheiro informado ainda não entrou totalmente.
            # A "queda implícita" = o quanto a odd deveria cair da bookie até o fair value.
            drop_pct = ((bookie_odd / fair_odd) - 1.0) * 100.0

            if drop_pct < min_drop_pct:
                continue

            score, confidence_level, tier_name = calculate_confidence_score(drop_pct, league_code)

            # Classificar Perfil do Drop
            sharpness_score, profile_type = classify_drop_profile(
                drop_pct=drop_pct,
                league_identifier=league_code,
                commence_time_str=date_str,
                bookmaker_name='Bet365',
                match_entry=None,
                comp_key=None
            )

            # Resolver resultado
            won = None
            profit = 0.0
            if pd.notna(ftr):
                ftr_str = str(ftr).strip().upper()
                if mkt in ('home', 'draw', 'away'):
                    won = (
                        (mkt == 'home' and ftr_str == 'H') or
                        (mkt == 'draw' and ftr_str == 'D') or
                        (mkt == 'away' and ftr_str == 'A')
                    )
                elif mkt in ('over25', 'under25'):
                    # Calcular gols totais
                    fthg = row.get('FTHG', np.nan)
                    ftag = row.get('FTAG', np.nan)
                    if pd.notna(fthg) and pd.notna(ftag):
                        total_goals = fthg + ftag
                        won = (mkt == 'over25' and total_goals > 2.5) or \
                              (mkt == 'under25' and total_goals < 2.5)

                if won is not None:
                    executed_odd = bookie_odd
                    if latency_seconds > 0:
                        import math
                        sf = 1.0 - math.exp(-0.005 * latency_seconds)
                        executed_odd = max(1.01, bookie_odd - (bookie_odd - fair_odd) * sf)
                    
                    profit = round((executed_odd - 1.0) * stake_value if won else -stake_value, 2)

            steam_moves.append({
                'date': date_str,
                'match': f"{home_team} vs {away_team}",
                'league_code': league_code,
                'bookmaker': 'Bet365',
                'market': mkt,
                'opening_odd': round(fair_odd, 3),      # fair value = "abertura teórica"
                'current_odd': round(bookie_odd, 3),     # odd bookie = "mercado atual"
                'executed_odd': round(executed_odd, 3) if won is not None else round(bookie_odd, 3),
                'drop_pct': round(drop_pct, 1),
                'confidence_score': score,
                'confidence_level': confidence_level,
                'liquidity_tier': tier_name,
                'sharpness_score': sharpness_score,
                'profile_type': profile_type,
                'won': won,
                'profit': profit,
                'stake_value': stake_value,
                'resolved': won is not None,
                'source': 'historical_csv'
            })

    return steam_moves


# ─────────────────────────────────────────────
#  CLASSE PRINCIPAL
# ─────────────────────────────────────────────

class SmartMoneyBacktester:
    def __init__(self, data_loader_fn=None):
        self.data_loader_fn = data_loader_fn
        # O history_file aponta para a pasta data/ na raiz do projeto
        self.history_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'data', 'live_steam_moves_history.json'
        )

    def _load_history_alerts(self):
        """Carrega alertas do arquivo JSON de histórico ao vivo."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _load_league_df(self, league_code: str, start_date: str) -> pd.DataFrame:
        """Carrega dados históricos de uma liga via data_loader_fn ou retorna DataFrame vazio."""
        if self.data_loader_fn is None:
            return pd.DataFrame()
        try:
            return self.data_loader_fn(league_code, start_date=start_date)
        except Exception:
            return pd.DataFrame()

    def scan_steam_moves(
        self,
        league_code=None,
        min_drop_pct=5.0,
        markets=None,
        start_date='2021-01-01',
        end_date='2026-12-31',
        stake_value=10,
        profile_filter='all',  # 'all', 'sharps', 'squares'
        latency_seconds=0
    ):
        """
        Varre steam moves em dois modos complementares:

        1. HISTÓRICO CSV  →  Detecta drops implícitos comparando odds Bet365 dos CSVs
                             com fair value calculado pelo modelo Poisson.
                             Popula dados imediatamente mesmo sem servidor rodando 24/7.

        2. LIVE JSON      →  Usa alertas coletados em tempo real pelo live_odds_tracker.

        Os dois modos são combinados e agrupados por nicho (liga|mercado).
        """
        if markets is None:
            markets = ['home', 'away', 'draw']

        default_leagues = ['BRA', 'E0', 'F1', 'D1', 'I1', 'SP1']
        leagues_to_scan = [league_code] if league_code else default_leagues

        # ── MODO 1: Histórico CSV ──────────────────────────────────────────
        csv_alerts = []
        for lcode in leagues_to_scan:
            df = self._load_league_df(lcode, start_date=start_date)
            if df is not None and not df.empty:
                moves = _extract_steam_moves_from_df(
                    df=df,
                    league_code=lcode,
                    markets=markets,
                    min_drop_pct=min_drop_pct,
                    stake_value=stake_value,
                    start_date=start_date,
                    end_date=end_date,
                    latency_seconds=latency_seconds
                )
                csv_alerts.extend(moves)

        # ── MODO 2: Live JSON ──────────────────────────────────────────────
        live_alerts = self._load_history_alerts()

        # Combinar ambas as fontes
        all_alerts = csv_alerts + live_alerts

        # ── AGRUPAR POR NICHO ──────────────────────────────────────────────
        niche_groups: dict = {}

        # Pré-popular nichos para garantir exibição mesmo sem dados
        for lcode in leagues_to_scan:
            for mkt in markets:
                niche_key = f"{lcode}|{mkt}"
                niche_groups[niche_key] = []

        for alert in all_alerts:
            lcode = alert.get('league_code', '')
            mkt = str(alert.get('market', '')).lower()
            if not lcode or not mkt:
                continue

            # Aplicar simulação de latência na odd executada e lucro para alertas da Live
            current_odd = alert.get('current_odd', 1.0)
            opening_odd = alert.get('opening_odd', current_odd)
            won = alert.get('won')
            
            executed_odd = current_odd
            if latency_seconds > 0 and won is not None:
                import math
                sf = 1.0 - math.exp(-0.005 * latency_seconds)
                if opening_odd > current_odd:
                    executed_odd = max(1.01, current_odd - (opening_odd - current_odd) * sf)
                
                stake = alert.get('stake_value', stake_value)
                alert['executed_odd'] = round(executed_odd, 3)
                alert['profit'] = round((executed_odd - 1.0) * stake if won else -stake, 2)
            else:
                alert['executed_odd'] = round(executed_odd, 3)
                if won is not None:
                    stake = alert.get('stake_value', stake_value)
                    alert['profit'] = round((current_odd - 1.0) * stake if won else -stake, 2)

            # Fallback para alertas sem perfil (por exemplo, antigos salvos na live)
            if 'profile_type' not in alert:
                drop_pct = alert.get('drop_pct', 0.0)
                commence_time_str = alert.get('date', '')
                bookie = alert.get('bookmaker', 'Bet365')
                sh_score, p_type = classify_drop_profile(
                    drop_pct=drop_pct,
                    league_identifier=lcode,
                    commence_time_str=commence_time_str,
                    bookmaker_name=bookie,
                    match_entry=None,
                    comp_key=None
                )
                alert['sharpness_score'] = sh_score
                alert['profile_type'] = p_type

            # Filtrar por perfil do drop
            prof = alert.get('profile_type', 'Squares')
            if profile_filter == 'sharps' and prof != 'Sharps':
                continue
            if profile_filter == 'squares' and prof != 'Squares':
                continue

            # Filtrar por data
            alert_date_str = alert.get('date', '')
            try:
                alert_dt = pd.to_datetime(alert_date_str, errors='coerce')
                if pd.notna(alert_dt):
                    if alert_dt < pd.to_datetime(start_date) or alert_dt > pd.to_datetime(end_date):
                        continue
            except Exception:
                pass

            # Filtrar por liga
            if league_code and lcode != league_code:
                continue

            if mkt not in markets:
                continue

            if alert.get('drop_pct', 0.0) < min_drop_pct:
                continue

            niche_key = f"{lcode}|{mkt}"
            if niche_key not in niche_groups:
                niche_groups[niche_key] = []
            niche_groups[niche_key].append(alert)

        # ── CALCULAR MÉTRICAS POR NICHO ────────────────────────────────────
        results = []
        for niche_key, bets in niche_groups.items():
            lcode, mkt = niche_key.split('|')
            tier_name, _ = estimate_liquidity_tier(lcode)

            if not bets:
                score, confidence_level, tier_name = calculate_confidence_score(0.0, lcode)
                results.append({
                    'code': niche_key,
                    'market_name': mkt.capitalize(),
                    'total_bets': 0,
                    'net_profit': 0.0,
                    'roi': 0.0,
                    'avg_drop': 0.0,
                    'win_rate': 0.0,
                    'liquidity_tier': tier_name,
                    'confidence_score': score,
                    'confidence_level': confidence_level,
                    'resolved_count': 0,
                    'source_csv': 0,
                    'source_live': 0
                })
                continue

            total_bets = len(bets)
            resolved_bets = [b for b in bets if b.get('resolved') is True]
            resolved_count = len(resolved_bets)

            net_profit = sum(b.get('profit', 0.0) for b in resolved_bets)
            total_staked = sum(b.get('stake_value', stake_value) for b in resolved_bets)
            roi = (net_profit / total_staked * 100) if total_staked > 0 else 0.0

            avg_drop = float(np.mean([b.get('drop_pct', 0.0) for b in bets]))

            wins = sum(1 for b in resolved_bets if b.get('won') is True)
            win_rate = (wins / resolved_count * 100) if resolved_count > 0 else 0.0

            # Confiança baseada no drop médio ponderado pelo número de alertas
            score, confidence_level, tier_name = calculate_confidence_score(avg_drop, lcode)

            # Contar fontes
            source_csv = sum(1 for b in bets if b.get('source') == 'historical_csv')
            source_live = sum(1 for b in bets if b.get('source') != 'historical_csv')

            results.append({
                'code': niche_key,
                'market_name': mkt.capitalize(),
                'total_bets': total_bets,
                'net_profit': round(net_profit, 2),
                'roi': round(roi, 2),
                'avg_drop': round(avg_drop, 2),
                'win_rate': round(win_rate, 1),
                'liquidity_tier': tier_name,
                'confidence_score': score,
                'confidence_level': confidence_level,
                'resolved_count': resolved_count,
                'source_csv': source_csv,
                'source_live': source_live
            })

        return results


def calculate_odds_metrics(updates: list):
    """
    Calcula velocidade (queda % por hora) e aceleração de uma série de atualizações de cotações.
    Cada update em 'updates' deve ser um dicionário contendo 'timestamp' (ISO 8601) e 'price' (float).
    Retorna um dicionário com:
        - velocity_global: float (%/h total)
        - velocity_recent: float (%/h no último intervalo)
        - acceleration_ratio: float (recent / global)
        - acceleration_text: str ("Aceleração Forte", "Acelerando", "Desacelerando", "Constante")
        - drop_total_pct: float (% drop total)
    """
    if not updates or len(updates) < 2:
        # Tenta extrair valores padrão se for uma lista vazia ou ponto único
        return {
            "velocity_global": 0.0,
            "velocity_recent": 0.0,
            "acceleration_ratio": 1.0,
            "acceleration_text": "Constante",
            "drop_total_pct": 0.0
        }
        
    def parse_dt(ts):
        if not ts:
            return datetime.now(timezone.utc)
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except Exception:
            return datetime.now(timezone.utc)

    # Ordenar por timestamp por garantia
    sorted_updates = sorted(updates, key=lambda x: x.get('timestamp', ''))
    
    t0 = parse_dt(sorted_updates[0].get('timestamp'))
    p0 = float(sorted_updates[0].get('price', 1.0))
    
    t_last = parse_dt(sorted_updates[-1].get('timestamp'))
    p_last = float(sorted_updates[-1].get('price', 1.0))
    
    # Duração total em horas
    dur_global = (t_last - t0).total_seconds() / 3600.0
    if dur_global < 0.016:  # Mínimo 1 minuto para evitar divisão por zero
        dur_global = 0.016
        
    drop_global = 0.0
    if p0 > 0 and p_last > 0:
        drop_global = max(0.0, ((p0 / p_last) - 1.0) * 100.0)
        
    vel_global = drop_global / dur_global
    
    # Recente: penúltimo vs último
    t_prev = parse_dt(sorted_updates[-2].get('timestamp'))
    p_prev = float(sorted_updates[-2].get('price', 1.0))
    
    dur_recent = (t_last - t_prev).total_seconds() / 3600.0
    if dur_recent < 0.016:
        dur_recent = 0.016
        
    drop_recent = 0.0
    if p_prev > 0 and p_last > 0:
        drop_recent = max(0.0, ((p_prev / p_last) - 1.0) * 100.0)
        
    vel_recent = drop_recent / dur_recent
    
    # Aceleração
    if vel_global > 0.1:
        acc_ratio = vel_recent / vel_global
    else:
        acc_ratio = 1.0
        
    # Texto de classificação
    if acc_ratio >= 2.0 and vel_recent >= 8.0:
        acc_text = "Aceleração Forte"
    elif acc_ratio >= 1.3 and vel_recent >= 4.0:
        acc_text = "Acelerando"
    elif acc_ratio <= 0.7:
        acc_text = "Desacelerando"
    else:
        acc_text = "Constante"
        
    return {
        "velocity_global": round(vel_global, 2),
        "velocity_recent": round(vel_recent, 2),
        "acceleration_ratio": round(acc_ratio, 2),
        "acceleration_text": acc_text,
        "drop_total_pct": round(drop_global, 2)
    }


def calculate_time_decay_adjusted_drop(norm_market: str, opening: float, current: float, elapsed_minutes: float):
    """
    Calcula a odd esperada pelo decaimento natural de tempo em partidas In-Play
    e retorna (odd_decay, adjusted_drop_pct).
    """
    if elapsed_minutes <= 0:
        return opening, max(0.0, ((opening / current) - 1.0) * 100.0)
        
    m_lower = str(norm_market).lower().strip()
    
    # 1. Fator de decaimento por tipo de mercado
    if 'under25' in m_lower or 'under 2.5' in m_lower:
        decay_ratio = max(0.0, 1.0 - (elapsed_minutes / 90.0))
        odd_decay = 1.0 + (opening - 1.0) * decay_ratio
    elif 'draw' in m_lower or 'empate' in m_lower:
        decay_ratio = max(0.0, 1.0 - (elapsed_minutes / 110.0))
        odd_decay = 1.0 + (opening - 1.0) * decay_ratio
    elif 'home' in m_lower or 'away' in m_lower:
        decay_ratio = max(0.0, 1.0 - (elapsed_minutes / 90.0))
        odd_decay = 1.0 + (opening - 1.0) * decay_ratio
    else:
        odd_decay = opening
        
    odd_decay = max(1.01, min(opening, odd_decay))
    
    if current < odd_decay:
        adjusted_drop = ((odd_decay / current) - 1.0) * 100.0
    else:
        adjusted_drop = 0.0
        
    return round(odd_decay, 3), round(adjusted_drop, 2)
