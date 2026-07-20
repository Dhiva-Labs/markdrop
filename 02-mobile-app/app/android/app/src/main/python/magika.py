"""Stub for magika (real package needs onnxruntime, unavailable on Android).

markitdown imports magika unconditionally and calls
Magika().identify_stream(stream). Returning a non-"ok" status makes markitdown
fall back to extension/mimetype-based StreamInfo guessing, which our bridge
always supplies. Prediction shape mirrors the real API just enough."""


class _Output:
    label = "unknown"
    mime_type = None
    is_text = False
    extensions = []


class _Prediction:
    output = _Output()


class _Result:
    status = "stubbed"  # anything != "ok"
    prediction = _Prediction()


class Magika:
    def __init__(self, *args, **kwargs):
        pass

    def identify_stream(self, *args, **kwargs):
        return _Result()

    def identify_bytes(self, *args, **kwargs):
        return _Result()
