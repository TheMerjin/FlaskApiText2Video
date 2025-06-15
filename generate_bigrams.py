import os
import csv
import re
from itertools import product
from moviepy import VideoFileClip, concatenate_videoclips

# Constants
BIGRAM_DIR = "bigrams"
DATA_CSV = "data.csv"
os.makedirs(BIGRAM_DIR, exist_ok=True)


# Load mapping from CSV
def load_mapping():
    mapping = {}
    try:
        with open(DATA_CSV, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                letter = row["words"].upper()
                raw_path = row["path"].replace(".pose", ".mp4")

                # Fix the path (from "ase/foo.mp4" to "videos/foo.mp4")
                fixed_path = re.sub(r"[/\\]?ase[/\\]", "videos/", raw_path)
                video_path = fixed_path

                mapping[letter] = video_path
    except FileNotFoundError:
        print("❌ data.csv not found")
        raise
    except Exception as e:
        print(f"❌ Error loading video mapping: {str(e)}")
        raise
    return mapping


def generate_bigrams(mapping):
    from string import ascii_uppercase

    letters = list(ascii_uppercase)

    generated = 0
    skipped = []

    for a, b in product(letters, repeat=2):
        bigram = a + b
        output_path = os.path.join(BIGRAM_DIR, f"{bigram}.mp4")

        if os.path.exists(output_path):
            continue

        if a not in mapping or b not in mapping:
            skipped.append(bigram)
            continue

        try:
            clip1 = VideoFileClip(os.path.abspath(mapping[a]))
            clip2 = VideoFileClip(os.path.abspath(mapping[b]))
            final = concatenate_videoclips([clip1, clip2])
            final.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
            )
            clip1.close()
            clip2.close()
            final.close()
            print(f"✅ Saved: {bigram}.mp4")
            generated += 1
        except Exception as e:
            print(f"❌ Error with {bigram}: {e}")
            skipped.append(bigram)

    print("\n--- DONE ---")
    print(f"Generated {generated} bigrams.")
    if skipped:
        print(
            f"Skipped {len(skipped)} due to missing files or errors: {', '.join(skipped)}"
        )


if __name__ == "__main__":
    mapping = load_mapping()
    generate_bigrams(mapping)
