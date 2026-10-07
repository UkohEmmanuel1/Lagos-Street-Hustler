from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app=FastAPI(title="Lagos Street Hustler API",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
MISSIONS=[{"id":"first-day","title":"First Day in Lagos","description":"Find your first street contact.","reward":"2500","xp":100},{"id":"food-run","title":"Food Delivery","description":"Deliver a food order before traffic wins.","reward":"15000","xp":250},{"id":"industrial","title":"Industrial Delivery","description":"Take the logistics contract to the refinery district.","reward":"2500000","xp":1200}]
@app.get("/health")
def health(): return {"status":"ok","service":"lagos-street-hustler-api"}
@app.get("/missions")
def missions(): return MISSIONS
@app.get("/players/me")
def player(): return {"id":"demo-player","name":"Street Hustler","level":1,"xp":0,"reputation":0,"money":{"balance":"2500000","currency":"NGN"}}
@app.post("/missions/{mission_id}/complete")
def complete(mission_id:str):
    mission=next((m for m in MISSIONS if m["id"]==mission_id),None)
    if not mission: return {"error":"mission_not_found"}
    return {"mission":mission,"reward":mission["reward"]}
