document.addEventListener('DOMContentLoaded', () => {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
    const themeToggle = document.getElementById('themeToggle');
    const themeMenu = document.getElementById('themeMenu');
    const THEME_KEY = 'cybertest-theme';

    function applyTheme(mode) {
        document.documentElement.dataset.theme = mode;
    }

    function getInitialTheme() {
        const stored = localStorage.getItem(THEME_KEY);
        if (stored) return stored;
        return prefersDark.matches ? 'dark' : 'light';
    }

    function syncTheme(mode) {
        const value = mode === 'system' ? (prefersDark.matches ? 'dark' : 'light') : mode;
        applyTheme(value);
        localStorage.setItem(THEME_KEY, mode);
    }

    const initial = getInitialTheme();
    syncTheme(initial);

    if (themeToggle && themeMenu) {
        const closeThemeMenu = (focusToggle = false) => {
            themeMenu.hidden = true;
            themeToggle.setAttribute('aria-expanded', 'false');
            if (focusToggle) themeToggle.focus();
        };

        const openThemeMenu = () => {
            themeMenu.hidden = false;
            themeToggle.setAttribute('aria-expanded', 'true');
            requestAnimationFrame(() => {
                themeMenu.querySelector('button')?.focus();
            });
        };

        themeToggle.addEventListener('click', () => {
            const expanded = themeToggle.getAttribute('aria-expanded') === 'true';
            if (expanded) {
                closeThemeMenu();
            } else {
                openThemeMenu();
            }
        });

        themeToggle.addEventListener('keydown', (ev) => {
            if (ev.key === 'Escape') closeThemeMenu(true);
        });

        themeMenu.querySelectorAll('button[data-theme]').forEach(btn => {
            btn.addEventListener('click', () => {
                const mode = btn.dataset.theme || 'system';
                syncTheme(mode);
                closeThemeMenu(true);
            });
        });

        themeMenu.addEventListener('keydown', (ev) => {
            if (ev.key === 'Escape') {
                ev.preventDefault();
                closeThemeMenu(true);
            }
        });

        themeMenu.addEventListener('focusout', (ev) => {
            const nextTarget = ev.relatedTarget;
            if (!themeMenu.hidden && (!nextTarget || (!themeMenu.contains(nextTarget) && nextTarget !== themeToggle))) {
                closeThemeMenu();
            }
        });

        document.addEventListener('click', (ev) => {
            if (!themeMenu.hidden && !themeMenu.contains(ev.target) && ev.target !== themeToggle) {
                closeThemeMenu();
            }
        });
    }

    prefersDark.addEventListener('change', () => {
        const stored = localStorage.getItem(THEME_KEY);
        if (stored === 'system' || !stored) syncTheme('system');
    });
    // Enable continue button if exam in session (if present)
    fetch('/exam_status')
        .then(res => res.json())
        .then(data => {
            const cont = document.querySelector('.continue-button');
            if (cont && data.active) cont.disabled = false;
        })
        .catch(() => {});

    // Setup form validation and simple version selection visuals
    const setupForm = document.querySelector('.exam-setup-form');
    if (setupForm) {
        const versionInputs = setupForm.querySelectorAll('input[name="version"]');
        const versionLabels = setupForm.querySelectorAll('.version-group .version-pill');
        const versionToggle = setupForm.querySelector('.version-toggle');
        const versionGroup = setupForm.querySelector('.version-group');
        const startBtn = document.getElementById('startExamBtn');

        function updateVersionVisuals() {
            versionLabels.forEach(lbl => {
                const id = lbl.getAttribute('for');
                const inp = id ? document.getElementById(id) : lbl.previousElementSibling;
                if (inp && inp.checked) lbl.classList.add('selected'); else lbl.classList.remove('selected');
            });
        }

        versionInputs.forEach(inp => inp.addEventListener('change', updateVersionVisuals));

        // enable start button when a version is selected and update toggle text
        function onVersionSelected(ev) {
            const inp = ev.target || ev;
            if (!inp) return;
            // update toggle text to show chosen version
            const lbl = setupForm.querySelector(`label[for="${inp.id}"]`);
            if (lbl && versionToggle) versionToggle.textContent = lbl.textContent.trim();
            // enable start button
            if (startBtn) {
                startBtn.disabled = false;
                startBtn.removeAttribute('data-tooltip');
            }
            // optionally close the selector after choice
            if (versionGroup) {
                versionGroup.hidden = true;
                if (versionToggle) versionToggle.setAttribute('aria-expanded', 'false');
            }
            if (versionToggle) {
                versionToggle.dataset.locked = 'true';
                versionToggle.classList.add('version-toggle-locked');
            }
        }

        versionInputs.forEach(inp => inp.addEventListener('change', onVersionSelected));

        // add keyboard support to labels
        versionLabels.forEach(lbl => {
            lbl.setAttribute('tabindex', '0');
            lbl.addEventListener('keydown', (ev) => {
                if (ev.key === 'Enter' || ev.key === ' ') {
                    ev.preventDefault();
                    const id = lbl.getAttribute('for');
                    const inp = id ? document.getElementById(id) : lbl.previousElementSibling;
                    if (inp) inp.checked = true;
                    updateVersionVisuals();
                    onVersionSelected(inp);
                }
            });
        });

        // toggle button to show/hide version list
        if (versionToggle && versionGroup) {
            versionToggle.addEventListener('click', () => {
                if (versionToggle.dataset.locked === 'true') return;
                const isOpen = !(versionGroup.hidden);
                versionGroup.hidden = isOpen; // hide if open, show if closed
                versionToggle.setAttribute('aria-expanded', String(!isOpen));
                if (!isOpen) {
                    // focus first radio for keyboard users
                    const first = setupForm.querySelector('input[name="version"]');
                    if (first) first.focus();
                }
            });
        }

        // initial sync
        updateVersionVisuals();
        const preselected = setupForm.querySelector('input[name="version"]:checked');
        if (preselected) onVersionSelected(preselected);

        setupForm.addEventListener('submit', (e) => {
            const checked = setupForm.querySelector('input[name="version"]:checked');
            if (!checked) {
                if (startBtn) startBtn.setAttribute('data-tooltip', 'Please select version 12 to start the exam');
                e.preventDefault();
                alert('Please select a CEH version');
            }
        });
    }

    // Exam logic
    const examArea = document.getElementById('exam-area');
    if (!examArea) return;

    const TOTAL = document.querySelectorAll('.question-card').length;

    const timerStrip = document.getElementById('examTimer');
    const timerDisplay = document.getElementById('timerDisplay');
    const totalSeconds = timerStrip ? parseInt(timerStrip.dataset.totalSeconds, 10) || 0 : 0;
    let timeRemaining = totalSeconds;
    let timerInterval = null;
    let examTimedOut = false;

    const summaryTrigger = document.getElementById('summaryTrigger');
    const summaryBtn = document.getElementById('viewSummaryBtn');
    const breakModal = document.getElementById('breakModal');
    const breakCountdown = document.getElementById('breakCountdown');
    let stats = { attempted: 0, correct: 0, incorrect: 0 };
    let resultsChart = null;
    let breakTimer = null;

    function handleCompletion(force = false) {
        if (!force && stats.attempted !== TOTAL) return;
        if (summaryTrigger && summaryTrigger.hidden) summaryTrigger.hidden = false;
        if (summaryBtn) {
            summaryBtn.disabled = false;
            if (!summaryBtn.classList.contains('is-available')) {
                if (!force) summaryBtn.focus();
                summaryBtn.classList.add('is-available');
                summaryBtn.classList.add('pulse-action');
                setTimeout(() => summaryBtn.classList.remove('pulse-action'), 3200);
            }
        }
        if (!force && timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
            if (timerStrip) {
                timerStrip.classList.add('timer-complete');
                timerStrip.classList.remove('timer-warning', 'timer-expired');
            }
        }
    }

    function showFinalResults(force = false) {
        if (!force && stats.attempted !== TOTAL) return;
        const modal = document.getElementById('finalModal');
        const resultsDiv = document.getElementById('results-chart');
        const canvas = document.getElementById('resultsChart');
        const correctEl = document.getElementById('modal-correct');
        const totalEl = document.getElementById('modal-total');
        const scoreEl = document.getElementById('modal-score');
        const messageEl = document.getElementById('modal-message');
        if (!modal || !resultsDiv || !canvas || !correctEl || !totalEl || !scoreEl) return;

        const score = TOTAL ? Math.round((stats.correct / TOTAL) * 100) : 0;

        modal.hidden = false;
        modal.setAttribute('aria-hidden', 'false');
        resultsDiv.hidden = false;

        correctEl.textContent = stats.correct;
        totalEl.textContent = TOTAL;
        scoreEl.textContent = score;

        if (messageEl) {
            if (examTimedOut) {
                messageEl.textContent = 'Time is up! Review how you performed below.';
            } else {
                messageEl.textContent = score >= 75
                    ? `Congratulations! You have attempted the CEH exam and got ${score}%.`
                    : 'Keep practising to boost your CEH score next time.';
            }
        }

        const ctx = canvas.getContext('2d');
        if (resultsChart) resultsChart.destroy();
        resultsChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Correct', 'Incorrect'],
                datasets: [{ data: [stats.correct, stats.incorrect], backgroundColor: ['#4CAF50', '#f44336'] }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });

        const closeBtn = document.getElementById('closeModal');
        if (closeBtn) closeBtn.focus();
    }

    function formatTime(seconds) {
        const safeSeconds = Math.max(seconds, 0);
        const hrs = Math.floor(safeSeconds / 3600);
        const mins = Math.floor((safeSeconds % 3600) / 60);
        const secs = safeSeconds % 60;

        if (hrs > 0) {
            const hoursPart = hrs.toString().padStart(2, '0');
            const minutesPart = mins.toString().padStart(2, '0');
            const secondsPart = secs.toString().padStart(2, '0');
            return `${hoursPart}:${minutesPart}:${secondsPart}`;
        }

        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    function updateTimerDisplay() {
        if (!timerDisplay) return;
        const clamped = Math.max(timeRemaining, 0);
        timerDisplay.textContent = formatTime(clamped);
        if (!timerStrip) return;
        const showWarning = clamped <= 60 && clamped > 0;
        const showExpired = clamped <= 0 && !timerStrip.classList.contains('timer-complete');
        timerStrip.classList.toggle('timer-warning', showWarning);
        timerStrip.classList.toggle('timer-expired', showExpired);
    }

    function onTimeExpired() {
        if (examTimedOut) return;
        examTimedOut = true;
        if (timerStrip) {
            timerStrip.classList.add('timer-expired');
            timerStrip.classList.remove('timer-warning', 'timer-complete');
        }
        hideBreakModal();
        alert('Time is up! Your exam has ended.');
        document.querySelectorAll('.verify-btn').forEach(btn => { btn.disabled = true; });
        document.querySelectorAll('.nav-btn').forEach(btn => { btn.disabled = true; });
        document.querySelectorAll('input[type="radio"]').forEach(inp => { inp.disabled = true; });
        handleCompletion(true);
        showFinalResults(true);
    }

    function hideBreakModal() {
        if (!breakModal) return;
        clearInterval(breakTimer);
        breakModal.hidden = true;
        breakModal.setAttribute('aria-hidden', 'true');
    }

    function showBreakModal(onComplete) {
        if (!breakModal || !breakCountdown) {
            if (typeof onComplete === 'function') onComplete();
            return;
        }

        const duration = Math.floor(Math.random() * 6) + 5; // 5 to 10 seconds
        let remaining = duration;
        breakCountdown.textContent = remaining.toString();
        breakModal.hidden = false;
        breakModal.setAttribute('aria-hidden', 'false');

        clearInterval(breakTimer);
        breakTimer = setInterval(() => {
            remaining -= 1;
            if (remaining <= 0) {
                if (breakCountdown) breakCountdown.textContent = '0';
                clearInterval(breakTimer);
                hideBreakModal();
                if (typeof onComplete === 'function') onComplete();
            } else if (breakCountdown) {
                breakCountdown.textContent = remaining.toString();
            }
        }, 1000);
    }

    function startTimer() {
        if (!timerStrip || totalSeconds <= 0) return;
        updateTimerDisplay();
        timerInterval = setInterval(() => {
            timeRemaining -= 1;
            if (timeRemaining <= 0) {
                timeRemaining = 0;
                updateTimerDisplay();
                clearInterval(timerInterval);
                onTimeExpired();
            } else {
                updateTimerDisplay();
            }
        }, 1000);
    }

    function navigateToQuestion(number) {
        if (number < 1 || number > TOTAL) return;
        document.querySelectorAll('.question-card').forEach(card => {
            card.classList.add('hidden');
            if (parseInt(card.dataset.questionNumber, 10) === number) card.classList.remove('hidden');
        });
        document.querySelectorAll('.question-number').forEach(num => {
            num.classList.toggle('current', parseInt(num.dataset.question, 10) === number);
        });
    }

    // Wire up sidebar numbers
    document.querySelectorAll('.question-number').forEach(num => {
        num.addEventListener('click', () => navigateToQuestion(parseInt(num.dataset.question, 10)));
    });

    // Prev/Next buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const card = e.target.closest('.question-card');
            if (!card) return;
            const current = parseInt(card.dataset.questionNumber, 10);
            const next = btn.classList.contains('next-btn') ? current + 1 : current - 1;
            navigateToQuestion(next);
        });
    });

    // Answer verification
    document.querySelectorAll('.verify-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const parent = e.target.closest('.question-card');
            if (!parent) return;
            const qid = parent.dataset.id;
            const qnum = parseInt(parent.dataset.questionNumber, 10);
            const answer = parent.querySelector('input[type="radio"]:checked');
            const resultBox = parent.querySelector('.result');
            const indicator = document.querySelector(`.question-number[data-question="${qnum}"]`);

            if (examTimedOut) { alert('Time is up. The exam has ended.'); return; }
            if (!answer) { alert('Please select an answer!'); return; }
            btn.disabled = true;

            try {
                const res = await fetch('/verify_answer', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question_id: qid, user_answer: answer.value })
                });
                const data = await res.json();
                const correct = data.result === 'correct';
                if (resultBox) resultBox.textContent = correct ? '✅ Correct!' : '❌ Wrong!';
                if (indicator) indicator.classList.add(correct ? 'correct' : 'incorrect');

                if (indicator && !indicator.classList.contains('attempted')) {
                    stats.attempted++;
                    if (correct) stats.correct++; else stats.incorrect++;
                    indicator.classList.add('attempted');
                }

                handleCompletion();

                const next = qnum + 1;
                const needsBreak = !examTimedOut && stats.attempted < TOTAL && stats.attempted % 5 === 0;

                if (needsBreak) {
                    showBreakModal(() => {
                        if (next <= TOTAL) navigateToQuestion(next);
                    });
                } else if (next <= TOTAL) {
                    setTimeout(() => navigateToQuestion(next), 800);
                }
            } catch (err) {
                console.error(err);
                if (resultBox) resultBox.textContent = '❌ Error verifying answer. Please try again.';
                btn.disabled = false;
            }
        });
    });

    // Mark first question current
    const first = document.querySelector('.question-number[data-question="1"]');
    if (first) first.classList.add('current');

    function hideModal() {
        const modal = document.getElementById('finalModal');
        const resultsDiv = document.getElementById('results-chart');
        if (!modal || !resultsDiv) return;
        modal.hidden = true;
        modal.setAttribute('aria-hidden', 'true');
        resultsDiv.hidden = true;
        if (summaryBtn) summaryBtn.focus();
    }

    const closeModal = document.getElementById('closeModal');
    if (closeModal) closeModal.addEventListener('click', hideModal);

    const modalOverlay = document.getElementById('finalModal');
    if (modalOverlay) {
        modalOverlay.addEventListener('click', (ev) => {
            if (ev.target === modalOverlay) hideModal();
        });
    }

    if (summaryBtn) summaryBtn.addEventListener('click', () => {
        const force = examTimedOut || stats.attempted !== TOTAL;
        showFinalResults(force);
    });

    document.addEventListener('keydown', (ev) => {
        if (ev.key === 'Escape') hideModal();
    });

    startTimer();
});
