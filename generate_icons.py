import os
from PIL import Image, ImageDraw

def create_icon(filename, draw_function, size=(24, 24), output_dir=r"C:\Users\Prashanth S\Desktop\new_one\icons"):
    # Create a transparent image
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw_function(draw, size)
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    # Save the icon
    img.save(os.path.join(output_dir, filename), "PNG")

def draw_tag(draw, size):
    w, h = size
    # Draw a tag shape
    draw.polygon([w/4, h/4, 3*w/4, h/4, 3*w/4, 3*h/4, w/4, 3*h/4], outline="gray", width=2)
    draw.ellipse([w/4-3, h/4-3, w/4+3, h/4+3], fill="gray")

def draw_clock(draw, size):
    w, h = size
    # Draw a circle for the clock face
    draw.ellipse([4, 4, w-4, h-4], outline="gray", width=2)
    # Draw clock hands
    draw.line([w/2, h/2, w/2, h/4], fill="gray", width=2)  # Hour hand
    draw.line([w/2, h/2, 3*w/4, h/2], fill="gray", width=2)  # Minute hand

def draw_table(draw, size):
    w, h = size
    # Draw a 2x2 grid
    draw.rectangle([4, 4, w-4, h-4], outline="gray", width=2)
    draw.line([4, h/2, w-4, h/2], fill="gray", width=2)
    draw.line([w/2, 4, w/2, h-4], fill="gray", width=2)

def draw_waveform(draw, size):
    w, h = size
    # Draw a simple waveform
    points = [(x, h/2 + 4 * (1 if x % 8 < 4 else -1)) for x in range(4, w-4, 2)]
    draw.line(points, fill="gray", width=2)

def draw_waterfall(draw, size):
    w, h = size
    # Draw stacked bars
    for y in range(6, h-6, 4):
        draw.rectangle([4, y, w-4, y+2], fill="gray")

def draw_orbit(draw, size):
    w, h = size
    # Draw a planet with an orbit path
    draw.ellipse([w/2-6, h/2-6, w/2+6, h/2+6], outline="gray", width=2)  # Orbit path
    draw.ellipse([w/2-2, h/2-2, w/2+2, h/2+2], fill="gray")  # Planet

def draw_trend(draw, size):
    w, h = size
    # Draw an upward trend line
    draw.line([4, h-4, w-4, 4], fill="gray", width=2)

def draw_multi_trend(draw, size):
    w, h = size
    # Draw two trend lines
    draw.line([4, h-4, w-4, 4], fill="gray", width=2)
    draw.line([4, h-8, w-4, 8], fill="gray", width=2)

def draw_bode(draw, size):
    w, h = size
    # Draw a frequency graph (axes with a curve)
    draw.line([4, h-4, w-4, h-4], fill="gray", width=2)  # X-axis
    draw.line([4, h-4, 4, 4], fill="gray", width=2)  # Y-axis
    points = [(x, h/2 + 3 * (1 if x % 8 < 4 else -1)) for x in range(4, w-4, 2)]
    draw.line(points, fill="gray", width=2)

def draw_history(draw, size):
    w, h = size
    # Draw a timeline with dots
    draw.line([4, h/2, w-4, h/2], fill="gray", width=2)
    for x in range(8, w-8, 6):
        draw.ellipse([x-2, h/2-2, x+2, h/2+2], fill="gray")

def draw_report_time(draw, size):
    w, h = size
    # Draw a document with a small clock
    draw.rectangle([6, 4, w-6, h-4], outline="gray", width=2)
    draw.line([6, 4, 8, 6], fill="gray", width=2)  # Folded corner
    draw.ellipse([w/2-4, h/2-4, w/2+4, h/2+4], outline="gray", width=2)  # Clock
    draw.line([w/2, h/2, w/2, h/2-2], fill="gray", width=1)  # Hour hand

def draw_report(draw, size):
    w, h = size
    # Draw a document
    draw.rectangle([6, 4, w-6, h-4], outline="gray", width=2)
    draw.line([6, 4, 8, 6], fill="gray", width=2)  # Folded corner
    for y in range(8, h-8, 4):
        draw.line([8, y, w-8, y], fill="gray", width=1)  # Text lines

# Generate all icons
icon_functions = [
    # ("tag.png", draw_tag),
    ("clock.png", draw_clock),
    ("table.png", draw_table),
    ("waveform.png", draw_waveform),
    ("waterfall.png", draw_waterfall),
    ("orbit.png", draw_orbit),
    ("trend.png", draw_trend),
    ("multi-trend.png", draw_multi_trend),
    ("bode.png", draw_bode),
    ("history.png", draw_history),
    ("report-time.png", draw_report_time),
    ("report.png", draw_report),
]

for filename, draw_func in icon_functions:
    create_icon(filename, draw_func)

print("Icons generated successfully in 'C:\\Users\\Prashanth S\\Desktop\\new_one\\icons'.")