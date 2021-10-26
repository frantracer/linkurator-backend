"""
Main file of the application
"""

from fastapi import FastAPI

# Application initialisation
app = FastAPI()


# Endpoints definition
@app.get("/health")
async def health() -> None:
    """
    Health endpoint returns a 200 if the service is alive
    """
    return
