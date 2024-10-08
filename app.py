# chia chat thành phiên làm việc theo keyword, có lịch sử chat riêng

import os
import time
from dotenv import load_dotenv
from flask import Flask, request, render_template, Response, jsonify, send_file
import requests
from bs4 import BeautifulSoup
import pymysql
import re
import datetime
import pytz
import threading
import json
import google.generativeai as genai
import markdown2

app = Flask(__name__)

# Load environment variables from .env
load_dotenv()

api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)

generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction="You're Jack, a job search assistant. Provide relevant job recommendations based on user preferences (salary, job type, hours, etc.) without repeatedly asking for details. Use the latest knowledge.json data, updated three times per session. Communicate clearly and concisely, keeping responses brief yet informative. When recommending a job, include a brief introduction and a link: <a href='https://www.linkedin.com/jobs/view/job_id' target='_blank'>See details</a>. Ideally, suggest 3-5 jobs per consultation.",
)

# Global variable to store chat sessions
chat_sessions = {}
current_chat_index = 0  # Index for naming chat sessions

# Function to export jobs to a JSON file based on the keyword
def export_jobs_to_file(keyword):
    connection = connect_db()
    try:
        with connection.cursor() as cursor:
            # Select jobs based on keyword
            sql = "SELECT * FROM jobs WHERE LOWER(keyword) = LOWER(%s)"
            cursor.execute(sql, (keyword,))
            jobs = cursor.fetchall()

            # Define the path for the knowledge file
            file_path = "knowledge.json"

            # Convert the datetime objects to strings
            for job in jobs:
                for key, value in job.items():
                    if isinstance(value, datetime.datetime):
                        job[key] = value.strftime('%Y-%m-%d %H:%M:%S')

            # Write the jobs to the knowledge.json file
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(jobs, file, ensure_ascii=False, indent=4)
    finally:
        connection.close()

# Read the content from knowledge.json if it exists
def read_knowledge_file():
    file_path = "knowledge.json"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            file_content = file.read()
        print(f"Loaded knowledge file: {file_content[:100]}...")  # Log for checking
        return file_content
    return ""

# Function to export and update the chat content
def export_and_update_chat():
    global chat_sessions, current_chat_index

    # Tạo tên cho chat session mới
    chat_name = f"chat{current_chat_index}"
    print(f"Creating new chat session: {chat_name}")

    # Tạo chat session mới
    chat_sessions[chat_name] = model.start_chat(
        history=[
            {
                "role": "model",
                "parts": "Hello! I’m Jack, your job search assistant. Tell me about your ideal job—things like salary, job type (full-time, part-time, freelance), working hours, location, and benefits. The more details you provide, the better I can help you find the right match!",
            }
        ]
    )
    
    current_chat_index += 1  # Tăng chỉ số cho phiên chat tiếp theo

    # Log thông tin
    print(f"Chat session {chat_name} created successfully.")
    # print(f"Current chat index: {current_chat_index}")

# Function to continue an existing chat session
def continue_chat_session():
    global chat_sessions, current_chat_index

    # Sử dụng phiên chat hiện tại
    chat_name = f"chat{current_chat_index - 1}"
    print(f"Continuing chat session: {chat_name}")

    if chat_name in chat_sessions:
        # Lưu lại toàn bộ lịch sử chat hiện tại, không bao gồm knowledge cũ
        chat_history = chat_sessions[chat_name].history
        chat_history = [
            {
                "role": entry.role,
                "parts": entry.parts
            } for entry in chat_history
        ]

        # Làm mới nội dung file_content
        file_content = read_knowledge_file()

        # Tạo lại chat với nội dung knowledge mới và lịch sử chat cũ
        chat_sessions[chat_name] = model.start_chat(
            history=chat_history + [
                {
                    "role": "model",
                    "parts": "knowledge.json:",
                },
                {
                    "role": "model",
                    "parts": [file_content],
                },
            ]
        )
        print(f"Updated chat session {chat_name} with new file_content.")
    else:
        print(f"Chat session {chat_name} not found.")

# Khởi tạo chat với nội dung knowledge hiện tại (nếu có) khi trang được tải
export_and_update_chat()

log_messages = []  # Log storage
job_messages = []  # Job storage
reset_flag = threading.Event()  # Flag to reset processing
processing_thread = None  # Current processing thread
retry_count = 0  # Retry count
displayed_job_ids = set()  # Set of displayed job_ids

# Database connection
def connect_db():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        db='gemini_app',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# Send log to client
def send_log(message):
    print(message)  # Print to terminal for checking
    log_messages.append(message)  # Store log in the list

# Send new job info to client
def send_job(job_details):
    job_id = job_details.get('job_id')
    if job_id and job_id not in displayed_job_ids:
        displayed_job_ids.add(job_id)
        job_messages.append(job_details)

# Fetch job_ids based on keyword
def get_job_ids(keyword):
    base_url = "https://www.linkedin.com/jobs/search/"
    params = {
        'currentJobId': '3965318907',
        'f_WT': '2',
        'geoId': '104195383',
        'keywords': keyword,
        'location': 'Vietnam',
        'origin': 'JOB_SEARCH_PAGE_SEARCH_BUTTON',
        'originalSubdomain': 'vn',
        'refresh': 'true',
        'position': '1',
        'pageNum': '0'
    }
    job_ids = set()
    page = 0

    while True:
        if reset_flag.is_set():
            break

        params['pageNum'] = str(page)
        response = requests.get(base_url, params=params)

        if response.status_code != 200:
            send_log(f"Cannot access the website, status code: {response.status_code}")
            break
        
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')

        job_cards = soup.find_all('div', class_='base-card relative w-full hover:no-underline focus:no-underline base-card--link base-search-card base-search-card--link job-search-card')
        
        if not job_cards:
            break

        for job_card in job_cards:
            entity_urn = job_card.get('data-entity-urn')
            if entity_urn and 'jobPosting' in entity_urn:
                job_id = entity_urn.split(':')[-1]
                job_ids.add(job_id)
        
        page += 1

    return list(job_ids)

# Fetch job details by job_id
def get_job_details(job_id):
    if reset_flag.is_set():
        return None

    url = f'https://www.linkedin.com/jobs/view/{job_id}'
    response = requests.get(url)
    job_details = {}

    if response.status_code == 200:
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        show_more_less_div = soup.find('div', class_='show-more-less-html__markup')

        title = soup.find('h1', class_='top-card-layout__title')
        job_details['title'] = title.get_text(strip=True) if title else 'None'

        if job_details['title'] == 'None':
            return None

        job_details['url'] = url

        company_name = soup.find('a', class_='topcard__org-name-link')
        job_details['company_name'] = company_name.get_text(strip=True) if company_name else 'Not found'

        posted_time = soup.find('span', class_='posted-time-ago__text')
        job_details['posted_time'] = posted_time.get_text(strip=True) if posted_time else 'Not found'

        num_applicants = soup.find('span', class_='num-applicants__caption')
        if num_applicants:
            num_applicants_text = num_applicants.get_text(strip=True)
            match = re.search(r'\d+', num_applicants_text)
            job_details['num_applicants'] = match.group(0) if match else '<25'
        else:
            job_details['num_applicants'] = '<25'

        criteria_texts = soup.find_all('span', class_='description__job-criteria-text')
        job_details['seniority_level'] = criteria_texts[0].get_text(strip=True) if len(criteria_texts) > 0 else 'Not found'
        job_details['employment_type'] = criteria_texts[1].get_text(strip=True) if len(criteria_texts) > 1 else 'Not found'
        job_details['job_function'] = criteria_texts[2].get_text(strip=True) if len(criteria_texts) > 2 else 'Not found'
        job_details['industries'] = criteria_texts[3].get_text(strip=True) if len(criteria_texts) > 3 else 'Not found'

        place = soup.find('span', class_='topcard__flavor--bullet')
        job_details['place'] = place.get_text(strip=True) if place else 'None'

        job_details['job_description'] = str(show_more_less_div) if show_more_less_div else 'Not found'

    return job_details

# Save job details to database
def save_job_to_db(job_details, keyword):
    connection = connect_db()
    try:
        with connection.cursor() as cursor:
            check_sql = "SELECT job_id FROM jobs WHERE job_id=%s"
            cursor.execute(check_sql, (job_details.get('job_id'),))
            result = cursor.fetchone()
            if result:
                delete_sql = "DELETE FROM jobs WHERE job_id=%s"
                cursor.execute(delete_sql, (job_details.get('job_id'),))

            sql = """
            INSERT INTO jobs 
            (job_id, title, company_name, posted_time, num_applicants, seniority_level, employment_type, job_function, industries, place, job_description, submit_time, keyword) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                job_details.get('job_id', 'None'),
                job_details.get('title', 'None'),
                job_details.get('company_name', 'None'),
                job_details.get('posted_time', 'None'),
                job_details.get('num_applicants', '<25'),
                job_details.get('seniority_level', 'None'),
                job_details.get('employment_type', 'None'),
                job_details.get('job_function', 'None'),
                job_details.get('industries', 'None'),
                job_details.get('place', 'None'),
                job_details.get('job_description', 'None'),
                job_details.get('submit_time', 'None'),
                keyword
            ))
        connection.commit()
        send_job(job_details)
    finally:
        connection.close()

# Fetch existing jobs from database based on keyword
def get_existing_job_ids_from_db(keyword):
    connection = connect_db()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT job_id FROM jobs WHERE LOWER(keyword) = LOWER(%s)"
            cursor.execute(sql, (keyword,))
            job_ids = [job['job_id'] for job in cursor.fetchall()]
        return job_ids
    finally:
        connection.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    global processing_thread, retry_count, displayed_job_ids, current_keyword
    data = request.get_json()
    keyword = data.get('keyword')

    reset_flag.set()
    if processing_thread is not None:
        processing_thread.join()

    reset_flag.clear()
    log_messages.clear()
    retry_count = 0
    displayed_job_ids.clear()

    # Reset chat history khi tìm kiếm mới
    current_keyword = keyword
    export_and_update_chat()

    def search_and_process_jobs():
        global retry_count

        # Export jobs based on the keyword and update the chatbot content
        export_jobs_to_file(keyword)
        continue_chat_session()

        while retry_count < 10:
            job_ids = get_job_ids(keyword)
            if job_ids:
                send_log(f"Found {len(job_ids)} job ids")
                break
            else:
                retry_count += 1
                send_log(f"No job ids found, retrying {retry_count}")
                # time.sleep(1)

        if not job_ids:
            send_log("No jobs found after 10 attempts.")
            return

        vn_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
        submit_time = datetime.datetime.now(vn_timezone).strftime('%Y-%m-%d %H:%M')

        def process_jobs():
            processed_job_ids = set()

            for index, job_id in enumerate(job_ids, start=1):
                if reset_flag.is_set():
                    send_log("Processing canceled.")
                    break
                send_log(f"Processing job id {index}/{len(job_ids)}: {job_id}")
                job_details = get_job_details(job_id)
                if job_details:
                    job_details['job_id'] = job_id
                    job_details['submit_time'] = submit_time
                    save_job_to_db(job_details, keyword)
                    processed_job_ids.add(job_id)

            send_log("Saved new jobs to the database.")

            # Export and update the chatbot after processing new jobs
            export_jobs_to_file(keyword)
            continue_chat_session()

            existing_job_ids = get_existing_job_ids_from_db(keyword)
            for job_id in existing_job_ids:
                if job_id not in processed_job_ids:
                    job_details = get_job_details(job_id)
                    if job_details:
                        job_details['job_id'] = job_id
                        job_details['submit_time'] = submit_time
                        save_job_to_db(job_details, keyword)
                        send_job(job_details)
                        processed_job_ids.add(job_id)

            # Export and update the chatbot after processing all jobs
            export_jobs_to_file(keyword)
            continue_chat_session()

        process_jobs()

    processing_thread = threading.Thread(target=search_and_process_jobs)
    processing_thread.start()

    return jsonify({"message": "Job processing started."})

@app.route('/download_knowledge')
def download_knowledge():
    file_path = "knowledge.json"
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"message": "File not found"}), 404

@app.route('/send_message', methods=["POST"])
def send_message():
    user_input = request.json.get("message")
    chat_name = f"chat{current_chat_index - 1}"

    if chat_name in chat_sessions:
        response = chat_sessions[chat_name].send_message([user_input])
        markdown_response = markdown2.markdown(response.text)
        return jsonify({"response": markdown_response})
    else:
        return jsonify({"error": "Chat session not found."}), 404

@app.route('/stream')
def stream():
    def event_stream():
        while True:
            if log_messages:
                message = log_messages.pop(0)
                yield f'data: {message}\n\n'
            if job_messages:
                job = job_messages.pop(0)
                yield f'data: new_job:{json.dumps(job, default=str)}\n\n'
            time.sleep(0.1)
    return Response(event_stream(), content_type='text/event-stream')

@app.route('/job/<job_id>')
def job(job_id):
    connection = connect_db()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM jobs WHERE job_id=%s"
            cursor.execute(sql, (job_id,))
            job = cursor.fetchone()
        return jsonify(job)
    finally:
        connection.close()

if __name__ == '__main__':
    app.run(debug=False, use_reloader=False)
