from config.settings import settings
from langchain_mistralai import ChatMistralAI

API_MISTRAL_KEY = settings.API_MISTRAL_KEY

LLM = ChatMistralAI(
    model="mistral-small-latest",
    temperature=0,
    max_retries=2,
    api_key=API_MISTRAL_KEY,
)

MESSAGES = [
    (
        "system",
        "You are a helpful assistant.",
    ),
    ("human", "Cuáles son las posibilidades de que te caiga un rayo?"),
]

def test_mistral_ai():
    ai_msg = LLM.invoke(MESSAGES)
    print(ai_msg)