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
    """Get the duration of an MP3 file using ffprobe."""
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
        print(f"Error getting duration for {file_path}: {e}")
        return None


def trim_mp3(audio_folder, output_file, target_length):
    """Select and concatenate MP3 files to match the specified length using FFmpeg."""
    audio_files = glob.glob(os.path.join(audio_folder, "*.mp3"))
    if not audio_files:
        raise FileNotFoundError(f"No MP3 files found in {audio_folder}")

    # Shuffle the list of MP3 files
    random.shuffle(audio_files)

    total_duration = 0
    concat_list = []

    # Iterate through the files and calculate their durations
    for audio_file in audio_files:
        duration = get_mp3_duration(audio_file)
        if duration is None:
            print(f"Skipping invalid file: {audio_file}")
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
        raise RuntimeError("Not enough valid MP3 files to reach the target length.")

    # Create a temporary file listing the files to concatenate
    concat_list_file = os.path.join(audio_folder, "concat_list.txt")
    try:
        with open(concat_list_file, "w") as f:
            for audio_file, duration in concat_list:
                abs_path = os.path.abspath(audio_file).replace("\\", "/")  # Ensure proper path formatting
                if duration:
                    f.write(f"file '{abs_path}'\ninpoint 0\noutpoint {duration}\n")
                else:
                    f.write(f"file '{abs_path}'\n")
    except Exception as e:
        print(f"Error creating concat list: {e}")
        input("Press any key to close...")
        return

    # Use FFmpeg to concatenate the files and trim to the target length
    try:
        print("Concatenating audio files...")
        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list_file, "-t", str(target_length), "-c", "copy",
            output_file
        ], check=True)
        print(f"Concatenated audio saved to: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e}")
        input("Press any key to close...")
    finally:
        # Cleanup temporary files
        if os.path.exists(concat_list_file):
            os.remove(concat_list_file)


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
    # Get the video duration
    result = subprocess.run(
        [
            "ffprobe", "-i", input_file, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"
        ],
        stdout=subprocess.PIPE,
        text=True,
        check=True
    )
    duration = float(result.stdout.strip())
    loops = math.ceil(length / duration)  # Calculate the number of loops needed

    print(f"Looping video: {input_file} -> {output_file} ({loops} loops)")
    subprocess.run(
        [
            "ffmpeg", "-stream_loop", str(loops - 1), "-i", input_file, "-t", str(length), "-c", "copy", output_file
        ],
        check=True)


def loop_bgm_audio(bgm_source, output_file, target_length, volume=0.3, is_file=False):
    """Loop BGM to target length with volume adjustment.
    
    Args:
        bgm_source: Either a folder path (random selection) or a file path (fixed file)
        output_file: Output file path
        target_length: Target duration in seconds
        volume: Volume adjustment (0.0-1.0)
        is_file: If True, bgm_source is a file path; if False, it's a folder path
    """
    if is_file:
        # Use the specified file directly
        if not os.path.isfile(bgm_source):
            print(f"BGM file not found: {bgm_source}, skipping BGM...")
            return None
        bgm_file = bgm_source
        print(f"Using fixed BGM: {bgm_file}")
    else:
        # Random selection from folder
        bgm_files = glob.glob(os.path.join(bgm_source, "*.mp3"))
        if not bgm_files:
            print(f"No BGM files found in {bgm_source}, skipping BGM...")
            return None
        bgm_file = random.choice(bgm_files)
        print(f"Selected random BGM: {bgm_file}")
    
    try:
        # Loop BGM to target length with volume adjustment
        subprocess.run([
            "ffmpeg", "-stream_loop", "-1", "-i", bgm_file,
            "-t", str(target_length),
            "-af", f"volume={volume}",
            "-c:a", "libmp3lame", "-q:a", "2",
            output_file
        ], check=True)
        print(f"BGM looped and saved to: {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error processing BGM: {e}")
        return None


def mix_audio(main_audio, bgm_audio, output_file):
    """Mix main audio with background music."""
    print(f"Mixing audio: {main_audio} + {bgm_audio} -> {output_file}")
    try:
        subprocess.run([
            "ffmpeg", "-i", main_audio, "-i", bgm_audio,
            "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2",
            "-c:a", "libmp3lame", "-q:a", "2",
            output_file
        ], check=True)
        print(f"Mixed audio saved to: {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error mixing audio: {e}")
        return None


def merge_audio_video(video_file, audio_file, output_file, audio_bitrate):
    """Merge the trimmed audio and looped video into a final output."""
    print(f"Merging audio and video: {video_file} + {audio_file} -> {output_file}")
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
            # Generate random output length within range
            output_length = random.randint(output_length_min, output_length_max)
            print(f"\n=== Video {i+1}/{output_file} - Target length: {output_length} seconds ===")
            
            trim_mp3(audio_folder, trimmed_audio, output_length)
            
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
