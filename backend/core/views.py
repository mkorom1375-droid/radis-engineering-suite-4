from django.http import JsonResponse
from django.utils import timezone


def health_check(request):
    return JsonResponse(
        {
            "success": True,
            "status": "ok",
            "service": "RADIS ENGINEERING SUITE API",
            "timestamp": timezone.now().isoformat(),
        }
    )