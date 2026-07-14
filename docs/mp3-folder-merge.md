# Tool: MP3 Folder Merge

## Mục tiêu
Ghép toàn bộ file MP3 trong mỗi folder thành 1 file MP3 dài. Nhận nhiều folder cùng lúc (ví dụ 5 folder, mỗi folder 20 mp3), xử lý song song, output lưu ngay trong folder input.

## Thiết kế
- `merge_mp3.py` — logic + CLI:
  - `list_mp3_files(folder, mode)`: liệt kê mp3, loại trừ output cũ (`*_merged.mp3`).
    - `sequential`: natural sort theo tên file (`1.mp3, 2.mp3, ..., 10.mp3`).
    - `random`: shuffle ngẫu nhiên.
  - `merge_folder(folder, mode)`: ghi `concat_list.txt` → chạy `ffmpeg -f concat -safe 0 -c copy` (stream copy, không re-encode nên rất nhanh) → output `<tên_folder>_merged.mp3` trong chính folder đó → xóa file tạm.
  - `merge_folders(folders, mode, workers)`: `ThreadPoolExecutor`, mỗi folder 1 thread (ffmpeg là subprocess nên chạy song song thực sự).
- `merge_app.py` — GUI tkinter (theo pattern `app.py`): chọn nhiều folder, chọn mode, số luồng, lưu config vào `merge_config.json`, chạy ghép trên background thread để không treo UI.
- `tests/test_merge_mp3.py` — unit test cho natural sort, lọc file, loại trừ output cũ, escape path trong concat list, error case.

## Cách dùng
```bash
# CLI — ghép theo thứ tự tên file
python merge_mp3.py --mode sequential "D:/audio/f1" "D:/audio/f2" "D:/audio/f3"

# CLI — ghép random, 5 folder song song
python merge_mp3.py --mode random --workers 5 "D:/audio/f1" ... "D:/audio/f5"

# GUI
python merge_app.py

# Test
python -m unittest discover -s tests
```

## Ghi chú
- Yêu cầu `ffmpeg` có trong PATH (giống tool render hiện tại).
- Dùng `-c copy` nên các file trong 1 folder nên cùng sample rate/bitrate (cùng nguồn xuất). Nếu nguồn lẫn lộn và file output bị lỗi duration, đổi sang re-encode: thay `-c copy` bằng `-c:a libmp3lame -q:a 2`.
- Chạy lại tool sẽ ghi đè output cũ (`-y`) và không ghép nhầm output cũ vào input.

## Tiến độ
- [x] Sprint 1: logic ghép + CLI + đa luồng + unit test (8/8 pass) + GUI — hoàn thành 2026-07-14.
- [ ] Chưa làm: e2e với ffmpeg thật (máy dev hiện tại chưa cài ffmpeg); tùy chọn re-encode; progress bar per-folder trong GUI.
