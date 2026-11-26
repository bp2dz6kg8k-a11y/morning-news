import json
import os
import re
from datetime import datetime, timezone, timedelta
import feedparser
from google import genai
from google.genai import types
from pydantic import BaseModel

client = genai.Client()

FEEDS = {
    "Financial Times": "https://www.ft.com/?format=rss",
    "The Economist": "https://www.economist.com/finance-and-economics/rss.xml",
}


class TranslatedArticle(BaseModel):
    title_ja: str
    summary_ja: str


def clean_html(raw_html: str) -> str:
    return re.sub(r"<[^>]+>", "", raw_html or "").strip()


def translate_article(title: str, summary: str) -> dict:
    prompt = f"""
    以下の英語の経済ニュースの見出しと概要を、日本の経済紙のような自然なビジネス日本語に翻訳してください。
    概要が短い場合は見出しの文脈も踏まえて分かりやすく簡潔にまとめてください。

    Title: {title}
    Summary: {summary}
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TranslatedArticle,
        ),
    )
    return json.loads(response.text)


def main():
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst).strftime("%Y/%m/%d %H:%M")
    articles = []

    for source, url in FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:6]:
            title = clean_html(entry.get("title", ""))
            summary = clean_html(entry.get("summary", ""))
            link = entry.get("link", "")

            if not title:
                continue

            try:
                translated = translate_article(title, summary)
                articles.append({
                    "source": source,
                    "original_title": title,
                    "title_ja": translated.get("title_ja", title),
                    "summary_ja": translated.get("summary_ja", summary),
                    "link": link,
                    "fetched_at": now_jst,
                })
            except Exception as e:
                print(f"Error translating '{title}': {e}")

    with open("daily_news.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
