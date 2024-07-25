document.addEventListener('DOMContentLoaded', (event) => {
    var eventSource = new EventSource('/stream');
    var totalJobs = 0;
    var currentJob = 0;
    var retryCount = 0;  // Biến đếm số lần retry

    eventSource.onmessage = function(event) {
        var log = document.getElementById('log');
        var newLog = document.createElement('p');

        // Update total job IDs
        if (event.data.includes("Đã lấy được") || event.data.includes("Không tìm thấy job id nào")) {
            var parts = event.data.split(" ");
            if (parts[2] === "lấy") {
                totalJobs = parseInt(parts[3]);
            } else {
                retryCount++;
                if (retryCount >= 3) {
                    retryCount = 0;
                }
            }
            newLog.textContent = event.data;
            log.appendChild(newLog);
            log.scrollTop = log.scrollHeight;

        // Update job processing status
        } else if (event.data.includes("Đang xử lý job id")) {
            var match = event.data.match(/Đang xử lý job id (\d+)\/(\d+): (\d+)/);
            if (match) {
                currentJob = parseInt(match[1]);
                totalJobs = parseInt(match[2]);
                var jobId = match[3];
                newLog.textContent = `Đang xử lý job id ${currentJob}/${totalJobs}: ${jobId}`;
                log.appendChild(newLog);
                log.scrollTop = log.scrollHeight;
            }
        } else {
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
            currentJob = 0;
            totalJobs = 0;
            retryCount = 0;  // Reset biến đếm khi gửi yêu cầu mới
        });
    };

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
