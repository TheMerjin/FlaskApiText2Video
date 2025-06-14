from flask import Flask, request, jsonify, send_file, abort, Response
import os
import csv
from functools import lru_cache
from werkzeug.utils import secure_filename
import re
from moviepy import VideoFileClip, concatenate_videoclips
import tempfile
import uuid
import re
import random
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
# Constants
VIDEO_BASE_PATH = os.path.abspath("")
MAX_TEXT_LENGTH = 100  # Maximum allowed text length
ALLOWED_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")  # Allowed characters


def load_video_mapping():
    """Load video mapping from CSV file."""
    mapping = {}
    try:
        with open("data.csv", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                letter = row["words"].upper()
                raw_path = row["path"].replace(".pose", ".mp4")

                # Fix the doubling issue
                # This replaces only 'ase/' or 'ase\' with 'videos/' safely
                fixed_path = re.sub(r"[/\\]?ase[/\\]", "videos/", raw_path)

                # If it still doesn't work, use this safer alternative:
                # fixed_path = raw_path.replace("ase/", "videos/").replace("ase\\", "videos\\")

                video_path = os.path.join("videos", fixed_path)

                print("Mapped:", letter, "→", video_path)

                mapping[letter] = video_path
    except FileNotFoundError:
        app.logger.error("data.csv file not found")
        raise
    except Exception as e:
        app.logger.error(f"Error loading video mapping: {str(e)}")
        raise
    return mapping


# Load video mapping at startup
mapping = load_video_mapping()


def validate_text(text):
    """Validate input text."""
    if not text:
        return False, "Text cannot be empty"
    if len(text) > MAX_TEXT_LENGTH:
        return (
            False,
            f"Text length exceeds maximum limit of {MAX_TEXT_LENGTH} characters",
        )
    if not all(char in ALLOWED_CHARS for char in text):
        return False, "Text contains invalid characters. Only letters are allowed"
    return True, None


def stitch_videos(video_paths):
    """Stitch multiple videos together."""
    print("Stitching...")
    try:
        # Load all video clips
        clips = []
        for path in video_paths:
            if random.random() < 0.01:
                print(path)
            print("About to get the full path")
            print(f"Trying to load: {full_path}")
            full_path = os.path.abspath(path)
            print(f"Trying to load: {full_path}")
            full_path = path.replace("/videos/videos/", "/videos/", 1)
            print(f"Trying to load: {full_path}")

            print("VideoFiling the clip")
            print(f"Trying to load: {full_path}")
            assert os.path.exists(full_path), f"File does not exist: {full_path}"
            clip = VideoFileClip(full_path)
            clips.append(clip)
        print("Final clip about to be made")
        # Concatenate all clips
        final_clip = concatenate_videoclips(clips)

        # Create a temporary file for the output
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")
        print("Writing")
        # Write the result to the temporary file
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

        # Close all clips to free up resources
        final_clip.close()
        for clip in clips:
            clip.close()

        return output_path
    except Exception as e:
        app.logger.error(f"Error stitching videos: {str(e)}")
        raise


@app.route("/translate", methods=["POST"])
def translate():

    data = request.json
    print(data)
    if not data or "text" not in data:
        print("error: Missing text in JSON payload")
        return jsonify({"error": 'Missing "text" in JSON payload'}), 400

    text = data["text"].upper()
    text = re.sub(r"\s+", "", text)
    # Validate text
    is_valid, error_message = validate_text(text)
    if not is_valid:
        print(f"error: {error_message}")
        return jsonify({"error": error_message}), 400

    try:
        # Get video paths
        video_files = [mapping[char] for char in text if char in mapping]

        # Check if all characters have mappings
        if len(video_files) != len(text):
            missing_chars = set(text) - set(mapping.keys())
            return (
                jsonify(
                    {
                        "error": f"No video mapping for characters: {', '.join(missing_chars)}"
                    }
                ),
                400,
            )
        print("Stithing videos together")
        # Stitch videos together
        stitched_video_path = stitch_videos(video_files)
        print("Stiched videos together")
        # Return the video file
        return send_file(
            stitched_video_path,
            mimetype="video/mp4",
            as_attachment=True,
            download_name="sign_language.mp4",
        )

    except Exception as e:
        app.logger.error(f"Error processing translation request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/video/<filename>")
def serve_video(filename):
    # Secure the filename
    secure_name = secure_filename(filename)
    if secure_name != filename:
        abort(400, description="Invalid filename")

    # Construct full path
    full_path = os.path.join(VIDEO_BASE_PATH, "videos", secure_name)

    if not os.path.exists(full_path):
        abort(404, description="Video not found")

    # Add proper video streaming headers
    response = send_file(
        full_path,
        mimetype="video/mp4",
        as_attachment=False,
        conditional=True,  # Enable conditional responses
    )

    # Add cache control headers
    response.headers["Cache-Control"] = "public, max-age=31536000"  # Cache for 1 year
    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
