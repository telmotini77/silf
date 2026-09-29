import secrets

def generate():
    token = secrets.token_urlsafe(32)
    print("========================================")
    print("GENERADOR DE SECRETOS")
    print("========================================")
    print(f"ADMIN_TOKEN={token}")
    print("========================================")
    print("Copia este token y pégalo en tu archivo .env")

if __name__ == "__main__":
    generate()
