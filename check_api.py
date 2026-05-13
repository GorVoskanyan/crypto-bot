import asyncio
import os
from binance import AsyncClient
from dotenv import load_dotenv

async def check_connectivity():
    load_dotenv()
    api_key = os.getenv("EXCHANGE_API_KEY")
    secret = os.getenv("EXCHANGE_SECRET")
    testnet = os.getenv("USE_TESTNET", "false").lower() == "true"

    print(f"--- API Diagnostic ---")
    print(f"Environment: {'Binance TESTNET' if testnet else 'Binance MAINNET'}")
    print(f"API Key: {api_key[:5]}...{api_key[-5:] if api_key else ''}")

    client = await AsyncClient.create(api_key, secret, testnet=testnet)
    try:
        # Test 1: Account Info
        acc = await client.futures_account()
        print("✅ Connection Successful!")
        print(f"✅ Account Type: {acc.get('feeTier', 'Standard')}")
        print(f"✅ Total Wallet Balance: {acc.get('totalWalletBalance')} USDT")

        # Test 2: Permissions
        try:
            await client.futures_change_leverage(symbol="BTCUSDT", leverage=1)
            print("✅ Futures Permissions: OK")
        except Exception as e:
            print(f"❌ Futures Write Permissions Failed: {e}")

    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        print("\nPossible reasons:")
        print("1. Your API Key/Secret is incorrect.")
        print("2. You are using Mainnet keys on Testnet environment (or vice versa).")
        print("3. Your IP is not whitelisted in Binance settings.")
        print("4. Futures are not enabled for this API Key.")

    await client.close_connection()

if __name__ == "__main__":
    asyncio.run(check_connectivity())
