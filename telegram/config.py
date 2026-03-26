import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env")
if not NEO4J_PASSWORD:
    raise ValueError("NEO4J_PASSWORD not found in .env")