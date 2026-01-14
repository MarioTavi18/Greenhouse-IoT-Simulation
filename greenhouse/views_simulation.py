import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from greenhouse.services.simulation_runner import SimulationRunner

# Simple singleton runner for dev/demo (single process)
RUNNER = SimulationRunner()


@csrf_exempt
@require_http_methods(["POST"])
def start_simulation(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"ok": False, "error": "Invalid JSON body. Send application/json."},
            status=400
        )

    config = payload.get("config", "optimal")
    interval = float(payload.get("interval", 1.0))
    clear_data = bool(payload.get("clear_data", False))

    RUNNER.start(config_name=config, interval=interval, clear_data=clear_data)
    return JsonResponse({"ok": True, "status": RUNNER.status()})

@csrf_exempt
@require_http_methods(["POST"])
def stop_simulation(request):
    RUNNER.stop()
    return JsonResponse({"ok": True, "status": RUNNER.status()})


@require_http_methods(["GET"])
def simulation_status(request):
    return JsonResponse({"ok": True, "status": RUNNER.status()})
