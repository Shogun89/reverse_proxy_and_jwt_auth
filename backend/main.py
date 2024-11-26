import os
from fastapi import FastAPI, Request
from api import router
import uvicorn

app = FastAPI(title=f"FastAPI Shard {os.getenv('SHARD', 'unknown').upper()}")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"Received request: {request.method} {request.url.path}")
    print(f"Base URL: {request.base_url}")
    print(f"Headers: {request.headers}")
    response = await call_next(request)
    return response

app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Backend API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
