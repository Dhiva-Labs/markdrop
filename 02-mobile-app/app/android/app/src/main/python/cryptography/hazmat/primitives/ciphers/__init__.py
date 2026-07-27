class _Unavailable(RuntimeError):
    MSG = "Encrypted PDFs are not supported on Android (cryptography unavailable)"


class Cipher:
    def __init__(self, *a, **k):
        raise _Unavailable(_Unavailable.MSG)


class _Raiser:
    def __getattr__(self, name):
        def _fail(*a, **k):
            raise _Unavailable(_Unavailable.MSG)
        return _fail


algorithms = _Raiser()
modes = _Raiser()
