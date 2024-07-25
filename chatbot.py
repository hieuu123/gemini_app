"""
Install the Google AI Python SDK

$ pip install google-generativeai
$ pip install pillow

See the getting started guide for more information:
https://ai.google.dev/gemini-api/docs/get-started/python
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai
import requests
from PIL import Image
from io import BytesIO

# Load API key from .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Configure the Gemini API with the API key
genai.configure(api_key=api_key)

# Function to describe image using Gemini API
def describe_image(image_url):
    # Download the image from the URL
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    
    # Create the model
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Generate content with the image
    response = model.generate_content([img], stream=True)
    
    # Collect the response text
    description = ""
    for chunk in response:
        description += chunk.text
    
    return description

# URL of the image to describe
image_url = "https://ai.google.dev/static/gemini-api/docs/get-started/python_files/output_CjnS0vNTsVis_0.png"

# Get the description of the image
description = describe_image(image_url)

# Print the description
print(description)