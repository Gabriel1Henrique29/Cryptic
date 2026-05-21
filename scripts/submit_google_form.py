#!/usr/bin/env python3
"""Submit responses to the QUIZ Google Form (bulk population)."""

from __future__ import annotations

import argparse
import random
import time
import urllib.error
import urllib.parse
import urllib.request

FORM_ID = "1FAIpQLSfHadmQFS-vjpIqr7m2lw1bOXB_C14wx8g9yEtgXJgz3Up0lA"
FORM_URL = f"https://docs.google.com/forms/d/e/{FORM_ID}/formResponse"
VIEW_URL = f"https://docs.google.com/forms/d/e/{FORM_ID}/viewform"
FBZX = "-5346189538593769706"

# Multiple-choice questions: entry_id -> correct option text
QUESTIONS: dict[int, str] = {
    187353751: "b) 35",
    1500585471: "d) 900",
    1392109831: "d) 30",
    1393465468: "b) 108 reais",
    1601397375: "d) 32",
    2047410285: "c) 28",
    1271726355: "b) 5",
    394388907: "b) Sexta-feira",
    177309771: "d) 21",
    734763879: "c) 12",
}

OPTIONS_BY_QUESTION: dict[int, list[str]] = {
    187353751: ["a) 30", "b) 35", "c) 32", "d) 37", "e) 29"],
    1500585471: ["a) 600", "b) 700", "c) 800", "d) 900", "e) 1000"],
    1392109831: ["a) 24", "b) 26", "c) 28", "d) 30", "e) 32"],
    1393465468: [
        "a) 96 reais",
        "b) 108 reais",
        "c) 112 reais",
        "d) 120 reais",
        "e) 132 reais",
    ],
    1601397375: ["a) 18", "b) 24", "c) 30", "d) 32", "e) 36"],
    2047410285: ["a) 24", "b) 26", "c) 28", "d) 30", "e) 32"],
    1271726355: ["a) 4", "b) 5", "c) 8", "d) 10", "e) 20"],
    394388907: [
        "a) Quinta-feira",
        "b) Sexta-feira",
        "c) Sábado",
        "d) Domingo",
        "e) Segunda-feira",
    ],
    177309771: ["a) 18", "b) 19", "c) 20", "d) 21", "e) 22"],
    734763879: ["a) 10", "b) 11", "c) 12", "d) 13", "e) 14"],
}

FIRST_NAMES = [
    "Ana",
    "Bruno",
    "Carla",
    "Diego",
    "Elena",
    "Felipe",
    "Gabriela",
    "Henrique",
    "Isabela",
    "João",
    "Larissa",
    "Marcos",
    "Natália",
    "Otávio",
    "Paula",
    "Rafael",
    "Sofia",
    "Thiago",
    "Úrsula",
    "Vinícius",
]

LAST_NAMES = [
    "Silva",
    "Santos",
    "Oliveira",
    "Souza",
    "Lima",
    "Costa",
    "Ferreira",
    "Almeida",
    "Pereira",
    "Rodrigues",
    "Gomes",
    "Ribeiro",
    "Carvalho",
    "Martins",
    "Araújo",
]

REFERRERS = [
    "Amigo",
    "Família",
    "Professor",
    "Colega de classe",
    "Redes sociais",
    "WhatsApp",
    "Instagram",
    "LinkedIn",
    "Fórum da faculdade",
    "Indicação",
]


def pick_answer(entry_id: int, correct_probability: float, rng: random.Random) -> str:
    correct = QUESTIONS[entry_id]
    options = OPTIONS_BY_QUESTION[entry_id]
    if rng.random() < correct_probability:
        return correct
    wrong = [o for o in options if o != correct]
    return rng.choice(wrong)


def build_payload(index: int, correct_probability: float, seed: int | None) -> dict[str, str]:
    rng = random.Random((seed or 0) + index)
    answers: dict[str, str] = {}
    for entry_id in QUESTIONS:
        answers[f"entry.{entry_id}"] = pick_answer(entry_id, correct_probability, rng)

    first = rng.choice(FIRST_NAMES)
    last = rng.choice(LAST_NAMES)
    answers["entry.1001904144"] = f"{first} {last} {index:04d}"
    answers["entry.54794259"] = rng.choice(REFERRERS)
    return answers


def submit_once(payload: dict[str, str], timeout: float) -> tuple[bool, str]:
    data = list(payload.items()) + [
        ("pageHistory", "0"),
        ("fvv", "1"),
        ("fbzx", FBZX),
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
                "resposta foi registrada" in body or "recorded" in body or "obrigado" in body
            ):
                return True, "ok"
            return False, f"unexpected_status_{resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"http_{e.code}"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1924)
    parser.add_argument(
        "--correct-probability",
        type=float,
        default=0.45,
        help="Chance each question gets the correct answer (0-1).",
    )
    parser.add_argument("--delay", type=float, default=0.35, help="Seconds between submissions.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start", type=int, default=1, help="1-based index to start from.")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    success = 0
    failed = 0
    start_time = time.time()

    for i in range(args.start, args.start + args.count):
        payload = build_payload(i, args.correct_probability, args.seed)
        ok, detail = submit_once(payload, args.timeout)
        if ok:
            success += 1
        else:
            failed += 1
            print(f"[{i}] FAIL: {detail}")

        if i % 25 == 0 or i == args.start + args.count - 1:
            elapsed = time.time() - start_time
            print(
                f"Progress: {i - args.start + 1}/{args.count} | ok={success} fail={failed} | {elapsed:.0f}s"
            )

        if args.delay > 0 and i < args.start + args.count - 1:
            time.sleep(args.delay)

    elapsed = time.time() - start_time
    print(f"Done. success={success} failed={failed} elapsed={elapsed:.1f}s")


if __name__ == "__main__":
    main()
