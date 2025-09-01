document.addEventListener('DOMContentLoaded', function() {
    // --- All of your existing timer and local storage code goes here ---
    // --- (No changes needed in the timer logic) ---

    // --- State Variables ---
    let activeTimer = null;
    let activeTaskId = null;
    let startTime = null;
    let intervalId = null;
    let isPaused = false;
    let pausedDuration = 0;

    // --- Local Storage Management ---
    function loadState() {
        const storedState = JSON.parse(localStorage.getItem('activeTimerState'));
        if (storedState) {
            activeTaskId = storedState.taskId;
            startTime = new Date(storedState.startTime);
            isPaused = storedState.isPaused;
            pausedDuration = storedState.pausedDuration;
            const taskCard = document.querySelector(`.card[data-task-id="${activeTaskId}"]`);
            if (taskCard) {
                if (isPaused) {
                    showPausedState(taskCard);
                } else {
                    startTimer(taskCard, true);
                }
            }
        }
    }

    function saveState() {
        if (!activeTaskId) return;
        const state = {
            taskId: activeTaskId,
            startTime: startTime.toISOString(),
            isPaused: isPaused,
            pausedDuration: pausedDuration
        };
        localStorage.setItem('activeTimerState', JSON.stringify(state));
    }

    function clearState() {
        localStorage.removeItem('activeTimerState');
    }

    // --- Timer Logic Functions ---
    function formatTime(seconds) {
        const h = Math.floor(seconds / 3600).toString().padStart(2, '0');
        const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
        const s = Math.floor(seconds % 60).toString().padStart(2, '0');
        return `${h}:${m}:${s}`;
    }

    function updateTimerDisplay() {
        if (!startTime || !activeTimer || isPaused) return;
        const now = new Date();
        const elapsedSinceStart = Math.floor((now - startTime) / 1000);
        activeTimer.textContent = formatTime(pausedDuration + elapsedSinceStart);
    }

    function startTimer(taskCard, isResuming = false) {
        if (!isResuming) {
            pausedDuration = 0;
        }
        activeTaskId = taskCard.dataset.taskId;
        activeTimer = taskCard.querySelector('.timer-display');
        isPaused = false;
        startTime = new Date();
        document.querySelectorAll('.start-timer-btn').forEach(btn => {
            btn.style.display = 'inline-block';
            btn.textContent = 'Start';
        });
        const startBtn = taskCard.querySelector('.start-timer-btn');
        const stopBtn = taskCard.querySelector('.stop-timer-btn');
        startBtn.textContent = 'Pause';
        stopBtn.style.display = 'inline-block';
        if (intervalId) clearInterval(intervalId);
        intervalId = setInterval(updateTimerDisplay, 1000);
        saveState();
    }
    
    function pauseTimer(taskCard) {
        if (intervalId) clearInterval(intervalId);
        isPaused = true;
        const now = new Date();
        pausedDuration += Math.floor((now - startTime) / 1000);
        showPausedState(taskCard);
        saveState();
    }

    function showPausedState(taskCard) {
        taskCard.querySelector('.timer-display').textContent = formatTime(pausedDuration);
        taskCard.querySelector('.start-timer-btn').textContent = 'Resume';
        taskCard.querySelector('.stop-timer-btn').style.display = 'inline-block';
    }

    // --- Event Listeners ---
    document.querySelectorAll('.start-timer-btn').forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const taskCard = this.closest('.card');
            const currentTaskId = taskCard.dataset.taskId;
            if (activeTaskId && activeTaskId !== currentTaskId) {
                alert('Another task is already running. Please stop it first.');
                return;
            }
            if (this.textContent === 'Start' || this.textContent === 'Resume') {
                startTimer(taskCard, this.textContent === 'Resume');
            } else {
                pauseTimer(taskCard);
            }
        });
    });

    document.querySelectorAll('.stop-timer-btn').forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const taskCard = this.closest('.card');
            const currentTaskId = taskCard.dataset.taskId;
            if (!activeTaskId || activeTaskId !== currentTaskId) return;
            let finalDuration = pausedDuration;
            if (!isPaused) {
                const now = new Date();
                finalDuration += Math.floor((now - startTime) / 1000);
            }
            if (finalDuration > 0) {
                fetch(`/task/log_time/${activeTaskId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ duration: finalDuration }),
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status !== 'success') alert('Error: ' + data.message);
                })
                .catch(error => console.error('Error:', error))
                .finally(() => {
                    clearInterval(intervalId);
                    clearState();
                    window.location.reload();
                });
            } else {
                clearInterval(intervalId);
                clearState();
                window.location.reload();
            }
        });
    });

    // \/\/\/ This is the new function to render the chart \/\/\/
    function renderPerformanceChart() {
        const ctx = document.getElementById('performanceChart');
        if (!ctx) {
            return; // Don't run if the chart canvas isn't on the page
        }

        fetch('/api/chart_data')
            .then(response => response.json())
            .then(chartData => {
                new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: chartData.labels,
                        datasets: [{
                            label: 'Time Spent (in minutes)',
                            data: chartData.data,
                            backgroundColor: 'rgba(0, 123, 255, 0.5)',
                            borderColor: 'rgba(0, 123, 255, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Minutes'
                                }
                            }
                        }
                    }
                });
            })
            .catch(error => console.error('Error fetching chart data:', error));
    }

    // --- Initialize Page ---
    loadState();
    renderPerformanceChart(); // Call the new chart function on page load
});