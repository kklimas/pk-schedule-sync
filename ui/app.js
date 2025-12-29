const API_BASE = '/api/v1';

let currentPage = 1;
const pageSize = 5;

// Utility to format dates to local browser timezone
function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    // Ensure the date string is treated as UTC if it doesn't have a timezone
    const utcDateStr = dateStr.endsWith('Z') ? dateStr : dateStr + 'Z';
    const date = new Date(utcDateStr);
    return date.toLocaleString();
}

// Fetch Lectures
async function fetchLectures(page = 1) {
    try {
        const response = await fetch(`${API_BASE}/lectures/?page=${page}&size=${pageSize}`);
        const data = await response.json();
        renderLectures(data.items);
        updatePagination(data.page, data.total, data.size);
    } catch (error) {
        console.error('Error fetching lectures:', error);
        document.getElementById('lectureList').innerHTML = '<div class="card">Error loading lectures.</div>';
    }
}

// Render Lectures
function renderLectures(lectures) {
    const list = document.getElementById('lectureList');
    if (lectures.length === 0) {
        list.innerHTML = '<div class="card" style="text-align: center;">No upcoming lectures found.</div>';
        return;
    }

    list.innerHTML = lectures.map((lecture, index) => `
        <div class="card lecture-card" style="animation-delay: ${index * 0.05}s">
            <div class="lecture-time">
                <span class="time-start">${lecture.start_time}</span>
                <span class="time-end">${lecture.end_time}</span>
                <span style="font-size: 0.75rem; margin-top: 0.5rem; color: var(--accent-primary)">${lecture.date}</span>
            </div>
            <div class="lecture-info">
                <h3>${lecture.subject || lecture.summary}</h3>
                <div class="lecture-meta">
                    <span>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
                        ${lecture.teacher || 'Unknown Teacher'}
                    </span>
                    <span>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
                        ${lecture.room || 'No Room'}
                    </span>
                    <span>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>
                        ${lecture.type || 'Lecture'}
                    </span>
                </div>
            </div>
            <div class="lecture-status">
                 <!-- Tooltip or badge for last sync if needed -->
            </div>
        </div>
    `).join('');
}

// Fetch Sync History (Jobs)
async function fetchJobs() {
    try {
        const response = await fetch(`${API_BASE}/jobs/?page=1&size=5`);
        const data = await response.json();
        renderJobs(data.items);
    } catch (error) {
        console.error('Error fetching jobs:', error);
        document.getElementById('jobList').innerHTML = '<div class="card">Error loading history.</div>';
    }
}

// Render Jobs
function renderJobs(jobs) {
    const list = document.getElementById('jobList');
    list.innerHTML = jobs.map(job => `
        <div class="card job-card">
            <div class="job-header">
                <span style="font-weight: 600;">Job #${job.job_id.slice(0, 8)}</span>
                <span class="status-badge status-${job.status.toLowerCase()}">${job.status}</span>
            </div>
            <div style="color: var(--text-muted); font-size: 0.8rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between;">
                <span>${formatDate(job.started_at)}</span>
                <span style="font-style: italic; opacity: 0.8;">via ${job.triggered_by}</span>
            </div>
            <div style="font-size: 0.85rem; margin-bottom: 0.5rem;">${job.message || 'Processing...'}</div>
            ${job.sheet_url ? `
                <a href="${job.sheet_url}" target="_blank" class="download-link">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                    Download Excel
                </a>
            ` : ''}
        </div>
    `).join('');
}

// Pagination Logic
function updatePagination(page, total, size) {
    currentPage = page;
    const totalPages = Math.ceil(total / size);
    document.getElementById('pageInfo').innerText = `Page ${page} of ${totalPages || 1}`;
    document.getElementById('prevPage').disabled = page <= 1;
    document.getElementById('nextPage').disabled = page >= totalPages;
}

// Trigger Sync
async function triggerSync() {
    const btn = document.getElementById('syncNowBtn');
    const originalText = btn.innerHTML;

    try {
        btn.disabled = true;
        btn.innerHTML = 'Triggering...';

        const response = await fetch(`${API_BASE}/jobs/`, { method: 'POST' });
        if (response.ok) {
            alert('Synchronization job triggered! Please wait for it to complete.');
            fetchJobs(); // Refresh job list
        } else {
            alert('Failed to trigger synchronization.');
        }
    } catch (error) {
        alert('Error communicating with server.');
    } finally {
        setTimeout(() => {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }, 1000);
    }
}

// Event Listeners
document.getElementById('syncNowBtn').addEventListener('click', triggerSync);
document.getElementById('prevPage').addEventListener('click', () => {
    if (currentPage > 1) fetchLectures(currentPage - 1);
});
document.getElementById('nextPage').addEventListener('click', () => {
    fetchLectures(currentPage + 1);
});

// Initial Load
fetchLectures();
fetchJobs();

// Auto-refresh jobs every 30s
setInterval(fetchLectures, 30000);
setInterval(fetchJobs, 30000);
