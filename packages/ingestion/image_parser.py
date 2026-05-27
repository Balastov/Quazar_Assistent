import base64
import io
import logging
from pathlib import Path

from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/tiff",
}


def _ocr_image(img: Image.Image, language: str) -> str:
    try:
        import pytesseract
    except ImportError:
        return ""

    try:
        return pytesseract.image_to_string(img, lang=language).strip()
    except Exception as e:
        logger.warning("OCR failed: %s", e)
        return ""


def _vision_describe(content: bytes, mime_type: str, filename: str, model: str, api_key: str, base_url: str) -> str:
    if not api_key:
        return ""

    try:
        import httpx

        b64 = base64.standard_b64encode(content).decode()
        data_url = f"data:{mime_type};base64,{b64}"
        response = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Опиши содержимое изображения для корпоративной базы знаний. "
                                    "Извлеки весь видимый текст, таблицы, диаграммы и подписи. "
                                    f"Файл: {filename}"
                                ),
                            },
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                "max_tokens": 2000,
            },
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning("Vision API failed: %s", e)
        return ""


def extract_image(
    content: bytes,
    mime_type: str,
    filename: str,
    *,
    ocr_language: str = "rus+eng",
    vision_fallback: bool = True,
    vision_model: str = "gpt-4o-mini",
    openai_api_key: str = "",
    openai_base_url: str = "https://api.openai.com/v1",
) -> str:
    ext = Path(filename).suffix.lower()
    parts = [f"# Изображение: {filename}"]

    try:
        img = Image.open(io.BytesIO(content))
        img.load()
        parts.append(f"Формат: {img.format or ext}, размер: {img.width}x{img.height}, режим: {img.mode}")

        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        ocr_text = _ocr_image(img, ocr_language)
        if ocr_text:
            parts.append("\n## Распознанный текст (OCR)\n")
            parts.append(ocr_text)
        elif vision_fallback:
            vision_text = _vision_describe(content, mime_type, filename, vision_model, openai_api_key, openai_base_url)
            if vision_text:
                parts.append("\n## Описание (vision)\n")
                parts.append(vision_text)
            else:
                parts.append(
                    "\n(Текст на изображении не распознан. Установите Tesseract OCR "
                    "или настройте OPENAI_API_KEY для vision-анализа.)"
                )
        else:
            parts.append("\n(Текст на изображении не распознан.)")

    except Exception as e:
        parts.append(f"\nОшибка обработки изображения: {e}")

    return "\n".join(parts)
