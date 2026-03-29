import asyncio
import sys
import os

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.scout import get_trending_context
from utils.image_utils import select_best_image
from db.session import SessionLocal

async def verify():
    print("--- Verifying Scouting ---")
    context = await get_trending_context()
    print(f"Context Found:\n{context[:500]}...")
    
    print("\n--- Verifying Image Matching ---")
    db = SessionLocal()
    test_content = "Check out this amazing new SaaS dashboard UI I've been working on! #SaaS #Design"
    match = await select_best_image(test_content, db)
    print(f"Post: {test_content}")
    print(f"Matched Image: {match}")
    db.close()

if __name__ == "__main__":
    asyncio.run(verify())
