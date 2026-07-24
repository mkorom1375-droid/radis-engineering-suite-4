from rest_framework.response import Response


def success_response(
    data=None,
    message=None,
    status_code=200,
):
    payload = {
        "success": True,
    }

    if message is not None:
        payload["message"] = message

    if data is not None:
        payload["data"] = data

    return Response(
        payload,
        status=status_code,
    )


def error_response(
    message,
    errors=None,
    status_code=400,
):
    return Response(
        {
            "success": False,
            "message": message,
            "errors": errors,
        },
        status=status_code,
    )