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

    summaryForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Reset state
        errorAlert.style.display = 'none';
        resultContainer.style.display = 'none';
        loadingOverlay.style.display = 'flex';

        const formData = {
            gene: document.getElementById('gene').value.trim(),
            change: document.getElementById('change').value.trim(),
            level: document.getElementById('level').value
        };

        try {
            const response = await fetch('/api/generate-llm-summary', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to generate summary');
            }

            // Display result
            const result = data.result;
            
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

        } catch (error) {
            console.error('Error:', error);
            errorMessage.textContent = error.message;
            errorAlert.style.display = 'block';
        } finally {
            loadingOverlay.style.display = 'none';
        }
    });

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
