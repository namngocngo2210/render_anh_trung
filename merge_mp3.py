"""Tool ghép toàn bộ file MP3 trong nhiều folder thành 1 file MP3 dài (mỗi folder 1 output).

- Mode "sequential": ghép theo thứ tự tên file (natural sort: 1.mp3, 2.mp3, ..., 10.mp3).
- Mode "random": ghép theo thứ tự ngẫu nhiên.
- Output lưu ngay trong folder input: <tên_folder>_merged.mp3
- Chạy đa luồng: mỗi folder xử lý trên 1 thread (ffmpeg chạy song song).

Cách dùng:
    python merge_mp3.py --mode sequential "D:/audio/folder1" "D:/audio/folder2"
    python merge_mp3.py --mode random --workers 5 "D:/audio/folder1" ... "D:/audio/folder5"
"""

import argparse
import random
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUTPUT_SUFFIX = "_merged.mp3"


def natural_key(name):
    """Sort key để '2.mp3' đứng trước '10.mp3' (natural sort)."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", name)]


def list_mp3_files(folder, mode):
    """Liệt kê file mp3 trong folder theo mode, loại trừ file output cũ của tool."""
    folder = Path(folder)
    files = [f for f in folder.glob("*.mp3") if not f.name.endswith(OUTPUT_SUFFIX)]
    if mode == "random":
        random.shuffle(files)
    else:
        files.sort(key=lambda f: natural_key(f.name))
    return files


def write_concat_list(files, list_file):
    """Ghi file danh sách cho ffmpeg concat demuxer (escape dấu nháy đơn trong path)."""
    with open(list_file, "w", encoding="utf-8") as f:
        for mp3 in files:
            path = str(mp3.resolve()).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{path}'\n")


def merge_folder(folder, mode):
    """Ghép toàn bộ mp3 trong 1 folder thành 1 file, trả về đường dẫn output."""
    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"Không tìm thấy folder: {folder}")

    files = list_mp3_files(folder, mode)
    if not files:
        raise FileNotFoundError(f"Không có file mp3 nào trong: {folder}")

    output_file = folder / f"{folder.name}{OUTPUT_SUFFIX}"
    concat_list_file = folder / "concat_list.txt"
    try:
        write_concat_list(files, concat_list_file)
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "concat", "-safe", "0", "-i", str(concat_list_file),
                "-c", "copy", str(output_file),
            ],
            check=True,
        )
    finally:
        if concat_list_file.exists():
            concat_list_file.unlink()

    return output_file


def merge_folders(folders, mode, max_workers=None):
    """Ghép nhiều folder song song. Trả về dict {folder: output hoặc Exception}."""
    max_workers = max_workers or len(folders)
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(merge_folder, folder, mode): folder for folder in folders}
        for future in as_completed(futures):
            folder = futures[future]
            try:
                output = future.result()
                results[folder] = output
                print(f"✅ {folder} -> {output}")
            except Exception as e:
                results[folder] = e
                print(f"❌ {folder}: {e}")
    return results


def main():
    parser = argparse.ArgumentParser(description="Ghép toàn bộ mp3 trong mỗi folder thành 1 file mp3 dài.")
    parser.add_argument("folders", nargs="+", help="Danh sách folder chứa file mp3")
    parser.add_argument("--mode", choices=["sequential", "random"], default="sequential",
                        help="sequential: theo thứ tự tên file, random: ngẫu nhiên (mặc định: sequential)")
    parser.add_argument("--workers", type=int, default=None,
                        help="Số folder xử lý song song (mặc định: bằng số folder)")
    args = parser.parse_args()

    results = merge_folders(args.folders, args.mode, args.workers)
    failed = [f for f, r in results.items() if isinstance(r, Exception)]
    print(f"\nHoàn tất: {len(results) - len(failed)}/{len(results)} folder thành công.")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
