import subprocess
from pathlib import Path
import shutil
import re
import unicodedata
import time
from google.cloud import speech
from google.oauth2 import service_account

# 🔹 Escopos mínimos para usar a API Speech
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

# Caminhos das pastas
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_DIR = BASE_DIR / "secret"
AUDIO_DIR = BASE_DIR / "audio"
CHECKED_AUDIO_DIR = BASE_DIR / "checked_audio"

# Garante que a pasta de destino exista
CHECKED_AUDIO_DIR.mkdir(exist_ok=True)


# ----------------------------
# Autenticação com Service Account
# ----------------------------
def get_service_account():
    json_files = list(SECRET_DIR.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"Nenhum arquivo JSON encontrado em {SECRET_DIR}")
    print(f"✅ Usando credencial de Service Account: {json_files[0]}")
    return json_files[0]


def load_credentials():
    secret_path = get_service_account()
    creds = service_account.Credentials.from_service_account_file(
        str(secret_path), scopes=SCOPES
    )
    return creds


# ----------------------------
# Função auxiliar: cria nome de arquivo baseado na transcrição
# ----------------------------
def gerar_nome_audio(transcricao: str) -> str:
    # Remove acentos e caracteres especiais
    texto_limpo = unicodedata.normalize("NFKD", transcricao).encode("ASCII", "ignore").decode()
    # Mantém apenas letras, números e espaços
    texto_limpo = re.sub(r"[^a-zA-Z0-9\s]", "", texto_limpo)
    # Pega os 10 primeiros caracteres e substitui espaços por "_"
    prefixo = "_".join(texto_limpo.strip().split())[:10]
    return f"{prefixo}_check.mp3"


# ----------------------------
# Transcrição de áudio
# ----------------------------
def transcrever_audio():
    tempo_inicio_total = time.time()  # 🕒 Início do processo total

    if not AUDIO_DIR.exists():
        print("❌ Pasta 'audio' não encontrada.")
        return

    converted_files = []

    # 1️⃣ Converte todos os .webm para .mp3 antes de transcrever
    print("\n🎧 Iniciando conversão de arquivos .webm → .mp3...")
    tempo_inicio_conversao = time.time()

    webm_files = list(AUDIO_DIR.glob("*.webm"))
    for file in webm_files:
        mp3_file = file.with_suffix(".mp3")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(file), str(mp3_file)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"✅ Convertido: {file.name} → {mp3_file.name}")
            converted_files.append((file, mp3_file))
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao converter {file.name}: {e.stderr.decode()}")

    tempo_fim_conversao = time.time()
    print(f"⏱️ Conversão concluída em {tempo_fim_conversao - tempo_inicio_conversao:.2f} segundos.\n")

    # 2️⃣ Carrega credenciais e inicializa cliente
    creds = load_credentials()
    client = speech.SpeechClient(credentials=creds)

    # 3️⃣ Transcreve cada arquivo convertido
    for original_file, mp3_file in converted_files:
        tempo_inicio_transcricao = time.time()
        print(f"[INFO] Transcrevendo: {mp3_file.name}")

        with open(mp3_file, "rb") as f:
            audio_content = f.read()

        audio_google = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.MP3,
            sample_rate_hertz=44100,
            language_code="pt-BR",
            model="default"
        )

        try:
            response = client.recognize(config=config, audio=audio_google)

            if not response.results:
                print("⚠️ Nenhuma transcrição encontrada.")
                continue

            texto_transcrito = " ".join(
                [result.alternatives[0].transcript for result in response.results]
            )
            print(f"[TRANSCRIÇÃO] {texto_transcrito}")

            # 4️⃣ Gera novo nome do arquivo de áudio
            novo_nome = gerar_nome_audio(texto_transcrito)
            destino = CHECKED_AUDIO_DIR / novo_nome

            # 5️⃣ Move e renomeia o áudio convertido para /checked_audio
            shutil.move(mp3_file, destino)
            print(f"📦 Áudio movido e renomeado para: {destino.name}")

            # 6️⃣ Remove o arquivo original .webm
            original_file.unlink(missing_ok=True)
            print(f"🗑️ Removido original: {original_file.name}")

        except Exception as e:
            print(f"❌ Erro na transcrição de {mp3_file.name}: {e}")

        tempo_fim_transcricao = time.time()
        print(f"⏱️ Tempo da transcrição: {tempo_fim_transcricao - tempo_inicio_transcricao:.2f} segundos\n")

    tempo_total = time.time() - tempo_inicio_total
    print(f"✅ Processo completo finalizado em {tempo_total:.2f} segundos 🚀")


# ----------------------------
# Execução principal
# ----------------------------
if __name__ == "__main__":
    transcrever_audio()
