document.addEventListener('DOMContentLoaded', (event) => {
    var eventSource = new EventSource('/stream');
    var totalJobs = 0;
    var currentJob = 0;
    var retryCount = 0;
    var ellipsisInterval; // Biến để lưu khoảng thời gian của hiệu ứng
    var currentChatIndex = 0; // Biến để theo dõi chỉ số chat hiện tại

    eventSource.onmessage = function(event) {
        var log = document.getElementById('log');
        var newLog = document.createElement('p');

        if (event.data.startsWith("new_job:")) {
            var job = JSON.parse(event.data.replace("new_job:", ""));
            var jobList = document.getElementById('job-list');
            var jobItem = document.createElement('div');
            jobItem.className = 'job-item';
            jobItem.dataset.jobId = job.job_id;
            jobItem.innerHTML = `<strong>${job.title}</strong><br>${job.company_name}<br>${job.place}<br>${job.posted_time}`;
            jobItem.onclick = function() {
                fetchJobDetails(job.job_id);
                selectJobItem(jobItem);
            };
            jobList.appendChild(jobItem);
        } else {
            newLog.textContent = event.data;
            log.appendChild(newLog);
            log.scrollTop = log.scrollHeight;
        }
    };

    var form = document.getElementById('job-form');
    form.onsubmit = function(e) {
        if (e) e.preventDefault();
        var keyword = form.querySelector('input[name="keyword"]').value;
        fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ keyword: keyword })
        })
        .then(response => response.json())
        .then(data => {
            var log = document.getElementById('log');
            log.innerHTML = '';
            var jobList = document.getElementById('job-list');
            jobList.innerHTML = '';
            var jobDetails = document.getElementById('job-details');
            jobDetails.innerHTML = '';
            currentJob = 0;
            totalJobs = 0;
            retryCount = 0;

            clearInterval(ellipsisInterval); // Dừng hiệu ứng trước khi bắt đầu một cái mới
            var chatbox = document.getElementById('chatbox-container');
            if (chatbox.style.display === 'none' || chatbox.style.display === '') {
                toggleChatbox();  // Mở chatbot nếu chưa mở
            }

            // Gửi tin nhắn "Processing your request..."
            appendMessage('Chatbot', '<i id="processing-message">Processing your request...</i><br><br>');

            // Nếu đang làm việc với chat1, gửi thêm tin nhắn "Hello there!"
            if (currentChatIndex === 0) {
                setTimeout(() => {
                    appendMessage('Chatbot', 'Hello! I’m Jack, your job search assistant. Tell me about your ideal job—things like salary, job type (full-time, part-time, freelance), working hours, location, and benefits. The more details you provide, the better I can help you find the right match!<br><br>');
                }, 1000);
            }

            currentChatIndex++; // Tăng chỉ số chat hiện tại
        });
    };

    function fetchJobDetails(jobId) {
        clearInterval(ellipsisInterval); // Dừng hiệu ứng chấm lửng khi công việc hoàn thành
        fetch(`/job/${jobId}`)
        .then(response => response.json())
        .then(data => {
            if (data && data.job_id) {
                var jobDetails = document.getElementById('job-details');
                jobDetails.innerHTML = `<a href="https://www.linkedin.com/jobs/view/${data.job_id}" target="_blank">View Job on LinkedIn</a>
                                        <h2>${data.title}</h2>
                                        <p><strong>Company:</strong> ${data.company_name}</p>
                                        <p><strong>Location:</strong> ${data.place}</p>
                                        <p><strong>Posted:</strong> ${data.posted_time}</p>
                                        <p><strong>Number of Applicants:</strong> ${data.num_applicants}</p>
                                        <p><strong>Seniority Level:</strong> ${data.seniority_level}</p>
                                        <p><strong>Employment Type:</strong> ${data.employment_type}</p>
                                        <p><strong>Job Function:</strong> ${data.job_function}</p>
                                        <p><strong>Industries:</strong> ${data.industries}</p>
                                        <p><strong>Description:</strong></p>
                                        <div>${data.job_description}</div>`;
            } else {
                console.error(`Job details for job id ${jobId} not found.`);
            }
        })
        .catch(error => {
            console.error('Error fetching job details:', error);
        });
    }

    function selectJobItem(jobItem) {
        var jobItems = document.querySelectorAll('.job-item');
        jobItems.forEach(item => item.classList.remove('selected'));
        jobItem.classList.add('selected');
    }

    var toggleButton = document.getElementById('toggle-log');
    toggleButton.onclick = function() {
        var logContainer = document.getElementById('log-container');
        if (logContainer.style.display === 'none') {
            logContainer.style.display = 'block';
        } else {
            logContainer.style.display = 'none';
        }
    };
});
