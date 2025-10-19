import re
import time
import sys
from googletrans import Translator

# ===== CONFIG =====
input_file = "cstrike_schinese.txt"
output_file = "cstrike_schinese_out.txt"
batch_size = 10
retry_delay = 2
# ==================

translator = Translator()
chinese_re = re.compile(r"[\u4e00-\u9fff]")

# Pakai regex untuk proteksi
PLACEHOLDERS = {
    r"&([0-9A-Fa-f])": r"__AMP\1__",   # &8, &7, &F
    r"\\n": r"__NEWLINE__",            # \n
    r"/n": r"__SLASHN__",              # /n
    r"\\t": r"__TAB__"                 # \t
}

def protect_special(text):
    for pattern, replacement in PLACEHOLDERS.items():
        text = re.sub(pattern, replacement, text)
    return text

def restore_special(text):
    # Case-insensitive restore
    text = re.sub(r"__amp([0-9a-f])__", lambda m: "&" + m.group(1), text, flags=re.IGNORECASE)
    text = re.sub(r"__newline__", r"\\n", text, flags=re.IGNORECASE)
    text = re.sub(r"__slashn__", r"/n", text, flags=re.IGNORECASE)
    text = re.sub(r"__tab__", r"\\t", text, flags=re.IGNORECASE)
    return text

def safe_translate(text, src="zh-cn", dest="id", max_retry=3):
    protected = protect_special(text)
    for attempt in range(max_retry):
        try:
            translated = translator.translate(protected, src=src, dest=dest).text
            return restore_special(translated)
        except Exception as e:
            print(f"[WARN] Gagal translate (percobaan {attempt+1}): {e}")
            time.sleep(retry_delay)
    return restore_special(protected)

def translate_batch(batch, idx):
    protected_batch = [protect_special(line.rstrip("\n\r")) for line in batch]
    try:
        filtered = [l for l in protected_batch if chinese_re.search(l)]
        if not filtered:
            return [restore_special(l) + "\n" for l in protected_batch]

        results = translator.translate(filtered, src="zh-cn", dest="id")
        if not isinstance(results, list):
            results = [results]

        translated_iter = iter(results)
        translated_lines = []
        for line in protected_batch:
            if chinese_re.search(line):
                translated_lines.append(restore_special(next(translated_iter).text) + "\n")
            else:
                translated_lines.append(restore_special(line) + "\n")
        return translated_lines

    except Exception as e:
        print(f"[WARNING] Batch {idx} gagal, fallback per-baris. Error: {e}")
        return [safe_translate(line) + "\n" for line in batch]

def main():
    print("[INFO] Membaca file input...")
    with open(input_file, "r", encoding="utf-16") as f:
        lines = f.readlines()

    total_lines = len(lines)
    print(f"[INFO] Total {total_lines} baris, diproses dalam {len(lines)//batch_size+1} batch...")

    translated_lines = []
    for i in range(0, total_lines, batch_size):
        batch = lines[i:i+batch_size]
        translated_batch = translate_batch(batch, i // batch_size)
        translated_lines.extend(translated_batch)

        progress = len(translated_lines) / total_lines * 100
        sys.stdout.write(f"\r[PROGRESS] {len(translated_lines)}/{total_lines} baris selesai ({progress:.1f}%)")
        sys.stdout.flush()

    print("\n[INFO] Menyimpan hasil...")
    with open(output_file, "w", encoding="utf-16") as f:
        f.writelines(translated_lines)

    print(f"[SELESAI] {len(translated_lines)} baris diterjemahkan & disimpan ke {output_file}")

if __name__ == "__main__":
    main()
