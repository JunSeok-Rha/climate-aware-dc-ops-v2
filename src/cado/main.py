from fastapi import FastAPI

from cado.db.supabase_client import get_supabase_client

app = FastAPI()


@app.get("/api/health")
def health():
    try:
        get_supabase_client().table("zone_aggregated_metrics").select(
            "*", count="exact"
        ).limit(1).execute()
        db_status = "UP"
    except Exception:
        db_status = "DOWN"

    return {"status": "UP", "db": db_status}
