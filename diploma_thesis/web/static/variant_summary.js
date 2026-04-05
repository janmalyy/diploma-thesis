import { MOCK_EVENTS } from "./mock_data.js";

document.addEventListener("DOMContentLoaded", () => {
    const summaryForm = document.getElementById("summary-form");
    const loadingOverlay = document.getElementById("loading-overlay");
    const resultContainer = document.getElementById("result-container");
    const summaryContent = document.getElementById("summary-content");
    const structuredContainer = document.getElementById("structured-summary-container");
    const pathogenicityValue = document.getElementById("pathogenicity-value");
    const confidenceValue = document.getElementById("confidence-value");
    const pathogenicityCounts = document.getElementById("pathogenicity-counts");
    const conflictWarning = document.getElementById("conflicting-evidence-warning");
    const errorAlert = document.getElementById("error-alert");
    const errorMessage = document.getElementById("error-message");
    const copyBtn = document.getElementById("copy-btn");
    const stopBtn = document.getElementById("stop-btn");
    const loadingStatus = document.getElementById("loading-status");
    const loadingSubtext = document.getElementById("loading-subtext");
    const relevanceProgressContainer = document.getElementById("relevance-progress-container");
    const relevanceProgressBar = document.getElementById("relevance-progress-bar");
    const externalLinksContainer = document.getElementById("external-links-container");
    const clinvarLinksList = document.getElementById("clinvar-links-list");
    const omimLinkContainer = document.getElementById("omim-link-container");

    const articleEvidenceModal = new bootstrap.Modal(document.getElementById("articleEvidenceModal"));
    const articleEvidenceBody = document.getElementById("article-evidence-body");
    const copyEvidenceBtn = document.getElementById("copy-evidence-btn");
    const testUiBtn = document.getElementById("test-ui-btn");

    const aboutModal = new bootstrap.Modal(document.getElementById("aboutModal"));
    const helpModal = new bootstrap.Modal(document.getElementById("helpModal"));
    const aboutBtn = document.getElementById("about-btn");
    const helpBtn = document.getElementById("help-btn");
    const aboutContent = document.getElementById("about-content");
    const helpContent = document.getElementById("help-content");

    const modalTabs = document.getElementById("modal-evidence-tabs");
    const prevEvidenceBtn = document.getElementById("prev-evidence-btn");
    const nextEvidenceBtn = document.getElementById("next-evidence-btn");
    const groupedEvidenceContainer = document.getElementById("grouped-evidence-container");
    const groupedEvidenceBody = document.getElementById("grouped-evidence-body");
    const levelSelect = document.getElementById("level");
    const geneContainer = document.getElementById("gene-container");
    const geneInput = document.getElementById("gene");
    const changeLabel = document.getElementById("change-label");
    const changeInput = document.getElementById("change");

    let abortController = null;
    let currentArticleEvidences = [];
    let sortedArticlesForModal = [];
    let modalEvidenceQueue = [];
    let currentModalIndex = 0;

    // Helper to fetch and render Markdown
    async function loadMarkdownContent(filename, container) {
        try {
            const response = await fetch(`/static/${filename}`);
            if (!response.ok) throw new Error(`Could not load ${filename}`);
            const text = await response.text();

            const rawHtml = marked.parse(text);

            const cleanHtml = DOMPurify.sanitize(rawHtml, {
                ADD_ATTR: ["target"],
                FORBID_TAGS: ["style"],
            });

            container.innerHTML = cleanHtml;

            const links = container.querySelectorAll("a");
            links.forEach(link => {
                link.setAttribute("target", "_blank");
                link.setAttribute("rel", "noopener noreferrer");
            });

        } catch (error) {
            console.error(error);
            container.innerHTML = `<div class="alert alert-danger">Error loading content.</div>`;
        }
    }

    aboutBtn.addEventListener("click", () => {
        aboutModal.show();
        loadMarkdownContent("about.md", aboutContent);
    });

    helpBtn.addEventListener("click", () => {
        helpModal.show();
        loadMarkdownContent("help.md", helpContent);
    });

    // Load saved results if any
    const savedResult = sessionStorage.getItem("variant_summary_result");
    if (savedResult) {
        try {
            const resultData = JSON.parse(savedResult);
            displayResult(resultData);
            const savedForm = sessionStorage.getItem("variant_summary_form");
            if (savedForm) {
                const formData = JSON.parse(savedForm);
                geneInput.value = formData.gene || "";
                changeInput.value = formData.change || "";
                levelSelect.value = formData.level || "";
                updateFieldsBasedOnLevel(formData.level);
            }
        } catch (e) {
            console.error("Failed to load saved result:", e);
        }
    }

    function updateFieldsBasedOnLevel(level) {
        if (!level) return;

        if (level === "dbsnp" || level === "clingen") {
            geneContainer.style.display = "none";
            geneInput.required = false;
            geneInput.value = "";
            changeLabel.textContent = "Reference ID";
        } else {
            geneContainer.style.display = "block";
            geneInput.required = true;
            changeLabel.textContent = "Change";
        }

        switch (level) {
            case "protein":
                geneInput.placeholder = "e.g. NOP10";
                changeInput.placeholder = "e.g. D12H";
                break;
            case "transcript":
                geneInput.placeholder = "e.g. NOP10";
                changeInput.placeholder = "e.g. c.34G>C";
                break;
            case "genome":
                geneInput.placeholder = "e.g. NOP10";
                changeInput.placeholder = "e.g. g.34343040C>G";
                break;
            case "clingen":
                changeInput.placeholder = "e.g. CA7464815";
                break;
            case "dbsnp":
                changeInput.placeholder = "e.g. rs146261631";
                break;
            default:
                geneInput.placeholder = "e.g. BRCA1";
                changeInput.placeholder = "e.g. Q804H";
        }
    }

    levelSelect.addEventListener("change", (e) => {
        updateFieldsBasedOnLevel(e.target.value);
    });

    function stopGeneration() {
        if (abortController) {
            abortController.abort();
            abortController = null;
        }
        loadingOverlay.style.display = "none";
    }

    stopBtn.addEventListener("click", stopGeneration);

    document.addEventListener("keydown", (e) => {
        const evidenceModalEl = document.getElementById("articleEvidenceModal");
        const aboutModalEl = document.getElementById("aboutModal");
        const helpModalEl = document.getElementById("helpModal");

        if (e.key === "Escape") {
            if (loadingOverlay.style.display === "flex") {
                stopGeneration();
            } else {
                if (evidenceModalEl.classList.contains("show")) articleEvidenceModal.hide();
                if (aboutModalEl.classList.contains("show")) aboutModal.hide();
                if (helpModalEl.classList.contains("show")) helpModal.hide();
            }
        }

        if (evidenceModalEl.classList.contains("show")) {
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
        sessionStorage.removeItem("variant_summary_result");
        loadingOverlay.style.display = "flex";
        loadingStatus.textContent = "Initializing...";
        loadingSubtext.textContent = "This may take a minute.";
        relevanceProgressContainer.style.display = "none";
        relevanceProgressBar.style.width = "0%";

        const formData = {
            gene: geneInput.value.trim(),
            change: changeInput.value.trim(),
            level: levelSelect.value
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
                throw new Error(`Failed to generate summary: ${data.detail}`);
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
            resultContainer.style.display = "none";
        }
    });

    let currentTotalCalls = 0;
    let currentCompletedCalls = 0;

    function handleProgressUpdate(data) {
        if (data.error) {
            displayStreamingError(data.error);
            return;
        }

        if (data.total_calls !== undefined) {
            currentTotalCalls = data.total_calls;
            updateProgressBar();
        }

        if (data.completed_calls !== undefined) {
            currentCompletedCalls = data.completed_calls;
            updateProgressBar();
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

    function displayStreamingError(message) {
        console.error("Streaming Error:", message);
        errorMessage.textContent = message;
        errorAlert.style.display = "block";
        loadingOverlay.style.display = "none";
        resultContainer.style.display = "none";

        if (abortController) {
            abortController.abort();
            abortController = null;
        }
    }

    function updateProgressBar() {
        if (currentTotalCalls > 0) {
            const percent = (currentCompletedCalls / currentTotalCalls) * 100;
            relevanceProgressContainer.style.display = "flex";
            relevanceProgressBar.style.width = `${percent}%`;
        }
    }

    function formatNarrativeSummary(rawText) {
        if (!rawText) return "";
        const rawHtml = marked.parse(rawText);
        const cleanHtml = DOMPurify.sanitize(rawHtml);
        return linkifyReferences(cleanHtml);
    }

    function displayResult(result) {
        loadingOverlay.style.display = "none";
        abortController = null;

        currentArticleEvidences = result.article_evidences || [];
        sessionStorage.setItem("variant_summary_result", JSON.stringify(result));

        if (typeof result === "string") {
            summaryContent.textContent = result;
            structuredContainer.style.display = "none";
            externalLinksContainer.style.display = "none";
        } else {
            const narrative = result.narrative_summary || "No narrative summary available.";
            summaryContent.innerHTML = formatNarrativeSummary(narrative);

            if (result.structured_summary) {
                const ss = result.structured_summary;
                pathogenicityValue.textContent = ss.overall_pathogenicity || "unknown";
                confidenceValue.textContent = ss.overall_confidence || "unknown";

                const pathColor = getPathogenicityColor(ss.overall_pathogenicity);
                pathogenicityValue.className = `badge rounded-pill bg-${pathColor} evidence-badge text-capitalize`;

                const confColor = getConfidenceColor(ss.overall_confidence);
                confidenceValue.className = `badge rounded-pill bg-${confColor} evidence-badge text-capitalize`;

                pathogenicityCounts.innerHTML = "";
                if (ss.pathogenicity_counts) {
                    Object.entries(ss.pathogenicity_counts).forEach(([path, count]) => {
                        if (count === 0) return;

                        const badge = document.createElement("span");
                        const pathColor = getPathogenicityColor(path);
                        badge.className = `badge rounded-pill bg-${pathColor} evidence-badge text-capitalize me-1 mb-1`;
                        badge.textContent = `${path}: ${count}`;
                        badge.style.pointerEvents = "none";
                        badge.style.userSelect = "none";

                        pathogenicityCounts.appendChild(badge);
                    });
                }

                conflictWarning.style.display = ss.conflicting_evidence ? "block" : "none";
                structuredContainer.style.display = "block";
            } else {
                structuredContainer.style.display = "none";
            }

            const hasClinVar = result.clinvar_urls && result.clinvar_urls.length > 0;
            const hasOmim = !!result.omim_url;

            if (hasClinVar || hasOmim) {
                renderExternalLinks(result.clinvar_urls, result.omim_url, result.gene);
                externalLinksContainer.style.display = "block";
            } else {
                externalLinksContainer.style.display = "none";
            }
        }

        renderGroupedEvidences(currentArticleEvidences);

        resultContainer.style.display = "block";
        resultContainer.scrollIntoView({ behavior: "smooth" });
    }

    function renderExternalLinks(clinvarUrls, omimUrl, geneName) {
        clinvarLinksList.innerHTML = "";
        if (clinvarUrls && clinvarUrls.length > 0) {
            clinvarUrls.forEach(url => {
                const clinvarId = url.split("/").pop();
                const a = document.createElement("a");
                a.href = url;
                a.target = "_blank";
                a.className = "btn btn-sm btn-outline-primary";
                a.innerHTML = `Variation ${clinvarId} ↗`;
                clinvarLinksList.appendChild(a);
            });
        } else {
            clinvarLinksList.innerHTML = '<span class="text-muted small">No ClinVar records found.</span>';
        }

        omimLinkContainer.innerHTML = "";
        if (omimUrl) {
            const a = document.createElement("a");
            a.href = omimUrl;
            a.target = "_blank";
            a.className = "btn btn-sm btn-outline-primary";

            if (geneName) {
                a.innerHTML = `gene ${geneName} ↗`;
            } else {
                const omimId = omimUrl.split("/").pop();
                a.innerHTML = `Entry ${omimId} ↗`;
            }

            omimLinkContainer.appendChild(a);
        } else {
            omimLinkContainer.innerHTML = '<span class="text-muted small">No OMIM records found.</span>';
        }
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

            geneInput.value = "BRCA1";
            changeInput.value = "R7C";
            levelSelect.value = "protein";
            updateFieldsBasedOnLevel("protein");

            errorAlert.style.display = "none";
            resultContainer.style.display = "none";
            loadingOverlay.style.display = "flex";
            loadingStatus.textContent = "Initializing (Mock)...";
            loadingSubtext.textContent = "Simulation started";
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

    function getPathogenicityColor(pathogenicityLevel) {
        if (!pathogenicityLevel) return "secondary";
        const p = pathogenicityLevel.toLowerCase();
        if (p.includes("supports pathogenicity") || p.includes("pathogenic")) return "danger";
        if (p.includes("supports benignity") || p.includes("benign")) return "success";
        if (p.includes("no claim")) return "info";
        if (p.includes("uncertain") || p.includes("vus")) return "secondary";
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
        return text.replace(/\b(PMC\d+)|(\d{5,})\b/gi, (match) => {
            const cleanId = match.replace(/^PMC/i, "").trim();
            const prefix = match.toUpperCase().startsWith("PMC") ? "PMC" : "";
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
            a.mentions && a.mentions.some(m => {
                return m.mention_type.toLowerCase() === type.toLowerCase();
            })
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

        const isPMC = articleId.toString().toUpperCase().startsWith("PMC");
        const cleanId = articleId.toString().replace(/^PMC/i, "");
        const externalUrl = isPMC
            ? `https://pmc.ncbi.nlm.nih.gov/articles/PMC${cleanId}/`
            : `https://pubmed.ncbi.nlm.nih.gov/${cleanId}/`;

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

        const isSupplOnly = article.data_sources &&
                            article.data_sources.length === 1 &&
                            article.data_sources[0] === "suppl";

        const supplBadgeHtml = isSupplOnly
            ? `<span class="badge bg-light text-dark border evidence-badge ms-1 align-middle" title="Information found only in supplementary data">
                 <span class="text-info d-inline-flex align-items-center">
                   <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" class="bi bi-info-circle me-1" viewBox="0 0 16 16">
                     <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16"/>
                     <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0"/>
                   </svg>
                   <small>only in suppl. data</small>
                 </span>
               </span>`
            : "";

        let html = `
            <div class="mb-3">
                <h5 class="text-primary">${escapeHtml(article.title + " (" + article.pub_year + ")" || "Title not available")}</h5>
                <div class="d-flex align-items-center mb-3">
                    <a href="${externalUrl}" target="_blank" class="btn btn-sm btn-outline-secondary">
                        View on ${isPMC ? 'PMC' : 'PubMed'} ↗
                    </a>
                    ${supplBadgeHtml ? supplBadgeHtml.replace('ms-1', 'ms-2') : ""}
                </div>
            </div>
            <div class="mb-4">
                <h6><strong>Article Conclusion:</strong></h6>
                <p>${escapeHtml(article.overall_article_summary || "N/A")}</p>
            </div>
        `;

        if (article.mentions && article.mentions.length > 0) {
            html += `<h6><strong>Evidences:</strong></h6>`;
            article.mentions.forEach(m => {
                const claimValue = m.claim ? (m.claim.split(':').pop().replace(/['>]/g, '').trim()) : "no claim";
                const claimColor = getClaimColor(claimValue);
                const mentionType = m.mention_type ? (m.mention_type.split(':').pop().replace(/['>]/g, '').trim()) : "unknown";

                html += `
                    <div class="evidence-item mb-3 p-2 bg-light border-start border-4">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span class="badge evidence-type-badge bg-info text-dark">${escapeHtml(mentionType)}</span>
                            <span class="badge evidence-badge text-capitalize bg-${claimColor}">${escapeHtml(claimValue)}</span>
                        </div>
                        ${m.quoted_text ? `
    <div class="mb-0 mt-2 italic text-muted small quote-container"
         style="font-style: italic; white-space: pre-wrap; margin: 0; padding: 0;">${DOMPurify.sanitize(marked.parse(m.quoted_text.trim().replace(/\\n/g, '\n')))}</div>` : ""}
                    </div>
                `;
            });
        } else {
            html += `<p class="text-muted">No specific mentions extracted.</p>`;
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

        function scoreArticle(article) {
            if (!article || !article.mentions) return 0;
            const weights = { high: 4, moderate: 2 };
            let score = 0;
            for (const m of article.mentions) {
                const claim = (m.claim || "").toLowerCase();
                if (!claim) continue;
                const strengthStr = m.strength ? m.strength.split(':').pop().replace(/['>]/g, '').trim().toLowerCase() : "low";
                const w = weights[strengthStr] ?? 1;
                score += w;
            }
            return score;
        }

        sortedArticlesForModal = [...articles].sort((a, b) => {
            const sa = scoreArticle(a);
            const sb = scoreArticle(b);
            return sb - sa;
        });

        groupedEvidenceBody.innerHTML = "";
        sortedArticlesForModal.forEach((article, index) => {
            const card = document.createElement("div");
            card.className = "card m-3 article-card";
            card.tabIndex = 0;

            let evidenceListHtml = "";
            if (article.mentions) {
                article.mentions.forEach(m => {
                    const claimValue = m.claim ? (m.claim.split(':').pop().replace(/['>]/g, '').trim()) : "no claim";
                    const mentionType = m.mention_type ? (m.mention_type.split(':').pop().replace(/['>]/g, '').trim()) : "unknown";
                    const claimColor = getClaimColor(claimValue);

                    evidenceListHtml += `<span class="badge bg-light text-dark border evidence-badge me-1 mb-1"
                               title="${escapeHtml(m.quoted_text ? m.quoted_text.trim() : '')}">
        <small>${escapeHtml(mentionType)}: </small><span class="text-${claimColor}">${escapeHtml(claimValue)}</span>
    </span>`;
                });
            }

            const isSupplOnly = article.data_sources &&
                                article.data_sources.length === 1 &&
                                article.data_sources[0] === "suppl";

            const supplBadgeHtml = isSupplOnly
                ? `<span class="badge bg-light text-dark border evidence-badge ms-2 align-middle" title="Information found only in supplementary data">
                     <span class="text-info d-inline-flex align-items-center">
                       <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="currentColor" class="bi bi-info-circle me-1" viewBox="0 0 16 16">
                         <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16"/>
                         <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0"/>
                       </svg>
                       <small>only in suppl. data</small>
                     </span>
                   </span>`
                : "";

            card.innerHTML = `
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <h6 class="card-title mb-0 d-flex align-items-center">Article: ${escapeHtml(article.article_id)}${supplBadgeHtml}</h6>
                        <button class="btn btn-sm btn-outline-primary view-details-btn">View Details</button>
                    </div>
                    <p class="card-text small mb-2 text-muted">${escapeHtml(article.overall_article_summary || "No conclusion provided.")}</p>
                    <div class="evidence-summary-list">
                        ${evidenceListHtml}
                    </div>
                </div>
            `;

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
        return getPathogenicityColor(claim);
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
