import os

target_file = r"backend\telegram_bot.py"

new_functions = """

def format_pure_blood_tip(league_name, match_name, match_date, time_str, market_label, prob, ev_pct, cluster_desc, avg_goals):
    min_odd = 1.05 / (prob / 100.0) if prob > 0 else 0
    message = (
        f"🚨 <b>SINAL PURO-SANGUE CONFIRMADO!</b> 🚨\\n\\n"
        f"🏆 <b>Liga:</b> {league_name}\\n"
        f"⚽ <b>Jogo:</b> {match_name}\\n"
        f"📅 <b>Data:</b> {match_date} às {time_str}\\n\\n"
        f"📊 <b>Mercado Indicado:</b> {market_label}\\n"
        f"📈 <b>Probabilidade Real (Scanner):</b> {prob:.1f}%\\n"
        f"🧬 <b>Validação IA (Cluster):</b> Aprovado!\\n"
        f"<i>A liga pertence ao {cluster_desc} (Média: {avg_goals:.2f} gols). O edge é real e estatisticamente comprovado.</i>\\n\\n"
        f"💰 <b>Odd Mínima de Entrada (+5% EV):</b> @{min_odd:.2f}\\n"
        f"<i>(Se a casa oferecer odd maior ou igual a essa, você tem vantagem matemática garantida a longo prazo!)</i>\\n"
    )
    return message

def format_contrarian_tip(league_name, match_name, match_date, time_str, market_label, bookie_odd, cluster_desc, recommended_action):
    message = (
        f"⚠️ <b>ANOMALIA DE ODD ENCONTRADA!</b> ⚠️\\n\\n"
        f"🏆 <b>Liga:</b> {league_name}\\n"
        f"⚽ <b>Jogo:</b> {match_name}\\n"
        f"📅 <b>Data:</b> {match_date} às {time_str}\\n\\n"
        f"🧬 <b>DNA do Campeonato:</b> {cluster_desc}\\n"
        f"📉 <b>Odd da Casa de Apostas:</b> {market_label} pagando absurdos <b>@{bookie_odd:.2f}</b>!\\n\\n"
        f"💡 <b>Análise:</b> A casa de apostas está precificando uma expectativa de jogo que contradiz completamente o comportamento histórico (Cluster) dessa liga.\\n\\n"
        f"🤖 <b>Ação Recomendada (Contrarian):</b> {recommended_action}\\n"
        f"<i>Há um EV (Valor Esperado) gigantesco em ir contra a manada aqui!</i>\\n"
    )
    return message

def format_dna_shift_alert(league_name, old_cluster_desc, new_cluster_desc, recommended_markets):
    message = (
        f"🔄 <b>MUDANÇA DE COMPORTAMENTO DETECTADA!</b> 🔄\\n\\n"
        f"🏆 <b>Liga:</b> {league_name}\\n\\n"
        f"O motor de IA detectou que esta liga sofreu uma mutação matemática nesta temporada:\\n"
        f"📉 <b>Saiu de:</b> {old_cluster_desc}\\n"
        f"📈 <b>Entrou em:</b> {new_cluster_desc}\\n\\n"
        f"💡 <b>Dica da IA:</b> Os robôs das casas de aposta demoram semanas para corrigir seus modelos de preço após uma mudança de cluster.\\n\\n"
        f"🎯 <b>Foque o Scanner em:</b> {recommended_markets}\\n"
        f"<i>Fique de olho em oportunidades de valor esmagador nestes mercados para as próximas rodadas!</i>\\n"
    )
    return message
"""

with open(target_file, "a", encoding="utf-8") as f:
    f.write(new_functions)

print("Updated telegram_bot.py successfully!")
