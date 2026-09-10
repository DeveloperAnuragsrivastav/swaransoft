from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form

from app.core.location import is_location_query, get_location_response
from app.core.rag import get_rag_answer
from app.core.llm import ask_llm_about_image
from app.core.language import detect_language, to_english, from_english, SUPPORTED_LANGUAGES

router = APIRouter()


@router.post("/chat")
async def chat(
    message: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    language: Optional[str] = Form(None),  # manual override, e.g. "hi" - None means auto-detect
):
    """
    Unified multimodal, multi-language endpoint. Accepts text, an image, or both.

    Flow:
    1. Detect the user's language (or use their manual override).
    2. Translate their typed message to English internally.
    3. If an image is attached, describe it using the local vision model
       (vision model output is already in English).
    4. Combine the (translated) message + image description into one query.
    5. If the combined query is location-related, answer directly from
       the fixed company config.
    6. Otherwise, run the combined query through the RAG pipeline.
    7. Translate the final answer back into the user's language before
       returning it.
    """
    text_message = (message or "").strip()

    # Step 1: figure out target language (manual override wins over auto-detect)
    if language and language in SUPPORTED_LANGUAGES:
        user_lang = language
    else:
        user_lang = detect_language(text_message)

    # Step 2: translate the typed message to English for internal processing
    english_message = to_english(text_message, user_lang) if text_message else ""

    image_description = ""
    if image is not None:
        image_bytes = await image.read()
        image_description = ask_llm_about_image(
            image_bytes,
            "Describe what is in this image in detail, including any text, "
            "signage, or location cues visible.",
        )

    combined_parts = [p for p in [english_message, image_description] if p]
    combined_query = " ".join(combined_parts).strip()

    if not combined_query:
        fallback = "Please send a message or an image to ask about."
        return {"type": "text", "text": from_english(fallback, user_lang), "language": user_lang}

    response: dict = {"type": "text", "language": user_lang}

    if image_description:
        response["image_description"] = image_description

    if is_location_query(combined_query):
        location_data = get_location_response()
        answer_text = location_data["text"]
        if image_description:
            answer_text = f"{image_description}\n\n{answer_text}"
        response.update(location_data)
        response["text"] = from_english(answer_text, user_lang)
        return response

    answer = get_rag_answer(combined_query)
    if image_description:
        answer = f"{image_description}\n\n{answer}"

    response["text"] = from_english(answer, user_lang)
    return response
