from fastapi import FastAPI
# from .routers import example

app = FastAPI()

# app.include_router(example.router, prefix="/example", tags=["Example"])

@app.get("/")
def read_root():
    return {"message": "Hello World"}