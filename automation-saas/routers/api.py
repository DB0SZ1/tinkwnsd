from fastapi import APIRouter
from routers.topics import router as topics_router
from routers.posts import router as posts_router
from routers.leads import router as leads_router
from routers.images import router as images_router
from routers.settings import router as settings_router
from routers.jobs import router as jobs_router
from routers.whatsapp import router as whatsapp_router

api_router = APIRouter()

api_router.include_router(topics_router)
api_router.include_router(posts_router)
api_router.include_router(leads_router)
api_router.include_router(images_router)
api_router.include_router(settings_router)
api_router.include_router(jobs_router)
api_router.include_router(whatsapp_router, prefix="/whatsapp", tags=["whatsapp"])
