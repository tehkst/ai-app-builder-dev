from app.platform.api.app_build.dashboard import router as dashboard_router
from app.platform.api.app_build.demo_routes import router as demo_router
from app.platform.api.app_build.generated_file_content_routes import router as generated_file_content_router
from app.platform.api.app_build.generated_file_runtime_routes import router as generated_file_runtime_router
from app.platform.api.app_build.materialization_routes import router as materialization_router
from app.platform.api.app_build.module_routes import router as module_router
from app.platform.api.app_build.repair_routes import router as repair_router
from app.platform.api.app_build.restore_approval_routes import router as restore_approval_router
from app.platform.api.app_build.runs import router as runs_router
from app.platform.api.app_build.workflow_runtime_routes import router as workflow_runtime_router


APP_BUILD_ROUTERS = (
    dashboard_router,
    demo_router,
    runs_router,
    workflow_runtime_router,
    module_router,
    repair_router,
    generated_file_runtime_router,
    generated_file_content_router,
    materialization_router,
    restore_approval_router,
)
