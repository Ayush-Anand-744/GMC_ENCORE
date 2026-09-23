from io import BytesIO
from pathlib import Path
try:
    import msoffcrypto
except Exception:
    msoffcrypto = None
from pypdf import PdfReader, PdfWriter

class IncorrectPassword(ValueError): pass
class UnsupportedEncryption(ValueError): pass

OFFICE_EXTS = {".xlsx", ".xlsm", ".docx"}

def is_password_protected(filename: str, data: bytes) -> bool:
    ext = Path(filename).suffix.lower()
    try:
        if ext == ".pdf":
            return bool(PdfReader(BytesIO(data)).is_encrypted)
        if ext in OFFICE_EXTS and msoffcrypto is not None:
            f = msoffcrypto.OfficeFile(BytesIO(data))
            return bool(f.is_encrypted())
    except Exception:
        return False
    return False

def unlock_bytes(filename: str, data: bytes, password: str) -> bytes:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        try:
            reader = PdfReader(BytesIO(data))
            if not reader.is_encrypted: return data
            if reader.decrypt(password) == 0: raise IncorrectPassword("Incorrect password")
            out = BytesIO(); writer = PdfWriter()
            for p in reader.pages: writer.add_page(p)
            writer.write(out); return out.getvalue()
        except IncorrectPassword:
            raise
        except Exception as e:
            raise IncorrectPassword("Incorrect password") from e
    if ext in OFFICE_EXTS:
        if msoffcrypto is None:
            raise RuntimeError("msoffcrypto-tool is required to unlock protected Office files")
        try:
            office = msoffcrypto.OfficeFile(BytesIO(data))
            if not office.is_encrypted(): return data
            office.load_key(password=password, verify_password=True)
            out = BytesIO(); office.decrypt(out); return out.getvalue()
        except IncorrectPassword:
            raise
        except Exception as e:
            raise IncorrectPassword("Incorrect password") from e
    return data
