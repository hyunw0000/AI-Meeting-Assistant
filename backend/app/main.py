from fastapi import FastAPI

app = FastAPI(title="AI Meeting Assistant")

@app.get("/")
async def root():
    return {"message": "Welcome to AI Meeting Assistant API"}
