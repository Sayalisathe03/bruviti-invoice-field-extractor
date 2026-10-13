"""FastAPI application providing /extract API, /health probe, and single-page UI."""

from pathlib import Path
from typing import Any, Dict
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from app.extractor import extract_invoice
from app.pdf_reader import (
    CorruptPDFError,
    InvalidPDFError,
    NoExtractableTextError,
    extract_text_from_pdf_bytes,
)
from app.schemas import ExtractionResponse, HealthResponse

app = FastAPI(
    title="Bruviti Invoice Field Extraction Service",
    description="Offline service extracting normalized header fields and confidence scores from digital PDF invoices.",
    version="1.0.0",
)

# HTML UI Template (self-contained, offline, enterprise-grade design, no external CSS/fonts/scripts)
UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bruviti Document Intelligence | Invoice Field Extractor</title>
  <style>
    :root {
      --bg: #090d16;
      --card-bg: #111827;
      --card-subtle: #172033;
      --border: #1f293d;
      --border-focus: #38bdf8;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --text-dim: #6b7280;
      --primary: #38bdf8;
      --primary-hover: #0284c7;
      --accent: #6366f1;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --radius-sm: 6px;
      --radius: 10px;
      --radius-lg: 14px;
      --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: var(--font);
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 24px;
      -webkit-font-smoothing: antialiased;
    }
    .container {
      max-width: 1180px;
      margin: 0 auto;
    }
    /* Top Navbar */
    .nav-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 24px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-icon {
      width: 36px;
      height: 36px;
      border-radius: var(--radius-sm);
      background: linear-gradient(135deg, #38bdf8, #6366f1);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #0f172a;
      font-weight: 800;
      font-size: 1.1rem;
    }
    .brand-title {
      font-size: 1.25rem;
      font-weight: 700;
      color: #fff;
      letter-spacing: -0.02em;
    }
    .brand-tag {
      font-size: 0.8rem;
      color: var(--text-muted);
    }
    .nav-status {
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 6px 14px;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      color: #34d399;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: #10b981;
      box-shadow: 0 0 8px #10b981;
    }

    /* Cards */
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: 24px;
      margin-bottom: 24px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }

    /* Presets bar */
    .presets-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 20px;
      background: var(--card-subtle);
      padding: 12px 16px;
      border-radius: var(--radius);
      border: 1px solid var(--border);
    }
    .preset-label {
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
      margin-right: 6px;
    }
    .preset-btn {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      color: #e2e8f0;
      padding: 5px 12px;
      border-radius: var(--radius-sm);
      font-size: 0.78rem;
      cursor: pointer;
      transition: all 0.15s ease;
      font-family: inherit;
    }
    .preset-btn:hover {
      background: rgba(56, 189, 248, 0.15);
      border-color: var(--primary);
      color: var(--primary);
    }

    /* Upload Area */
    .dropzone {
      border: 2px dashed #2d3748;
      border-radius: var(--radius);
      padding: 40px 20px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s ease;
      background: rgba(23, 32, 51, 0.4);
    }
    .dropzone:hover, .dropzone.dragover {
      border-color: var(--primary);
      background: rgba(56, 189, 248, 0.04);
    }
    .dropzone input { display: none; }
    .upload-icon {
      width: 48px;
      height: 48px;
      margin: 0 auto 12px;
      color: var(--primary);
      opacity: 0.9;
    }
    .dropzone h3 {
      font-size: 1.05rem;
      font-weight: 600;
      color: #f8fafc;
      margin-bottom: 4px;
    }
    .dropzone p {
      font-size: 0.85rem;
      color: var(--text-muted);
    }
    .file-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.3);
      color: var(--primary);
      padding: 6px 14px;
      border-radius: var(--radius-sm);
      margin-top: 14px;
      font-size: 0.85rem;
      font-weight: 500;
    }

    /* Actions */
    .actions-bar {
      display: flex;
      justify-content: flex-end;
      align-items: center;
      gap: 12px;
      margin-top: 16px;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 18px;
      font-size: 0.9rem;
      font-weight: 600;
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: all 0.15s ease;
      border: none;
      font-family: inherit;
    }
    .btn-primary {
      background: linear-gradient(135deg, #38bdf8, #0284c7);
      color: #0f172a;
    }
    .btn-primary:hover:not(:disabled) {
      filter: brightness(1.1);
      box-shadow: 0 4px 12px rgba(56, 189, 248, 0.3);
    }
    .btn-primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .btn-secondary {
      background: transparent;
      color: var(--text-muted);
      border: 1px solid var(--border);
    }
    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.05);
      color: var(--text);
    }

    /* Loading Spinner */
    .spinner {
      display: none;
      margin: 20px auto;
      width: 38px;
      height: 38px;
      border: 3px solid rgba(56, 189, 248, 0.2);
      border-top-color: var(--primary);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* Alerts */
    .alert {
      padding: 14px 18px;
      border-radius: var(--radius);
      margin-top: 16px;
      font-size: 0.9rem;
      display: flex;
      align-items: flex-start;
      gap: 12px;
    }
    .alert-error {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #fca5a5;
    }
    .alert-warning {
      background: rgba(245, 158, 11, 0.1);
      border: 1px solid rgba(245, 158, 11, 0.3);
      color: #fcd34d;
    }

    /* Results Dashboard */
    .results-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 20px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .vendor-pill {
      font-size: 1.35rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 3px 10px;
      font-size: 0.75rem;
      font-weight: 600;
      border-radius: 9999px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .badge-success { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-warning { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-danger { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-info { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }

    /* 2-Column Grid Layout */
    .grid-2col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }
    @media (max-width: 900px) {
      .grid-2col { grid-template-columns: 1fr; }
    }

    /* Field Panels */
    .panel {
      background: var(--card-subtle);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 18px;
      margin-bottom: 16px;
    }
    .panel-title {
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-muted);
      font-weight: 700;
      margin-bottom: 12px;
      display: flex;
      justify-content: space-between;
    }

    .key-value-row {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      padding: 8px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    }
    .key-value-row:last-child { border-bottom: none; }
    .k-label { font-size: 0.85rem; color: var(--text-muted); }
    .k-val { font-size: 1rem; font-weight: 600; color: #fff; }
    .k-val-lg { font-size: 1.4rem; font-weight: 800; color: #38bdf8; }

    /* Confidence Bars */
    .confidence-item {
      margin-bottom: 12px;
    }
    .confidence-item:last-child { margin-bottom: 0; }
    .conf-header {
      display: flex;
      justify-content: space-between;
      font-size: 0.8rem;
      margin-bottom: 4px;
    }
    .conf-bar-bg {
      height: 6px;
      background: #1f293d;
      border-radius: 9999px;
      overflow: hidden;
    }
    .conf-bar-fill {
      height: 100%;
      border-radius: 9999px;
      transition: width 0.4s ease;
    }

    /* Tabs & JSON display */
    .tabs-header {
      display: flex;
      gap: 8px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 12px;
    }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 8px 14px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.15s ease;
    }
    .tab-btn.active {
      color: var(--primary);
      border-bottom-color: var(--primary);
    }
    .tab-content { display: none; }
    .tab-content.active { display: block; }

    pre {
      background: #090d16;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px;
      overflow-x: auto;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.82rem;
      color: #7dd3fc;
      max-height: 480px;
    }

    .table-audit {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
    }
    .table-audit th {
      text-align: left;
      padding: 8px 10px;
      color: var(--text-muted);
      font-size: 0.75rem;
      text-transform: uppercase;
      border-bottom: 1px solid var(--border);
    }
    .table-audit td {
      padding: 10px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    }

    .hidden { display: none !important; }
  </style>
</head>
<body>
  <div class="container">
    <!-- Navbar -->
    <div class="nav-bar">
      <div class="brand">
        <div class="brand-icon">B</div>
        <div>
          <div class="brand-title">Bruviti Invoice Field Extractor</div>
          <div class="brand-tag">Enterprise Supplier Invoice Field Extraction Engine</div>
        </div>
      </div>
      <div class="nav-status">
        <div class="status-dot"></div>
        <span>ENGINE READY • CPU OFFLINE</span>
      </div>
    </div>

    <!-- Main Upload Card -->
    <div class="card">
      <!-- Quick Test Presets -->
      <div class="presets-bar">
        <span class="preset-label">Quick Test Presets:</span>
        <button class="preset-btn" onclick="loadSamplePreset('northwind_standard.pdf')">Northwind (UK • GBP)</button>
        <button class="preset-btn" onclick="loadSamplePreset('kestrel_0311.pdf')">Kestrel (US • Net 30)</button>
        <button class="preset-btn" onclick="loadSamplePreset('meridian_industrial_german.pdf')">Meridian (DE • EUR)</button>
        <button class="preset-btn" onclick="loadSamplePreset('sakura_precision_jpy.pdf')">Sakura (JP • JPY)</button>
        <button class="preset-btn" onclick="loadSamplePreset('pinecrest_packaging_inr.pdf')">Pinecrest (IN • INR)</button>
        <button class="preset-btn" onclick="loadSamplePreset('non_invoice_quotation.pdf')">Quotation (Rule O4)</button>
        <button class="preset-btn" onclick="loadSamplePreset('unknown_vendor.pdf')">Unknown Vendor</button>
      </div>

      <!-- Dropzone -->
      <div class="dropzone" id="dropZone" onclick="document.getElementById('fileInput').click()">
        <svg class="upload-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <h3>Choose an invoice PDF or drag & drop</h3>
        <p>Supports digital text-layer PDF documents for all six canonical vendors</p>
        <input type="file" id="fileInput" accept=".pdf" onchange="handleFileSelected(event)">
        <div id="fileBadge" class="file-badge hidden"></div>
      </div>

      <!-- Action Bar -->
      <div class="actions-bar">
        <button id="resetBtn" class="btn btn-secondary hidden" onclick="resetForm()">Clear</button>
        <button id="extractBtn" class="btn btn-primary" onclick="uploadAndExtract()" disabled>
          <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24"><path d="M5 3v18l15-9L5 3z"/></svg>
          Extract Invoice Fields
        </button>
      </div>

      <div id="spinner" class="spinner"></div>
      <div id="errorMessage" class="alert alert-error hidden"></div>
    </div>

    <!-- Results Section -->
    <div id="resultsCard" class="card hidden">
      <div class="results-header">
        <div>
          <div class="vendor-pill" id="resVendorName">
            Northwind Traders
          </div>
          <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;" id="resVendorMeta">
            Canonical Vendor Match • United Kingdom
          </div>
        </div>
        <div id="docStatusBadge">
          <span class="badge badge-success">Valid Invoice</span>
        </div>
      </div>

      <!-- Warnings Alert Banner -->
      <div id="warningsBanner" class="alert alert-warning hidden">
        <svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20" style="flex-shrink:0;">
          <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <div>
          <div style="font-weight:700; margin-bottom: 4px;">Processing Notices & Heuristic Audit</div>
          <ul id="warningsList" style="padding-left: 18px;"></ul>
        </div>
      </div>

      <!-- 2-Column Grid -->
      <div class="grid-2col" style="margin-top: 20px;">
        <!-- Left Column: Business Summary & Confidences -->
        <div>
          <!-- Identification Panel -->
          <div class="panel">
            <div class="panel-title">Document Identification & Dates</div>
            <div class="key-value-row">
              <span class="k-label">Invoice Number</span>
              <span class="k-val" id="resInvoiceNum">—</span>
            </div>
            <div class="key-value-row">
              <span class="k-label">Invoice Date</span>
              <span class="k-val" id="resInvoiceDate">—</span>
            </div>
            <div class="key-value-row">
              <span class="k-label">Due Date</span>
              <span class="k-val" id="resDueDate">—</span>
            </div>
            <div class="key-value-row">
              <span class="k-label">Currency</span>
              <span class="badge badge-info" id="resCurrency">—</span>
            </div>
          </div>

          <!-- Financial Breakdown Panel -->
          <div class="panel">
            <div class="panel-title">
              <span>Financial Breakdown</span>
              <span id="arithmeticBadge" class="badge badge-success">Balanced</span>
            </div>
            <div class="key-value-row">
              <span class="k-label">Subtotal</span>
              <span class="k-val" id="resSubtotal">—</span>
            </div>
            <div class="key-value-row">
              <span class="k-label">Tax Total</span>
              <span class="k-val" id="resTax">—</span>
            </div>
            <div class="key-value-row" style="margin-top: 6px; padding-top: 10px; border-top: 1px solid var(--border);">
              <span class="k-label" style="font-weight: 700; color: #fff;">Amount Payable (Total)</span>
              <span class="k-val-lg" id="resTotal">—</span>
            </div>
          </div>

          <!-- Field Confidences -->
          <div class="panel">
            <div class="panel-title">Extraction Confidence Breakdown</div>
            <div id="confidenceBarsContainer"></div>
          </div>
        </div>

        <!-- Right Column: Normalized JSON and Audit Table -->
        <div>
          <div class="tabs-header">
            <button class="tab-btn active" onclick="switchTab('jsonTab')">Normalized JSON</button>
            <button class="tab-btn" onclick="switchTab('auditTab')">Field Audit Table</button>
          </div>

          <!-- Tab 1: JSON -->
          <div id="jsonTab" class="tab-content active">
            <div style="display: flex; justify-content: flex-end; gap: 8px; margin-bottom: 8px;">
              <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.75rem;" onclick="copyJsonToClipboard()">
                <span id="copyBtnText">Copy JSON</span>
              </button>
            </div>
            <pre id="jsonViewer"></pre>
          </div>

          <!-- Tab 2: Audit Table -->
          <div id="auditTab" class="tab-content">
            <table class="table-audit">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Extracted Value</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody id="auditTableBody"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    let currentFile = null;
    let lastJsonData = null;

    function handleFileSelected(event) {
      const file = event.target.files[0];
      if (file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
          showError('Please select a valid PDF file.');
          return;
        }
        currentFile = file;
        const badge = document.getElementById('fileBadge');
        badge.innerHTML = '📄 ' + escapeHtml(file.name) + ' (' + (file.size / 1024).toFixed(1) + ' KB)';
        badge.classList.remove('hidden');
        document.getElementById('extractBtn').disabled = false;
        document.getElementById('resetBtn').classList.remove('hidden');
        document.getElementById('errorMessage').classList.add('hidden');
      }
    }

    // Drag and drop handlers
    const dropZone = document.getElementById('dropZone');
    ['dragenter', 'dragover'].forEach(name => {
      dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
    });
    ['dragleave', 'drop'].forEach(name => {
      dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.remove('dragover'); });
    });
    dropZone.addEventListener('drop', (e) => {
      if (e.dataTransfer.files.length) {
        document.getElementById('fileInput').files = e.dataTransfer.files;
        handleFileSelected({ target: { files: e.dataTransfer.files } });
      }
    });

    async function loadSamplePreset(filename) {
      try {
        const response = await fetch('/sample/' + filename);
        if (!response.ok) throw new Error('Sample not found');
        const blob = await response.blob();
        const file = new File([blob], filename, { type: 'application/pdf' });
        currentFile = file;

        const badge = document.getElementById('fileBadge');
        badge.innerHTML = '📄 Preset: ' + escapeHtml(filename) + ' (' + (file.size / 1024).toFixed(1) + ' KB)';
        badge.classList.remove('hidden');
        document.getElementById('extractBtn').disabled = false;
        document.getElementById('resetBtn').classList.remove('hidden');
        document.getElementById('errorMessage').classList.add('hidden');

        // Automatically trigger extraction for quick testing
        uploadAndExtract();
      } catch (err) {
        showError('Unable to load preset: ' + err.message);
      }
    }

    async function uploadAndExtract() {
      if (!currentFile) return;

      const spinner = document.getElementById('spinner');
      const extractBtn = document.getElementById('extractBtn');
      const errBox = document.getElementById('errorMessage');
      const resultsCard = document.getElementById('resultsCard');

      spinner.style.display = 'block';
      extractBtn.disabled = true;
      errBox.classList.add('hidden');
      resultsCard.classList.add('hidden');

      const formData = new FormData();
      formData.append('file', currentFile);

      try {
        const response = await fetch('/extract', {
          method: 'POST',
          body: formData
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || data.error || ('HTTP Error ' + response.status));
        }

        lastJsonData = data;
        renderResults(data);
      } catch (err) {
        showError(err.message || 'An error occurred during extraction.');
      } finally {
        spinner.style.display = 'none';
        extractBtn.disabled = false;
      }
    }

    function renderResults(data) {
      const resultsCard = document.getElementById('resultsCard');
      const jsonViewer = document.getElementById('jsonViewer');
      const warningsBanner = document.getElementById('warningsBanner');
      const warningsList = document.getElementById('warningsList');

      jsonViewer.innerText = JSON.stringify(data, null, 2);

      // Vendor Info
      document.getElementById('resVendorName').innerText = data.vendor || 'unknown';
      document.getElementById('resInvoiceNum').innerText = data.invoice_number != null ? data.invoice_number : '—';
      document.getElementById('resInvoiceDate').innerText = data.invoice_date || '—';
      document.getElementById('resDueDate').innerText = data.due_date || '—';
      document.getElementById('resCurrency').innerText = data.currency || 'None';

      const currSym = data.currency === 'USD' ? '$' : data.currency === 'GBP' ? '£' : data.currency === 'EUR' ? '€' : data.currency === 'JPY' ? '¥' : data.currency === 'INR' ? '₹' : '';

      document.getElementById('resSubtotal').innerText = data.subtotal != null ? currSym + data.subtotal.toFixed(2) : '—';
      document.getElementById('resTax').innerText = data.tax != null ? currSym + data.tax.toFixed(2) : '—';
      document.getElementById('resTotal').innerText = data.total != null ? currSym + data.total.toFixed(2) : '—';

      // Status Badge (Invoice vs Non-Invoice)
      const statusBadge = document.getElementById('docStatusBadge');
      if (data.invoice_number == null && data.total == null && data.warnings.some(w => w.toLowerCase().includes('document detected as'))) {
        statusBadge.innerHTML = '<span class="badge badge-warning">Non-Invoice Document</span>';
      } else {
        statusBadge.innerHTML = '<span class="badge badge-success">Valid Invoice</span>';
      }

      // Warnings
      if (data.warnings && data.warnings.length > 0) {
        warningsList.innerHTML = data.warnings.map(w => '<li>' + escapeHtml(w) + '</li>').join('');
        warningsBanner.classList.remove('hidden');
      } else {
        warningsBanner.classList.add('hidden');
      }

      // Arithmetic Badge
      const arithBadge = document.getElementById('arithmeticBadge');
      if (data.warnings && data.warnings.some(w => w.includes('Arithmetic mismatch'))) {
        arithBadge.className = 'badge badge-danger';
        arithBadge.innerText = 'Mismatch';
      } else if (data.subtotal != null && data.total != null) {
        arithBadge.className = 'badge badge-success';
        arithBadge.innerText = 'Balanced ±0.01';
      } else {
        arithBadge.className = 'badge badge-info';
        arithBadge.innerText = 'N/A';
      }

      // Render Confidence Progress Bars
      const confContainer = document.getElementById('confidenceBarsContainer');
      const fields = [
        { label: 'Vendor Identification', key: 'vendor' },
        { label: 'Invoice Number', key: 'invoice_number' },
        { label: 'Invoice Date', key: 'invoice_date' },
        { label: 'Due Date', key: 'due_date' },
        { label: 'Currency', key: 'currency' },
        { label: 'Subtotal Amount', key: 'subtotal' },
        { label: 'Tax Amount', key: 'tax' },
        { label: 'Total Amount', key: 'total' }
      ];

      confContainer.innerHTML = fields.map(f => {
        const val = data.confidence[f.key] || 0.0;
        const pct = Math.round(val * 100);
        const color = pct >= 90 ? '#10b981' : pct >= 75 ? '#38bdf8' : pct > 0 ? '#f59e0b' : '#6b7280';
        return `
          <div class="confidence-item">
            <div class="conf-header">
              <span style="color:var(--text-muted);">${f.label}</span>
              <span style="font-weight:600; color:${color};">${pct}%</span>
            </div>
            <div class="conf-bar-bg">
              <div class="conf-bar-fill" style="width: ${pct}%; background-color: ${color};"></div>
            </div>
          </div>
        `;
      }).join('');

      // Render Audit Table
      const auditTbody = document.getElementById('auditTableBody');
      const auditRows = [
        { name: 'Vendor', val: data.vendor, conf: data.confidence.vendor },
        { name: 'Invoice Number', val: data.invoice_number, conf: data.confidence.invoice_number },
        { name: 'Invoice Date', val: data.invoice_date, conf: data.confidence.invoice_date },
        { name: 'Due Date', val: data.due_date, conf: data.confidence.due_date },
        { name: 'Currency', val: data.currency, conf: data.confidence.currency },
        { name: 'Subtotal', val: data.subtotal != null ? data.subtotal.toFixed(2) : null, conf: data.confidence.subtotal },
        { name: 'Tax', val: data.tax != null ? data.tax.toFixed(2) : null, conf: data.confidence.tax },
        { name: 'Total', val: data.total != null ? data.total.toFixed(2) : null, conf: data.confidence.total }
      ];

      auditTbody.innerHTML = auditRows.map(r => `
        <tr>
          <td style="font-weight:600; color:#fff;">${escapeHtml(r.name)}</td>
          <td>${r.val != null ? escapeHtml(String(r.val)) : '<span style="color:var(--text-dim)">null</span>'}</td>
          <td><span style="font-weight:600; color:${r.conf >= 0.9 ? '#10b981' : r.conf >= 0.75 ? '#38bdf8' : '#f59e0b'}">${(r.conf * 100).toFixed(0)}%</span></td>
        </tr>
      `).join('');

      resultsCard.classList.remove('hidden');
    }

    function switchTab(tabId) {
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      if (tabId === 'jsonTab') {
        document.querySelectorAll('.tab-btn')[0].classList.add('active');
        document.getElementById('jsonTab').classList.add('active');
      } else {
        document.querySelectorAll('.tab-btn')[1].classList.add('active');
        document.getElementById('auditTab').classList.add('active');
      }
    }

    function copyJsonToClipboard() {
      if (!lastJsonData) return;
      navigator.clipboard.writeText(JSON.stringify(lastJsonData, null, 2)).then(() => {
        const btnText = document.getElementById('copyBtnText');
        btnText.innerText = 'Copied!';
        setTimeout(() => { btnText.innerText = 'Copy JSON'; }, 2000);
      });
    }

    function resetForm() {
      currentFile = null;
      lastJsonData = null;
      document.getElementById('fileInput').value = '';
      document.getElementById('fileBadge').classList.add('hidden');
      document.getElementById('extractBtn').disabled = true;
      document.getElementById('resetBtn').classList.add('hidden');
      document.getElementById('errorMessage').classList.add('hidden');
      document.getElementById('resultsCard').classList.add('hidden');
    }

    function showError(msg) {
      const errBox = document.getElementById('errorMessage');
      errBox.innerText = msg;
      errBox.classList.remove('hidden');
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.innerText = text;
      return div.innerHTML;
    }
  </script>
</body>
</html>
"""


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
def health_check() -> Dict[str, str]:
    """Health probe returning HTTP 200 and {'status': 'ok'}."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse, tags=["UI"])
def serve_ui() -> HTMLResponse:
    """Serve the single-page offline HTML reviewer tool."""
    return HTMLResponse(content=UI_HTML, status_code=status.HTTP_200_OK)


@app.get("/sample/{filename}", include_in_schema=False)
def serve_sample_pdf(filename: str) -> FileResponse:
    """Serve synthetic fixture PDF for one-click UI preset demonstrations."""
    fixtures_dir = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
    target = fixtures_dir / filename
    if not target.exists() or not filename.endswith(".pdf"):
        raise HTTPException(status_code=404, detail="Sample fixture not found")
    return FileResponse(target, media_type="application/pdf", filename=filename)


@app.post("/extract", response_model=ExtractionResponse, tags=["Extraction"])
async def extract_invoice_endpoint(file: UploadFile = File(...)) -> ExtractionResponse:
    """
    Extract normalized header fields, confidence scores, and warnings from a digital PDF invoice.

    - Validates file format and digital text layer.
    - Operates completely offline with sub-second CPU latency.
    """
    # 1. Validate file presence and filename
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File upload is required under the form-data key 'file'.",
        )

    filename_lower = file.filename.lower()
    if not filename_lower.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.filename}'. Only PDF documents are supported.",
        )

    # 2. Read bytes safely into memory
    try:
        pdf_bytes = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(e)}",
        )

    # 3. Extract text layer with safety checks
    try:
        full_text, lines = extract_text_from_pdf_bytes(pdf_bytes)
    except InvalidPDFError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except CorruptPDFError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except NoExtractableTextError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error extracting text from PDF: {str(e)}",
        )

    # 4. Perform deterministic header field extraction
    try:
        response_data = extract_invoice(full_text=full_text, lines=lines)
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected extraction error occurred: {str(e)}",
        )
