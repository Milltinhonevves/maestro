import os, uuid, base64, requests, traceback, json, random
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')

# Letras pré-geradas por estilo
LETRAS = {
    'funk': [
        ("Minha Voz", "Eu chego chegando, todo mundo me olha\nMinha voz é fogo, ninguém me segura\nNo baile da vida eu sei dançar\nCom minha música vou te conquistar"),
        ("Na Pista", "Na pista eu domino, meu flow é original\nMinha voz ecoa, é algo especial\nVem comigo agora, vem me ouvir cantar\nEssa música nova vai te agitar"),
    ],
    'sertanejo': [
        ("Saudade do Interior", "Lembro dos campos, do pôr do sol dourado\nDa voz do meu pai quando eu era criança\nSaudade do interior me pegou\nEssa música do coração brotou"),
        ("Estrada da Vida", "Na estrada da vida eu aprendi a cantar\nCada nota é uma história pra contar\nMinha voz leva tudo que eu sinto\nÉ puro sertanejo, é genuíno e distinto"),
    ],
    'trap': [
        ("No Topo", "Vim do zero, hoje estou no topo\nMinha voz ressoa em todo o povo\nO game mudou quando eu cheguei\nCom meu flow diferente eu provei"),
        ("Meu Ritmo", "Meu ritmo é pesado, minha voz é real\nNão tem quem me pare nesse carnaval\nDrip no flow, tudo original\nSou o novo som do Brasil"),
    ],
    'pagode': [
        ("Amor de Verdade", "Quando você chega, tudo muda ao redor\nMinha voz te canta com todo o amor\nNo pagode da vida você é meu compasso\nCada nota é um passo, cada passo é um laço"),
        ("Roda de Samba", "Na roda de samba minha voz floresce\nO tamborim bate e o coração cresce\nCanto pra você com toda a emoção\nEssa é minha voz, essa é minha canção"),
    ],
    'pop': [
        ("Brilhar", "Hoje eu vou brilhar, ninguém vai me parar\nMinha voz é luz que vai te iluminar\nCom essa música nova vou mostrar\nQue nasci pra cantar e conquistar"),
        ("Momento", "Esse é o momento de mostrar quem sou\nMinha voz ressoa onde quer que vou\nA música é minha maior expressão\nVem sentir comigo essa emoção"),
    ],
}

def no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.after_request
def after_request(response):
    return no_cache(response)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/letras', methods=['POST'])
def get_letras():
    data = request.get_json()
    estilo = data.get('estilo', 'pop').lower()
    letras = LETRAS.get(estilo, LETRAS['pop'])
    resultado = [{'titulo': t, 'letra': l} for t, l in letras]
    return jsonify({'letras': resultado})

@app.route('/api/vozes', methods=['GET'])
def listar_vozes():
    """Lista as vozes disponíveis do ElevenLabs (prontas para usar)"""
    try:
        resp = requests.get(
            'https://api.elevenlabs.io/v1/voices',
            headers={'xi-api-key': ELEVENLABS_API_KEY},
            timeout=30
        )
        if resp.status_code == 200:
            voices = resp.json().get('voices', [])
            # Retorna nome, id e categoria de cada voz
            resultado = [
                {
                    'voice_id': v['voice_id'],
                    'name': v['name'],
                    'category': v.get('category', 'premade'),
                    'labels': v.get('labels', {})
                }
                for v in voices
            ]
            return jsonify({'vozes': resultado})
        else:
            return jsonify({'vozes': [], 'error': resp.text}), 400
    except Exception as e:
        return jsonify({'vozes': [], 'error': str(e)}), 500

@app.route('/api/gerar_musica', methods=['POST'])
def gerar_musica():
    """Gera áudio com uma voz pronta do ElevenLabs"""
    try:
        data = request.get_json()
        voice_id = data.get('voice_id')
        letra = data.get('letra')
        titulo = data.get('titulo', 'Minha Música')

        if not voice_id or not letra:
            return jsonify({'error': 'voice_id e letra são obrigatórios'}), 400

        resp = requests.post(
            f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
            headers={
                'xi-api-key': ELEVENLABS_API_KEY,
                'Content-Type': 'application/json'
            },
            json={
                'text': letra,
                'model_id': 'eleven_multilingual_v2',
                'voice_settings': {
                    'stability': 0.4,
                    'similarity_boost': 0.8,
                    'style': 0.5,
                    'use_speaker_boost': True
                }
            },
            timeout=120
        )

        if resp.status_code == 200:
            audio_b64 = base64.b64encode(resp.content).decode('utf-8')
            return jsonify({
                'success': True,
                'audio': audio_b64,
                'titulo': titulo,
                'formato': 'audio/mpeg'
            })
        else:
            return jsonify({'error': f'Erro ao gerar áudio: {resp.text}'}), 400

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
