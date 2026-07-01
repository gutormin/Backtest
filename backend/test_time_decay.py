import sys
import os

# Add parent dir to path so we can import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.smart_money import calculate_time_decay_adjusted_drop

def test_pre_live():
    print("\n[Test 1] Jogo pré-live (0 minutos decorridos)")
    # Se elapsed_minutes = 0, a odd decay é igual à abertura
    # Abertura: 1.90, Atual: 1.70. Drop nominal: ((1.90/1.70)-1)*100 = 11.76%
    odd_decay, adj_drop = calculate_time_decay_adjusted_drop("under25", 1.90, 1.70, 0.0)
    print(f"Decay: {odd_decay} | Drop Ajustado: {adj_drop}%")
    assert odd_decay == 1.90
    assert abs(adj_drop - 11.76) < 0.1
    print("Test 1 OK!")

def test_under25_decay():
    print("\n[Test 2] Decaimento no mercado Under 2.5 gols (In-Play)")
    # Abertura: 1.90. No minuto 45, espera-se que a cotação natural do Under 2.5 caia.
    # Fórmula: 1.0 + (1.90 - 1.0) * (1 - 45/90) = 1.0 + 0.9 * 0.5 = 1.45
    # Se a cotação atual for 1.40:
    # A odd atual (1.40) é menor que a teórica (1.45).
    # Drop Ajustado = ((1.45/1.40)-1)*100 = 3.57%
    odd_decay, adj_drop = calculate_time_decay_adjusted_drop("under25", 1.90, 1.40, 45.0)
    print(f"Decay (45'): {odd_decay} | Drop Ajustado: {adj_drop}%")
    assert odd_decay == 1.45
    assert abs(adj_drop - 3.57) < 0.1
    
    # Se a cotação atual for 1.50 (superior a 1.45), o drop deve ser 0% (movimento natural superior ao detectado)
    _, adj_drop_high = calculate_time_decay_adjusted_drop("under25", 1.90, 1.50, 45.0)
    print(f"Atual (1.50) > Decay (1.45) | Drop Ajustado: {adj_drop_high}%")
    assert adj_drop_high == 0.0
    print("Test 2 OK!")

def test_draw_decay():
    print("\n[Test 3] Decaimento no mercado de Empate (In-Play)")
    # Abertura: 3.40. No minuto 55 (metade do jogo), decaimento de empate:
    # Fator: 1 - 55/110 = 0.5
    # Odd Decay: 1.0 + 2.4 * 0.5 = 2.20
    # Se a odd atual for 1.80:
    # Drop Ajustado = ((2.20/1.80)-1)*100 = 22.22%
    odd_decay, adj_drop = calculate_time_decay_adjusted_drop("draw", 3.40, 1.80, 55.0)
    print(f"Decay (55'): {odd_decay} | Drop Ajustado: {adj_drop}%")
    assert odd_decay == 2.20
    assert abs(adj_drop - 22.22) < 0.1
    print("Test 3 OK!")

def test_over25_no_decay():
    print("\n[Test 4] Mercado Over 2.5 (sem decaimento de tempo para queda)")
    # Cotações de Over sobem com a passagem do tempo. Se caírem, é totalmente anormal.
    # Logo, odd decay deve ser igual à abertura teórica (sem decaimento para queda).
    odd_decay, adj_drop = calculate_time_decay_adjusted_drop("over25", 1.90, 1.70, 45.0)
    print(f"Decay (45'): {odd_decay} | Drop Ajustado: {adj_drop}%")
    assert odd_decay == 1.90
    assert abs(adj_drop - 11.76) < 0.1
    print("Test 4 OK!")

if __name__ == "__main__":
    print("Iniciando testes do Módulo In-Play e Decaimento de Tempo...")
    test_pre_live()
    test_under25_decay()
    test_draw_decay()
    test_over25_no_decay()
    print("\nTodos os testes de decaimento de tempo passaram com sucesso!")
