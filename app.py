from flask import Flask, request, render_template, Response, jsonify
import requests
from bs4 import BeautifulSoup
import pymysql
import re
import datetime
import pytz
import time
import threading
import json

app = Flask(__name__)

log_messages = []  # Danh sách lưu trữ log
job_messages = []  # Danh sách lưu trữ các công việc mới
reset_flag = threading.Event()  # Cờ để reset quá trình xử lý
processing_flag = threading.Event()  # Cờ để kiểm soát quá trình xử lý

# Kết nối cơ sở dữ liệu MySQL
def connect_db():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        db='gemini_app',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# Hàm gửi log tới client
def send_log(message):
    print(message)  # In ra terminal để kiểm tra
    log_messages.append(message)  # Lưu log vào danh sách

# Hàm gửi thông tin công việc mới tới client
def send_job(message):
    job_messages.append(message)

# Hàm lấy job_id từ từ khóa
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
    job_ids = set()  # Sử dụng tập hợp để đảm bảo tính duy nhất
    page = 0

    while True:
        if reset_flag.is_set():
            break

        params['pageNum'] = str(page)
        response = requests.get(base_url, params=params)

        if response.status_code != 200:
            send_log(f"Không thể truy cập trang web, mã trạng thái: {response.status_code}")
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
                job_ids.add(job_id)  # Thêm vào tập hợp để đảm bảo tính duy nhất
        
        page += 1

    return list(job_ids)  # Chuyển đổi tập hợp thành danh sách

# Hàm lấy thông tin chi tiết của công việc
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

        # Nếu title là None, bỏ qua job này
        if job_details['title'] == 'None':
            return None

        company_name = soup.find('a', class_='topcard__org-name-link')
        job_details['company_name'] = company_name.get_text(strip=True) if company_name else 'Không tìm thấy tên công ty'

        posted_time = soup.find('span', class_='posted-time-ago__text')
        job_details['posted_time'] = posted_time.get_text(strip=True) if posted_time else 'Không tìm thấy thời gian đăng tin'

        num_applicants = soup.find('span', class_='num-applicants__caption')
        if num_applicants:
            num_applicants_text = num_applicants.get_text(strip=True)
            match = re.search(r'\d+', num_applicants_text)
            job_details['num_applicants'] = match.group(0) if match else '<25'
        else:
            job_details['num_applicants'] = '<25'

        criteria_texts = soup.find_all('span', class_='description__job-criteria-text')
        job_details['seniority_level'] = criteria_texts[0].get_text(strip=True) if len(criteria_texts) > 0 else 'Không tìm thấy seniority level'
        job_details['employment_type'] = criteria_texts[1].get_text(strip=True) if len(criteria_texts) > 1 else 'Không tìm thấy employment type'
        job_details['job_function'] = criteria_texts[2].get_text(strip=True) if len(criteria_texts) > 2 else 'Không tìm thấy job function'
        job_details['industries'] = criteria_texts[3].get_text(strip=True) if len(criteria_texts) > 3 else 'Không tìm thấy industries'

        place = soup.find('span', class_='topcard__flavor--bullet')
        job_details['place'] = place.get_text(strip=True) if place else 'None'

        # Lấy tất cả nội dung HTML bên trong thẻ show_more_less_div
        job_details['job_description'] = str(show_more_less_div) if show_more_less_div else 'Không tìm thấy mô tả công việc'

    return job_details

# Lưu thông tin công việc vào cơ sở dữ liệu
def save_job_to_db(job_details, keyword):
    connection = connect_db()
    try:
        with connection.cursor() as cursor:
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
        send_job(job_details)  # Gửi thông tin công việc mới tới client
    finally:
        connection.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    keyword = data.get('keyword')

    # Dừng quá trình xử lý từ khóa hiện tại nếu có
    reset_flag.set()
    time.sleep(1)  # Đợi một khoảng thời gian ngắn để đảm bảo tất cả các luồng xử lý hiện tại đã dừng

    reset_flag.clear()  # Xóa cờ reset

    # Reset log và công việc hiện tại
    log_messages.clear()
    job_messages.clear()

    job_ids = get_job_ids(keyword)
    send_log(f"Đã lấy được {len(job_ids)} job id")

    vn_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
    submit_time = datetime.datetime.now(vn_timezone).strftime('%Y-%m-%d %H:%M')

    # Bắt đầu xử lý job IDs trong một luồng riêng
    def process_jobs():
        for index, job_id in enumerate(job_ids, start=1):
            if reset_flag.is_set():
                send_log("Quá trình xử lý đã bị hủy.")
                break
            send_log(f"Đang xử lý job id {index}/{len(job_ids)}: {job_id}")
            job_details = get_job_details(job_id)
            if job_details:
                job_details['job_id'] = job_id
                job_details['submit_time'] = submit_time
                save_job_to_db(job_details, keyword)
        send_log("Đã lưu thông tin các công việc vào cơ sở dữ liệu.")

    processing_thread = threading.Thread(target=process_jobs)
    processing_thread.start()

    return jsonify({"message": "Đã bắt đầu xử lý các công việc."})

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
            time.sleep(0.1)  # Giảm thời gian chờ xuống 0.1 giây
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
    app.run(debug=True)
