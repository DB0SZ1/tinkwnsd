"""
X (Twitter) Free Tier API Test Script
======================================

FREE TIER LIMITS:
  - GET /2/users/me          (Get Authenticated User)
  - POST /2/tweets           (Create Tweet)
  - DELETE /2/tweets/:id     (Delete Tweet)  

This script tests all free-tier-allowed endpoints.
"""

import os
import sys
import time

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

import tweepy

def mask(s):
    if not s: return "(empty)"
    if len(s) <= 8: return "****"
    return f"{s[:4]}...{s[-4:]}"

def test_endpoint(name, func, *args, **kwargs):
    print(f"\n[TESTING] {name}...")
    try:
        res = func(*args, **kwargs)
        print(f"  [SUCCESS] {name} worked!")
        return res
    except Exception as e:
        print(f"  [FAIL] {name} failed: {type(e).__name__}: {e}")
        return None

def main():
    print("=" * 60)
    print("  X (Twitter) Free Tier API Test")
    print("=" * 60)
    
    # Load credentials - support both naming conventions
    api_key = os.getenv("X_CONSUMER_KEY") or os.getenv("X_API_KEY", "")
    api_secret = os.getenv("X_CONSUMER_KEY_SECRET") or os.getenv("X_API_SECRET", "")
    access_token = os.getenv("X_ACCESS_TOKEN", "")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET", "")
    
    print(f"\n[CHECK] Credentials:")
    print(f"  Consumer Key:         {mask(api_key)}")
    print(f"  Consumer Secret:      {mask(api_secret)}")
    print(f"  Access Token:         {mask(access_token)}")
    print(f"  Access Token Secret:  {mask(access_token_secret)}")
    
    missing = []
    if not api_key: missing.append("X_CONSUMER_KEY / X_API_KEY")
    if not api_secret: missing.append("X_CONSUMER_KEY_SECRET / X_API_SECRET")
    if not access_token: missing.append("X_ACCESS_TOKEN")
    if not access_token_secret: missing.append("X_ACCESS_TOKEN_SECRET")
    
    if missing:
        print(f"\n[FAIL] MISSING: {', '.join(missing)}")
        return
    
    print("\n[OK] All 4 credentials present.")
    
    # Build client
    print("\n[BUILD] Building tweepy.Client (OAuth 1.0a User Context)...")
    client = tweepy.Client(
        consumer_key=api_key.strip(),
        consumer_secret=api_secret.strip(),
        access_token=access_token.strip(),
        access_token_secret=access_token_secret.strip(),
        wait_on_rate_limit=True
    )
    print("  Client built successfully.")
    
    # 1. Test GET /2/users/me
    me_res = test_endpoint("GET /2/users/me", client.get_me)
    if me_res and me_res.data:
        print(f"  User ID: {me_res.data.id}, Username: {me_res.data.username}")

    # 2. Test POST /2/tweets
    test_text = f"API connectivity test - will be deleted. [{int(time.time())}]"
    print(f"  Text: \"{test_text}\"")
    
    max_retries = 3
    create_res = None
    for attempt in range(max_retries):
        create_res = test_endpoint(f"POST /2/tweets (Attempt {attempt+1}/{max_retries})", client.create_tweet, text=test_text)
        if create_res:
            break
        print("  Waiting 5 seconds before retry...")
        time.sleep(5)
        
    if create_res and create_res.data:
        tweet_id = create_res.data["id"]
        print(f"  Tweet ID: {tweet_id}")
        
        # 3. Test DELETE /2/tweets/:id
        print(f"\n[WAIT] Waiting 3 seconds before delete...")
        time.sleep(3)
        delete_res = test_endpoint("DELETE /2/tweets/:id", client.delete_tweet, tweet_id)
        if delete_res and delete_res.data.get('deleted'):
            print(f"  [OK] Test tweet deleted successfully.")
            
    print("\n" + "=" * 60)
    print("  [DONE] Free Tier Endpoints Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()

