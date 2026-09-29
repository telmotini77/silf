import pytest
from email.message import EmailMessage

@pytest.fixture
def sample_email_bytes():
    msg = EmailMessage()
    msg['Subject'] = 'Alerta iMonnit'
    msg['From'] = 'alertas@imonnit.com'
    msg['Date'] = 'Tue, 17 Oct 2023 10:00:00 +0000'
    msg['Message-ID'] = '<12345@imonnit.com>'
    
    html_content = """
    <html>
    <head><style>.hidden { display: none; }</style></head>
    <body>
        <div class="hidden">Preheader secreto</div>
        <script>alert('xss');</script>
        <h1>Alerta Crítica</h1>
        <table>
            <tr><td><b>Sensor:</b></td><td>Temperatura Sala 1</td></tr>
            <tr><td>Estado:</td><td>Fuera de rango</td></tr>
            <tr><td>Detalle extra</td></tr>
        </table>
        <ul>
            <li>Acción requerida</li>
        </ul>
        <a href="javascript:alert(1)">Enlace Malo</a>
        <img src="cid:imagen_logo" alt="Logo">
    </body>
    </html>
    """
    
    msg.set_content("Alerta de texto plano.")
    msg.add_alternative(html_content, subtype='html')
    msg.add_attachment(b"dummy", maintype='image', subtype='png', cid='<imagen_logo>')
    msg.add_attachment(b"csv_data", maintype='text', subtype='csv', filename='data.csv')
    
    return msg.as_bytes()
