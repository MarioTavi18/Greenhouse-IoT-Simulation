from django.urls import path
from greenhouse.views_simulation import (
    start_simulation,
    stop_simulation,
    simulation_status,
)

urlpatterns = [
    path("api/sim/start", start_simulation),
    path("api/sim/stop", stop_simulation),
    path("api/sim/status", simulation_status),
]
