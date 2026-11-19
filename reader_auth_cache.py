"""Windows user-encrypted session cache for the local Floating Page Reader.

Data is protected with Windows DPAPI (CryptProtectData), using the current
Windows user's profile. It is not a portable plaintext JSON credentials file.
Never place these credentials in webpage JavaScript or print their values.
"""

import ctypes
import json
import os
from pathlib import Path
import tempfile

CACHE_DIR = Path.home() / '.floating_page_reader'
CACHE_FILE = CACHE_DIR / 'session.dpapi'
_MAGIC = b'FPR-SESSION-DPAPI-V1\n'


class _DataBlob(ctypes.Structure):
    _fields_ = [('cbData', ctypes.c_ulong), ('pbData', ctypes.c_void_p)]


def _crypt(data: bytes, decrypt: bool) -> bytes:
    if os.name != 'nt':
        raise OSError('Secure login cache requires Windows DPAPI.')
    from ctypes import wintypes
    crypt32 = ctypes.WinDLL('Crypt32.dll', use_last_error=True)
    kernel32 = ctypes.WinDLL('Kernel32.dll', use_last_error=True)
    crypt32.CryptProtectData.argtypes = [ctypes.POINTER(_DataBlob), wintypes.LPCWSTR,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_DataBlob)]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    crypt32.CryptUnprotectData.argtypes = [ctypes.POINTER(_DataBlob), ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_DataBlob)]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    source_buffer = ctypes.create_string_buffer(data)
    source = _DataBlob(len(data), ctypes.cast(source_buffer, ctypes.c_void_p))
    output = _DataBlob()
    if decrypt:
        success = crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None,
                                               None, 0, ctypes.byref(output))
    else:
        success = crypt32.CryptProtectData(ctypes.byref(source),
                                           'Floating Page Reader login cache', None,
                                           None, None, 0, ctypes.byref(output))
    if not success:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel32.LocalFree(output.pbData)


def save_session(session: dict) -> None:
    """Atomically write an encrypted copy. Call on login AND each token refresh."""
    required = ('access_token', 'refresh_token', 'client_id', 'expires_at')
    if any(not session.get(key) for key in required):
        raise ValueError('Cannot save incomplete login session.')
    data = {key: session[key] for key in required}
    # Subject binds the cache to the registration's original signed-in account.
    data['subject'] = str(session.get('subject', ''))
    encrypted = _MAGIC + _crypt(json.dumps(data, separators=(',', ':')).encode('utf-8'), False)
    CACHE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix='.session-', dir=CACHE_DIR)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encrypted)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, CACHE_FILE)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def read_session():
    """Return session fields or None if absent, invalid, or not decryptable here."""
    try:
        raw = CACHE_FILE.read_bytes()
        if not raw.startswith(_MAGIC):
            return None
        data = json.loads(_crypt(raw[len(_MAGIC):], True).decode('utf-8'))
        if not isinstance(data, dict):
            return None
        if not all(data.get(field) for field in ('access_token','refresh_token','client_id','expires_at')):
            return None
        return data
    except (OSError, ValueError, TypeError, UnicodeDecodeError):
        return None


def clear_session():
    try:
        CACHE_FILE.unlink(missing_ok=True)
    except OSError:
        pass
