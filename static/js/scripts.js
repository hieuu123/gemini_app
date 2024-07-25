document.addEventListener('DOMContentLoaded', (event) => {
    var eventSource = new EventSource('/stream');
    var totalJobs = 0;
    var currentJob = 0;
    var retryCount = 0;  // Biến đếm số lần retry

    eventSource.onmessage = function(event) {
        var log = document.getElementById('log');
        var newLog = document.createElement('p');

        // Update total job IDs
        if (event.data.includes("Đã lấy được")) {
            totalJobs = parseInt(event.data.split(" ")[3]);
            newLog.textContent = `Đã lấy được ${totalJobs} job id`;
            log.appendChild(newLog);
            log.scrollTop = log.scrollHeight;

            // Nếu không tìm được job id nào, tự động gửi lại form sau 1 giây
            if (totalJobs === 0 && retryCount < 3) {  // Giới hạn số lần retry
                retryCount++;
                setTimeout(() => {
                    form.onsubmit();
                }, 1000);  // 1 giây
            } else {
                retryCount = 0;  // Reset biến đếm nếu tìm được job hoặc đã retry đủ số lần
            }
        }

        // Update job processing status
        else if (event.data.includes("Đang xử lý job id")) {
            var match = event.data.match(/Đang xử lý job id (\d+)\/(\d+): (\d+)/);
            if (match) {
                currentJob = parseInt(match[1]);
                totalJobs = parseInt(match[2]);
                var jobId = match[3];
                newLog.textContent = `Đang xử lý job id ${currentJob}/${totalJobs}: ${jobId}`;
                log.appendChild(newLog);
                log.scrollTop = log.scrollHeight;
            }
        }

        // Handle new job data
        else if (event.data.startsWith("new_job:")) {
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
        }

        // Log other messages
        else {
            newLog.textContent = event.data;
            log.appendChild(newLog);
            log.scrollTop = log.scrollHeight;
        }
    };

    var form = document.getElementById('job-form');
    form.onsubmit = function(e) {
        if (e) e.preventDefault(); // Kiểm tra xem có sự kiện e hay không
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
            retryCount = 0;  // Reset biến đếm khi gửi yêu cầu mới
        });
    };

    function fetchJobDetails(jobId) {
        fetch(`/job/${jobId}`)
        .then(response => response.json())
        .then(data => {
            if (data) {
                var jobDetails = document.getElementById('job-details');
                jobDetails.innerHTML = `<h2>${data.title}</h2>
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
