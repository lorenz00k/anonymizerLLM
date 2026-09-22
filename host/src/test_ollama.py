import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

def ask(prompt: str) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


if __name__ == "__main__":
    antwort = ask("Hallo, wer bist du? Antworte in einem Satz.")
    print(antwort)