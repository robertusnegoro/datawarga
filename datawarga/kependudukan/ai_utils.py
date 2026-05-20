import io
import json
import re
from PIL import Image


def optimize_image(image_bytes: bytes, max_size=(800, 800), quality=80) -> bytes:
    """
    Resizes the image preserving aspect ratio to not exceed max_size,
    and compresses it to JPEG format to save memory and token count.
    """
    img = Image.open(io.BytesIO(image_bytes))

    # Convert RGBA/P modes to RGB to enable saving as JPEG
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    out_io = io.BytesIO()
    img.save(out_io, format="JPEG", quality=quality, optimize=True)
    return out_io.getvalue()


def parse_extracted_json(text: str) -> dict:
    """
    Cleans up LLM markdown text blocks and parses the JSON content.
    """
    text = text.strip()
    # Search for json block in markdown
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        # Check for non-language code block
        match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            json_str = text

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Fallback to matching first '{' to last '}'
        match = re.search(r"\{.*\}", json_str, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Could not parse JSON from text: {text}")


def map_extracted_data(data: dict) -> dict:
    """
    Normalizes keys and maps the values to match the models.Warga fields and choices.
    """
    normalized = {}

    # Normalize NIK
    nik = data.get("nik") or data.get("nomor_ktp") or data.get("nomor") or ""
    if isinstance(nik, str):
        # Keep only digits
        nik = re.sub(r"[^\d]", "", nik)
    elif isinstance(nik, int):
        nik = str(nik)
    normalized["nik"] = nik

    # Normalize Nama Lengkap
    nama = data.get("nama") or data.get("nama_lengkap") or ""
    normalized["nama_lengkap"] = str(nama).strip()

    # Normalize Alamat KTP
    alamat = data.get("alamat_ktp") or data.get("alamat") or ""
    normalized["alamat_ktp"] = str(alamat).strip()

    # Normalize and map Jenis Kelamin to LAKI-LAKI or PEREMPUAN
    jk_raw = str(data.get("jenis_kelamin") or data.get("gender") or "").upper()
    if "PEREMPUAN" in jk_raw or "WANITA" in jk_raw or "FEMALE" in jk_raw:
        normalized["jenis_kelamin"] = "PEREMPUAN"
    elif "LAKI" in jk_raw or "PRIA" in jk_raw or "MALE" in jk_raw:
        normalized["jenis_kelamin"] = "LAKI-LAKI"
    else:
        normalized["jenis_kelamin"] = ""

    # Normalize and map Religion (choices match model exactly)
    agama_raw = str(data.get("agama") or data.get("religion") or "").upper().strip()
    valid_religions = ["ISLAM", "KATHOLIK", "KRISTEN", "HINDU", "BUDDHA", "KONGHUCU"]
    mapped_religion = ""
    for r in valid_religions:
        if r in agama_raw:
            mapped_religion = r
            break
    normalized["agama"] = mapped_religion

    return normalized
