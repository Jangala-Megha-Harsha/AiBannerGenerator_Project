from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
import os
import requests
import io
import random
import time
from banner_templates import BANNER_TEMPLATES
from config import GEMINI_API_KEY

app = Flask(__name__)
CORS(app)

ADJECTIVES = ["colorful", "minimalist", "vintage", "modern", "artistic", "abstract", "bright", "soft", "dramatic"]
STYLES = ["in bright lighting", "with soft focus", "close-up", "from above", "outdoors", "indoors", "cinematic"]


def generate_gemini_content(theme, product, offer):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [{
            "parts": [{
                "text": f"Create a catchy headline and subheadline for a BigBasket banner. Theme: {theme}, Product: {product}, Offer: {offer}. Format: Headline: [headline] | Subheadline: [subheadline]"
            }]
        }],
        "generationConfig": {
            "temperature": 0.9,
            "topK": 1,
            "topP": 1,
            "maxOutputTokens": 200,
            "stopSequences": []
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        content = result['candidates'][0]['content']['parts'][0]['text'].strip().split('|')
        headline = content[0].split(':')[1].strip()
        subheadline = content[1].split(':')[1].strip()
    except Exception as e:
        print(f"Error with Gemini API: {str(e)}")
        headline = "Grocery Sale"
        subheadline = "Great deals on fresh produce"

    return headline, subheadline


def create_banner(template, headline, subheadline, image_io):
    width, height = template['banner_size']['width'], template['banner_size']['height']
    banner = Image.new("RGB", (width, height), color=hex_to_rgb(template['color_scheme'][0]))
    draw = ImageDraw.Draw(banner)

    # Load custom fonts (ensure these font files exist in your project)
    try:
        headline_font = ImageFont.truetype("static/fonts/OpenSans-Bold.ttf", size=48)
        subheadline_font = ImageFont.truetype("static/fonts/OpenSans-Regular.ttf", size=32)
    except IOError:
        print("Error loading custom fonts. Using default font.")
        headline_font = ImageFont.load_default()
        subheadline_font = ImageFont.load_default()

    # Load and paste the generated image
    if image_io:
        try:
            img = Image.open(image_io)
            img = img.resize((int(width * 0.4), int(height * 0.8)))
            banner.paste(img, (int(width * 0.6), int(height * 0.1)))
        except Exception as e:
            print(f"Error loading generated image: {str(e)}")

    # Draw headline
    draw.text((20, 10), headline, fill=hex_to_rgb(template['color_scheme'][2]), font=headline_font)

    # Draw subheadline
    draw.text((20, 60), subheadline, fill=hex_to_rgb(template['color_scheme'][2]), font=subheadline_font)

    # Draw logo
    try:
        logo = Image.open("static/images/bigbasket_logo.png")
        logo = logo.resize((100, 50))  # Adjust size as needed
        banner.paste(logo, (width - 120, 10), logo if logo.mode == 'RGBA' else None)
    except IOError:
        print("Error loading logo. Skipping logo placement.")

    # Draw CTA
    cta_bbox = subheadline_font.getbbox(template['cta'])
    cta_width = cta_bbox[2] - cta_bbox[0]
    draw.rectangle([20, height - 60, 20 + cta_width + 20, height - 20], fill=hex_to_rgb(template['color_scheme'][1]))
    draw.text((30, height - 55), template['cta'], fill=hex_to_rgb(template['color_scheme'][2]), font=subheadline_font)

    output_path = f"static/output/banner_{template['id']}_{int(time.time())}.jpg"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    banner.save(output_path)
    return output_path


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


@app.route('/')
def home():
    return render_template('index.html', templates=BANNER_TEMPLATES)


def generate_image_stable_diffusion(prompt):
    api_url = "https://api-inference.huggingface.co/models/CompVis/stable-diffusion-v1-4"
    headers = {"Authorization": "Bearer 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"}  # Replace with your API key

    # Generate random temperature and seed
    temperature = random.uniform(0.7, 1.5)  # Temperature range
    seed = random.randint(0, 10000)  # Random seed range

    # Add a random adjective and style to the prompt for variety
    random_adjective = random.choice(ADJECTIVES)
    random_style = random.choice(STYLES)

    # Modify the prompt
    modified_prompt = f"{random_adjective}, {random_style}. {prompt}"

    payload = {
        "inputs": modified_prompt,
        "parameters": {
            "temperature": temperature,
            "seed": seed
        }
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload)

        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            print(f"Response: {response.json()}")
            return None

        content_type = response.headers.get("Content-Type")
        if not content_type.startswith("image/"):
            print(f"Error: Expected an image, but received {content_type}")
            print(f"Response: {response.json()}")
            return None

        # Load the generated image into a PIL Image object
        generated_image = Image.open(io.BytesIO(response.content))

        # Load the logo and paste it onto the generated image
        logo = Image.open("static/images/bigbasket_logo.jpeg")  # Use the correct path
        logo = logo.resize((100, 50))  # Adjust size as needed

        # Paste the logo at the top-left corner of the generated image
        generated_image.paste(logo, (10, 10), logo if logo.mode == 'RGBA' else None)

        # Return the modified image in bytes
        output_io = io.BytesIO()
        generated_image.save(output_io, format='PNG')
        output_io.seek(0)  # Reset stream position
        return output_io  # Return the image with logo added

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None


@app.route('/generate-banner', methods=['POST'])
def generate_banner():
    try:
        data = request.json
        template_id = int(data['template_id'])
        theme = data['theme']
        product = data['product']
        offer = data['offer']

        template = next((t for t in BANNER_TEMPLATES if t['id'] == template_id), None)
        if not template:
            return jsonify({"error": "Template not found"}), 400

        # Generate Gemini content
        headline, subheadline = generate_gemini_content(theme, product, offer)

        # Use the generated headline and subheadline for the image prompt
        image_prompt = f"{headline}. {subheadline}"
        image_io = generate_image_stable_diffusion(image_prompt)  # Use Stable Diffusion instead

        if not image_io:
            return jsonify({"error": "Image generation failed"}), 500

        # Create the banner
        banner_path = create_banner(template, headline, subheadline, image_io)

        return jsonify({
            "banner_url": f"/static/output/banner_{template_id}_{int(time.time())}.jpg",
            "headline": headline,
            "subheadline": subheadline
        })
    except Exception as e:
        print(f"Error generating banner: {str(e)}")
        return jsonify({"error": "An error occurred while generating the banner"}), 500


if __name__ == '__main__':
    app.run(debug=True)