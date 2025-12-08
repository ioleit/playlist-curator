import os
import shutil

class VideoCreator:
    def __init__(self, output_dir: str = "data"):
        self.output_dir = output_dir
        
        # Detect ffmpeg binary
        self.ffmpeg_cmd = shutil.which("ffmpeg")
        if not self.ffmpeg_cmd:
            possible_path = "/opt/homebrew/bin/ffmpeg"
            if os.path.exists(possible_path):
                self.ffmpeg_cmd = possible_path
                
        if not self.ffmpeg_cmd:
            print("❌ Error: FFmpeg not found. Please install it (e.g., 'brew install ffmpeg').")

    def create_video(self, audio_path: str, image_path: str = None, output_filename: str = None, use_waveform: bool = False):
        if not self.ffmpeg_cmd:
            return None
            
        if not os.path.exists(audio_path):
            print(f"❌ Error: Audio file not found: {audio_path}")
            return None

        # Determine output path
        if not output_filename:
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            output_filename = f"{base_name}.mp4"
            
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Determine image path
        if not image_path or not os.path.exists(image_path):
            # Try to find a background image if not provided or invalid
            # Check playlist dir (output_dir) first, then global data dir
            bg_playlist = os.path.join(self.output_dir, "background.png")
            bg_data = os.path.join("data", "background.png")
            
            if os.path.exists(bg_playlist):
                image_path = bg_playlist
                use_waveform = True
                print(f"  Using local background.png: {image_path}")
            elif os.path.exists(bg_data):
                image_path = bg_data
                use_waveform = True
                print(f"  Using global background.png: {image_path}")
            else:
                # Fallback to placeholder
                image_path = os.path.join(self.output_dir, "placeholder.jpg")
                if not os.path.exists(image_path):
                    # Try creating placeholder
                    try:
                        from PIL import Image
                        img = Image.new('RGB', (1920, 1080), color = (73, 109, 137))
                        img.save(image_path)
                    except ImportError:
                        print("❌ Error: Pillow library not found. Cannot create placeholder image.")
                        return None
                print(f"  Using placeholder: {image_path}")

        print(f"🎥 Rendering {output_filename}...")
        
        # ffmpeg command
        if use_waveform:
            # Waveform visualization overlay
            # Using 'blend' filter with 'add' or 'screen' mode for true compositing.
            # This makes the black background of the waveform disappear and adds the white waveform to the background image.
            # mode=p2p creates a denser 'filled' look compared to standard lines.
            
            # Ensure background is 1920x1080
            bg_filter = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=gbrp"
            
            cmd = (
                f"{self.ffmpeg_cmd} -y -loop 1 -i '{image_path}' -i '{audio_path}' "
                f"-filter_complex \"[0:v]{bg_filter}[bg];"
                f"[1:a]showwaves=s=1920x1080:mode=p2p:colors=white:scale=sqrt,format=gbrp[wave];"
                f"[bg][wave]blend=all_mode=addition:all_opacity=1.0[out]\" "
                f"-map \"[out]\" -map 1:a "
                f"-c:v libx264 -c:a aac -b:a 192k -pix_fmt yuv420p "
                f"-shortest '{output_path}' > /dev/null 2>&1"
            )
        else:
            # Standard static image
            cmd = (
                f"{self.ffmpeg_cmd} -y -loop 1 -i '{image_path}' -i '{audio_path}' "
                f"-c:v libx264 -c:a aac -b:a 192k -pix_fmt yuv420p "
                f"-vf 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1' "
                f"-shortest '{output_path}' > /dev/null 2>&1"
            )
            
        ret = os.system(cmd)
        
        if ret == 0:
            print(f"✅ Video created: {output_path}")
            return output_path
        else:
            print(f"❌ FFmpeg failed. Command: {cmd}")
            return None

