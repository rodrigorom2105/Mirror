import subprocess, os, tempfile
from pydub import AudioSegment

WHISPER_CPP_PATH = os.getenv("WHISPER_CPP_PATH", "./whisper.cpp/main")
MODEL_PATH = os.getenv("WHISPER_MODEL", "./data/models/ggml-small.bin")

def _convert_to_wav(input_path: str) -> str:
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    out_path = input_path.rsplit(".", 1)[0] + "_converted.wav"
    audio.export(out_path, format="wav")
    return out_path

def transcribe_audio(audio_path: str) -> dict:
    wav_path = _convert_to_wav(audio_path)
    try:
        result = subprocess.run(
            [WHISPER_CPP_PATH, "-m", MODEL_PATH, "-f", wav_path, "-l", "es", "--output-txt"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        text = result.stdout.strip()
        duration = len(AudioSegment.from_wav(wav_path)) / 1000.0
        return {"text": text, "duration": duration}
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)

# FALLBACK: uncomment if whisper.cpp compilation fails
# from faster_whisper import WhisperModel
# _model = WhisperModel("small", device="cpu", compute_type="int8")
# def transcribe_audio(audio_path: str) -> dict:
#     wav_path = _convert_to_wav(audio_path)
#     segments, info = _model.transcribe(wav_path, language="es")
#     text = " ".join(s.text for s in segments)
#     return {"text": text.strip(), "duration": info.duration}
