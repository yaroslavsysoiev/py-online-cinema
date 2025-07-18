from fastapi import APIRouter

router = APIRouter(prefix="/orders", tags=["orders"])

@router.get("/health", summary="Order router health check")
def order_health():
    return {"status": "ok"} 