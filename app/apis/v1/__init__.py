from fastapi import APIRouter

from app.apis.v1.alarm_routers import alarm_router
from app.apis.v1.analysis_routers import analysis_router
from app.apis.v1.auth_routers import auth_router
from app.apis.v1.chat_routers import chat_router
from app.apis.v1.common_routers import common_router
from app.apis.v1.current_med_routers import current_med_router
from app.apis.v1.guide_routers import guide_router
from app.apis.v1.health_routers import health_router
from app.apis.v1.medication_routers import medication_router
from app.apis.v1.multimodal_routers import multimodal_router
from app.apis.v1.result_routers import result_router
from app.apis.v1.system_routers import system_router
from app.apis.v1.upload_routers import upload_router
from app.apis.v1.user_routers import user_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(user_router)
api_v1_router.include_router(health_router)
api_v1_router.include_router(upload_router)
api_v1_router.include_router(analysis_router)
api_v1_router.include_router(result_router)
api_v1_router.include_router(medication_router)
api_v1_router.include_router(guide_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(alarm_router)
api_v1_router.include_router(current_med_router)
api_v1_router.include_router(multimodal_router)
api_v1_router.include_router(system_router)
api_v1_router.include_router(common_router)
