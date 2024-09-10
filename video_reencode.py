import os
import subprocess
import json
from pathlib import Path
from rich.logging import RichHandler
import logging
import argparse
import datetime
from typing import List, TypedDict, Union, Dict, Any
from rich.console import Console
from rich.table import Table

# Set up logging
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)

log = logging.getLogger("video_reencode")

# Directory to search
VIDEO_DIR = "/Volumes/video/Other Rips"

# Supported file extensions
VIDEO_EXTENSIONS = ['.mp4', '.m4v', '.mkv']

# Groupings by Resolution
RESOLUTION_GROUPS = {
    '4k': 3800,
    '1080p': 1900,
    '720p': 1200,
    'SD': 0
}

class VideoInfo(TypedDict):
    width: int
    height: int
    bit_rate: int
    file_path: str
    file_size: int
    duration: int

def get_video_info_supplemental(file_path: str) -> Dict[str, Any]:
    """
    Retrieves supplemental information about a video file using ffprobe. This is neeeded in some
    situations with matroska files where the duration and bit rate are not available in the main
    stream information.

    Args:
        file_path (str): The path to the video file.
    Returns:
        Dict[str, Any]: A dictionary containing the supplemental information of the video file.
    """
    ffprobe_cmd = [ 
        "ffprobe", "-v", "error", "-print_format", "json", "-select_streams", "v:0",
        "-show_format", "-show_streams", file_path ]

    # Run ffprobe and capture output
    result = subprocess.run(ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if result.returncode != 0:
        print(f"Error getting supplemental info for {file_path}: {result.stderr}")
        return {}
    
    # Parse JSON output
    supplemental_info = json.loads(result.stdout)

    return supplemental_info.get("format", {})

def get_video_info(file_path: str) -> Union[VideoInfo, None]:
    """
    Retrieves information about a video file.
    Args:
        file_path (str): The path to the video file.
    Returns:
        Union[VideoInfo, None]: The video information as a dictionary, or None if an error occurred.
    Raises:
        None
    Examples:
        >>> get_video_info("/path/to/video.mp4")
        {
            'width': 1920,
            'height': 1080,
            'bit_rate': 5000000,
            'duration': 3600,
            'file_path': '/path/to/video.mp4',
            'file_size': 10485760
        }
    """
    try:
        # Command to get video stream information
        ffprobe_cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=width,height,bit_rate,duration", "-of", "json", file_path
        ]
        # Run ffprobe and capture output
        result = subprocess.run(ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print(f"Error with {file_path}: {result.stderr}")
            return None
        
        # Parse JSON output
        video_info = json.loads(result.stdout)


        log.debug(f"video_info: {video_info}")
        stream_info = video_info.get('streams', [None])[0]  # Get the first video stream
        log.debug(f"stream_info: {stream_info}")
        stream_info['file_path'] = file_path
        stream_info['file_size'] = os.path.getsize(file_path)
        stream_info['duration'] = int(float(stream_info.get('duration', 0)))
        stream_info['bit_rate'] = int(stream_info.get('bit_rate', 0))

        if stream_info['duration'] == 0 or stream_info['bit_rate'] == 0:
            supplemental_data = get_video_info_supplemental(file_path)
            stream_info['duration'] = int(float(supplemental_data.get('duration', 0)))
            stream_info['bit_rate'] = int(supplemental_data.get('bit_rate', 0))

        return stream_info
    except Exception as e:
        print(f"Exception occurred: {e}")
        return None

def categorize_by_resolution(video_info: VideoInfo, default: str="UNKNOWN") -> str:
    """
    Categorizes a video based on its resolution. These are defined in RESOLUTION_GROUPS above and
    rely on the fact that Python 3.7 and newer preserve the order of dictionary keys.
    Parameters:
    - video_info (VideoInfo): A dictionary containing information about the video.
    - default (str): The default category to return if the video resolution does not match any category.
    Returns:
    - str: The category label of the video based on its resolution.
    """
    width = video_info['width']
    
    # Iterate through the resolution groups sorted by their pixel threshold in descending order
    for label, min_width in RESOLUTION_GROUPS.items():
        if width > min_width:
            return label
    return default
    
        
def main(video_dir: str, video_extensions: List[str], output_json: bool = False):
    # raise error if video_dir does not exist
    if not os.path.exists(video_dir):
        log.error(f"Directory \"{video_dir}\" does not exist.")
        return
    
    # Collect video files
    video_files = [str(p) for p in Path(video_dir).rglob('*') if p.suffix in video_extensions]
    log.info(f"Found {len(video_files)} video files in \"{video_dir}\"")

    # Dictionaries to hold grouped files
    groups: Dict[str, List[VideoInfo]] = {resolution: [] for resolution in RESOLUTION_GROUPS.keys()}

    # Process each video file
    for video_file in video_files:
        log.info(f"Processing: \"{video_file}\"")
        video_info = get_video_info(video_file)
        log.debug(f"video_info: {video_info}")
        if video_info:
            resolution_group = categorize_by_resolution(video_info)
            groups[resolution_group].append(video_info)

    # Sort files by bitrate within each group in descending order
    for group in groups:
        groups[group].sort(key=lambda x: x.get('bit_rate',0), reverse=True)

    # Print results
    table = Table(title=f"\nVideos (sorted by bitrate)")
    table.add_column("File Path")
    table.add_column("Bit Rate (kbps)", style="cyan")
    table.add_column("Duration", style="magenta")

    for group, files in groups.items():
        
        table.add_row(f"[bold]{group.upper()}", style="bright_white on green")
        for file_info in files:
            file_path = file_info['file_path']
            bit_rate = int(file_info.get('bit_rate', 0) / 1024)
            duration = file_info.get('duration', 0)
            duration_formatted = str(datetime.timedelta(seconds=duration))
            table.add_row(file_path, str(bit_rate), duration_formatted)

    console = Console()
    console.print(table)


if __name__ == "__main__":
    # Create argument parser
    parser = argparse.ArgumentParser(description='Video Reencode')

    # Add arguments
    parser.add_argument('-d', '--directory', type=str, help='Directory to search', default=VIDEO_DIR)
    parser.add_argument('-e', '--extensions', nargs='+', type=str, help='Supported file extensions', default=VIDEO_EXTENSIONS)

    # Parse the arguments
    args = parser.parse_args()

    # Set the directory and extensions
    video_dir = args.directory
    video_extensions = args.extensions

    # Call the main function
    main(video_dir, video_extensions)