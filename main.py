from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# لازم يكون اسم المتغير app بالظبط
app = FastAPI(title="AgeixAISOC Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "success", "message": "AgeixAI Master Brain is Online!"}

@app.get("/api/dashboard/soc")
async def soc_dashboard():
    return {
        "active_alerts": 5,
        "pending_decisions": 2,
        "threats_blocked": 12,
        "ai_status": "Hive-Mind Active"
    }