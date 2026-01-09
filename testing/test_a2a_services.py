import asyncio
import httpx

async def test_services():
    services = [
        ("Data Agent", "http://localhost:8001/health"),
        ("Analysis Agent", "http://localhost:8002/health"),
        ("Memory Agent", "http://localhost:8003/health"),
    ]
    
    async with httpx.AsyncClient() as client:
        for name, url in services:
            try:
                response = await client.get(url, timeout=2.0)
                if response.status_code == 200:
                    print(f"{name}: OK")
                else:
                    print(f"{name}: Error {response.status_code}")
            except Exception as e:
                print(f"{name}: No disponible - {e}")

if __name__ == "__main__":
    asyncio.run(test_services())