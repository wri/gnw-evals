from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()

HAIKU = ChatAnthropic(
    model="claude-haiku-4-5",
    temperature=0,
    max_tokens=8_192,
)
