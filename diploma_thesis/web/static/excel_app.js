import { batchConvertAndApplyPubmedLinks } from "./utils.js";
import { showError, showSuccess, hideMessages, showModal } from "./dom_helpers.js";

document.addEventListener("DOMContentLoaded", () => {
  // -------------------- DOM Elements --------------------
  const uploadForm = document.getElementById("upload-form");
  const fileInput = document.getElementById("file-input");
  const errorMessage = document.getElementById("error-message");
  const successMessage = document.getElementById("success-message");
  const editorContainer = document.getElementById("editor-container");
  const currentFileName = document.querySelector("#current-file span");
  const exportXlsxBtn = document.getElementById("export-xlsx");
  const exportCsvBtn = document.getElementById("export-csv");
  const hotContainer = document.getElementById("hot-container");
  const confirmOverwriteBtn = document.getElementById("confirmOverwrite");
  const confirmOverwriteModal = new bootstrap.Modal(document.getElementById("confirmOverwriteModal"));

  const summaryModalEl = document.getElementById("summaryModal");
  const summaryModalBody = document.getElementById("summaryModalBody");
  const summaryModal = new bootstrap.Modal(summaryModalEl);

  // -------------------- State --------------------
  let hot;
  let currentData = null;
  let originalFileName = "";
  let pendingFile = null;

  // -------------------- Helpers --------------------
  function createCosmicLinks(value) {
    if (!value) return "";
    return value
      .split(",")
      .map(id => `<a href="https://cancer.sanger.ac.uk/cosmic/search?q=${id.trim()}" target="_blank">${id.trim()}</a>`)
      .join(", ");
  }

  const bgColorRenderer = (instance, td, row, col, prop, value, cellProperties) => {
    Handsontable.renderers.TextRenderer(instance, td, row, col, prop, value, cellProperties);

    if (value === 'Benign') {
     td.style.background = 'rgba(86,177,68,0.85)';
    } else if (value === 'Benign/Likely_benign') {
        td.style.background = 'rgba(181,234,169,0.85)';
      } else if (value === 'Likely_benign') {
        td.style.background = 'rgba(255,233,195,0.85)';
      } else if (value === 'Conflicting_classifications_of_pathogenicity') {
        td.style.background = 'rgba(255,193,87,0.85)';
      }
  };

  // maps function to a lookup string
  Handsontable.renderers.registerRenderer('bgColorRenderer', bgColorRenderer);

  // -------------------- Upload --------------------
  async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);
    hideMessages(errorMessage, successMessage);

    try {
      const response = await fetch("/api/excel/upload", { method: "POST", body: formData });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Error uploading file");
      }

      const data = await response.json();
      currentData = data.data;
      originalFileName = data.filename;

      showSuccess(successMessage, errorMessage, `File "${originalFileName}" uploaded successfully.`);
      currentFileName.textContent = originalFileName;
      editorContainer.style.display = "block";

      initializeHandsontable(currentData);
    } catch (error) {
      showError(errorMessage, successMessage, error.message);
    }
  }

  uploadForm.addEventListener("submit", e => {
    e.preventDefault();
    const file = fileInput.files[0];
    if (!file) { showError(errorMessage, successMessage, "Please select a file to upload."); return; }

    if (file.name.split(".").pop().toLowerCase() !== "xlsx") {
      showError(errorMessage, successMessage, "Only .xlsx files are supported.");
      return;
    }

    if (currentData !== null) {
      pendingFile = file;
      confirmOverwriteModal.show();
    } else { uploadFile(file); }
  });

  confirmOverwriteBtn.addEventListener("click", () => {
    confirmOverwriteModal.hide();
    if (pendingFile) { uploadFile(pendingFile); pendingFile = null; }
  });

  // -------------------- Handsontable --------------------
  function initializeHandsontable(data) {
    if (hot) hot.destroy();

    let cosmicCol = -1, pubmedCol = -1, clinvarSignCol = -1;
    if (data?.length) {
      const headers = data[0];
      cosmicCol = headers.indexOf("COSMIC");
      pubmedCol = headers.indexOf("PUBMED");
      clinvarSignCol = headers.indexOf("clinvar_sig");
    }

    hot = new Handsontable(hotContainer, {
      data,
      rowHeaders: true,
      colHeaders: true,
      contextMenu: {
        items: {
          "generateLLMSummary": {
            name: "Generate LLM summary",
            callback: (_, selection) => {
              const rowIndex = selection[0].start.row;
              const rowId = hot.getDataAtRow(rowIndex)[0];
              generateLLMSummary(rowId);
            }
          },
          "sep1": "---------",
          "copy": {},
          "remove_row": {}
        }
      },
      colWidths: 250,
      manualColumnResize: true,
      manualRowResize: true,
      licenseKey: 'non-commercial-and-evaluation',
      stretchH: 'all',
      autoColumnSize: true,
      minSpareRows: 1,
      minSpareCols: 1,
      height: '100%',
      width: '100%',
      filters: true,
      dropdownMenu: true,
      formulas: true,
      fixedRowsTop: 1,
      cells: (row, col) => {
        const cellProps = {};
        if (row === 0) cellProps.className = 'first-row-bold';
        if (cosmicCol !== -1 && col === cosmicCol && row > 0) {
          cellProps.renderer = (_, td, row, col, prop, value) => {
            td.innerHTML = value ? createCosmicLinks(value) : "";
            return td;
          };
        }
        if (pubmedCol !== -1 && col === pubmedCol && row > 0) cellProps.renderer = "html";
        if (clinvarSignCol !== -1 && col === clinvarSignCol && row > 0) cellProps.renderer = "bgColorRenderer";
        return cellProps;
      }
    });

    if (pubmedCol !== -1) {
      batchConvertAndApplyPubmedLinks(hot, pubmedCol)
        .catch(error => { console.error(error); showError(errorMessage, successMessage, "Error converting PubMed IDs: " + error.message); });
    }
  }

  // -------------------- LLM Summary --------------------
  async function generateLLMSummary(rowId) {
    try {
      const response = await fetch("/api/generate-llm-summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ row_id: rowId })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Error generating LLM summary");
      }

      const data = await response.json();
      showModal(summaryModal, summaryModalBody, data.result);
    } catch (error) {
      showModal(summaryModal, summaryModalBody, "Error: " + error.message);
    }
  }

  // -------------------- Export --------------------
  async function exportFile(format) {
    if (!currentData) { showError(errorMessage, successMessage, "No data to export."); return; }
    const data = hot.getData(0, 0, hot.countRows() - 1, hot.countCols() - 1, true);
    const filename = format === "csv" ? originalFileName.replace(".xlsx", ".csv") : originalFileName;
    const contentType = format === "csv" ? "text/csv" : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

    try {
      const response = await fetch(`/api/excel/export/${format}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data, filename })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Error exporting file");
      }

      const blob = new Blob([await response.arrayBuffer()], { type: contentType });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      showSuccess(successMessage, errorMessage, `File exported successfully as ${format.toUpperCase()}.`);
    } catch (error) {
      showError(errorMessage, successMessage, error.message);
    }
  }

  exportXlsxBtn.addEventListener("click", () => exportFile("xlsx"));
  exportCsvBtn.addEventListener("click", () => exportFile("csv"));
});
