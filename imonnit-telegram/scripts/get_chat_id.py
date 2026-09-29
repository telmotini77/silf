import asyncio
import httpx
import sys

async def get_chat_id(token: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://api.telegram.org/bot{token}/getUpdates")
        if resp.status_code != 200:
            print(f"Error: {resp.text}")
            return
            
        data = resp.json()
        if not data["result"]:
            print("No hay mensajes nuevos. Envía un mensaje a tu bot en Telegram y vuelve a intentarlo.")
            return
            
        for update in data["result"]:
            if "message" in update:
                chat = update["message"]["chat"]
                print(f"Chat encontrado: {chat['title'] if 'title' in chat else chat['first_name']} (Tipo: {chat['type']})")
                print(f"TELEGRAM_CHAT_ID={chat['id']}")
                return
                
        print("No se encontró chat_id. Envía un mensaje al bot.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python get_chat_id.py <TELEGRAM_BOT_TOKEN>")
        sys.exit(1)
    asyncio.run(get_chat_id(sys.argv[1]))
