"""Verify bundled detector/OCR inference assets before building or publishing."""

import hashlib
import json
from pathlib import Path


def verify_bundle() -> None:
    backend = Path(__file__).resolve().parents[1]
    manifest = json.loads((backend / "models/alpr-manifest.json").read_text(encoding="utf-8"))
    detector = manifest["detector"]
    files = {backend / detector["weights_path"]: detector["sha256"]}
    ocr = manifest["ocr"]
    directory = backend / ocr["model_dir"]
    files.update({directory / name: digest for name, digest in ocr["sha256"].items()})
    for file, expected in files.items():
        actual = hashlib.sha256(file.read_bytes()).hexdigest()
        if actual.lower() != expected.lower():
            raise RuntimeError(f"Model checksum mismatch: {file.name}")
    print(f"PASS: {len(files)} detector/OCR asset checksums")


if __name__ == "__main__":
    verify_bundle()
