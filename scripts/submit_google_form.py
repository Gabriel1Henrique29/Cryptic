#!/usr/bin/env python3
"""Submit responses to the QUIZ Google Form (bulk population)."""

from __future__ import annotations

import argparse
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

FORM_ID = "1FAIpQLSfHadmQFS-vjpIqr7m2lw1bOXB_C14wx8g9yEtgXJgz3Up0lA"
FORM_URL = f"https://docs.google.com/forms/d/e/{FORM_ID}/formResponse"
VIEW_URL = f"https://docs.google.com/forms/d/e/{FORM_ID}/viewform"

# entry.* IDs (from form HTML), NOT the outer field/question IDs
VALID_ANSWERS: dict[int, str] = {
    1635834919: "b) 35",
    2122334591: "d) 900",
    306584075: "d) 30",
    1356253822: "b) 108 reais",
    1344785961: "d) 32",
    951134325: "c) 28",
    641548762: "b) 5",
    1899402559: "b) Sexta-feira",
    486652124: "d) 21",
    106747039: "c) 12",
}

TEXT_ENTRIES = {
    290197840: "name",  # Seu nome Completo
    353255535: "referrer",  # Quem enviou para você?
}

OPTIONS_BY_QUESTION: dict[int, list[str]] = {
    1635834919: ["a) 30", "b) 35", "c) 32", "d) 37", "e) 29"],
    2122334591: ["a) 600", "b) 700", "c) 800", "d) 900", "e) 1000"],
    306584075: ["a) 24", "b) 26", "c) 28", "d) 30", "e) 32"],
    1356253822: [
        "a) 96 reais",
        "b) 108 reais",
        "c) 112 reais",
        "d) 120 reais",
        "e) 132 reais",
    ],
    1344785961: ["a) 18", "b) 24", "c) 30", "d) 32", "e) 36"],
    951134325: ["a) 24", "b) 26", "c) 28", "d) 30", "e) 32"],
    641548762: ["a) 4", "b) 5", "c) 8", "d) 10", "e) 20"],
    1899402559: [
        "a) Quinta-feira",
        "b) Sexta-feira",
        "c) Sábado",
        "d) Domingo",
        "e) Segunda-feira",
    ],
    486652124: ["a) 18", "b) 19", "c) 20", "d) 21", "e) 22"],
    106747039: ["a) 10", "b) 11", "c) 12", "d) 13", "e) 14"],
}

FIRST_NAMES = [
    "Ana", "Bruno", "Carla", "Diego", "Elena", "Felipe", "Gabriela", "Henrique",
    "Isabela", "João", "Larissa", "Marcos", "Natália", "Otávio", "Paula",
    "Rafael", "Sofia", "Thiago", "Vinícius",
]
LAST_NAMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Lima", "Costa", "Ferreira",
    "Almeida", "Pereira", "Rodrigues", "Gomes", "Ribeiro", "Carvalho",
]
REFERRERS = [
    "Amigo", "Família", "Professor", "Colega de classe", "Redes sociais",
    "WhatsApp", "Instagram", "Indicação",
]


def fetch_form_meta() -> tuple[str, str]:
    """Return (fbzx, page_history) from live viewform HTML."""
    req = urllib.request.Request(VIEW_URL, method="GET")
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    seed_m = re.search(r'data-shuffle-seed="(-?\d+)"', html)
    fbzx = seed_m.group(1) if seed_m else "-5346189538593769706"

    # Count pages: [[1,1,1,1,1],...] -> intro + N question pages + footer
    pages_m = re.search(r"\[\[1,1,1,1,1\],1,0,1,0\]", html)
    if pages_m:
        page_history = ",".join(str(i) for i in range(13))
    else:
        page_history = "0,1,2,3,4,5,6,7,8,9,10,11,12"

    return fbzx, page_history


def pick_answer(entry_id: int, correct_probability: float, rng: random.Random) -> str:
    correct = VALID_ANSWERS[entry_id]
    if rng.random() < correct_probability:
        return correct
    wrong = [o for o in OPTIONS_BY_QUESTION[entry_id] if o != correct]
    return rng.choice(wrong)


def build_payload(index: int, correct_probability: float, seed: int | None) -> dict[str, str]:
    rng = random.Random((seed or 0) + index)
    answers = {
        f"entry.{entry_id}": pick_answer(entry_id, correct_probability, rng)
        for entry_id in VALID_ANSWERS
    }
    first = rng.choice(FIRST_NAMES)
    last = rng.choice(LAST_NAMES)
    answers["entry.290197840"] = f"{first} {last} {index:04d}"
    answers["entry.353255535"] = rng.choice(REFERRERS)
    return answers


def submit_once(
    payload: dict[str, str], fbzx: str, page_history: str, timeout: float
) -> tuple[bool, str]:
    data = list(payload.items()) + [
        ("pageHistory", page_history),
        ("fvv", "1"),
        ("fbzx", fbzx),
        ("submissionTimestamp", "-1"),
    ]
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(FORM_URL, data=encoded, method="POST")
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Referer", VIEW_URL)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace").lower()
            if resp.status == 200 and (
                "resposta foi registrada" in body
                or "recorded" in body
                or "obrigado" in body
            ):
                return True, "ok"
            return False, f"unexpected_status_{resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"http_{e.code}"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--correct-probability", type=float, default=1.0)
    parser.add_argument("--delay", type=float, default=0.35)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    fbzx, page_history = fetch_form_meta()
    print(f"Using fbzx={fbzx} pageHistory={page_history}", flush=True)

    success = 0
    failed = 0
    start_time = time.time()

    for i in range(args.start, args.start + args.count):
        payload = build_payload(i, args.correct_probability, args.seed)
        ok, detail = submit_once(payload, fbzx, page_history, args.timeout)
        if ok:
            success += 1
        else:
            failed += 1
            print(f"[{i}] FAIL: {detail}", flush=True)

        if i % 10 == 0 or i == args.start + args.count - 1:
            elapsed = time.time() - start_time
            print(
                f"Progress: {i - args.start + 1}/{args.count} | ok={success} fail={failed} | {elapsed:.0f}s",
                flush=True,
            )

        if args.delay > 0 and i < args.start + args.count - 1:
            time.sleep(args.delay)

    print(f"Done. success={success} failed={failed}", flush=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
