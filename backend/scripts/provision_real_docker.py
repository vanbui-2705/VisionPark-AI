"""Provision existing local model assets for the CPU real-ALPR Compose override."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ocr-model-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "models/ocr/latin_PP-OCRv5_mobile_rec",
    )
    args = parser.parse_args()
    backend = Path(__file__).resolve().parents[1]
    manifest = json.loads((backend / "models/alpr-manifest.json").read_text(encoding="utf-8"))
    weights = backend / manifest["detector"]["weights_path"]
    if not weights.is_file():
        parser.error(f"Provision the detector weights first: {weights}")
    checksum = hashlib.sha256(weights.read_bytes()).hexdigest()
    if checksum.casefold() != manifest["detector"]["sha256"].casefold():
        parser.error("Detector checksum differs from the manifest.")
    for name in ("inference.json", "inference.pdiparams", "inference.yml"):
        if not (args.ocr_model_dir / name).is_file():
            parser.error(f"OCR model cache is incomplete: {args.ocr_model_dir / name}")
    target = backend / "var/models"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(args.ocr_model_dir, target / "ocr", dirs_exist_ok=True)
    manifest["ocr"]["model_dir"] = "/models/ocr"
    (target / "alpr-manifest.docker.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print("Detector checksum verified; OCR cache and Docker manifest provisioned.")


if __name__ == "__main__":
    main()
