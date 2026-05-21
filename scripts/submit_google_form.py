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
    "Ana", "Beatriz", "Bruno", "Camila", "Carlos", "Daniela", "Eduardo", "Fernanda",
    "Gabriel", "Helena", "Igor", "Juliana", "Lucas", "Mariana", "Mateus", "Natália",
    "Pedro", "Rafaela", "Renato", "Sandra", "Thiago", "Vanessa", "Victor", "Yasmin",
    "Amanda", "André", "Bianca", "Caio", "Débora", "Enzo", "Fabiana", "Gustavo",
    "Isabela", "João", "Larissa", "Leonardo", "Letícia", "Marcos", "Patrícia", "Ricardo",
    "Roberta", "Rodrigo", "Samuel", "Simone", "Tatiane", "Vinícius", "Wesley",
]

MIDDLE_NAMES = [
    "Paula", "Pedro", "Luiz", "Luiza", "Miguel", "Maria", "José", "Ana", "Carlos",
    "Fernanda", "Rafael", "Beatriz", "Antônio", "Clara", "Eduardo", "Helena", "Felipe",
    "Cristina", "Rodrigo", "Amanda", "Henrique", "Juliana", "Augusto", "Camila",
]

LAST_NAMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Lima", "Costa", "Ferreira", "Almeida",
    "Pereira", "Rodrigues", "Gomes", "Ribeiro", "Carvalho", "Martins", "Araújo",
    "Barbosa", "Rocha", "Dias", "Nascimento", "Mendes", "Freitas", "Cardoso", "Teixeira",
    "Correia", "Monteiro", "Cavalcanti", "Pinto", "Moura", "Castro", "Campos", "Lopes",
]

NAME_PARTICLES = ["da", "de", "do", "dos", "das"]

REFERRERS = [
    "Amigo", "Família", "Professor", "Colega de classe", "Colega do trabalho",
    "Redes sociais", "WhatsApp", "Instagram", "Facebook", "LinkedIn",
    "Grupo da faculdade", "Indicação", "Colega", "Primo", "Prima",
]


def fetch_form_meta() -> tuple[str, str]:
    req = urllib.request.Request(VIEW_URL, method="GET")
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    seed_m = re.search(r'data-shuffle-seed="(-?\d+)"', html)
    fbzx = seed_m.group(1) if seed_m else "-5346189538593769706"
    page_history = ",".join(str(i) for i in range(13))
    return fbzx, page_history


def random_real_name(rng: random.Random) -> str:
    first = rng.choice(FIRST_NAMES)
    last = rng.choice(LAST_NAMES)

    if rng.random() < 0.35:
        middle = rng.choice(MIDDLE_NAMES)
        if rng.random() < 0.2:
            particle = rng.choice(NAME_PARTICLES)
            return f"{first} {middle} {particle} {last}"
        return f"{first} {middle} {last}"

    if rng.random() < 0.15:
        particle = rng.choice(NAME_PARTICLES)
        return f"{first} {particle} {last}"

    return f"{first} {last}"


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
    answers["entry.290197840"] = random_real_name(rng)
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


def submit_with_retry(
    payload: dict[str, str],
    fbzx: str,
    page_history: str,
    timeout: float,
    max_retries: int,
) -> tuple[bool, str]:
    delay = 1.0
    last = "unknown"
    for attempt in range(max_retries + 1):
        ok, detail = submit_once(payload, fbzx, page_history, timeout)
        if ok:
            return True, detail
        last = detail
        if attempt < max_retries and (
            detail.startswith("http_429")
            or detail.startswith("http_5")
            or "timed out" in detail.lower()
        ):
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
            continue
        break
    return False, last


def log_progress(
    done: int,
    total: int,
    success: int,
    failed: int,
    elapsed: float,
    last_errors: list[str],
) -> None:
    rate = done / elapsed if elapsed > 0 else 0
    remaining = total - done
    eta_s = remaining / rate if rate > 0 else 0
    pct = 100.0 * done / total if total else 0
    err_tail = ""
    if last_errors:
        err_tail = f" | últimos erros: {'; '.join(last_errors[-3:])}"
    print(
        f"[{pct:5.1f}%] {done}/{total} | ok={success} erros={failed} | "
        f"{elapsed:.0f}s | {rate:.1f}/s | ETA ~{eta_s/60:.0f} min{err_tail}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--correct-probability", type=float, default=1.0)
    parser.add_argument("--delay", type=float, default=0.28)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--error-log", type=str, default="submission_errors.log")
    args = parser.parse_args()

    fbzx, page_history = fetch_form_meta()
    print(f"Início | total={args.count} | fbzx={fbzx}", flush=True)
    print(f"pageHistory={page_history}", flush=True)

    success = 0
    failed = 0
    last_errors: list[str] = []
    start_time = time.time()
    error_log_path = args.error_log

    with open(error_log_path, "w", encoding="utf-8") as err_file:
        err_file.write(f"# run start={time.strftime('%Y-%m-%d %H:%M:%S')} count={args.count}\n")

        for i in range(args.start, args.start + args.count):
            payload = build_payload(i, args.correct_probability, args.seed)
            ok, detail = submit_with_retry(
                payload, fbzx, page_history, args.timeout, args.retries
            )
            if ok:
                success += 1
            else:
                failed += 1
                name = payload.get("entry.290197840", "?")
                line = f"{time.strftime('%H:%M:%S')} idx={i} nome={name!r} erro={detail}\n"
                err_file.write(line)
                err_file.flush()
                last_errors.append(f"#{i}:{detail}")
                if len(last_errors) > 10:
                    last_errors.pop(0)

            done = i - args.start + 1
            if done % args.progress_every == 0 or done == args.count:
                log_progress(done, args.count, success, failed, time.time() - start_time, last_errors)

            if args.delay > 0 and i < args.start + args.count - 1:
                time.sleep(args.delay)

    elapsed = time.time() - start_time
    print(
        f"Concluído | ok={success} erros={failed} | {elapsed/60:.1f} min | log={error_log_path}",
        flush=True,
    )
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
