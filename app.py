from flask import Flask, request, jsonify, send_file, abort
import os
import csv
import re
from moviepy import VideoFileClip, concatenate_videoclips
import tempfile
from werkzeug.utils import secure_filename
import uuid
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

                # Fix the doubling issue, replace 'ase/' or 'ase\' with 'videos/'
                fixed_path = re.sub(r"[/\\]?ase[/\\]", "videos/", raw_path)

                video_path = fixed_path
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


def stitch_videos_from_text(text, mapping):
    clips = []
    i = 0
    while i < len(text):
        # Try to use bigram first
        if i + 1 < len(text):
            bigram = text[i] + text[i + 1]
            bigram_path = os.path.join("bigrams", f"{bigram}.mp4")
            if os.path.exists(bigram_path):
                clips.append(VideoFileClip(os.path.abspath(bigram_path)))
                i += 2
                continue
        # Fallback to single character video
        char = text[i]
        if char not in mapping:
            raise ValueError(f"No video found for character: {char}")
        path = os.path.abspath(mapping[char])
        if not os.path.exists(path):
            raise ValueError(f"Video file not found: {path}")
        clips.append(VideoFileClip(path))
        i += 1

    final_clip = concatenate_videoclips(clips)
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp4")
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

    final_clip.close()
    for clip in clips:
        clip.close()

    return output_path


import string


@app.route("/translate", methods=["POST"])
def translate():
    data = request.json
    if not data or "text" not in data:
        return jsonify({"error": 'Missing "text" in JSON payload'}), 400

    text = data["text"].upper()
    # Remove all whitespace and punctuation — keep only letters A-Z
    text = re.sub(r"[^A-Z]", "", text)

    is_valid, error_message = validate_text(text)
    if not is_valid:
        return jsonify({"error": error_message}), 400

    try:
        stitched_video_path = stitch_videos_from_text(text, mapping)
        return send_file(
            stitched_video_path,
            mimetype="video/mp4",
            as_attachment=True,
            download_name="sign_language.mp4",
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Error processing translation request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/video/<filename>")
def serve_video(filename):
    secure_name = secure_filename(filename)
    if secure_name != filename:
        abort(400, description="Invalid filename")

    full_path = os.path.join(VIDEO_BASE_PATH, "videos", secure_name)
    if not os.path.exists(full_path):
        abort(404, description="Video not found")

    response = send_file(
        full_path,
        mimetype="video/mp4",
        as_attachment=False,
        conditional=True,
    )
    response.headers["Cache-Control"] = "public, max-age=31536000"  # Cache 1 year
    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
