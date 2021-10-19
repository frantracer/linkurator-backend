from fastapi import FastAPI

# Application initialisation
app = FastAPI()


# Endpoints definition
@app.get("/health")
async def root() -> None:
    return
