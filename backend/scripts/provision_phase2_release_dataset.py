"""Provision and verify the public-media part of the Phase 2 release dataset."""

from __future__ import annotations

import argparse
import hashlib
import time
import urllib.request
from pathlib import Path

ASSETS = {
    "captiva-01.jpg": (
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/ca/"
        "2006-2011_Chevrolet_Captiva_LS_wagon_%282015-12-28%29_01.jpg/"
        "1280px-2006-2011_Chevrolet_Captiva_LS_wagon_%282015-12-28%29_01.jpg",
        "cdf3b3108eec92cfddd0c12fa8276274d4a644f14b11648e0612a55eb57771a3",
    ),
    "nissan-rear.jpg": (
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/1/13/"
        "Nissan_Sunny_XL_sedan%2C_rear_view.jpg/"
        "1280px-Nissan_Sunny_XL_sedan%2C_rear_view.jpg",
        "525b6ea2d09d4e0c86e4b92beb6633cd7376738e33c5e23df1624a4b296a79a1",
    ),
    "kia-morning.jpg": (
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/f/fc/"
        "White_Kia_Morning_second_generation.jpg/"
        "1280px-White_Kia_Morning_second_generation.jpg",
        "2adcf1c9f089ef12d8cb34a07492f40921a9cfdbf0426e26177316000beb6f37",
    ),
    "bus-51b04392.jpg": (
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/6/60/"
        "51B_04392_%2823747124141%29.jpg/1280px-51B_04392_%2823747124141%29.jpg",
        "7353f90130384058e0134a9211ebf720222fbb6df749bcd0193c767aaa24c4ed",
    ),
    "daewoo-rear.jpg": (
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/f/ff/"
        "Daewoo_Super_Salon_rear.jpg/1280px-Daewoo_Super_Salon_rear.jpg",
        "4433b30603cd3a84df80f60bd53f3e5d1dd4006170f20d4d7fe88af99f727137",
    ),
    "ecobus-01.jpg": (
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/4/45/"
        "Parked_Ecobuses%2C_Ecopark_%282018%29_01.jpg/"
        "1280px-Parked_Ecobuses%2C_Ecopark_%282018%29_01.jpg",
        "79c0b6a9fc969d793242a43650c344431b1b06af5468b7fe914a96f4d6b5e024",
    ),
    "kon-tum.jpg": (
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/5/5a/"
        "Bi%E1%BB%83n_s%E1%BB%91_xe_Kon_Tum.jpg/"
        "1280px-Bi%E1%BB%83n_s%E1%BB%91_xe_Kon_Tum.jpg",
        "e34a32a5a96d4165465a57e919e884de5085a82b074e51398053daea1b553ef6",
    ),
    "binh-duong.jpg": (
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/1/19/"
        "Bi%E1%BB%83n_s%E1%BB%91_xe_b%C3%ACnh_d%C6%B0%C6%A1ng.jpg/"
        "1280px-Bi%E1%BB%83n_s%E1%BB%91_xe_b%C3%ACnh_d%C6%B0%C6%A1ng.jpg",
        "b11fa87283bb83dad2944ae7b7723e36132aa0569cba0e87051777bdae4e5afa",
    ),
    "evening-street.jpg": (
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/d/de/"
        "Evening_streetscene_%2814424306687%29.jpg/"
        "1280px-Evening_streetscene_%2814424306687%29.jpg",
        "6334486cc23ae1f878c7cbd884bc8d7cd523d6245372fbba3e728765ee19958f",
    ),
    "kim-ma-traffic.jpg": (
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/9/9f/"
        "Kim_Ma_motorbike_traffic_HN.jpg/1280px-Kim_Ma_motorbike_traffic_HN.jpg",
        "1a1547dfe45c28f27eda6e5826dc6fd2c4996fa3a1577f1889fcb9f66be63642",
    ),
    "honda-hanoi.jpg": (
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/f/fb/"
        "Honda_motorcycle_in_Hanoi%2C_17-03-2026_E1.jpg/"
        "1280px-Honda_motorcycle_in_Hanoi%2C_17-03-2026_E1.jpg",
        "c02bae776b42478abdfacd348c45a20c6f61e9fd31fb3f5452a6fb39ba30853a",
    ),
    "vinfast-vf6.jpg": (
        "https://thumb.wikimedia.org/wikipedia/commons/thumb/6/65/"
        "NewOne_-_red_electric_Suv_VinFast_VF_6.jpg/"
        "1280px-NewOne_-_red_electric_Suv_VinFast_VF_6.jpg",
        "658b74b07e53412881f5a1116a3a7552dba366166b480fc248d051929186ff10",
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, target: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "VisionPark-Phase2-Evaluation/1.0 (internal evaluation)"},
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                target.write_bytes(response.read())
            return
        except Exception as exc:  # pragma: no cover - network-dependent retry
            last_error = exc
            time.sleep(attempt + 1)
    raise RuntimeError(f"could not download {url}: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument(
        "--target",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "var" / "phase2-release-dataset",
    )
    args = parser.parse_args()
    args.target.mkdir(parents=True, exist_ok=True)

    for name, (url, expected_hash) in ASSETS.items():
        target = args.target / name
        if not target.is_file() and args.verify_only:
            raise SystemExit(f"missing asset: {target}")
        if not target.is_file():
            temporary = target.with_suffix(target.suffix + ".part")
            download(url, temporary)
            temporary.replace(target)
        actual_hash = sha256(target)
        if actual_hash != expected_hash:
            raise SystemExit(f"sha256 mismatch for {target}: {actual_hash}")
        print(f"verified {name} {actual_hash}")


if __name__ == "__main__":
    main()
