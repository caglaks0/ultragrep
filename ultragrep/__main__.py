#!/usr/bin/env python3
"""
ultragrep - Ripgrep'ten daha akıllı kod arama aracı
Kullanım:
  python -m ultragrep "def main" ./src
  python -m ultragrep "def main" ./src --json
  python -m ultragrep --replace "eski" --new "yeni" ./src
  python -m ultragrep --replace "eski" --new "yeni" ./src --dry-run
"""
import sys
import time
import json
import argparse

try:
    import colorama
    colorama.init()
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD    = "\033[1m"
    RESET   = "\033[0m"
except ImportError:
    RED = GREEN = YELLOW = CYAN = MAGENTA = BOLD = RESET = ""

from ultragrep.searcher import search, search_json, replace


def main():
    parser = argparse.ArgumentParser(
        prog="ultragrep",
        description="UltraGrep — Ripgrep'ten daha akıllı kod arama ve değiştirme aracı",
        epilog="""
Örnekler:
  python -m ultragrep "def main" .
  python -m ultragrep "import" ./src --json
  python -m ultragrep --replace "eski_ad" --new "yeni_ad" . --dry-run
        """
    )

    parser.add_argument("pattern", nargs="?", help="Aranacak metin veya regex")
    parser.add_argument("path", help="Aranacak dizin yolu")
    parser.add_argument("--replace", "-r", dest="old_text", help="Değiştirilecek metin")
    parser.add_argument("--new",     "-n", dest="new_text", help="Yeni metin")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Değiştirmeden önizle")
    parser.add_argument("--json",    "-j", action="store_true", help="JSON çıktısı (AI için)")
    parser.add_argument("--quiet",   "-q", action="store_true", help="Sessiz mod")

    args = parser.parse_args()

    # ── Replace modu ─────────────────────────────────────────────────────────
    if args.old_text:
        if not args.new_text:
            print(f"{RED}Hata: --new parametresi gerekli{RESET}", file=sys.stderr)
            sys.exit(1)

        if not args.quiet:
            mode = "ÖNİZLEME (dry-run)" if args.dry_run else "DEĞİŞTİRME"
            print(f"\n{BOLD}✏️  {mode}{RESET}")
            print(f"  {YELLOW}'{args.old_text}'{RESET} → {GREEN}'{args.new_text}'{RESET}")
            print(f"  📁 {args.path}\n")

        start = time.time()
        total_changes, all_changes = replace(
            args.old_text, args.new_text, args.path, args.dry_run
        )

        for file_path, changes in all_changes:
            print(f"\n{CYAN}{BOLD}📄 {file_path}{RESET}")
            for line_no, old_line, new_line in changes:
                print(f"  {YELLOW}{line_no:>5}{RESET}  {RED}-{old_line}{RESET}")
                print(f"         {GREEN}+{new_line}{RESET}")

        elapsed = time.time() - start
        if not args.quiet:
            label = "önizlendi" if args.dry_run else "değiştirildi"
            print(f"\n{BOLD}✅ Toplam {total_changes} satır {label}{RESET}")
            print(f"⏱️  Süre: {elapsed:.3f} saniye")
        return

    # ── Search modu ──────────────────────────────────────────────────────────
    if not args.pattern:
        parser.print_help()
        sys.exit(1)

    # JSON modu
    if args.json:
        result = search_json(args.pattern, args.path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Normal arama
    if not args.quiet:
        print(f"\n{BOLD}🔎 '{args.pattern}' aranıyor...{RESET}")
        print(f"   📁 {args.path}\n")

    start = time.time()
    count = 0
    current_file = None

    for file_path, line_no, line, scope, scope_type in search(args.pattern, args.path):
        # Yeni dosyaya geçince başlık yaz
        if file_path != current_file:
            current_file = file_path
            rel = file_path.replace("\\", "/")
            print(f"\n{CYAN}{BOLD}📄 {rel}{RESET}")
            print("─" * min(len(rel) + 4, 80))

        # Scope bilgisi (ripgrep'te yok!)
        scope_str = f"  {MAGENTA}[{scope_type}: {scope}]{RESET}" if scope else ""

        print(f"  {GREEN}{line_no:>5}{RESET}  {line.strip()}{scope_str}")
        count += 1

    elapsed = time.time() - start

    if not args.quiet:
        print(f"\n{'─'*50}")
        print(f"{BOLD}✅ {count} eşleşme bulundu{RESET}  |  ⏱️  {elapsed:.3f} saniye")


if __name__ == "__main__":
    main()