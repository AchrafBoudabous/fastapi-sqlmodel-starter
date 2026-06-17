from fastapi import APIRouter

from app.api.v1 import auth, items, users

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(items.router)
router.include_router(users.router)
