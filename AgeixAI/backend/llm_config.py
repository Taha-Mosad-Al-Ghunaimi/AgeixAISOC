from crewai import LLM
import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

def get_master_brain_llm():
    return LLM(model="ollama/qwen2.5:14b", base_url=OLLAMA_BASE_URL)

def get_coder_llm():
    return LLM(model="ollama/qwen2.5-coder:7b", base_url=OLLAMA_BASE_URL)

def get_fast_triage_llm():
    return LLM(model="ollama/llama3.1:latest", base_url=OLLAMA_BASE_URL)

def get_osint_llm():
    return LLM(model="ollama/gemma4:latest", base_url=OLLAMA_BASE_URL)
