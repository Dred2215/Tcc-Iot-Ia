import subprocess
from pathlib import Path
from google.cloud import speech
from google.oauth2 import service_account

# 🔹 Escopos mínimos para usar a API Speech
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

# Caminho da pasta secret
SECRET_DIR = Path(__file__).resolve().parent.parent / "secret"
# Caminho da pasta de áudios
AUDIO_DIR = Path(__file__).resolve().parent.parent / "audio"


# ----------------------------
# Conversão para MP3 com ffmpeg
# ----------------------------
def convert_audio_to_mp3():
    if not AUDIO_DIR.exists():
        print("❌ Pasta 'audio' não encontrada.")
        return

    for file in AUDIO_DIR.glob("*.webm"):
        mp3_file = file.with_suffix(".mp3")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(file), str(mp3_file)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print(f"✅ Convertido: {file.name} → {mp3_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao converter {file.name}: {e.stderr.decode()}")


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
# Transcrição de áudio
# ----------------------------
def transcrever_audio():
    creds = load_credentials()
    client = speech.SpeechClient(credentials=creds)

    # 📂 Pega o primeiro arquivo MP3 na pasta audio
    arquivos = list(AUDIO_DIR.glob("*.mp3"))
    if not arquivos:
        print("⚠️ Nenhum arquivo .mp3 encontrado em /audio")
        return

    arquivo_audio = arquivos[0]
    print(f"[INFO] Transcrevendo: {arquivo_audio.name}")

    with open(arquivo_audio, "rb") as f:
        audio_content = f.read()

    # Prepara configuração
    audio_google = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.MP3,
        sample_rate_hertz=44100,   # padrão de conversão
        language_code="pt-BR",
        model="default"
    )

    try:
        response = client.recognize(config=config, audio=audio_google)

        if not response.results:
            print("⚠️ Nenhuma transcrição encontrada.")
            return

        for result in response.results:
            print(f"[TRANSCRIÇÃO] {result.alternatives[0].transcript}")

    except Exception as e:
        print(f"❌ Erro na transcrição: {e}")


# ----------------------------
# Execução principal
# ----------------------------
if __name__ == "__main__":
    # 1. Converte todos os .webm encontrados para .mp3
    convert_audio_to_mp3()

    # 2. Transcreve o primeiro .mp3 disponível
    transcrever_audio()
