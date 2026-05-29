import os, uuid, base64, requests, traceback, json, random
from flask import Flask, request, jsonify, render_template
from pydub import AudioSegment
import io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')

# Letras pré-geradas por estilo (fallback sem OpenAI)
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
    """Retorna letras disponíveis para o estilo escolhido"""
    data = request.get_json()
    estilo = data.get('estilo', 'pop').lower()
    letras = LETRAS.get(estilo, LETRAS['pop'])
    resultado = [{'titulo': t, 'letra': l} for t, l in letras]
    return jsonify({'letras': resultado})

@app.route('/api/clone_voice', methods=['POST'])
def clone_voice():
    """Clona a voz usando ElevenLabs"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'Nenhum arquivo de áudio enviado'}), 400

        audio_file = request.files['audio']
        nome = request.form.get('nome', 'Minha Voz')

        # Salva o arquivo temporariamente
        tmp_path = f'/tmp/voice_{uuid.uuid4().hex}.webm'
        audio_file.save(tmp_path)

        # Converte para MP3
        mp3_path = tmp_path + '.mp3'
        os.system(f'ffmpeg -y -i {tmp_path} -ar 44100 -ac 1 {mp3_path} 2>/dev/null')

        # Envia para ElevenLabs para clonar a voz
        with open(mp3_path, 'rb') as f:
            resp = requests.post(
                'https://api.elevenlabs.io/v1/voices/add',
                headers={'xi-api-key': ELEVENLABS_API_KEY},
                data={'name': nome, 'description': 'Voz clonada pelo Maestro'},
                files={'files': (f'{nome}.mp3', f, 'audio/mpeg')},
                timeout=60
            )

        os.remove(tmp_path)
        os.remove(mp3_path)

        if resp.status_code == 200:
            voice_data = resp.json()
            voice_id = voice_data.get('voice_id')
            return jsonify({'success': True, 'voice_id': voice_id, 'nome': nome})
        else:
            return jsonify({'error': f'Erro ElevenLabs: {resp.text}'}), 400

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/gerar_musica', methods=['POST'])
def gerar_musica():
    """Gera a música com a voz clonada cantando a letra"""
    try:
        data = request.get_json()
        voice_id = data.get('voice_id')
        letra = data.get('letra')
        titulo = data.get('titulo', 'Minha Música')

        if not voice_id or not letra:
            return jsonify({'error': 'voice_id e letra são obrigatórios'}), 400

        # Usa ElevenLabs Text-to-Speech com a voz clonada
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
                    'stability': 0.5,
                    'similarity_boost': 0.8,
                    'style': 0.3,
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

@app.route('/api/listar_vozes', methods=['GET'])
def listar_vozes():
    """Lista as vozes clonadas do usuário"""
    try:
        resp = requests.get(
            'https://api.elevenlabs.io/v1/voices',
            headers={'xi-api-key': ELEVENLABS_API_KEY},
            timeout=30
        )
        if resp.status_code == 200:
            voices = resp.json().get('voices', [])
            # Filtra apenas vozes clonadas (não as padrão)
            cloned = [v for v in voices if v.get('category') == 'cloned']
            return jsonify({'vozes': cloned})
        else:
            return jsonify({'vozes': []})
    except Exception as e:
        return jsonify({'vozes': [], 'error': str(e)})

@app.route('/api/deletar_voz', methods=['POST'])
def deletar_voz():
    """Deleta uma voz clonada"""
    try:
        data = request.get_json()
        voice_id = data.get('voice_id')
        resp = requests.delete(
            f'https://api.elevenlabs.io/v1/voices/{voice_id}',
            headers={'xi-api-key': ELEVENLABS_API_KEY},
            timeout=30
        )
        return jsonify({'success': resp.status_code == 200})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
