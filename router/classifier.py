import logging
from router.models import TASK_KEYWORDS, TASK_ROUTING
from router.providers.groq_provider import GroqProvider

logger = logging.getLogger(__name__)
_groq_provider = None

async def classify(prompt: str, task_type: str | None = None) -> str:
    if task_type and task_type in TASK_ROUTING:
        return task_type

    safe_prompt = prompt.strip()[:1000]

    # Try LLM classification first (using Groq's fast model)
    global _groq_provider
    if _groq_provider is None:
        _groq_provider = GroqProvider()

    if await _groq_provider.is_available():
        try:
            valid_tasks = ", ".join(TASK_ROUTING.keys())
            system_prompt = (
                f"You are a task classifier. Respond ONLY with exactly one word from this list: [{valid_tasks}]. "
                f"Do not add any other text, punctuation, or explanations."
            )
            full_prompt = (
                f"{system_prompt}\n\nPrompt to classify:\n"
                f"---BEGIN PROMPT---\n{safe_prompt}\n---END PROMPT---"
            )

            # Use llama-3.1-8b for very fast classification
            response = await _groq_provider.ask("llama-3.1-8b", full_prompt)
            classification = response.strip().lower()

            # Clean up potential punctuation
            for char in [".", ",", "!", "'", '"']:
                classification = classification.replace(char, "")

            if classification in TASK_ROUTING:
                return classification
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}. Falling back to keywords.")

    # Fallback to keyword-based classification
    lower = safe_prompt.lower()
    scores = {}
    for task, keywords in TASK_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lower)
        if score > 0:
            scores[task] = score
    if not scores:
        return "general"
    return max(scores, key=scores.get)
