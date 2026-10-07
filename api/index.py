from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"ok": True, "service": "elipsis-probe"}

@app.get("/{full_path:path}")
def catchall(full_path: str):
    return {"ok": True, "path": full_path}
