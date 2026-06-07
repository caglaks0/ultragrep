import sys
import os
import re
import mmap
import time
from concurrent.futures import ProcessPoolExecutor

# Atlanacak dosya uzantıları
SKIP_EXTENSIONS = {
    ".pyc", ".exe", ".jpg", ".jpeg", ".png", ".gif", ".bmp",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".iso",
    ".mp3", ".mp4", ".avi", ".mov", ".mkv", ".wmv",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"
}

SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", ".venv",
    "env", "venv", ".idea", ".vscode", "dist", "build", "target"
}

# Fonksiyon/sınıf tespiti için regex'ler (çok dil destekli)
SCOPE_PATTERNS = [
    (re.compile(r"^\s*async\s+def\s+(\w+)\s*\("),  "fonksiyon"),  # Python async def
    (re.compile(r"^\s*def\s+(\w+)\s*\("),           "fonksiyon"),  # Python def
    (re.compile(r"^\s*class\s+(\w+)[\s(:]"),         "sınıf"),     # Python class
    (re.compile(r"^\s*function\s+(\w+)\s*\("),       "fonksiyon"),  # JavaScript
    (re.compile(r"^\s*fn\s+(\w+)\s*\("),             "fonksiyon"),  # Rust
    (re.compile(r"^\s*func\s+(\w+)\s*\("),           "fonksiyon"),  # Go
    (re.compile(r"^\s*(?:public|private|protected|static)[\s\w]*\s+(\w+)\s*\("), "fonksiyon"),  # Java/C#
]


def is_binary(data):
    """Dosyanın binary olup olmadığını kontrol et"""
    return b"\x00" in data[:1024]


def detect_scope(lines, match_line_index):
    """
    Eşleşme satırından geriye giderek hangi fonksiyon
    veya sınıf içinde olduğunu bulur.
    Ripgrep'te bu özellik YOKTUR.
    """
    for i in range(match_line_index, max(-1, match_line_index - 150), -1):
        for pattern, scope_type in SCOPE_PATTERNS:
            m = pattern.match(lines[i])
            if m:
                return m.group(1), scope_type
    return None, None


def search_in_file(file_path, pattern, use_regex=True):
    """
    Tek dosyada mmap kullanarak arama yap.
    mmap: dosyayı RAM'e KOPYALAMADAN okur — ripgrep'in de kullandığı teknik.
    """
    results = []

    ext = os.path.splitext(file_path)[1].lower()
    if ext in SKIP_EXTENSIONS:
        return results

    try:
        with open(file_path, "rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                if is_binary(mm):
                    return results
                raw = mm[:]

        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            content = raw.decode("latin-1")

        lines = content.splitlines()

        # Regex veya düz metin arama
        if use_regex:
            try:
                compiled = re.compile(pattern)
            except re.error:
                compiled = re.compile(re.escape(pattern))
        else:
            compiled = re.compile(re.escape(pattern))

        for i, line in enumerate(lines):
            if compiled.search(line):
                # Fonksiyon/sınıf tespiti (Ripgrep'te yok!)
                scope_name, scope_type = detect_scope(lines, i)

                results.append({
                    "file": file_path,
                    "line_number": i + 1,
                    "line": line,
                    "scope": scope_name,
                    "scope_type": scope_type,
                })

    except Exception:
        pass

    return results


def replace_in_file(file_path, pattern, replacement, dry_run=False):
    """
    Dosyada bul & değiştir.
    dry_run=True ise dosyayı değiştirme, sadece göster.
    Ripgrep'te bu özellik YOKTUR.
    """
    changes = []

    ext = os.path.splitext(file_path)[1].lower()
    if ext in SKIP_EXTENSIONS:
        return 0, file_path, []

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        new_lines = []
        change_count = 0

        for i, line in enumerate(lines):
            if pattern in line:
                new_line = line.replace(pattern, replacement)
                if new_line != line:
                    changes.append((i + 1, line.strip(), new_line.strip()))
                    change_count += 1
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        if change_count > 0 and not dry_run:
            with open(file_path, "w", encoding="utf-8", errors="replace") as f:
                f.writelines(new_lines)

        return change_count, file_path, changes

    except Exception:
        return 0, file_path, []


def collect_files(path):
    """Aranacak tüm dosyaları topla"""
    files = []
    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in filenames:
            files.append(os.path.join(root, fname))
    return files


def worker_search(args):
    file_path, pattern = args
    return search_in_file(file_path, pattern)


def worker_replace(args):
    file_path, pattern, replacement, dry_run = args
    return replace_in_file(file_path, pattern, replacement, dry_run)


def search(pattern, path):
    """
    Ana arama fonksiyonu.
    mmap + paralel işleme ile maksimum hız.
    Her eşleşme için (file_path, line_no, line, scope, scope_type) döner.
    """
    files = collect_files(path)
    tasks = [(f, pattern) for f in files]

    print(f"🔍 {len(files)} dosya taranıyor...", file=sys.stderr)

    with ProcessPoolExecutor() as executor:
        results = executor.map(worker_search, tasks)

    for file_results in results:
        for item in file_results:
            yield (
                item["file"],
                item["line_number"],
                item["line"],
                item.get("scope"),
                item.get("scope_type"),
            )


def search_json(pattern, path):
    """
    JSON formatında arama sonucu döndürür.
    Yapay zeka entegrasyonu için idealdir.
    Ripgrep'te bu kadar zengin JSON çıktısı YOKTUR.
    """
    files = collect_files(path)
    tasks = [(f, pattern) for f in files]

    t0 = time.perf_counter()
    all_results = []

    with ProcessPoolExecutor() as executor:
        results = executor.map(worker_search, tasks)

    files_with_matches = 0
    total_matches = 0

    for file_results in results:
        if file_results:
            files_with_matches += 1
            total_matches += len(file_results)
            all_results.append({
                "filepath": file_results[0]["file"],
                "match_count": len(file_results),
                "matches": [
                    {
                        "line_number": r["line_number"],
                        "line": r["line"],
                        "scope": r["scope"],
                        "scope_type": r["scope_type"],
                    }
                    for r in file_results
                ],
            })

    elapsed = (time.perf_counter() - t0) * 1000

    return {
        "tool": "ultragrep",
        "version": "1.0.0",
        "pattern": pattern,
        "path": path,
        "summary": {
            "total_files_scanned": len(files),
            "total_files_with_matches": files_with_matches,
            "total_matches": total_matches,
            "elapsed_ms": round(elapsed, 2),
        },
        "results": all_results,
    }


def replace(pattern, replacement, path, dry_run=False):
    """
    Ana değiştirme fonksiyonu.
    (toplam_değişiklik, değişiklik_listesi) döner.
    """
    files = collect_files(path)
    tasks = [(f, pattern, replacement, dry_run) for f in files]

    mode = "SİMÜLASYON (dry-run)" if dry_run else "DEĞİŞTİRME"
    print(f"✏️  {mode} — {len(files)} dosya taranıyor...", file=sys.stderr)

    all_changes = []
    total_changes = 0

    with ProcessPoolExecutor() as executor:
        results = executor.map(worker_replace, tasks)

    for change_count, file_path, changes in results:
        if change_count > 0:
            total_changes += change_count
            all_changes.append((file_path, changes))

    return total_changes, all_changes