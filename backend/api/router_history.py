import os
from fastapi import APIRouter, HTTPException
from ..history_manager import load_history, add_strategy, delete_strategy, save_history

router = APIRouter()

@router.get("/history")
def api_get_history():
    return load_history()

@router.get("/debug_db")
def api_debug_db():
    try:
        h = load_history()
        return {
            "file_exists": os.path.exists("data/history_strategies.json"),
            "file_size": os.path.getsize("data/history_strategies.json") if os.path.exists("data/history_strategies.json") else 0,
            "items_count": len(h),
            "items": [{"id": x.get("id"), "name": x.get("name"), "type": x.get("type"), "created_at": x.get("created_at")} for x in h]
        }
    except Exception as e:
        return {"error": str(e)}

@router.post("/history")
def api_save_history(payload: dict):
    try:
        new_entry = add_strategy(payload)
        return {"status": "ok", "entry": new_entry}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/history/{strategy_id}")
def api_delete_history(strategy_id: str):
    try:
        delete_strategy(strategy_id)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/history/{strategy_id}/toggle_active")
def api_toggle_active_portfolio(strategy_id: str):
    try:
        history = load_history()
        
        # Find the strategy or portfolio
        target = next((s for s in history if s.get('id') == strategy_id), None)
        if not target:
            raise HTTPException(status_code=404, detail="Estratégia ou portfólio não encontrado.")
            
        new_status = not target.get('is_tg_active', False)
        
        # Toggle target status only.
        for s in history:
            if s.get('id') == strategy_id:
                s['is_tg_active'] = new_status
                        
        save_history(history)
        return {"status": "ok", "is_tg_active": new_status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
