import os

from django.core.exceptions import ValidationError


DEFAULT_ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".dwg",
    ".dxf",
    ".txt",
    ".zip",
}


def validate_file_size(
    file,
    maximum_size_mb=25,
):
    maximum_size = maximum_size_mb * 1024 * 1024

    if file.size > maximum_size:
        raise ValidationError(
            f"حجم فایل نباید بیشتر از {maximum_size_mb} مگابایت باشد."
        )


def validate_file_extension(
    file,
    allowed_extensions=None,
):
    allowed_extensions = (
        allowed_extensions
        or DEFAULT_ALLOWED_DOCUMENT_EXTENSIONS
    )

    extension = os.path.splitext(
        file.name
    )[1].lower()

    if extension not in allowed_extensions:
        raise ValidationError(
            "پسوند فایل انتخاب‌شده مجاز نیست."
        )


def validate_document_file(file):
    validate_file_size(
        file,
        maximum_size_mb=25,
    )

    validate_file_extension(file)