import requests

def ask_llm(prompt, model="qwen2.5-coder:7b"):

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False
        }
    )

    response.raise_for_status()

    return response.json()["response"]

prompt = "Explain what the Linux scheduler does."

print(ask_llm(prompt))