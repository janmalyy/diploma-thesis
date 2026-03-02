document.addEventListener('DOMContentLoaded', () => {
    const summaryForm = document.getElementById('summary-form');
    const loadingOverlay = document.getElementById('loading-overlay');
    const resultContainer = document.getElementById('result-container');
    const summaryContent = document.getElementById('summary-content');
    const structuredContainer = document.getElementById('structured-summary-container');
    const pathogenicityValue = document.getElementById('pathogenicity-value');
    const confidenceValue = document.getElementById('confidence-value');
    const evidenceCounts = document.getElementById('evidence-counts');
    const conflictWarning = document.getElementById('conflicting-evidence-warning');
    const errorAlert = document.getElementById('error-alert');
    const errorMessage = document.getElementById('error-message');
    const copyBtn = document.getElementById('copy-btn');
    const stopBtn = document.getElementById('stop-btn');
    const loadingStatus = document.getElementById('loading-status');
    const loadingSubtext = document.getElementById('loading-subtext');
    const timeEstimate = document.getElementById('time-estimate');
    const etaValue = document.getElementById('eta-value');
    const relevanceProgressContainer = document.getElementById('relevance-progress-container');
    const relevanceProgressBar = document.getElementById('relevance-progress-bar');

    let abortController = null;

    // Load saved results if any
    const savedResult = sessionStorage.getItem('variant_summary_result');
    if (savedResult) {
        try {
            const resultData = JSON.parse(savedResult);
            displayResult(resultData);
            // Also restore form values
            const savedForm = sessionStorage.getItem('variant_summary_form');
            if (savedForm) {
                const formData = JSON.parse(savedForm);
                document.getElementById('gene').value = formData.gene || '';
                document.getElementById('change').value = formData.change || '';
                document.getElementById('level').value = formData.level || '';
            }
        } catch (e) {
            console.error('Failed to load saved result:', e);
        }
    }

    function stopGeneration() {
        if (abortController) {
            abortController.abort();
            abortController = null;
        }
        loadingOverlay.style.display = 'none';
    }

    stopBtn.addEventListener('click', stopGeneration);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && loadingOverlay.style.display === 'flex') {
            stopGeneration();
        }
    });

    summaryForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Prevent multiple submissions
        if (loadingOverlay.style.display === 'flex') {
            return;
        }

        // Reset state
        errorAlert.style.display = 'none';
        resultContainer.style.display = 'none';
        loadingOverlay.style.display = 'flex';
        loadingStatus.textContent = 'Initializing...';
        loadingSubtext.textContent = 'This may take a minute.';
        timeEstimate.style.display = 'none';
        relevanceProgressContainer.style.display = 'none';
        relevanceProgressBar.style.width = '0%';

        const formData = {
            gene: document.getElementById('gene').value.trim(),
            change: document.getElementById('change').value.trim(),
            level: document.getElementById('level').value
        };

        // Save form values to session storage
        sessionStorage.setItem('variant_summary_form', JSON.stringify(formData));

        abortController = new AbortController();

        try {
            const response = await fetch('/api/generate-llm-summary', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData),
                signal: abortController.signal
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Failed to generate summary');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let partialData = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                partialData += chunk;

                const lines = partialData.split('\n');
                partialData = lines.pop(); // Keep the last partial line

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const jsonStr = line.substring(6);
                        try {
                            const data = JSON.parse(jsonStr);
                            handleProgressUpdate(data);
                        } catch (e) {
                            console.error('Failed to parse JSON from SSE:', e, jsonStr);
                        }
                    }
                }
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Generation aborted by user');
                return;
            }
            console.error('Error:', error);
            errorMessage.textContent = error.message;
            errorAlert.style.display = 'block';
            loadingOverlay.style.display = 'none';
        }
    });

    let currentTotalCalls = 0;
    let currentCompletedCalls = 0;

    function handleProgressUpdate(data) {
        if (data.error) {
            throw new Error(data.error);
        }

        if (data.total_calls !== undefined) {
            currentTotalCalls = data.total_calls;
            timeEstimate.style.display = 'block';
            updateETA();
        }

        if (data.completed_calls !== undefined) {
            currentCompletedCalls = data.completed_calls;
            updateProgressBar();
            updateETA();
        }

        if (data.status) {
            loadingStatus.textContent = data.status;
        }

        if (data.article_count !== undefined) {
            const count = data.article_count;
            if (count === 0) {
                loadingSubtext.textContent = 'Combining evidence for final summary.';
            } else if (data.phase) {
                loadingSubtext.textContent = `Processing ${count} ${data.phase}.`;
            } else {
                loadingSubtext.textContent = `Processing ${count} articles.`;
            }
        }

        if (data.result) {
            displayResult(data.result);
        }
    }

    function updateProgressBar() {
        if (currentTotalCalls > 0) {
            const percent = (currentCompletedCalls / currentTotalCalls) * 100;
            relevanceProgressContainer.style.display = 'flex';
            relevanceProgressBar.style.width = `${percent}%`;
            relevanceProgressBar.textContent = `${currentCompletedCalls}/${currentTotalCalls} calls`;
        }
    }

    function updateETA() {
        if (currentTotalCalls > 0) {
            const remaining = Math.max(0, currentTotalCalls - currentCompletedCalls);
            etaValue.textContent = remaining * 5;
        }
    }

    function displayResult(result) {
        loadingOverlay.style.display = 'none';
        abortController = null;

        // Save result to session storage
        sessionStorage.setItem('variant_summary_result', JSON.stringify(result));
        
        if (typeof result === 'string') {
            // Handle case where API might still return a simple string (e.g. error messages)
            summaryContent.textContent = result;
            structuredContainer.style.display = 'none';
        } else {
            // Display Narrative Summary
            summaryContent.textContent = result.narrative_summary || 'No narrative summary available.';
            
            // Display Structured Summary
            if (result.structured_summary) {
                const ss = result.structured_summary;
                
                pathogenicityValue.textContent = ss.overall_pathogenicity || 'unknown';
                confidenceValue.textContent = ss.overall_confidence || 'unknown';
                
                // Set color based on pathogenicity
                const pathColor = getPathogenicityColor(ss.overall_pathogenicity);
                pathogenicityValue.className = `badge bg-${pathColor} text-capitalize`;
                
                // Set color based on confidence
                const confColor = getConfidenceColor(ss.overall_confidence);
                confidenceValue.className = `badge bg-${confColor} text-capitalize`;

                // Evidence counts
                evidenceCounts.innerHTML = '';
                if (ss.evidence_counts) {
                    Object.entries(ss.evidence_counts).forEach(([type, count]) => {
                        const badge = document.createElement('span');
                        badge.className = 'badge rounded-pill bg-info text-dark evidence-badge';
                        badge.textContent = `${type}: ${count}`;
                        evidenceCounts.appendChild(badge);
                    });
                }
                
                conflictWarning.style.display = ss.conflicting_evidence ? 'block' : 'none';
                structuredContainer.style.display = 'block';
            } else {
                structuredContainer.style.display = 'none';
            }
        }
        
        resultContainer.style.display = 'block';
        
        // Scroll to result
        resultContainer.scrollIntoView({ behavior: 'smooth' });
    }

    copyBtn.addEventListener('click', () => {
        const text = summaryContent.textContent;
        navigator.clipboard.writeText(text).then(() => {
            const originalText = copyBtn.textContent;
            copyBtn.textContent = 'Copied!';
            copyBtn.classList.replace('btn-outline-light', 'btn-success');
            
            setTimeout(() => {
                copyBtn.textContent = originalText;
                copyBtn.classList.replace('btn-success', 'btn-outline-light');
            }, 2000);
        });
    });

    function getPathogenicityColor(path) {
        if (!path) return 'secondary';
        const p = path.toLowerCase();
        if (p.includes('pathogenic') && !p.includes('likely')) return 'danger';
        if (p.includes('likely pathogenic')) return 'warning';
        if (p.includes('benign')) return 'success';
        if (p.includes('uncertain')) return 'secondary';
        return 'info';
    }

    function getConfidenceColor(conf) {
        if (!conf) return 'secondary';
        const c = conf.toLowerCase();
        if (c === 'high') return 'success';
        if (c === 'moderate') return 'primary';
        if (c === 'low') return 'secondary';
        return 'info';
    }
});
