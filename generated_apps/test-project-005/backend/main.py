from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
async def health_check():
    return {"ok": True}
