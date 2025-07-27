from fastapi import FastAPI

from routes import accounts_router, movie_router
from routes.directors import router as directors_router
from routes.certifications import router as certifications_router
from routes.genres import router as genres_router
from routes.actors import router as actors_router
from routes.orders import router as orders_router
from routes.payments import router as payments_router

app = FastAPI(
    title="Movies homework",
    description="Description of project"
)

api_version_prefix = "/api/v1"

app.include_router(accounts_router, prefix=f"{api_version_prefix}/accounts", tags=["accounts"])
app.include_router(movie_router, prefix=f"{api_version_prefix}/theater", tags=["theater"])
app.include_router(directors_router, prefix=f"{api_version_prefix}", tags=["directors"])
app.include_router(certifications_router, prefix=f"{api_version_prefix}", tags=["certifications"])
app.include_router(genres_router, prefix=f"{api_version_prefix}", tags=["genres"])
app.include_router(actors_router, prefix=f"{api_version_prefix}", tags=["actors"])
app.include_router(orders_router, prefix=f"{api_version_prefix}", tags=["orders"])
app.include_router(payments_router, prefix=f"{api_version_prefix}", tags=["payments"])
