from fastapi import FastAPI
import uvicorn

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


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