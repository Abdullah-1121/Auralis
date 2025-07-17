from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from auralis.models.models import CallContext
from auralis.mas import run_agent
import uvicorn
app = FastAPI(
    title="Auralis",
    description="Auralis API",
    version="0.0.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to Auralis!"}

@app.get("/run" , response_model=CallContext)
async def run():
    result = await run_agent()
    return result

if __name__ == "__main__": 
    uvicorn.run(app, host="0.0.0.0", port=8000 , reload=True)