from PIL import Image

# Open your image
image_path = "./image.png"  # Replace with your file path
output_path = "resized_image.jpg"

img = Image.open(image_path)

# Resize the image to 640x360
img_resized = img.resize((640, 360))

# Save the resized image
img_resized.save(output_path)
print("Image resized and saved!")
