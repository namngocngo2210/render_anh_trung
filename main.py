import os
import json
import subprocess
import glob
import math
import random
from pathlib import Path


def load_config(config_file):
    """Load configuration from a JSON file."""
    with open(config_file, "r") as f:
        return json.load(f)


def get_mp3_duration(file_path):
    """Lấy độ dài của file MP3 sử dụng ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
             file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Lỗi khi lấy độ dài cho {file_path}: {e}")
        return None


def trim_mp3(audio_folder, output_file, target_length, crossfade=False, crossfade_duration=2.0):
    """Chọn và ghép các file MP3 để đạt độ dài mong muốn sử dụng FFmpeg.

    Args:
        audio_folder: Đường dẫn đến thư mục chứa file MP3
        output_file: Đường dẫn file đầu ra
        target_length: Độ dài mục tiêu tính bằng giây
        crossfade: Nếu True, áp dụng hiệu ứng chuyển mượt giữa các file audio
        crossfade_duration: Độ dài crossfade tính bằng giây
    """
    audio_files = glob.glob(os.path.join(audio_folder, "*.mp3"))
    if not audio_files:
        raise FileNotFoundError(f"Không tìm thấy file MP3 trong {audio_folder}")

    # Xáo trộn danh sách file MP3
    random.shuffle(audio_files)

    total_duration = 0
    concat_list = []

    # Duyệt qua các file và tính độ dài của chúng
    for audio_file in audio_files:
        duration = get_mp3_duration(audio_file)
        if duration is None:
            print(f"Bỏ qua file không hợp lệ: {audio_file}")
            continue

        if total_duration + duration > target_length:
            remaining_duration = target_length - total_duration
            concat_list.append((audio_file, remaining_duration))
            total_duration += remaining_duration
            break
        else:
            concat_list.append((audio_file, None))
            total_duration += duration

    if total_duration < target_length:
        raise RuntimeError("Không đủ file MP3 hợp lệ để đạt độ dài mục tiêu.")

    # Tạo file tạm liệt kê các file cần ghép
    concat_list_file = os.path.join(audio_folder, "concat_list.txt")
    try:
        with open(concat_list_file, "w") as f:
            for audio_file, duration in concat_list:
                abs_path = os.path.abspath(audio_file).replace("\\", "/")  # Đảm bảo định dạng đường dẫn đúng
                if duration:
                    f.write(f"file '{abs_path}'\ninpoint 0\noutpoint {duration}\n")
                else:
                    f.write(f"file '{abs_path}'\n")
    except Exception as e:
        print(f"Lỗi khi tạo danh sách ghép: {e}")
        input("Nhấn phím bất kỳ để đóng...")
        return

    # Sử dụng FFmpeg để ghép các file và cắt theo độ dài mục tiêu
    try:
        print("Đang ghép các file audio...")
        if crossfade and len(concat_list) > 1:
            # Sử dụng crossfade giữa các file
            # Xây dựng filter_complex cho crossfade
            filter_parts = []
            for i, (audio_file, duration) in enumerate(concat_list):
                abs_path = os.path.abspath(audio_file).replace("\\", "/")
                if duration:
                    filter_parts.append(f"[{i}:a]atrim=0:{duration},asetpts=PTS-STARTPTS[a{i}]")
                else:
                    filter_parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]")

            # Xây dựng chuỗi crossfade
            crossfade_chain = ""
            for i in range(len(concat_list) - 1):
                if i == 0:
                    crossfade_chain += f"[a{i}][a{i+1}]acrossfade=d={crossfade_duration}:c1=tri:c2=tri[m{i}]"
                else:
                    crossfade_chain += f";[m{i-1}][a{i+1}]acrossfade=d={crossfade_duration}:c1=tri:c2=tri[m{i}]"

            # Ghép tất cả lại
            filter_complex = ";".join(filter_parts) + ";" + crossfade_chain

            # Xây dựng input list
            inputs = []
            for audio_file, duration in concat_list:
                abs_path = os.path.abspath(audio_file).replace("\\", "/")
                inputs.extend(["-i", abs_path])

            # Thêm -map để chỉ định output từ filter_complex
            cmd = ["ffmpeg"] + inputs + ["-filter_complex", filter_complex, "-map", f"[m{len(concat_list)-2}]", "-t", str(target_length), "-c:a", "libmp3lame", "-q:a", "2", output_file]
            print(f"Đang chạy crossfade với {len(concat_list)} file...")
            subprocess.run(cmd, check=True)
        else:
            # Sử dụng concat đơn giản không có crossfade
            subprocess.run([
                "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list_file, "-t", str(target_length), "-c", "copy",
                output_file
            ], check=True)
        print(f"Audio đã ghép được lưu vào: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Lỗi FFmpeg: {e}")
        input("Nhấn phím bất kỳ để đóng...")
    finally:
        # Dọn dẹp file tạm
        if os.path.exists(concat_list_file):
            os.remove(concat_list_file)


def concat_full_mp3(audio_folder, output_file, order="random", crossfade=False, crossfade_duration=2.0):
    """Ghép toàn bộ file MP3 trong thư mục thành một dải audio duy nhất.

    Args:
        audio_folder: Đường dẫn đến thư mục chứa file MP3
        output_file: Đường dẫn file đầu ra
        order: "random" để xáo trộn, "sequential" để ghép theo thứ tự tên file
        crossfade: Nếu True, áp dụng hiệu ứng chuyển mượt giữa các file audio
        crossfade_duration: Độ dài crossfade tính bằng giây

    Returns:
        Độ dài (giây) của audio đã ghép.
    """
    audio_files = glob.glob(os.path.join(audio_folder, "*.mp3"))
    if not audio_files:
        raise FileNotFoundError(f"Không tìm thấy file MP3 trong {audio_folder}")

    if order == "sequential":
        audio_files.sort()
    else:
        random.shuffle(audio_files)

    print(f"Đang ghép full {len(audio_files)} file MP3 (thứ tự: {order})...")

    if crossfade and len(audio_files) > 1:
        # Xây dựng filter_complex cho crossfade toàn bộ file
        filter_parts = []
        inputs = []
        for i, audio_file in enumerate(audio_files):
            abs_path = os.path.abspath(audio_file).replace("\\", "/")
            inputs.extend(["-i", abs_path])
            filter_parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]")

        crossfade_chain = ""
        for i in range(len(audio_files) - 1):
            if i == 0:
                crossfade_chain += f"[a{i}][a{i+1}]acrossfade=d={crossfade_duration}:c1=tri:c2=tri[m{i}]"
            else:
                crossfade_chain += f";[m{i-1}][a{i+1}]acrossfade=d={crossfade_duration}:c1=tri:c2=tri[m{i}]"

        filter_complex = ";".join(filter_parts) + ";" + crossfade_chain
        cmd = ["ffmpeg"] + inputs + [
            "-filter_complex", filter_complex, "-map", f"[m{len(audio_files)-2}]",
            "-c:a", "libmp3lame", "-q:a", "2", output_file
        ]
        subprocess.run(cmd, check=True)
    else:
        # Concat đơn giản không re-encode
        concat_list_file = os.path.join(audio_folder, "concat_list.txt")
        try:
            with open(concat_list_file, "w") as f:
                for audio_file in audio_files:
                    abs_path = os.path.abspath(audio_file).replace("\\", "/")
                    f.write(f"file '{abs_path}'\n")
            subprocess.run([
                "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list_file, "-c", "copy", output_file
            ], check=True)
        finally:
            if os.path.exists(concat_list_file):
                os.remove(concat_list_file)

    duration = get_mp3_duration(output_file)
    if duration is None:
        raise RuntimeError(f"Không đọc được độ dài audio đã ghép: {output_file}")
    print(f"Audio full đã ghép được lưu vào: {output_file} ({duration:.0f} giây)")
    return duration


def concat_random_videos(video_folder, start_video, output_path, n_random=3):
    folder = Path(video_folder)
    start_path = Path(start_video).resolve()
    output_path = Path(output_path).resolve()

    all_videos = [f for f in folder.glob("*.mp4") if f.name != start_path.name]

    if len(all_videos) < n_random:
        raise ValueError(f"Không đủ video. Có {len(all_videos)}, yêu cầu {n_random}.")

    selected = random.sample(all_videos, n_random)
    file_list_path = folder / "file_list.txt"

    try:
        with file_list_path.open("w") as f:
            f.write(f"file '{start_path}'\n")
            for video in selected:
                f.write(f"file '{video.resolve()}'\n")

        cmd = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(file_list_path), '-c', 'copy', str(output_path)]
        subprocess.run(cmd, check=True)
        print(f"✅ Đã nối thành công vào {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Lỗi ffmpeg: {e}")
    finally:
        if file_list_path.exists():
            file_list_path.unlink()
            print("🧹 Đã xóa file tạm file_list.txt")

def loop_mp4(input_file, output_file, length):
    # Lấy độ dài video
    result = subprocess.run(
        [
            "ffprobe", "-i", input_file, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"
        ],
        stdout=subprocess.PIPE,
        text=True,
        check=True
    )
    duration = float(result.stdout.strip())
    loops = math.ceil(length / duration)  # Tính số lần lặp cần thiết

    print(f"Đang lặp video: {input_file} -> {output_file} ({loops} lần lặp)")
    subprocess.run(
        [
            "ffmpeg", "-stream_loop", str(loops - 1), "-i", input_file, "-t", str(length), "-c", "copy", output_file
        ],
        check=True)


def loop_bgm_audio(bgm_source, output_file, target_length, volume=0.3, is_file=False):
    """Lặp BGM đến độ dài mục tiêu với điều chỉnh âm lượng.

    Args:
        bgm_source: Đường dẫn thư mục (chọn ngẫu nhiên) hoặc đường dẫn file (file cố định)
        output_file: Đường dẫn file đầu ra
        target_length: Độ dài mục tiêu tính bằng giây
        volume: Điều chỉnh âm lượng (0.0-1.0)
        is_file: Nếu True, bgm_source là đường dẫn file; nếu False, là đường dẫn thư mục
    """
    if is_file:
        # Sử dụng file được chỉ định trực tiếp
        if not os.path.isfile(bgm_source):
            print(f"Không tìm thấy file BGM: {bgm_source}, bỏ qua BGM...")
            return None
        bgm_file = bgm_source
        print(f"Sử dụng BGM cố định: {bgm_file}")
    else:
        # Chọn ngẫu nhiên từ thư mục
        bgm_files = glob.glob(os.path.join(bgm_source, "*.mp3"))
        if not bgm_files:
            print(f"Không tìm thấy file BGM trong {bgm_source}, bỏ qua BGM...")
            return None
        bgm_file = random.choice(bgm_files)
        print(f"Đã chọn BGM ngẫu nhiên: {bgm_file}")

    try:
        # Lặp BGM đến độ dài mục tiêu với điều chỉnh âm lượng
        subprocess.run([
            "ffmpeg", "-stream_loop", "-1", "-i", bgm_file,
            "-t", str(target_length),
            "-af", f"volume={volume}",
            "-c:a", "libmp3lame", "-q:a", "2",
            output_file
        ], check=True)
        print(f"BGM đã lặp và lưu vào: {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Lỗi khi xử lý BGM: {e}")
        return None


def mix_audio(main_audio, bgm_audio, output_file):
    """Trộn audio chính với nhạc nền."""
    print(f"Đang trộn audio: {main_audio} + {bgm_audio} -> {output_file}")
    try:
        subprocess.run([
            "ffmpeg", "-i", main_audio, "-i", bgm_audio,
            "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2",
            "-c:a", "libmp3lame", "-q:a", "2",
            output_file
        ], check=True)
        print(f"Audio đã trộn được lưu vào: {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Lỗi khi trộn audio: {e}")
        return None


def merge_audio_video(video_file, audio_file, output_file, audio_bitrate):
    """Ghép audio đã cắt và video đã lặp thành file đầu ra cuối cùng."""
    print(f"Đang ghép audio và video: {video_file} + {audio_file} -> {output_file}")
    subprocess.run(
        ["ffmpeg", "-i", video_file, "-i", audio_file, "-c:v", "copy", "-c:a", "aac", "-map", '0:v',
         "-map", "1:a", output_file],
        check=True
    )


def main():
    # Load configuration
    config_file = "config.json"
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file {config_file} not found.")

    config = load_config(config_file)
    audio_folder = config["audio_folder"]
    video_folder = config["video_folder"]
    output_folder = config["output_folder"]
    output_length_min = config.get("output_length_min", config.get("output_length", 600))
    output_length_max = config.get("output_length_max", config.get("output_length", 600))
    audio_bitrate = config["audio_bitrate"]
    videos_to_merge = config["videos_to_merge"]
    output_file = config["random_videos"]
    bgm_folder = config.get("bgm_folder", "")
    bgm_file = config.get("bgm_file", "")
    bgm_volume = config.get("bgm_volume", 0.3)
    bgm_mode = config.get("bgm_mode", "folder")  # "folder" or "file"
    crossfade = config.get("crossfade", False)  # crossfade option
    crossfade_duration = config.get("crossfade_duration", 2.0)  # crossfade duration in seconds
    audio_mode = config.get("audio_mode", "trim")  # "trim" (cắt theo độ dài) or "full" (ghép full folder)
    audio_order = config.get("audio_order", "random")  # "random" or "sequential"

    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # File paths
    trimmed_audio = os.path.join(output_folder, "trimmed_audio.mp3")
    bgm_audio = os.path.join(output_folder, "bgm_audio.mp3")
    mixed_audio = os.path.join(output_folder, "mixed_audio.mp3")
    loop_video = os.path.join(output_folder, "loop_video.mp4")
    concat_video = os.path.join(output_folder, "concat_video.mp4")

    count = 0
    try:
        video_files = glob.glob(os.path.join(video_folder, "*.mp4"))
        for i in range(0, output_file):
            if audio_mode == "full":
                # Ghép toàn bộ MP3 trong folder, độ dài video theo độ dài audio đã ghép
                print(f"\n=== Video {i+1}/{output_file} - Full audio mode (order: {audio_order}) ===")
                output_length = concat_full_mp3(
                    audio_folder, trimmed_audio, order=audio_order,
                    crossfade=crossfade, crossfade_duration=crossfade_duration
                )
            else:
                # Generate random output length within range
                output_length = random.randint(output_length_min, output_length_max)
                print(f"\n=== Video {i+1}/{output_file} - Target length: {output_length} seconds ===")

                trim_mp3(audio_folder, trimmed_audio, output_length, crossfade=crossfade, crossfade_duration=crossfade_duration)
            
            # Process BGM based on mode
            final_audio = trimmed_audio
            if bgm_mode == "file" and bgm_file:
                # Use fixed file mode
                bgm_result = loop_bgm_audio(bgm_file, bgm_audio, output_length, bgm_volume, is_file=True)
                if bgm_result:
                    mix_result = mix_audio(trimmed_audio, bgm_audio, mixed_audio)
                    if mix_result:
                        final_audio = mixed_audio
            elif bgm_mode == "folder" and bgm_folder and os.path.isdir(bgm_folder):
                # Use folder mode (random selection)
                bgm_result = loop_bgm_audio(bgm_folder, bgm_audio, output_length, bgm_volume, is_file=False)
                if bgm_result:
                    mix_result = mix_audio(trimmed_audio, bgm_audio, mixed_audio)
                    if mix_result:
                        final_audio = mixed_audio
            
            file_name = Path(video_files[i]).stem
            final_output = os.path.join(output_folder, f"{file_name}.mp4")
            concat_random_videos(video_folder, video_files[i], concat_video, videos_to_merge)
            loop_mp4(concat_video, loop_video, output_length)
            merge_audio_video(loop_video, final_audio, final_output, audio_bitrate)
            print(f"Process complete! Final video saved at: {final_output}")
            
            # Cleanup temp files
            if os.path.exists(trimmed_audio):
                os.remove(trimmed_audio)
            if os.path.exists(bgm_audio):
                os.remove(bgm_audio)
            if os.path.exists(mixed_audio):
                os.remove(mixed_audio)
            os.remove(concat_video)
            os.remove(loop_video)
            count += 1
    except Exception as e:
        print(f"Error: {e}")
        input("Press any key to close...")
        
def run():
    main()
