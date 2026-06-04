// Smart Resume Analyzer & ATS Score Predictor - Core Frontend JS

document.addEventListener('DOMContentLoaded', function () {
    initDragAndDrop();
    initCharts();
    initRecruiterCompare();
    initAlertAutoDismiss();
    initThemeToggle();
});

// 1. Drag & Drop Upload Zone Setup
function initDragAndDrop() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('resume-file');
    const fileLabel = document.getElementById('file-label-text');
    
    if (!dropZone || !fileInput) return;
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, function (e) {
            e.preventDefault();
            dropZone.classList.add('dragover');
        }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, function (e) {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        }, false);
    });
    
    dropZone.addEventListener('drop', function (e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files;
            updateFileInfo(files[0]);
        }
    });
    
    fileInput.addEventListener('change', function () {
        if (fileInput.files.length > 0) {
            updateFileInfo(fileInput.files[0]);
        }
    });
    
    function updateFileInfo(file) {
        const sizeKB = (file.size / 1024).toFixed(1);
        fileLabel.innerHTML = `<span class="text-secondary font-semibold">${file.name}</span> (${sizeKB} KB)`;
        
        // Dynamic file type icon styling
        const icon = dropZone.querySelector('.fa-cloud-upload-alt');
        if (icon) {
            icon.classList.remove('fa-cloud-upload-alt', 'text-indigo-400');
            icon.classList.add('fa-file-alt', 'text-emerald-400');
        }
    }
}

// 2. Dashboard & Analytics Charts using Chart.js
function initCharts() {
    // A. Gauge Chart (ATS Score)
    const scoreCanvas = document.getElementById('atsScoreGauge');
    if (scoreCanvas) {
        const score = parseFloat(scoreCanvas.dataset.score || 0);
        
        // Color mapping based on score (green, orange, red)
        let mainColor = '#EF4444'; // Red (Error)
        if (score >= 80) mainColor = '#22C55E'; // Green (Success)
        else if (score >= 50) mainColor = '#F59E0B'; // Orange (Warning)
        
        new Chart(scoreCanvas, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [score, 100 - score],
                    backgroundColor: [mainColor, 'rgba(255, 255, 255, 0.05)'],
                    borderWidth: 0,
                    circumference: 180,
                    rotation: 270,
                    cutout: '80%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
    }

    // B. Breakdown Bar Chart
    const breakdownCanvas = document.getElementById('atsBreakdownChart');
    if (breakdownCanvas) {
        const skillsScore = parseFloat(breakdownCanvas.dataset.skills || 0);
        const keywordsScore = parseFloat(breakdownCanvas.dataset.keywords || 0);
        const structureScore = parseFloat(breakdownCanvas.dataset.structure || 0);
        const contactScore = parseFloat(breakdownCanvas.dataset.contact || 0);
        
        new Chart(breakdownCanvas, {
            type: 'bar',
            data: {
                labels: ['Skill Match (60 pts)', 'Keywords (20 pts)', 'Structure (10 pts)', 'Contact (10 pts)'],
                datasets: [{
                    label: 'Points Earned',
                    data: [skillsScore, keywordsScore, structureScore, contactScore],
                    backgroundColor: [
                        'rgba(212, 175, 55, 0.85)',  // Primary Gold
                        'rgba(250, 204, 21, 0.85)',  // Secondary Gold
                        'rgba(229, 231, 235, 0.85)', // Silver (Light)
                        'rgba(156, 163, 175, 0.85)'  // Silver (Medium/Neutral)
                    ],
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#94a3b8' },
                        max: 60
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: '#f8fafc' }
                    }
                }
            }
        });
    }

    // C. Historical ATS score trends
    const historyCanvas = document.getElementById('atsTrendChart');
    if (historyCanvas) {
        const rawData = JSON.parse(historyCanvas.dataset.trend || '[]');
        if (rawData.length > 0) {
            const labels = rawData.map(item => item.date);
            const scores = rawData.map(item => item.score);
            
            new Chart(historyCanvas, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'ATS Match Score %',
                        data: scores,
                        borderColor: '#D4AF37', // Primary Gold
                        backgroundColor: 'rgba(212, 175, 55, 0.05)',
                        borderWidth: 3,
                        pointBackgroundColor: '#FACC15', // Secondary Gold
                        pointBorderColor: '#fff',
                        pointHoverRadius: 7,
                        tension: 0.35,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            ticks: { color: '#94a3b8' }
                        },
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.05)' },
                            ticks: { color: '#94a3b8' },
                            min: 0,
                            max: 100
                        }
                    }
                }
            });
        }
    }

    // D. Skill distribution radar / polar area chart
    const skillDistCanvas = document.getElementById('skillDistributionChart');
    if (skillDistCanvas) {
        const rawDist = JSON.parse(skillDistCanvas.dataset.distribution || '{}');
        const labels = Object.keys(rawDist);
        const data = Object.values(rawDist);
        
        new Chart(skillDistCanvas, {
            type: 'polarArea',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        'rgba(212, 175, 55, 0.65)',  // Primary Gold
                        'rgba(250, 204, 21, 0.65)',  // Secondary Gold
                        'rgba(229, 231, 235, 0.65)', // Light Silver
                        'rgba(156, 163, 175, 0.65)', // Dark Silver/Gray
                        'rgba(180, 150, 50, 0.65)',  // Bronze/Dark Gold
                        'rgba(115, 115, 115, 0.65)'  // Charcoal/Neutral
                    ],
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#94a3b8', font: { size: 10 } }
                    }
                },
                scales: {
                    r: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        angleLines: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { display: false }
                    }
                }
            }
        });
    }
}

// 3. Recruiter Multi-resume Comparison
function initRecruiterCompare() {
    const multiInput = document.getElementById('recruiter-resumes');
    const filesList = document.getElementById('files-list-container');
    
    if (!multiInput || !filesList) return;
    
    multiInput.addEventListener('change', function () {
        filesList.innerHTML = '';
        if (multiInput.files.length > 0) {
            const listGrid = document.createElement('div');
            listGrid.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-3 w-full';
            
            Array.from(multiInput.files).forEach(file => {
                const item = document.createElement('div');
                item.className = 'glass-panel p-3 flex items-center space-x-3 text-sm';
                
                let iconClass = 'fa-file-pdf text-rose-400';
                if (file.name.endsWith('.docx')) {
                    iconClass = 'fa-file-word text-blue-400';
                }
                
                item.innerHTML = `
                    <i class="far ${iconClass} text-2xl"></i>
                    <div class="truncate flex-1">
                        <p class="font-medium text-slate-200 truncate" title="${file.name}">${file.name}</p>
                        <p class="text-xs text-slate-400">${(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                `;
                listGrid.appendChild(item);
            });
            filesList.appendChild(listGrid);
        }
    });
}

// 4. Autohide Flask flash messages after 4 seconds
function initAlertAutoDismiss() {
    const alerts = document.querySelectorAll('.flask-alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(() => {
                alert.remove();
            }, 500);
        }, 4000);
    });
}

// 5. Theme Toggle handler
function initThemeToggle() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    const themeToggleIcon = document.getElementById('theme-toggle-icon');
    
    if (!themeToggleBtn || !themeToggleIcon) return;
    
    // Set initial toggle state icon based on page state
    updateToggleIcon();
    
    themeToggleBtn.addEventListener('click', function () {
        if (document.documentElement.classList.contains('light')) {
            document.documentElement.classList.remove('light');
            document.documentElement.classList.add('dark');
            localStorage.setItem('color-theme', 'dark');
        } else {
            document.documentElement.classList.remove('dark');
            document.documentElement.classList.add('light');
            localStorage.setItem('color-theme', 'light');
        }
        updateToggleIcon();
    });
    
    function updateToggleIcon() {
        if (document.documentElement.classList.contains('light')) {
            themeToggleIcon.classList.remove('fa-sun');
            themeToggleIcon.classList.add('fa-moon');
            themeToggleBtn.title = "Switch to Dark Mode";
        } else {
            themeToggleIcon.classList.remove('fa-moon');
            themeToggleIcon.classList.add('fa-sun');
            themeToggleBtn.title = "Switch to Light Mode";
        }
    }
}

