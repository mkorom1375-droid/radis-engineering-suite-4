from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(
        exc,
        context,
    )

    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            errors = exc.message_dict
        else:
            errors = {
                "non_field_errors": exc.messages,
            }

        return Response(
            {
                "success": False,
                "message": "اطلاعات ارسال‌شده معتبر نیست.",
                "errors": errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, IntegrityError):
        return Response(
            {
                "success": False,
                "message": "اطلاعات واردشده با داده‌های موجود تداخل دارد.",
                "errors": {
                    "non_field_errors": [
                        "امکان ذخیره اطلاعات به دلیل تکراری بودن یا نقض محدودیت دیتابیس وجود ندارد."
                    ]
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if response is None:
        return Response(
            {
                "success": False,
                "message": "خطای داخلی سرور رخ داده است.",
                "errors": None,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    errors = response.data

    if isinstance(errors, dict) and set(errors.keys()) == {"detail"}:
        message = errors["detail"]
    else:
        message = get_default_message(response.status_code)

    response.data = {
        "success": False,
        "message": message,
        "errors": errors,
    }

    return response


def get_default_message(status_code):
    messages = {
        status.HTTP_400_BAD_REQUEST: "درخواست ارسال‌شده معتبر نیست.",
        status.HTTP_401_UNAUTHORIZED: "برای انجام این عملیات باید وارد حساب کاربری شوید.",
        status.HTTP_403_FORBIDDEN: "شما اجازه انجام این عملیات را ندارید.",
        status.HTTP_404_NOT_FOUND: "اطلاعات موردنظر پیدا نشد.",
        status.HTTP_405_METHOD_NOT_ALLOWED: "این روش درخواست مجاز نیست.",
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "نوع محتوای ارسال‌شده پشتیبانی نمی‌شود.",
        status.HTTP_429_TOO_MANY_REQUESTS: "تعداد درخواست‌ها بیش از حد مجاز است.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "خطای داخلی سرور رخ داده است.",
    }

    return messages.get(
        status_code,
        "در پردازش درخواست خطایی رخ داده است.",
    )