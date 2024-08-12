Gemini Job Finder

Gemini Job Finder is a job search assistant application that uses the Gemini API to provide relevant job recommendations based on user preferences. The app interacts with LinkedIn to fetch job listings and uses a chatbot named Jack to assist users in finding the right job.

Features

Interactive Chatbot: Jack assists users in finding jobs by taking input on job preferences such as salary, job type, location, and more.

Job Recommendations: The app fetches job listings from LinkedIn based on the user's keyword and provides detailed job information.

Database Integration: Job details are stored in a MySQL database for easy access and retrieval.
Responsive Design: The application is designed with Bootstrap to ensure a clean, user-friendly interface.

Getting Started

Prerequisites

Python 3.x
MySQL Database (phpMyAdmin recommended)
Required Python libraries (listed in requirements.txt)
Installation

Clone the repository:
git clone https://github.com/hieuu123/gemini_app

Environment Variables:

Create a .env file in the root directory and add your Gemini API key:
API_KEY="your_gemini_api_key_here"

Run the application:

Start the Flask app:

python app.py

Access the application:

Open your web browser and go to http://localhost:5000.

Usage

Search for Jobs:

Enter a job-related keyword in the search bar.
Chatbot Jack will guide you through the job search process.

View Job Details:

Click on any job listing to see more details and a link to the original LinkedIn posting.
How It Works
The app fetches job IDs from LinkedIn based on the keyword entered by the user.
Job details are retrieved and stored in a MySQL database.
Chatbot Jack uses the Gemini API to assist users with job recommendations and general guidance during the job search process.

Testing

To test the application:

Connect to the MySQL database (using phpMyAdmin or another MySQL interface).
Run app.py in your terminal.
Open the web app in your browser and enter a job keyword.
Let chatbot Jack assist you in finding the right job!
Google Developer Tools Used
Gemini API: For interactive chatbot functionality.
Web/Chrome: For building and running the web application.

Contributing
Feel free to fork this project, make improvements, and submit a pull request. Contributions are welcome!