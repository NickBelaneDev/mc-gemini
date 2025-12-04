from fastapi import FastAPI
import uvicorn

from src.config.settings import GEMINI_API_KEY
from src.services.chat_service import SmartGeminiBackend

app = FastAPI()
GEMINI = SmartGeminiBackend(GEMINI_API_KEY)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/gemini/chat")
async def gemini_chat(player_name: str, prompt: str):
    print("Starting SmartGeminiBackend test client...")
    response = await GEMINI.chat(player_name, prompt)
    return {"response": response}



if __name__ == "__main__":
    # Dieser Block wird nur ausgeführt, wenn das Skript direkt mit `python main.py`
    # gestartet wird. Er dient dem lokalen Entwickeln.
    # - `uvicorn.run(...)`: Startet den ASGI-Server, der deine App ausführt.
    # - `reload=True`: Ist extrem nützlich in der Entwicklung. Der Server startet
    #   automatisch neu, sobald du eine Änderung im Code speicherst.
    # In einer Produktionsumgebung würdest du den Server anders starten,
    # z.B. mit: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`
    print("Starting FastAPI server... Go to 0.0.0.0")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)