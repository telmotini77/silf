import pytest
from email.message import EmailMessage

@pytest.fixture
def sample_email_bytes():
    msg = EmailMessage()
    msg['Subject'] = 'Alerta de Carbonio'
    msg['From'] = 'alertas@futurity.com.ec'
    msg['Date'] = 'Tue, 17 Oct 2023 10:00:00 +0000' # UTC
    msg['Message-ID'] = '<12345@futurity.com.ec>'
    
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
        <a href="https://example.com">Enlace Válido</a>
        <a href="javascript:alert(1)">Enlace Malo</a>
        <img src="cid:imagen_logo" alt="Logo">
    </body>
    </html>
    """
    
    msg.set_content("Alerta de texto plano. Sensor: Temperatura Sala 1. Estado: Fuera de rango.")
    msg.add_alternative(html_content, subtype='html')
    
    # Add inline image
    img_data = b"dummy_image_data"
    msg.add_attachment(img_data, maintype='image', subtype='png', cid='<imagen_logo>')
    
    # Add normal attachment
    csv_data = b"col1,col2\nval1,val2"
    msg.add_attachment(csv_data, maintype='text', subtype='csv', filename='data.csv')
    
    return msg.as_bytes()
