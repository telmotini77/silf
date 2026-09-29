import asyncio
import ssl
from aioimaplib import aioimaplib
import os
import sys

async def test_carbonio():
    host = os.getenv("CARBONIO_HOST")
    user = os.getenv("CARBONIO_USER")
    pwd = os.getenv("CARBONIO_PASSWORD")
    ca_file = os.getenv("CARBONIO_CA_FILE")
    
    if not all([host, user, pwd]):
        print("Faltan variables CARBONIO_HOST, CARBONIO_USER, o CARBONIO_PASSWORD")
        sys.exit(1)
        
    print(f"Conectando a {host}:993...")
    
    ssl_context = ssl.create_default_context()
    if ca_file:
        print(f"Usando CA personalizada: {ca_file}")
        ssl_context.load_verify_locations(cafile=ca_file)
        
    client = aioimaplib.IMAP4_SSL(host=host, port=993, ssl_context=ssl_context)
    await client.wait_hello_from_server()
    
    print("Login...")
    resp = await client.login(user, pwd)
    print(f"Respuesta Login: {resp.result}")
    if resp.result != 'OK':
        sys.exit(1)
        
    print("Capacidades:")
    cap_resp = await client.capability()
    print(cap_resp.lines[0].decode())
    
    print("Seleccionando INBOX...")
    resp = await client.select("INBOX")
    print(f"Respuesta Select: {resp.result}")
    
    print("Últimos 5 asuntos:")
    resp = await client.search("ALL")
    if resp.result == 'OK':
        uids = []
        for line in resp.lines:
            for part in line.decode().split():
                if part.isdigit(): uids.append(int(part))
        
        last_5 = uids[-5:]
        for uid in last_5:
            fetch_resp = await client.uid("FETCH", str(uid), "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])")
            for line in fetch_resp.lines:
                if b'Subject:' in line:
                    print(line.decode().strip())
                    
    await client.logout()

if __name__ == "__main__":
    asyncio.run(test_carbonio())
