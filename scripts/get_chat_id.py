import asyncio
import httpx

async def get_chat_id():
    token = input("Enter your Telegram Bot Token: ")
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    print(f"Buscando actualizaciones para el bot...")
    print("Asegúrate de haberle enviado al menos un mensaje al bot primero.")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            if data["ok"] and data["result"]:
                for result in data["result"]:
                    if "message" in result:
                        chat = result["message"]["chat"]
                        print(f"Chat ID encontrado: {chat['id']} (Tipo: {chat['type']})")
                        return
            print("No se encontraron mensajes. Envía un mensaje al bot e intenta de nuevo.")
        else:
            print(f"Error: {response.text}")

if __name__ == "__main__":
    asyncio.run(get_chat_id())
