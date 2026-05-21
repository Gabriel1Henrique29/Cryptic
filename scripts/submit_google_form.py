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
QUESTIONS_COUNT = 10

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

ENTRY_IDS = list(VALID_ANSWERS.keys())

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


def compute_rebalance_count(
    existing_responses: int,
    existing_correct_ratio: float,
    target_correct_ratio: float,
    wrong_per_new_form: int,
) -> int:
    """How many new forms (each with `wrong_per_new_form` wrong Qs) to reach target ratio."""
    existing_slots = existing_responses * QUESTIONS_COUNT
    existing_correct = existing_slots * existing_correct_ratio
    existing_wrong = existing_slots * (1 - existing_correct_ratio)
    correct_per_new = QUESTIONS_COUNT - wrong_per_new_form
    target_wrong_ratio = 1.0 - target_correct_ratio

    denom = wrong_per_new_form - target_wrong_ratio * QUESTIONS_COUNT
    numer = target_wrong_ratio * existing_slots - existing_wrong
    if abs(denom) < 1e-9:
        if correct_per_new == 0:
            need_correct = target_correct_ratio * existing_slots
            shortfall = existing_correct - need_correct
            if shortfall <= 0:
                return 0
            return int(shortfall / (target_correct_ratio * QUESTIONS_COUNT)) + 1
        return 0
    n = numer / denom
    return max(0, int(n) if abs(n - int(n)) < 1e-9 else int(n) + 1)


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


def pick_wrong_option(entry_id: int, rng: random.Random) -> str:
    correct = VALID_ANSWERS[entry_id]
    wrong = [o for o in OPTIONS_BY_QUESTION[entry_id] if o != correct]
    return rng.choice(wrong)


def build_payload(
    index: int,
    rng: random.Random,
    *,
    wrong_question_count: int,
) -> dict[str, str]:
    """
    Build one form response.

    wrong_question_count: how many of the 10 questions get a wrong (random) option.
    The wrong questions are chosen at random each time (not always Q1, Q2...).
    Each wrong question gets a different random incorrect alternative.
    """
    wrong_question_count = max(0, min(QUESTIONS_COUNT, wrong_question_count))
    wrong_ids = set(rng.sample(ENTRY_IDS, wrong_question_count))

    answers: dict[str, str] = {}
    for entry_id in ENTRY_IDS:
        if entry_id in wrong_ids:
            answers[f"entry.{entry_id}"] = pick_wrong_option(entry_id, rng)
        else:
            answers[f"entry.{entry_id}"] = VALID_ANSWERS[entry_id]

    answers["entry.290197840"] = random_real_name(rng)
    answers["entry.353255535"] = rng.choice(REFERRERS)
    return answers


def build_payload_mixed(index: int, seed: int | None, form_correct_ratio: float) -> dict[str, str]:
    """Per form: ~form_correct_ratio of questions correct (default 0.6 -> 6 right, 4 wrong)."""
    rng = random.Random((seed or 0) + index)
    wrong_count = QUESTIONS_COUNT - round(QUESTIONS_COUNT * form_correct_ratio)
    # slight variation so not every form is exactly 6/4
    if rng.random() < 0.25:
        wrong_count += rng.choice([-1, 1])
    wrong_count = max(1, min(QUESTIONS_COUNT - 1, wrong_count))
    return build_payload(index, rng, wrong_question_count=wrong_count)


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
    parser.add_argument(
        "--mode",
        choices=["all-correct", "mixed", "rebalance", "all-wrong"],
        default="mixed",
        help=(
            "all-correct: 10/10 right; mixed: ~60%% right per form (varied); "
            "rebalance/all-wrong: mostly wrong to fix dataset after all-correct run"
        ),
    )
    parser.add_argument(
        "--form-correct-ratio",
        type=float,
        default=0.6,
        help="For mixed mode: fraction of questions correct per form (0.6 = 6/10).",
    )
    parser.add_argument(
        "--wrong-per-form",
        type=int,
        default=10,
        help="For rebalance/all-wrong: wrong answers per form (10 = all wrong).",
    )
    parser.add_argument(
        "--existing-responses",
        type=int,
        default=4000,
        help="Already submitted forms (for --compute-rebalance).",
    )
    parser.add_argument(
        "--existing-correct-ratio",
        type=float,
        default=0.999,
        help="Estimated correct ratio in existing data (0.999 if ~99.9%%).",
    )
    parser.add_argument(
        "--target-correct-ratio",
        type=float,
        default=0.6,
        help="Target overall correct ratio across all answers.",
    )
    parser.add_argument(
        "--compute-rebalance",
        action="store_true",
        help="Print how many rebalance submissions needed and exit.",
    )
    parser.add_argument("--delay", type=float, default=0.28)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--error-log", type=str, default="submission_errors.log")
    args = parser.parse_args()

    if args.compute_rebalance:
        n = compute_rebalance_count(
            args.existing_responses,
            args.existing_correct_ratio,
            args.target_correct_ratio,
            args.wrong_per_form,
        )
        print(
            f"Para ~{args.target_correct_ratio*100:.0f}% corretas no total "
            f"com {args.existing_responses} formulários já enviados "
            f"({args.existing_correct_ratio*100:.1f}% corretos), "
            f"envie mais ~{n} formulários com {args.wrong_per_form}/10 erradas "
            f"(alternativas erradas variadas por pergunta)."
        )
        return

    if args.mode == "rebalance":
        if args.count <= 0:
            args.count = compute_rebalance_count(
                args.existing_responses,
                args.existing_correct_ratio,
                args.target_correct_ratio,
                args.wrong_per_form,
            )
            print(f"Modo rebalance: count auto = {args.count}", flush=True)

    fbzx, page_history = fetch_form_meta()
    print(
        f"Início | mode={args.mode} | total={args.count} | fbzx={fbzx}",
        flush=True,
    )

    success = 0
    failed = 0
    last_errors: list[str] = []
    start_time = time.time()

    with open(args.error_log, "w", encoding="utf-8") as err_file:
        err_file.write(
            f"# mode={args.mode} start={time.strftime('%Y-%m-%d %H:%M:%S')} count={args.count}\n"
        )

        for i in range(args.start, args.start + args.count):
            rng = random.Random(args.seed + i)

            if args.mode == "all-correct":
                payload = build_payload(i, rng, wrong_question_count=0)
            elif args.mode in ("rebalance", "all-wrong"):
                payload = build_payload(
                    i, rng, wrong_question_count=args.wrong_per_form
                )
            else:  # mixed
                payload = build_payload_mixed(i, args.seed, args.form_correct_ratio)

            ok, detail = submit_with_retry(
                payload, fbzx, page_history, args.timeout, args.retries
            )
            if ok:
                success += 1
            else:
                failed += 1
                name = payload.get("entry.290197840", "?")
                err_file.write(
                    f"{time.strftime('%H:%M:%S')} idx={i} nome={name!r} erro={detail}\n"
                )
                err_file.flush()
                last_errors.append(f"#{i}:{detail}")
                if len(last_errors) > 10:
                    last_errors.pop(0)

            done = i - args.start + 1
            if done % args.progress_every == 0 or done == args.count:
                log_progress(
                    done, args.count, success, failed, time.time() - start_time, last_errors
                )

            if args.delay > 0 and i < args.start + args.count - 1:
                time.sleep(args.delay)

    print(
        f"Concluído | ok={success} erros={failed} | {(time.time()-start_time)/60:.1f} min",
        flush=True,
    )
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
