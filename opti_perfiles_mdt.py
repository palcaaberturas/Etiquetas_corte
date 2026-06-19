import argparse
import csv
import json
import re
from html import unescape
from pathlib import Path


NOMBRE_PATTERN = re.compile(r"^(\d+)")
MAPPING_PATH = Path(__file__).with_name("obras_map.json")
EXCLUDED_PERFILES = {
    "MT-0212",
    "MT-0217",
    "MT-0220",
    "MT-0225",
    "MT-0226",
    "MT-0230",
    "MT-0231",
    "MT-0232",
    "MT-0233",
    "MT-0237",
    "MT-0238",
    "MT-0257",
    "MT-6535",
    "MT-0995",
    "MT-6090",
    "MT-6513",
    "MT-6508",
}


def read_text(path: str) -> str:
    path_obj = Path(path)
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return path_obj.read_text(encoding=encoding)
        except UnicodeError:
            continue
    return path_obj.read_text(encoding="utf-8", errors="replace")


def parse_nombre(raw: str) -> tuple[str | None, str, str, int | None]:
    raw_clean = " ".join(raw.split())
    if not raw_clean:
        return None, "", "", None

    parts = raw_clean.split(" ")
    prefix = None
    order = None

    if parts and parts[0].isdigit():
        prefix = parts.pop(0)

    if parts and parts[-1].isdigit():
        order = int(parts.pop())

    body = "".join(parts)
    if not body:
        body = raw_clean if prefix is None else ""

    core = (prefix or "") + body
    if not core:
        core = raw_clean

    return prefix, core, raw_clean, order


def normalize_perfil(perfil: str) -> str:
    """Remove spaces and uppercase to compare/exclude consistently."""
    return perfil.replace(" ", "").upper()


def perfil_sort_key(perfil: str) -> tuple[int, str]:
    """Use the first number in the perfil as the primary sort key."""
    match = re.search(r"(\d+)", perfil)
    if match:
        return int(match.group()), perfil
    return 10**9, perfil


def extract_rows(html_text: str) -> list[dict[str, object]]:
    text = re.sub(r"<[^>]+>", "\n", html_text)
    text = unescape(text)
    lines = [line.strip() for line in text.splitlines()]
    rows: list[dict[str, object]] = []
    current_profile: str | None = None

    for line in lines:
        if not line:
            continue
        if line.startswith("Perfil "):
            current_profile = line.split("Perfil", 1)[1].strip()
            continue
        if current_profile and "Tiras" in line:
            try:
                before, after = line.split("Tiras", 1)
            except ValueError:
                continue
            match = re.search(r"\d+", before)
            if not match:
                continue
            tiras = int(match.group())
            cuts_str = after.strip()
            for chunk in cuts_str.split('+'):
                chunk = re.sub(r"\s+", " ", chunk.strip())
                if not chunk or 'x' not in chunk:
                    continue
                size_part, rest = chunk.split('x', 1)
                size_part = size_part.strip()
                rest = rest.strip()
                size_match = re.search(r"\d+", size_part)
                if not size_match:
                    continue
                corte = int(size_match.group())
                qty_match = re.search(r"\d+", rest)
                if not qty_match:
                    continue
                qty = int(qty_match.group())
                name_candidate = rest[qty_match.end():].strip()
                if name_candidate:
                    name_raw = name_candidate
                else:
                    name_raw = rest[:qty_match.start()].strip() or rest.strip()
                prefix, core_name, nombre_full, orden = parse_nombre(name_raw)
                obra_key = prefix if prefix is not None else core_name
                if not obra_key:
                    obra_key = nombre_full
                prompt_label = prefix if prefix is not None else core_name
                if not prompt_label:
                    prompt_label = nombre_full
                total_rows = qty * tiras
                for _ in range(total_rows):
                    rows.append(
                        {
                            "Perfil": current_profile,
                            "Tiras": tiras,
                            "Corte_mm": corte,
                            "Nombre": nombre_full,
                            "Numero_de_Orden": orden,
                            "_obra_key": obra_key,
                            "_prompt_label": prompt_label,
                        }
                    )
    return rows


def assign_obras(rows: list[dict[str, object]]) -> None:
    prompts: dict[str, str] = {}
    if MAPPING_PATH.exists():
        try:
            stored = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                prompts.update({str(k): str(v) for k, v in stored.items()})
        except (json.JSONDecodeError, OSError):
            pass
    updated = False
    for row in rows:
        key = row["_obra_key"]
        if key not in prompts:
            label = row["_prompt_label"]
            prompts[key] = input(f"Designe un nombre para {label}: ").strip()
            updated = True
        row["Obra"] = prompts[key]
        del row["_obra_key"]
        del row["_prompt_label"]
    if updated:
        try:
            MAPPING_PATH.write_text(
                json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass


def write_csv(rows: list[dict[str, object]], output_path: str) -> None:
    fieldnames = ["Perfil", "Tiras", "Corte_mm", "Nombre", "Obra", "Numero_de_Orden"]
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            row_data = {}
            for field in fieldnames:
                value = row.get(field)
                row_data[field] = "" if value is None else value
            writer.writerow(row_data)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse MaxCut HTML output y emitir un CSV expandido de cortes."
    )
    parser.add_argument("html_path", help="Ruta al archivo HTML de MaxCut.")
    parser.add_argument("csv_path", help="Ruta donde escribir el CSV.")
    args = parser.parse_args()

    html_text = read_text(args.html_path)
    rows = extract_rows(html_text)
    excluded = {normalize_perfil(p) for p in EXCLUDED_PERFILES}
    rows = [row for row in rows if normalize_perfil(str(row["Perfil"])) not in excluded]
    rows.sort(key=lambda row: perfil_sort_key(str(row["Perfil"])))
    if not rows:
        raise SystemExit("No se encontraron cortes en el HTML proporcionado.")

    assign_obras(rows)
    write_csv(rows, args.csv_path)


if __name__ == "__main__":
    main()
