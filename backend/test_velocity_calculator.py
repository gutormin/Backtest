import sys
import os
from datetime import datetime, timedelta, timezone

# Add parent dir to path so we can import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.smart_money import calculate_odds_metrics

def test_constant_drop():
    print("\n[Test 1] Queda Linear / Constante")
    # Queda linear: 10% total em 2 horas
    t0 = datetime.now(timezone.utc) - timedelta(hours=2)
    t1 = datetime.now(timezone.utc) - timedelta(hours=1)
    t2 = datetime.now(timezone.utc)
    
    # Preços: 2.0 -> 1.9 -> 1.8. 
    # Drop global = (2.0 / 1.8 - 1) * 100 = 11.11% em 2h = 5.56%/h
    # Drop recente = (1.9 / 1.8 - 1) * 100 = 5.26% em 1h = 5.26%/h
    # Razão = 5.26 / 5.56 = ~0.95 -> Constante
    updates = [
        {'timestamp': t0.isoformat(), 'price': 2.0},
        {'timestamp': t1.isoformat(), 'price': 1.9},
        {'timestamp': t2.isoformat(), 'price': 1.8}
    ]
    
    res = calculate_odds_metrics(updates)
    print("Métricas:", res)
    assert res['velocity_global'] > 0.0
    assert res['acceleration_text'] == "Constante"
    print("Test 1 OK!")

def test_accelerating_drop():
    print("\n[Test 2] Queda Acelerada (Tipster / Sharp Heavy Entry)")
    # Queda lenta no início, depois queda brusca no final
    # 2h atrás: 2.0
    # 1h atrás: 1.95 (queda de 2.5% em 1 hora)
    # agora: 1.6 (queda de 21.8% em 1 hora!)
    # A velocidade recente deve ser muito maior que a global
    t0 = datetime.now(timezone.utc) - timedelta(hours=2)
    t1 = datetime.now(timezone.utc) - timedelta(hours=1)
    t2 = datetime.now(timezone.utc)
    
    updates = [
        {'timestamp': t0.isoformat(), 'price': 2.0},
        {'timestamp': t1.isoformat(), 'price': 1.95},
        {'timestamp': t2.isoformat(), 'price': 1.6}
    ]
    
    res = calculate_odds_metrics(updates)
    print("Métricas:", res)
    assert res['acceleration_ratio'] >= 1.5
    assert res['acceleration_text'] in ["Aceleração Forte", "Acelerando"]
    print("Test 2 OK!")

def test_decelerating_drop():
    print("\n[Test 3] Queda Desacelerada (Estabilização do Mercado)")
    # Queda brusca no início, depois estabilização no final
    # 2h atrás: 2.0
    # 1h atrás: 1.6 (queda de 25% em 1 hora)
    # agora: 1.58 (queda de 1.2% em 1 hora)
    # A velocidade recente deve ser muito menor que a global
    t0 = datetime.now(timezone.utc) - timedelta(hours=2)
    t1 = datetime.now(timezone.utc) - timedelta(hours=1)
    t2 = datetime.now(timezone.utc)
    
    updates = [
        {'timestamp': t0.isoformat(), 'price': 2.0},
        {'timestamp': t1.isoformat(), 'price': 1.6},
        {'timestamp': t2.isoformat(), 'price': 1.58}
    ]
    
    res = calculate_odds_metrics(updates)
    print("Métricas:", res)
    assert res['acceleration_ratio'] <= 0.7
    assert res['acceleration_text'] == "Desacelerando"
    print("Test 3 OK!")

def test_edge_cases():
    print("\n[Test 4] Casos Extremos")
    # Apenas um item
    res_single = calculate_odds_metrics([{'timestamp': datetime.now(timezone.utc).isoformat(), 'price': 2.0}])
    assert res_single['velocity_global'] == 0.0
    assert res_single['acceleration_text'] == "Constante"
    
    # Lista vazia
    res_empty = calculate_odds_metrics([])
    assert res_empty['velocity_global'] == 0.0
    print("Test 4 OK!")

if __name__ == "__main__":
    print("Iniciando testes do Rastreamento de Velocidade e Aceleração de Odds...")
    test_constant_drop()
    test_accelerating_drop()
    test_decelerating_drop()
    test_edge_cases()
    print("\nTodos os testes de velocidade e aceleração passaram com sucesso!")
