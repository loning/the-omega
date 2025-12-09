import sys
from PIL import Image

def crop_center(image_path, target_width, target_height):
    try:
        img = Image.open(image_path)
        width, height = img.size
        
        left = (width - target_width) / 2
        top = (height - target_height) / 2
        right = (width + target_width) / 2
        bottom = (height + target_height) / 2

        img_cropped = img.crop((left, top, right, bottom))
        img_cropped.save(image_path)
        print(f"Successfully cropped {image_path} to {target_width}x{target_height}")
    except Exception as e:
        print(f"Error cropping image: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 crop_cover.py <image_path> <target_width> <target_height>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    target_width = int(sys.argv[2])
    target_height = int(sys.argv[3])
    
    crop_center(image_path, target_width, target_height)
