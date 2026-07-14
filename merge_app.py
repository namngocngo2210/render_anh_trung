"""GUI cho tool ghép MP3 theo folder (merge_mp3.py).

Chọn nhiều folder, chọn mode (theo thứ tự / ngẫu nhiên), chạy ghép song song.
Output lưu ngay trong từng folder: <tên_folder>_merged.mp3
"""

import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import merge_mp3

CONFIG_FILE = "merge_config.json"


class MergeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MP3 Folder Merge")

        self.mode = tk.StringVar(value="sequential")
        self.workers = tk.StringVar(value="5")

        # Danh sách folder
        tk.Label(root, text="Folders:").grid(row=0, column=0, sticky="ne", padx=5, pady=5)
        self.folder_listbox = tk.Listbox(root, width=60, height=8, selectmode=tk.EXTENDED)
        self.folder_listbox.grid(row=0, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(root)
        btn_frame.grid(row=0, column=2, padx=5, pady=5, sticky="n")
        tk.Button(btn_frame, text="Thêm folder", command=self.add_folder).pack(fill="x", pady=2)
        tk.Button(btn_frame, text="Xóa folder", command=self.remove_selected).pack(fill="x", pady=2)

        # Mode ghép
        tk.Label(root, text="Chế độ ghép:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        mode_frame = tk.Frame(root)
        mode_frame.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        tk.Radiobutton(mode_frame, text="Theo thứ tự (trên xuống)", variable=self.mode,
                       value="sequential").pack(side="left")
        tk.Radiobutton(mode_frame, text="Ngẫu nhiên", variable=self.mode, value="random").pack(side="left")

        # Số luồng
        tk.Label(root, text="Số folder chạy song song:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(root, textvariable=self.workers, width=10).grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # Nút chạy
        tk.Button(root, text="Lưu cấu hình", command=self.save_config).grid(row=3, column=0, pady=15)
        self.run_btn = tk.Button(root, text="Chạy ghép", command=self.run_merge)
        self.run_btn.grid(row=3, column=1, pady=15)

        # Trạng thái
        self.status = tk.Label(root, text="Trạng thái: Sẵn sàng", fg="blue")
        self.status.grid(row=4, column=0, columnspan=3, pady=5)

        self.load_config()

    def add_folder(self):
        folder = filedialog.askdirectory()
        if folder and folder not in self.folder_listbox.get(0, tk.END):
            self.folder_listbox.insert(tk.END, folder)

    def remove_selected(self):
        for index in reversed(self.folder_listbox.curselection()):
            self.folder_listbox.delete(index)

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            for folder in config.get("folders", []):
                self.folder_listbox.insert(tk.END, folder)
            self.mode.set(config.get("mode", "sequential"))
            self.workers.set(str(config.get("workers", 5)))
        except FileNotFoundError:
            pass
        except Exception as e:
            messagebox.showwarning("Cảnh báo", f"Không thể đọc config: {e}")

    def save_config(self):
        try:
            config = {
                "folders": list(self.folder_listbox.get(0, tk.END)),
                "mode": self.mode.get(),
                "workers": int(self.workers.get() or 5),
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.status.config(text="Đã lưu cấu hình thành công!", fg="green")
        except ValueError:
            messagebox.showerror("Lỗi", "Số luồng phải là số nguyên.")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu config: {e}")

    def run_merge(self):
        folders = list(self.folder_listbox.get(0, tk.END))
        if not folders:
            messagebox.showerror("Lỗi", "Chưa chọn folder nào.")
            return
        try:
            workers = int(self.workers.get() or 5)
        except ValueError:
            messagebox.showerror("Lỗi", "Số luồng phải là số nguyên.")
            return

        self.run_btn.config(state="disabled")
        self.status.config(text=f"Đang ghép {len(folders)} folder...", fg="orange")
        thread = threading.Thread(target=self._merge_worker, args=(folders, self.mode.get(), workers), daemon=True)
        thread.start()

    def _merge_worker(self, folders, mode, workers):
        try:
            results = merge_mp3.merge_folders(folders, mode, workers)
            failed = [f for f, r in results.items() if isinstance(r, Exception)]
            if failed:
                message = "\n".join(f"{f}: {results[f]}" for f in failed)
                self.root.after(0, self._on_done, f"Xong, {len(failed)} folder lỗi", "red", message)
            else:
                self.root.after(0, self._on_done, f"Hoàn tất {len(results)} folder!", "green", None)
        except Exception as e:
            self.root.after(0, self._on_done, f"Lỗi: {e}", "red", str(e))

    def _on_done(self, text, color, error_message):
        self.status.config(text=text, fg=color)
        self.run_btn.config(state="normal")
        if error_message:
            messagebox.showerror("Lỗi khi ghép", error_message)


if __name__ == "__main__":
    root = tk.Tk()
    app = MergeApp(root)
    root.mainloop()
