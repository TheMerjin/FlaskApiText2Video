from flask import Flask, request, jsonify, send_file, abort, Response
import os
import csv
from functools import lru_cache
from werkzeug.utils import secure_filename
import re

app = Flask(__name__)

# Constants
VIDEO_BASE_PATH = os.path.abspath('')
MAX_TEXT_LENGTH = 100  # Maximum allowed text length
ALLOWED_CHARS = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ')  # Allowed characters

def load_video_mapping():
    """Load video mapping from CSV file."""
    mapping = {}
    try:
        with open("data.csv", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                letter = row["words"].upper()
                video_path = row["path"].replace(".pose", ".mp4")
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
        return False, f"Text length exceeds maximum limit of {MAX_TEXT_LENGTH} characters"
    if not all(char in ALLOWED_CHARS for char in text):
        return False, "Text contains invalid characters. Only letters and spaces are allowed"
    return True, None

@lru_cache(maxsize=100)
def get_video_paths(text):
    """Get video paths for text with caching."""
    return [mapping[char] for char in text if char in mapping]

@app.route("/translate", methods=["POST"])
def translate():
    data = request.json
    if not data or "text" not in data:
        return jsonify({"error": 'Missing "text" in JSON payload'}), 400

    text = data["text"].upper()
    
    # Validate text
    is_valid, error_message = validate_text(text)
    if not is_valid:
        return jsonify({"error": error_message}), 400

    try:
        # Get video paths with caching
        video_files = get_video_paths(text)
        
        # Check if all characters have mappings
        if len(video_files) != len(text):
            missing_chars = set(text) - set(mapping.keys())
            return jsonify({"error": f"No video mapping for characters: {', '.join(missing_chars)}"}), 400

        # Generate video URLs
        video_urls = [f"/video/{os.path.basename(path)}" for path in video_files]
        return jsonify({"videos": video_urls})

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
    full_path = os.path.join(VIDEO_BASE_PATH, "ase", secure_name)
    
    if not os.path.exists(full_path):
        abort(404, description="Video not found")

    # Add proper video streaming headers
    response = send_file(
        full_path,
        mimetype="video/mp4",
        as_attachment=False,
        conditional=True  # Enable conditional responses
    )
    
    # Add cache control headers
    response.headers['Cache-Control'] = 'public, max-age=31536000'  # Cache for 1 year
    return response

if __name__ == "__main__":
    app.run(debug=True)
