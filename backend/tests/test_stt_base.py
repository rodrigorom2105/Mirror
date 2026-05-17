from services.stt.base import Transcriber, TranscriptionResult


def test_transcription_result_holds_text():
    assert TranscriptionResult(text="hola mundo").text == "hola mundo"


def test_transcriber_protocol_is_runtime_checkable():
    class Dummy:
        name = "dummy"

        def transcribe(self, wav_path):
            return TranscriptionResult(text="x")

    assert isinstance(Dummy(), Transcriber)


def test_incomplete_class_is_not_a_transcriber():
    class NotATranscriber:
        name = "x"

    assert not isinstance(NotATranscriber(), Transcriber)
