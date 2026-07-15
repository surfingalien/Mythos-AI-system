"""Information tools: time, weather, news, Wikipedia, web search."""

from __future__ import annotations

import datetime

import requests

from jarvis.config import config
from jarvis.tools.registry import tool


@tool(description="Get the current local time and date.")
def get_time() -> str:
    now = datetime.datetime.now()
    return f"It is {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}."


@tool(
    description="Get the current weather for a city.",
    parameters={"city": {"type": "string", "description": "City name, e.g. 'Berlin'"}},
    enabled=lambda: config.has_weather,
)
def get_weather(city: str = "") -> str:
    city = city.strip() or config.default_city
    url = (f"https://api.openweathermap.org/data/2.5/weather?q={city}"
           f"&appid={config.weather_api_key}&units=metric")
    response = requests.get(url, timeout=10).json()
    if response.get("cod") == 200:
        temp = response["main"]["temp"]
        desc = response["weather"][0]["description"]
        feels = response["main"].get("feels_like", temp)
        return (f"It's {temp:.0f} degrees Celsius in {city} with {desc}, "
                f"feels like {feels:.0f}.")
    return f"I couldn't find weather for {city}."


@tool(
    description="Get today's top news headlines.",
    parameters={"count": {"type": "integer", "description": "Headlines to fetch (1-10)"}},
    required=[],
    enabled=lambda: config.has_news,
)
def get_news(count: int = 5) -> str:
    count = max(1, min(10, int(count)))
    url = (f"https://newsapi.org/v2/top-headlines?country={config.news_country}"
           f"&apiKey={config.news_api_key}")
    response = requests.get(url, timeout=10).json()
    articles = response.get("articles", [])[:count]
    if not articles:
        return "No headlines available right now."
    headlines = [a["title"] for a in articles]
    return "Here are the top headlines. " + ". ".join(headlines)


@tool(
    description="Look up a topic on Wikipedia and return a short summary.",
    parameters={"topic": {"type": "string", "description": "Topic to look up"}},
)
def wikipedia_summary(topic: str) -> str:
    import wikipedia

    try:
        return wikipedia.summary(topic, sentences=2)
    except Exception:
        return f"I couldn't find {topic} on Wikipedia."


@tool(
    description="Search the web and return the top result URLs with titles. "
                "Use open_url afterwards if the user wants a page opened.",
    parameters={"query": {"type": "string", "description": "Search query"}},
)
def web_search(query: str) -> str:
    from googlesearch import search

    try:
        results = list(search(query, num_results=3))
    except Exception as e:
        return f"Search failed: {e}"
    if not results:
        return "No results found."
    return "Top results: " + " ; ".join(str(r) for r in results)


@tool(
    description="Open a URL in the default web browser.",
    parameters={"url": {"type": "string", "description": "Full URL to open"}},
)
def open_url(url: str) -> str:
    import webbrowser

    webbrowser.open(url)
    return f"Opened {url}."
