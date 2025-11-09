import os
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict, field
from google.genai import types
from google.generativeai.types import GenerateContentResponse
from google import genai

# LLM configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
THINKING_BUDGET = int(os.getenv("THINKING_BUDGET", "8000"))
current_date = datetime.now().strftime("%Y-%m-%d")

def get_content(type, prompt):
    role = "system" if type == "system" else "user"
    contents = [
        types.Content(
            role=role,
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    return contents

def _get_tools(tools: bool = False):
    if tools:
        tools = [types.Tool(googleSearch=types.GoogleSearch())]
    else:
        tools = []

    return tools
    
def _get_generate_config( tools, instruction, thinking_budget = 0, res_type = "text/plain"):
    if thinking_budget == 0 and GEMINI_MODEL == "gemini-2.5-pro":
        thinking_budget = -1

    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_budget=thinking_budget,
        ),
        tools=tools,
        system_instruction=[
            instruction
        ],
        response_mime_type= res_type
    )


def search_tool(**kwargs) -> str:
    query = kwargs.get("search_query", "")
    instruction = kwargs.get("search_instruction", "")

    if not query:
        return "No query provided for search."
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"❌ Failed to create LLM client: {e}")
        client = None

    if not client:
        raise Exception("LLM client not configured")
    
    tools = _get_tools(True)
    content = get_content("user", query)
    config = _get_generate_config(tools, instruction, THINKING_BUDGET)

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=content,
            config=config
        )
        return response.text
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        # Return empty JSON on failure
        return "{}"


def url_context_tool(**kwargs) -> str:
    url = kwargs.get("url", "")
    query = kwargs.get("context_query", "")
    instruction = kwargs.get("context_instruction", "")

    if not url:
        return "No URL provided for context extraction."
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"❌ Failed to create LLM client: {e}")
        client = None

    if not client:
        raise Exception("LLM client not configured")
    
    tools = [
        types.Tool(url_context=types.UrlContext()),
        types.Tool(googleSearch=types.GoogleSearch(
        )),
    ]

    prompt = f"URL: {url} Query: {query}"
    content = get_content("user", prompt)
    config = _get_generate_config(tools, instruction, THINKING_BUDGET)

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=content,
            config=config
        )
        return response.text
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        # Return empty JSON on failure
        return "{}"


def map_tool(**kwargs) -> str:
    query = kwargs.get("map_search_query", "")
    instruction = kwargs.get("context_instruction", "")

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"❌ Failed to create LLM client: {e}")
        client = None

    if not client:
        raise Exception("LLM client not configured")
    
    system_instruction = f"""Your Identity:
    You are the 'Local Guide Agent,' a friendly and knowledgeable AI assistant. Your purpose is to act as a helpful local expert, answering a user's query about places, activities, or points of interest. You will present your findings in a clear, engaging, and human-readable summary.
    Core Mission:
    Your mission is to take a user's map_search_query, use your advanced search and map tools to discover relevant locations, gather key information, and then synthesize this into a well-structured, natural language response formatted with Markdown. Your goal is to provide a response that is immediately useful and pleasant for a person to read.
    Intelligent Tool Usage Protocol:
    Deconstruct the Query: First, understand the user's true intent. Are they looking for a list of options ('restaurants near the Eiffel Tower'), a specific type of experience ('a quiet park to read a book'), or details about a place ('opening hours for the British Museum')?
    Discover with Google Search (Primary Tool): For any query that requires discovery, recommendations, or qualitative information (e.g., 'best,' 'popular,' 'kid-friendly'), use GoogleSearch first. Use it to find promising place names and, more importantly, to understand why they are a good match for the query.
    Verify and Enrich with Google Maps (Secondary Tool): Once you have candidate place names, use the GoogleMaps tool to get factual details like the official name, precise address, and coordinates.
    Strict Output Requirements & Formatting:
    Your final output MUST be a human-readable text response. You MUST use Markdown to structure your answer for clarity. Do not output JSON.
    1. For Successful Queries with Recommendations:
    Start with a brief, friendly introductory sentence.
    For each recommended place, create a distinct section using a Markdown heading (###).
    Within each section, present the information clearly:
    Bulleted List for Facts: Use a bulleted list for key data like Address, Category, Website, or Hours.
    'Why it's a great choice': Following the facts, write a short, engaging paragraph explaining why this place is relevant to the user's query. This is where you add your value by synthesizing the information you found.
    2. For Queries About a Single Place:
    Provide the information in a clear, summarized format. A combination of a short paragraph and a bulleted list of key facts works best.
    3. If No Results Are Found:
    Do not return an empty response. Provide a polite and helpful message. For example: 'I couldn't find any specific matches for your query. You might have better luck if you try searching for a broader category or a different neighborhood.
    Note: {instruction}
    """

    tools = [
        types.Tool(google_maps=types.GoogleMaps()),
        types.Tool(googleSearch=types.GoogleSearch(
        )),
    ]

    prompt = f"Query: {query}"
    content = get_content("user", prompt)
    config = _get_generate_config(tools, system_instruction, THINKING_BUDGET)

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=content,
            config=config
        )
        return response.text
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        # Return empty JSON on failure
        return "{}"