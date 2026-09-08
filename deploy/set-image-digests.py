#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

IMAGE_PREFIX = "harbor.jedutools.io/jdevops/"


def validate_digest(value: str) -> str:
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise ValueError(f"invalid image digest: {value}")
    return value


def set_digest(path: Path, image: str, digest: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    target = f"- name: {IMAGE_PREFIX}{image}"
    for index, line in enumerate(lines):
        if line.strip() != target:
            continue
        for digest_index in range(index + 1, min(index + 5, len(lines))):
            if lines[digest_index].lstrip().startswith("digest:"):
                indent = lines[digest_index][: -len(lines[digest_index].lstrip())]
                lines[digest_index] = f"{indent}digest: {digest}"
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return
    raise RuntimeError(f"image {image} not found in {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=("dev", "production"))
    parser.add_argument("backend")
    parser.add_argument("filemon")
    parser.add_argument("procmon")
    args = parser.parse_args()

    digests = {
        "watcher-backend": validate_digest(args.backend),
        "watcher-filemon": validate_digest(args.filemon),
        "watcher-procmon": validate_digest(args.procmon),
    }
    app = Path("deploy/overlays") / args.target / "kustomization.yaml"
    for image, digest in digests.items():
        set_digest(app, image, digest)
    migration = Path("deploy/migration/overlays") / args.target / "kustomization.yaml"
    set_digest(migration, "watcher-backend", digests["watcher-backend"])


if __name__ == "__main__":
    main()
