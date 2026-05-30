from fastapi import FastAPI

app = FastAPI(title="Generated SaaS App")


@app.get("/health")
async def health_check():
    return {"ok": True}


@app.get("/")
async def root():
    return {"message": "Generated app is running"}
