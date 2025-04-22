
import asyncio

from modules.llm.gguf import LocalLLM


async def generate_text():
    llm = LocalLLM('Mistral-7B-Instruct-v0.3-Q8_0')

    print('Creating response')
    response = await llm.generate(
        prompt="What is RAG SYSTEM?",
        max_tokens=512,
        temperature=0.7
    )
    print('response created')
    print(response.get("text"))

# Run the async function
asyncio.run(generate_text())