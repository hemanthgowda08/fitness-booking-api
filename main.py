from fastapi import FastAPI

app = FastAPI()

@app.post("/")
def signup():
    return {"message": "User signed up successfully!"}