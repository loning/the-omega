# -*- coding: utf-8 -*-
"""
Refresh derived analysis tables inside Supabase via a PostgREST RPC (HTTPS/443).

This avoids direct Postgres connections and only requires supabase.env:
  - SUPABASE_URL
  - SUPABASE_KEY
"""

from __future__ import annotations

import argparse
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from progress_tools import Heartbeat
from supabase_env import load_env_file


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _postgrest_base(url: str) -> str:
    return url.rstrip("/") + "/rest/v1"


def _headers_with_key(key: str) -> dict[str, str]:
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _http_json(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    body: object | None = None,
    timeout_s: float = 120.0,
    ssl_context: ssl.SSLContext | None = None,
) -> tuple[int, dict[str, str], object | None]:
    data: bytes | None
    if body is None:
        data = None
    else:
        data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers = dict(headers)
        headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s, context=ssl_context) as resp:
            status = int(getattr(resp, "status", 0) or 0)
            resp_headers = {k: v for k, v in resp.headers.items()}
            raw = resp.read()
    except urllib.error.HTTPError as e:
        status = int(getattr(e, "code", 0) or 0)
        resp_headers = {k: v for k, v in getattr(e, "headers", {}).items()}
        raw = e.read() if hasattr(e, "read") else b""
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error calling Supabase: {e}") from e

    if not raw:
        return status, resp_headers, None

    try:
        return status, resp_headers, json.loads(raw.decode("utf-8"))
    except Exception:
        return status, resp_headers, raw.decode("utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Refresh derived tables inside Supabase via PostgREST RPC.")
    p.add_argument(
        "--env-file",
        default="",
        help="Optional env file (key=value). If empty, will use supabase.env in repo root.",
    )
    p.add_argument("--panel-name", default="corpus_panel_v1")
    p.add_argument("--panel-av", type=int, default=2)
    p.add_argument("--refseq-dataset", default="human_refseq_mrna")
    p.add_argument("--refseq-av", type=int, default=4)
    p.add_argument("--recoding-dataset", default="ncbi_recoding_genbank")
    p.add_argument("--recoding-av", type=int, default=7)
    p.add_argument("--heartbeat-s", type=float, default=60.0)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = root_dir()
    hb = Heartbeat(every_s=float(args.heartbeat_s), prefix="[progress] refresh_derived_tables")

    env_file = Path(args.env_file) if str(args.env_file).strip() else (root / "supabase.env")
    if not env_file.exists():
        raise SystemExit(f"Missing env file: {env_file}")
    env = load_env_file(env_file)
    supabase_url = str(env.get("SUPABASE_URL") or "").strip()
    supabase_key = str(env.get("SUPABASE_KEY") or "").strip()
    if not supabase_url:
        raise SystemExit("Missing SUPABASE_URL in env.")
    if not supabase_key:
        raise SystemExit("Missing SUPABASE_KEY in env.")

    payload = {
        "panel_name": str(args.panel_name),
        "panel_av": int(args.panel_av),
        "refseq_dataset": str(args.refseq_dataset),
        "refseq_av": int(args.refseq_av),
        "recoding_dataset": str(args.recoding_dataset),
        "recoding_av": int(args.recoding_av),
    }

    base = _postgrest_base(supabase_url)
    url = f"{base}/rpc/refresh_paper_derived_tables"
    headers = _headers_with_key(supabase_key)

    hb.force("calling RPC refresh_paper_derived_tables")
    t0 = time.time()
    status, _, out = _http_json(method="POST", url=url, headers=headers, body=payload, timeout_s=300.0, ssl_context=ssl.create_default_context())
    dt = time.time() - t0
    if status not in (200, 201, 204):
        raise SystemExit(f"RPC failed (status={status}): {out}")
    hb.force(f"done in {dt:.2f}s")
    if out is None:
        print("[ok] (no payload)")
        return
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


