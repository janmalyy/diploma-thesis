import { MOCK_EVENTS } from "./mock_data.js";

document.addEventListener("DOMContentLoaded", () => {
    const summaryForm = document.getElementById("summary-form");
    const loadingOverlay = document.getElementById("loading-overlay");
    const resultContainer = document.getElementById("result-container");
    const summaryContent = document.getElementById("summary-content");
    const structuredContainer = document.getElementById("structured-summary-container");
    const pathogenicityValue = document.getElementById("pathogenicity-value");
    const confidenceValue = document.getElementById("confidence-value");
    const evidenceCounts = document.getElementById("evidence-counts");
    const conflictWarning = document.getElementById("conflicting-evidence-warning");
    const errorAlert = document.getElementById("error-alert");
    const errorMessage = document.getElementById("error-message");
    const copyBtn = document.getElementById("copy-btn");
    const stopBtn = document.getElementById("stop-btn");
    const loadingStatus = document.getElementById("loading-status");
    const loadingSubtext = document.getElementById("loading-subtext");
    const timeEstimate = document.getElementById("time-estimate");
    const etaValue = document.getElementById("eta-value");
    const relevanceProgressContainer = document.getElementById("relevance-progress-container");
    const relevanceProgressBar = document.getElementById("relevance-progress-bar");

    const articleEvidenceModal = new bootstrap.Modal(document.getElementById("articleEvidenceModal"));
    const articleEvidenceBody = document.getElementById("article-evidence-body");
    const copyEvidenceBtn = document.getElementById("copy-evidence-btn");
    const testUiBtn = document.getElementById("test-ui-btn");

    const modalTabs = document.getElementById("modal-evidence-tabs");
    const prevEvidenceBtn = document.getElementById("prev-evidence-btn");
    const nextEvidenceBtn = document.getElementById("next-evidence-btn");
    const groupedEvidenceContainer = document.getElementById("grouped-evidence-container");
    const groupedEvidenceBody = document.getElementById("grouped-evidence-body");

    let abortController = null;
    let currentArticleEvidences = [];
    let sortedArticlesForModal = [];
    let modalEvidenceQueue = [];
    let currentModalIndex = 0;

    // Load saved results if any
    const savedResult = sessionStorage.getItem("variant_summary_result");
    if (savedResult) {
        try {
            const resultData = JSON.parse(savedResult);
            displayResult(resultData);
            // Also restore form values
            const savedForm = sessionStorage.getItem("variant_summary_form");
            if (savedForm) {
                const formData = JSON.parse(savedForm);
                document.getElementById("gene").value = formData.gene || "";
                document.getElementById("change").value = formData.change || "";
                document.getElementById("level").value = formData.level || "";
            }
        } catch (e) {
            console.error("Failed to load saved result:", e);
        }
    }

    function stopGeneration() {
        if (abortController) {
            abortController.abort();
            abortController = null;
        }
        loadingOverlay.style.display = "none";
    }

    stopBtn.addEventListener("click", stopGeneration);

    document.addEventListener("keydown", (e) => {
        const modalEl = document.getElementById("articleEvidenceModal");
        const isModalOpen = modalEl && modalEl.classList.contains("show");

        if (e.key === "Escape") {
            if (loadingOverlay.style.display === "flex") {
                stopGeneration();
            } else if (isModalOpen) {
                articleEvidenceModal.hide();
            }
        }

        if (isModalOpen) {
            if (e.key === "ArrowLeft") {
                if (modalEvidenceQueue.length > 1 && currentModalIndex > 0) {
                    currentModalIndex--;
                    updateModalContent();
                }
            } else if (e.key === "ArrowRight") {
                if (modalEvidenceQueue.length > 1 && currentModalIndex < modalEvidenceQueue.length - 1) {
                    currentModalIndex++;
                    updateModalContent();
                }
            }
            return;
        }

        // Grouped Evidence Navigation for Article Cards
        const activeCard = document.activeElement;
        if (activeCard && activeCard.classList.contains("article-card")) {
            const cards = Array.from(groupedEvidenceBody.querySelectorAll(".article-card"));
            let target = null;

            if (e.key === "ArrowLeft") {
                target = getElementInDirection(activeCard, cards, "left");
            } else if (e.key === "ArrowRight") {
                target = getElementInDirection(activeCard, cards, "right");
            } else if (e.key === "ArrowUp") {
                target = getElementInDirection(activeCard, cards, "up");
            } else if (e.key === "ArrowDown") {
                target = getElementInDirection(activeCard, cards, "down");
            } else if (e.key === "Enter") {
                activeCard.click();
            }

            if (target) {
                e.preventDefault();
                target.focus();
            }
        }
    });

    summaryForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        if (loadingOverlay.style.display === "flex") {
            return;
        }

        errorAlert.style.display = "none";
        resultContainer.style.display = "none";
        loadingOverlay.style.display = "flex";
        loadingStatus.textContent = "Initializing...";
        loadingSubtext.textContent = "This may take a minute.";
        timeEstimate.style.display = "none";
        relevanceProgressContainer.style.display = "none";
        relevanceProgressBar.style.width = "0%";

        const formData = {
            gene: document.getElementById("gene").value.trim(),
            change: document.getElementById("change").value.trim(),
            level: document.getElementById("level").value
        };

        sessionStorage.setItem("variant_summary_form", JSON.stringify(formData));

        abortController = new AbortController();

        try {
            const response = await fetch("/api/generate-llm-summary", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(formData),
                signal: abortController.signal
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || "Failed to generate summary");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let partialData = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                partialData += chunk;

                const lines = partialData.split("\n");
                partialData = lines.pop();

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const jsonStr = line.substring(6);
                        try {
                            const data = JSON.parse(jsonStr);
                            handleProgressUpdate(data);
                        } catch (e) {
                            console.error("Failed to parse JSON from SSE:", e, jsonStr);
                        }
                    }
                }
            }
        } catch (error) {
            if (error.name === "AbortError") {
                console.log("Generation aborted by user");
                return;
            }
            console.error("Error:", error);
            errorMessage.textContent = error.message;
            errorAlert.style.display = "block";
            loadingOverlay.style.display = "none";
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
            timeEstimate.style.display = "block";
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
                loadingSubtext.textContent = "Combining evidence for final summary.";
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
            relevanceProgressContainer.style.display = "flex";
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
        loadingOverlay.style.display = "none";
        abortController = null;

        currentArticleEvidences = result.article_evidences || [];
        sessionStorage.setItem("variant_summary_result", JSON.stringify(result));

        if (typeof result === "string") {
            summaryContent.textContent = result;
            structuredContainer.style.display = "none";
        } else {
            const narrative = result.narrative_summary || "No narrative summary available.";
            summaryContent.innerHTML = linkifyReferences(narrative);

            if (result.structured_summary) {
                const ss = result.structured_summary;
                pathogenicityValue.textContent = ss.overall_pathogenicity || "unknown";
                confidenceValue.textContent = ss.overall_confidence || "unknown";

                const pathColor = getPathogenicityColor(ss.overall_pathogenicity);
                pathogenicityValue.className = `badge bg-${pathColor} text-capitalize`;

                const confColor = getConfidenceColor(ss.overall_confidence);
                confidenceValue.className = `badge bg-${confColor} text-capitalize`;

                evidenceCounts.innerHTML = "";
                if (ss.evidence_counts) {
                    Object.entries(ss.evidence_counts).forEach(([type, count]) => {
                        if (count === 0) return;

                        const typeArticles = currentArticleEvidences.filter(a =>
                            a.evidence && a.evidence.some(ev => ev.evidence_type.toLowerCase() === type.toLowerCase())
                        );

                        const uniqueArticles = [];
                        const seenIds = new Set();
                        typeArticles.forEach(a => {
                            if (!seenIds.has(a.article_id)) {
                                uniqueArticles.push(a);
                                seenIds.add(a.article_id);
                            }
                        });

                        if (uniqueArticles.length > 0) {
                            const badge = document.createElement("span");
                            badge.className = "badge rounded-pill bg-info text-dark evidence-badge clickable me-1 mb-1";
                            badge.textContent = `${type}: ${count}`;
                            badge.style.cursor = "pointer";
                            badge.addEventListener("click", () => showTypeEvidence(type));
                            evidenceCounts.appendChild(badge);
                        }
                    });
                }

                conflictWarning.style.display = ss.conflicting_evidence ? "block" : "none";
                structuredContainer.style.display = "block";
            } else {
                structuredContainer.style.display = "none";
            }

            renderGroupedEvidences(currentArticleEvidences);
        }

        resultContainer.style.display = "block";
        resultContainer.scrollIntoView({ behavior: "smooth" });
    }

    copyBtn.addEventListener("click", () => {
        const text = summaryContent.textContent;
        navigator.clipboard.writeText(text).then(() => {
            const originalText = copyBtn.textContent;
            copyBtn.textContent = "Copied!";
            copyBtn.classList.replace("btn-outline-light", "btn-success");

            setTimeout(() => {
                copyBtn.textContent = originalText;
                copyBtn.classList.replace("btn-success", "btn-outline-light");
            }, 2000);
        });
    });

    if (testUiBtn) {
        testUiBtn.addEventListener("click", async () => {
            if (loadingOverlay.style.display === "flex") return;

            document.getElementById("gene").value = "BRAF";
            document.getElementById("change").value = "V600E";
            document.getElementById("level").value = "protein";

            errorAlert.style.display = "none";
            resultContainer.style.display = "none";
            loadingOverlay.style.display = "flex";
            loadingStatus.textContent = "Initializing (Mock)...";
            loadingSubtext.textContent = "Simulation started";
            timeEstimate.style.display = "none";
            relevanceProgressContainer.style.display = "none";
            relevanceProgressBar.style.width = "0%";

            currentTotalCalls = 0;
            currentCompletedCalls = 0;

            abortController = new AbortController();
            const signal = abortController.signal;

            try {
                for (const event of MOCK_EVENTS) {
                    if (signal.aborted) break;
                    await new Promise(resolve => setTimeout(resolve, 600));
                    if (signal.aborted) break;
                    handleProgressUpdate(event);
                }
            } catch (e) {
                console.error("Mock simulation error:", e);
            }
        });
    }

    function getPathogenicityColor(path) {
        if (!path) return "secondary";
        const p = path.toLowerCase();
        if (p.includes("pathogenic") && !p.includes("likely")) return "danger";
        if (p.includes("likely pathogenic")) return "warning";
        if (p.includes("benign")) return "success";
        if (p.includes("uncertain")) return "secondary";
        return "info";
    }

    function getConfidenceColor(conf) {
        if (!conf) return "secondary";
        const c = conf.toLowerCase();
        if (c === "high") return "success";
        if (c === "moderate") return "primary";
        if (c === "low") return "secondary";
        return "info";
    }

    summaryContent.addEventListener("click", (e) => {
        const refLink = e.target.closest(".ref-link");
        if (refLink) {
            e.preventDefault();
            const articleId = refLink.getAttribute("data-article-id");
            showArticleEvidence(articleId);
        }
    });

    function linkifyReferences(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        const escapedText = div.innerHTML;

        return escapedText.replace(/\[(PMC\s*:?\s*\d+|PMID\s*:?\s*\d+|\d+)\]/gi, (match, id) => {
            const cleanId = id.replace(/^(PMC|PMID)\s*:?\s*/i, "").trim();
            const prefix = id.toUpperCase().startsWith("PMC") ? "PMC" : "";
            return `<span class="ref-link" data-article-id="${prefix}${cleanId}">${match}</span>`;
        });
    }

    function escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    function showTypeEvidence(type) {
        const typeArticles = currentArticleEvidences.filter(a =>
            a.evidence && a.evidence.some(ev => ev.evidence_type.toLowerCase() === type.toLowerCase())
        );

        const uniqueArticles = [];
        const seenIds = new Set();
        typeArticles.forEach(a => {
            if (!seenIds.has(a.article_id)) {
                uniqueArticles.push(a);
                seenIds.add(a.article_id);
            }
        });

        if (uniqueArticles.length > 0) {
            renderEvidenceModal(uniqueArticles, 0);
        }
    }

    function renderEvidenceModal(articles, startIndex = 0) {
        modalEvidenceQueue = articles;
        currentModalIndex = startIndex;

        updateModalContent();
        articleEvidenceModal.show();
    }

    function updateModalContent() {
        if (modalEvidenceQueue.length === 0) return;

        const article = modalEvidenceQueue[currentModalIndex];
        const articleId = article.article_id;

        document.getElementById("articleEvidenceModalLabel").textContent = `Evidence from Article ${articleId}`;

        if (modalEvidenceQueue.length > 1) {
            modalTabs.style.display = "flex";
            modalTabs.innerHTML = "";
            modalEvidenceQueue.forEach((a, index) => {
                const li = document.createElement("li");
                li.className = "nav-item";
                const link = document.createElement("a");
                link.className = `nav-link ${index === currentModalIndex ? "active" : ""}`;
                link.href = "#";
                link.textContent = a.article_id;
                link.addEventListener("click", (e) => {
                    e.preventDefault();
                    currentModalIndex = index;
                    updateModalContent();
                });
                li.appendChild(link);
                modalTabs.appendChild(li);
            });
        } else {
            modalTabs.style.display = "none";
        }

        prevEvidenceBtn.style.display = modalEvidenceQueue.length > 1 ? "inline-block" : "none";
        nextEvidenceBtn.style.display = modalEvidenceQueue.length > 1 ? "inline-block" : "none";
        prevEvidenceBtn.disabled = currentModalIndex === 0;
        nextEvidenceBtn.disabled = currentModalIndex === modalEvidenceQueue.length - 1;

        let html = `
            <div class="mb-4">
                <h6><strong>Article Conclusion:</strong></h6>
                <p>${escapeHtml(article.overall_article_conclusion || "N/A")}</p>
            </div>
        `;

        if (article.evidence && article.evidence.length > 0) {
            html += `<h6><strong>Specific Evidence Points:</strong></h6>`;
            article.evidence.forEach(ev => {
                const claimColor = getClaimColor(ev.claim);
                html += `
                    <div class="evidence-item mb-3 p-2 bg-light border-start border-4">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span class="badge evidence-type-badge bg-info text-dark">${escapeHtml(ev.evidence_type)}</span>
                            <span class="badge text-capitalize bg-${claimColor}">${escapeHtml(ev.claim)}</span>
                        </div>
                        <p class="mb-1"><strong>Description:</strong> ${escapeHtml(ev.description)}</p>
                        <p class="mb-1"><small><strong>Context:</strong> ${escapeHtml(ev.study_context || "N/A")}</small></p>
                        ${ev.quoted_text ? `<p class="mb-0 mt-2 italic text-muted" style="font-style: italic;"><small>"${escapeHtml(ev.quoted_text)}"</small></p>` : ""}
                    </div>
                `;
            });
        } else {
            html += `<p class="text-muted">No specific evidence points extracted.</p>`;
        }

        if (article.uncertainties_or_limitations) {
            html += `
                <div class="mt-3 p-2 border rounded bg-light">
                    <h6><small><strong>Uncertainties/Limitations:</strong></small></h6>
                    <p class="mb-0"><small>${escapeHtml(article.uncertainties_or_limitations)}</small></p>
                </div>
            `;
        }

        articleEvidenceBody.innerHTML = html;
    }

    function renderGroupedEvidences(articles) {
        if (!articles || articles.length === 0) {
            groupedEvidenceContainer.style.display = "none";
            return;
        }

        const strengthMap = { "high": 4, "moderate": 3, "low": 2, "unclear": 1, "none": 0 };

        // Save the sorted list globally for modal navigation
        sortedArticlesForModal = [...articles].sort((a, b) => {
            const maxStrengthA = a.evidence ? Math.max(...a.evidence.map(ev => strengthMap[ev.strength.toLowerCase()] || 1)) : 0;
            const maxStrengthB = b.evidence ? Math.max(...b.evidence.map(ev => strengthMap[ev.strength.toLowerCase()] || 1)) : 0;
            return maxStrengthB - maxStrengthA;
        });

        groupedEvidenceBody.innerHTML = "";
        sortedArticlesForModal.forEach((article, index) => {
            const card = document.createElement("div");
            card.className = "card m-3 article-card";
            card.tabIndex = 0;

            let evidenceListHtml = "";
            if (article.evidence) {
                article.evidence.forEach(ev => {
                    const claimColor = getClaimColor(ev.claim);
                    evidenceListHtml += `<span class="badge bg-light text-dark border me-1 mb-1" title="${escapeHtml(ev.description)}">
                        <small>${escapeHtml(ev.evidence_type)}: </small><span class="text-${claimColor}">${escapeHtml(ev.claim)}</span>
                    </span>`;
                });
            }

            card.innerHTML = `
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <h6 class="card-title">Article: ${escapeHtml(article.article_id)}</h6>
                        <button class="btn btn-sm btn-outline-primary view-details-btn">View Details</button>
                    </div>
                    <p class="card-text small mb-2 text-muted">${escapeHtml(article.overall_article_conclusion || "No conclusion provided.")}</p>
                    <div class="evidence-summary-list">
                        ${evidenceListHtml}
                    </div>
                </div>
            `;

            // Pass the full sorted list and the specific index of this card
            card.addEventListener("click", (e) => {
                if (!e.target.classList.contains("view-details-btn")) {
                    renderEvidenceModal(sortedArticlesForModal, index);
                }
            });

            card.querySelector(".view-details-btn").addEventListener("click", () => {
                renderEvidenceModal(sortedArticlesForModal, index);
            });

            groupedEvidenceBody.appendChild(card);
        });

        groupedEvidenceContainer.style.display = "block";
    }

    function showArticleEvidence(articleId) {
        const targetClean = articleId.replace(/^(PMC|PMID)\s*:?\s*/i, "").toUpperCase().trim();

        // Find the index within the existing sorted list
        const index = sortedArticlesForModal.findIndex(a => {
            if (!a.article_id) return false;
            const articleClean = a.article_id.toString().replace(/^(PMC|PMID)\s*:?\s*/i, "").toUpperCase().trim();
            return articleClean === targetClean;
        });

        if (index === -1) {
            articleEvidenceBody.innerHTML = `<div class="alert alert-warning">No detailed evidence found for article ${escapeHtml(articleId)}.</div>`;
            modalTabs.style.display = "none";
            prevEvidenceBtn.style.display = "none";
            nextEvidenceBtn.style.display = "none";
            articleEvidenceModal.show();
            return;
        }

        // Open modal with the full list, starting at the found index
        renderEvidenceModal(sortedArticlesForModal, index);
    }

    prevEvidenceBtn.addEventListener("click", () => {
        if (currentModalIndex > 0) {
            currentModalIndex--;
            updateModalContent();
        }
    });

    nextEvidenceBtn.addEventListener("click", () => {
        if (currentModalIndex < modalEvidenceQueue.length - 1) {
            currentModalIndex++;
            updateModalContent();
        }
    });

    function getClaimColor(claim) {
        if (!claim) return "secondary";
        const c = claim.toLowerCase();
        if (c.includes("pathogenicity")) return "danger";
        if (c.includes("benignity")) return "success";
        if (c.includes("conflicting")) return "warning";
        return "secondary";
    }

    copyEvidenceBtn.addEventListener("click", () => {
        const text = articleEvidenceBody.innerText;
        navigator.clipboard.writeText(text).then(() => {
            const originalText = copyEvidenceBtn.textContent;
            copyEvidenceBtn.textContent = "Copied!";
            copyEvidenceBtn.classList.replace("btn-outline-primary", "btn-success");

            setTimeout(() => {
                copyEvidenceBtn.textContent = originalText;
                copyEvidenceBtn.classList.replace("btn-success", "btn-outline-primary");
            }, 2000);
        });
    });

    function getElementInDirection(currentEl, allEls, direction) {
        const currentRect = currentEl.getBoundingClientRect();
        const currentCenter = {
            x: currentRect.left + currentRect.width / 2,
            y: currentRect.top + currentRect.height / 2
        };

        let bestMatch = null;
        let minDistance = Infinity;

        allEls.forEach(el => {
            if (el === currentEl) return;
            const rect = el.getBoundingClientRect();
            const center = {
                x: rect.left + rect.width / 2,
                y: rect.top + rect.height / 2
            };

            let isCorrectDirection = false;
            switch (direction) {
                case "up":
                    if (center.y < currentCenter.y - currentRect.height / 2) isCorrectDirection = true;
                    break;
                case "down":
                    if (center.y > currentCenter.y + currentRect.height / 2) isCorrectDirection = true;
                    break;
                case "left":
                    if (center.x < currentCenter.x - currentRect.width / 2) isCorrectDirection = true;
                    break;
                case "right":
                    if (center.x > currentCenter.x + currentRect.width / 2) isCorrectDirection = true;
                    break;
            }

            if (isCorrectDirection) {
                let distance;
                if (direction === "up" || direction === "down") {
                    distance = Math.abs(center.y - currentCenter.y) * 2 + Math.abs(center.x - currentCenter.x);
                } else {
                    distance = Math.abs(center.x - currentCenter.x) * 2 + Math.abs(center.y - currentCenter.y);
                }

                if (distance < minDistance) {
                    minDistance = distance;
                    bestMatch = el;
                }
            }
        });
        return bestMatch;
    }
});
