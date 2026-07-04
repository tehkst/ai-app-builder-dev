from app.platform.api.app_build.dashboard import router as dashboard_router
from app.platform.api.app_build.generated_file_content_routes import router as generated_file_content_router
from app.platform.api.app_build.generated_file_runtime_routes import router as generated_file_runtime_router
from app.platform.api.app_build.materialization_routes import router as materialization_router
from app.platform.api.app_build.module_compat_routes import router as module_compat_router
from app.platform.api.app_build.module_routes import router as module_router
from app.platform.api.app_build.repair_routes import router as repair_router
from app.platform.api.app_build.restore_approval_routes import router as restore_approval_router
from app.platform.api.app_build.runs import router as runs_router
from app.platform.api.app_build.scoping_routes import router as scoping_router
from app.platform.api.app_build.workflow_runtime_routes import router as workflow_runtime_router
from app.platform.api.app_build.workflow_tracker_routes import router as workflow_tracker_router
from app.platform.api.package_api import router as package_router


APP_BUILD_ROUTERS = (
    dashboard_router,
    scoping_router,
    workflow_tracker_router,
    runs_router,
    workflow_runtime_router,
    module_router,
    module_compat_router,
    repair_router,
    generated_file_runtime_router,
    generated_file_content_router,
    materialization_router,
    restore_approval_router,
    package_router,
)
