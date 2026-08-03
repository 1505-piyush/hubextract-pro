from django.http import JsonResponse


def health_check(request):
    return JsonResponse({
        "status": "ok",
        "service": "HubExtract Pro",
        "version": "1.0.0"
    })
