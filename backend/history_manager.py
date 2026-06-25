import json
import os
import uuid
from datetime import datetime, timezone

HISTORY_FILE = "data/history_strategies.json"

def ensure_history_dir():
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def load_history():
    ensure_history_dir()
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        # Retrospective migration: ensure portfolios have type = 'portfolio'
        modified = False
        for s in history:
            if s.get('type') != 'portfolio' and 'strategy_ids' in s.get('params', {}):
                s['type'] = 'portfolio'
                modified = True
        if modified:
            save_history(history)
            
        return history
    except Exception:
        return []

def add_strategy(data: dict):
    history = load_history()
    
    provided_id = data.get("id")
    inferred_type = data.get("type", "strategy")
    if 'strategy_ids' in data.get("params", {}):
        inferred_type = "portfolio"
        
    entry = {
        # Respect client-provided ID so localStorage sync works correctly
        "id": provided_id if provided_id else str(uuid.uuid4()),
        "created_at": data.get("created_at") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "name": data.get("name", "Nova Estratégia"),
        "type": inferred_type,
        "is_tg_active": data.get("is_tg_active", False),
        "params": data.get("params", {}),
        "summary": data.get("summary", {})
    }
    
    # Upsert: replace if same ID already exists, else insert at beginning
    existing_idx = next((i for i, h in enumerate(history) if h.get("id") == entry["id"]), None)
    if existing_idx is not None:
        history[existing_idx] = entry
    else:
        history.insert(0, entry)
    
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)
        
    return entry

def save_history(history: list):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

def delete_strategy(strategy_id: str):
    history = load_history()
    new_history = [s for s in history if s.get("id") != strategy_id]
    
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_history, f, indent=4, ensure_ascii=False)
        
    return True
