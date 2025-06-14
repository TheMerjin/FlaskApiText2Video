import os
from pose_format import Pose
from pose_format.pose_visualizer import PoseVisualizer

# Input and output directories
input_dir = "ase"
output_dir = "videos"
os.makedirs(output_dir, exist_ok=True)

# Loop through all .pose files in the input directory
for filename in os.listdir(input_dir):
    if filename.endswith(".pose"):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename.replace(".pose", ".mp4"))

        try:
            print(f"Converting {filename} to mp4...")

            # Load the pose
            with open(input_path, "rb") as f:
                pose = Pose.read(f.read())

            # Visualize and save the video
            visualizer = PoseVisualizer(pose)
            visualizer.save_video(
                output_path,
                visualizer.draw(),
                custom_ffmpeg=r"C:\Users\Sreek\ffmpeg\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe",
            )

            print(f"Saved to {output_path}")
        except Exception as e:
            print(f"Failed to convert {filename}: {e}")
