import tkinter as tk
from tkinter import filedialog, messagebox
import json
import main  # giả sử main.py có hàm run() để chạy

CONFIG_FILE = "config.json"

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("video Render Settings")

        # Biến lưu dữ liệu
        self.audio_folder = tk.StringVar()
        self.video_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.output_length_min = tk.StringVar()
        self.output_length_max = tk.StringVar()
        self.audio_bitrate = tk.StringVar()
        self.random_videos = tk.StringVar()
        self.videos_to_merge = tk.StringVar()  # biến mới
        self.bgm_folder = tk.StringVar()  # thư mục nhạc nền
        self.bgm_file = tk.StringVar()  # file nhạc nền cố định
        self.bgm_volume = tk.StringVar()  # âm lượng BGM (0.0 - 1.0)
        self.bgm_mode = tk.StringVar(value="folder")  # "folder" hoặc "file"
        self.crossfade = tk.BooleanVar(value=False)  # crossfade option
        self.crossfade_duration = tk.StringVar(value="2.0")  # crossfade duration in seconds
        self.audio_mode = tk.StringVar(value="trim")  # "trim" (cắt theo độ dài) hoặc "full" (ghép full folder)
        self.audio_order = tk.StringVar(value="random")  # "random" hoặc "sequential"

        # Giao diện chọn thư mục
        self._create_folder_selector("Audio Folder:", self.audio_folder, 0)
        self._create_folder_selector("Video Folder:", self.video_folder, 1)
        self._create_folder_selector("Output Folder:", self.output_folder, 2)
        
        # Audio Mode selection
        tk.Label(root, text="Audio Mode:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        audio_mode_frame = tk.Frame(root)
        audio_mode_frame.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        tk.Radiobutton(audio_mode_frame, text="Cắt theo độ dài (min-max)", variable=self.audio_mode, value="trim", command=self._on_audio_mode_change).pack(side="left")
        tk.Radiobutton(audio_mode_frame, text="Ghép full folder", variable=self.audio_mode, value="full", command=self._on_audio_mode_change).pack(side="left")

        # Audio Order selection (chỉ dùng cho chế độ ghép full)
        tk.Label(root, text="Thứ tự ghép:").grid(row=4, column=0, sticky="e", padx=5, pady=5)
        audio_order_frame = tk.Frame(root)
        audio_order_frame.grid(row=4, column=1, sticky="w", padx=5, pady=5)
        self.audio_order_random_rb = tk.Radiobutton(audio_order_frame, text="Ngẫu nhiên", variable=self.audio_order, value="random")
        self.audio_order_random_rb.pack(side="left")
        self.audio_order_seq_rb = tk.Radiobutton(audio_order_frame, text="Theo thứ tự tên file", variable=self.audio_order, value="sequential")
        self.audio_order_seq_rb.pack(side="left")

        # BGM Mode selection
        tk.Label(root, text="BGM Mode:").grid(row=5, column=0, sticky="e", padx=5, pady=5)
        bgm_mode_frame = tk.Frame(root)
        bgm_mode_frame.grid(row=5, column=1, sticky="w", padx=5, pady=5)
        tk.Radiobutton(bgm_mode_frame, text="Folder (Random)", variable=self.bgm_mode, value="folder", command=self._on_bgm_mode_change).pack(side="left")
        tk.Radiobutton(bgm_mode_frame, text="Fixed File", variable=self.bgm_mode, value="file", command=self._on_bgm_mode_change).pack(side="left")

        # BGM Folder selector (store references for enabling/disabling)
        tk.Label(root, text="BGM Folder:").grid(row=6, column=0, sticky="e", padx=5, pady=5)
        self.bgm_folder_entry = tk.Entry(root, textvariable=self.bgm_folder, width=40)
        self.bgm_folder_entry.grid(row=6, column=1, padx=5, pady=5)
        self.bgm_folder_btn = tk.Button(root, text="Chọn thư mục", command=lambda: self._select_folder(self.bgm_folder))
        self.bgm_folder_btn.grid(row=6, column=2, padx=5, pady=5)

        # BGM File selector (store references for enabling/disabling)
        tk.Label(root, text="BGM File:").grid(row=7, column=0, sticky="e", padx=5, pady=5)
        self.bgm_file_entry = tk.Entry(root, textvariable=self.bgm_file, width=40)
        self.bgm_file_entry.grid(row=7, column=1, padx=5, pady=5)
        self.bgm_file_btn = tk.Button(root, text="Chọn file", command=lambda: self._select_file(self.bgm_file))
        self.bgm_file_btn.grid(row=7, column=2, padx=5, pady=5)

        # Entry nhập thủ công
        tk.Label(root, text="Output Length (min-max):").grid(row=8, column=0, sticky="e", padx=5, pady=5)
        length_frame = tk.Frame(root)
        length_frame.grid(row=8, column=1, sticky="w", padx=5, pady=5)
        self.output_length_min_entry = tk.Entry(length_frame, textvariable=self.output_length_min, width=10)
        self.output_length_min_entry.pack(side="left")
        tk.Label(length_frame, text=" - ").pack(side="left")
        self.output_length_max_entry = tk.Entry(length_frame, textvariable=self.output_length_max, width=10)
        self.output_length_max_entry.pack(side="left")
        tk.Label(length_frame, text=" (seconds)").pack(side="left")

        tk.Label(root, text="Audio Bitrate:").grid(row=9, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(root, textvariable=self.audio_bitrate, width=30).grid(row=9, column=1, padx=5, pady=5)

        tk.Label(root, text="BGM Volume (0.0-1.0):").grid(row=10, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(root, textvariable=self.bgm_volume, width=30).grid(row=10, column=1, padx=5, pady=5)

        tk.Label(root, text="Crossfade Audio:").grid(row=11, column=0, sticky="e", padx=5, pady=5)
        tk.Checkbutton(root, text="Bật hiệu ứng chuyển mượt giữa các file audio", variable=self.crossfade).grid(row=11, column=1, sticky="w", padx=5, pady=5)

        tk.Label(root, text="Crossfade Duration (s):").grid(row=12, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(root, textvariable=self.crossfade_duration, width=30).grid(row=12, column=1, padx=5, pady=5)

        tk.Label(root, text="Group:").grid(row=13, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(root, textvariable=self.videos_to_merge, width=30).grid(row=13, column=1, padx=5, pady=5)

        tk.Label(root, text="Outputs:").grid(row=14, column=0, sticky="e", padx=5, pady=5)
        tk.Entry(root, textvariable=self.random_videos, width=30).grid(row=14, column=1, padx=5, pady=5)

        # Nút lưu config và chạy xử lý
        tk.Button(root, text="Lưu cấu hình", command=self.save_config).grid(row=15, column=0, pady=15)
        tk.Button(root, text="Chạy xử lý", command=self.run_main).grid(row=15, column=1, pady=15)

        # Trạng thái
        self.status = tk.Label(root, text="Trạng thái: Sẵn sàng", fg="blue")
        self.status.grid(row=16, column=0, columnspan=2, pady=5)

        self.load_config()
        self._on_bgm_mode_change()  # Set initial state
        self._on_audio_mode_change()  # Set initial state

    def _on_audio_mode_change(self):
        """Enable/disable output length or audio order inputs based on audio mode."""
        mode = self.audio_mode.get()
        if mode == "full":
            # Ghép full folder: không cần độ dài, cho chọn thứ tự ghép
            self.output_length_min_entry.config(state="disabled")
            self.output_length_max_entry.config(state="disabled")
            self.audio_order_random_rb.config(state="normal")
            self.audio_order_seq_rb.config(state="normal")
        else:
            # Cắt theo độ dài: cần min-max, thứ tự ghép không áp dụng
            self.output_length_min_entry.config(state="normal")
            self.output_length_max_entry.config(state="normal")
            self.audio_order_random_rb.config(state="disabled")
            self.audio_order_seq_rb.config(state="disabled")

    def _on_bgm_mode_change(self):
        """Enable/disable BGM folder or file inputs based on selected mode."""
        mode = self.bgm_mode.get()
        if mode == "folder":
            # Enable folder, disable file
            self.bgm_folder_entry.config(state="normal")
            self.bgm_folder_btn.config(state="normal")
            self.bgm_file_entry.config(state="disabled")
            self.bgm_file_btn.config(state="disabled")
        else:
            # Enable file, disable folder
            self.bgm_folder_entry.config(state="disabled")
            self.bgm_folder_btn.config(state="disabled")
            self.bgm_file_entry.config(state="normal")
            self.bgm_file_btn.config(state="normal")

    def _create_folder_selector(self, label_text, variable, row):
        tk.Label(self.root, text=label_text).grid(row=row, column=0, sticky="e", padx=5, pady=5)
        entry = tk.Entry(self.root, textvariable=variable, width=40)
        entry.grid(row=row, column=1, padx=5, pady=5)
        btn = tk.Button(self.root, text="Chọn thư mục", command=lambda: self._select_folder(variable))
        btn.grid(row=row, column=2, padx=5, pady=5)

    def _select_folder(self, variable):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            variable.set(folder_selected)

    def _create_file_selector(self, label_text, variable, row):
        tk.Label(self.root, text=label_text).grid(row=row, column=0, sticky="e", padx=5, pady=5)
        entry = tk.Entry(self.root, textvariable=variable, width=40)
        entry.grid(row=row, column=1, padx=5, pady=5)
        btn = tk.Button(self.root, text="Chọn file", command=lambda: self._select_file(variable))
        btn.grid(row=row, column=2, padx=5, pady=5)

    def _select_file(self, variable):
        file_selected = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3"), ("All files", "*.*")])
        if file_selected:
            variable.set(file_selected)

    def load_config(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            self.audio_folder.set(config.get("audio_folder", ""))
            self.video_folder.set(config.get("video_folder", ""))
            self.output_folder.set(config.get("output_folder", ""))
            self.output_length_min.set(str(config.get("output_length_min", config.get("output_length", ""))))
            self.output_length_max.set(str(config.get("output_length_max", config.get("output_length", ""))))
            self.audio_bitrate.set(config.get("audio_bitrate", ""))
            self.random_videos.set(str(config.get("random_videos", "")))
            self.videos_to_merge.set(str(config.get("videos_to_merge", "")))  # load mới
            self.bgm_folder.set(config.get("bgm_folder", ""))
            self.bgm_file.set(config.get("bgm_file", ""))
            self.bgm_volume.set(str(config.get("bgm_volume", "0.3")))
            self.bgm_mode.set(config.get("bgm_mode", "folder"))
            self.crossfade.set(config.get("crossfade", False))
            self.crossfade_duration.set(str(config.get("crossfade_duration", "2.0")))
            self.audio_mode.set(config.get("audio_mode", "trim"))
            self.audio_order.set(config.get("audio_order", "random"))
        except Exception as e:
            messagebox.showwarning("Cảnh báo", f"Không thể đọc config: {e}")

    def save_config(self):
        try:
            if self.audio_mode.get() == "full":
                # Chế độ ghép full không dùng độ dài, cho phép để trống
                output_length_min_int = int(self.output_length_min.get()) if self.output_length_min.get() else 0
                output_length_max_int = int(self.output_length_max.get()) if self.output_length_max.get() else 0
            else:
                output_length_min_int = int(self.output_length_min.get())
                output_length_max_int = int(self.output_length_max.get())
            random_videos_int = int(self.random_videos.get()) if self.random_videos.get() else 0
            videos_to_merge_int = int(self.videos_to_merge.get()) if self.videos_to_merge.get() else 0
            bgm_volume_float = float(self.bgm_volume.get()) if self.bgm_volume.get() else 0.3
            crossfade_duration_float = float(self.crossfade_duration.get()) if self.crossfade_duration.get() else 2.0
            config = {
                "audio_folder": self.audio_folder.get(),
                "video_folder": self.video_folder.get(),
                "output_folder": self.output_folder.get(),
                "output_length_min": output_length_min_int,
                "output_length_max": output_length_max_int,
                "audio_bitrate": self.audio_bitrate.get(),
                "random_videos": random_videos_int,
                "videos_to_merge": videos_to_merge_int,
                "bgm_folder": self.bgm_folder.get(),
                "bgm_file": self.bgm_file.get(),
                "bgm_volume": bgm_volume_float,
                "bgm_mode": self.bgm_mode.get(),
                "crossfade": self.crossfade.get(),
                "crossfade_duration": crossfade_duration_float,
                "audio_mode": self.audio_mode.get(),
                "audio_order": self.audio_order.get(),
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            self.status.config(text="Đã lưu cấu hình thành công!", fg="green")
        except ValueError:
            messagebox.showerror("Lỗi", "Output Length, Random Videos và Videos to Merge phải là số nguyên.")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu config: {e}")

    def run_main(self):
        self.status.config(text="Đang chạy xử lý...", fg="orange")
        try:
            main.run()  # gọi hàm xử lý chính trong main.py
            self.status.config(text="Xử lý hoàn tất!", fg="green")
        except Exception as e:
            self.status.config(text=f"Lỗi: {e}", fg="red")
            messagebox.showerror("Lỗi khi chạy xử lý", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()