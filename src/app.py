import os
import uuid
import openai
import requests
import cloudinary
import cloudinary.uploader
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# Temporary in-memory store for event data
event_store = {}

@app.route('/generate-thumbnail', methods=['POST'])
def generate_thumbnail():
    data = request.json
    occasion = data.get("keyword", "").lower()
    name = data.get("recipient_name", None)

    # Prompt generation
    if name:
        prompt = f"A joyful and vibrant thumbnail for a {occasion} celebration, featuring themed decorations and the personalized message 'Happy {occasion.capitalize()}, {name}'"
    else:
        prompt = f"A high-quality thumbnail for a video about {occasion}, cinematic and visually appealing."

    try:
        # Generate image using OpenAI
        response = openai.Image.create(
            prompt=prompt,
            model="dall-e-3",
            size="1024x1024",
            n=1
        )

        image_url = response["data"][0]["url"]
        image_data = requests.get(image_url).content

        filename = f"{uuid.uuid4()}.jpg"
        with open(filename, "wb") as f:
            f.write(image_data)

        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(filename, format="jpg")
        cloudinary_url = upload_result.get("secure_url")
        os.remove(filename)

        # Generate unique shareable URL
        event_id = str(uuid.uuid4())
        event_store[event_id] = {
            "image_url": cloudinary_url,
            "title": f"{occasion.capitalize()} Message",
            "description": f"A special message for {name or 'you'}!",
            "share_url": f"https://yourdomain.com/share/{event_id}"
        }

        whatsapp_link = f"https://wa.me/?text=Check this out! {event_store[event_id]['share_url']}"

        return jsonify({
            "image": cloudinary_url,
            "share_url": event_store[event_id]["share_url"],
            "whatsapp_link": whatsapp_link,
            "message": "Thumbnail generated successfully",
            "status": 200
        })

    except Exception as e:
        return jsonify({"error": str(e), "message": "Failed to generate thumbnail", "status": 500})


@app.route('/share/<event_id>')
def share_page(event_id):
    event = event_store.get(event_id)
    if not event:
        return "Invalid or expired link", 404

    return render_template("share.html", **event)


if __name__ == '__main__':
    app.run(debug=True)
