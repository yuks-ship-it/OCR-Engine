const video        = document.getElementById('video');
const canvas       = document.getElementById('canvas');
const captureBtn   = document.getElementById('captureBtn');
const autoScanBtn  = document.getElementById('autoScanBtn');
const output       = document.getElementById('output');
const statusBadge  = document.getElementById('status-badge');
const videoWrapper = document.querySelector('.video-wrapper');

let isAutoScanning = false;
let scanInterval   = null;
let isProcessing   = false;

// ── Camera ────────────────────────────────────────────────────────────────────
async function startCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment' }
        });
        video.srcObject = stream;
        video.onloadedmetadata = () => {
            canvas.width  = video.videoWidth;
            canvas.height = video.videoHeight;
        };
    } catch (err) {
        setStatus('error');
        output.innerHTML = `<div class="processing-state" style="color:var(--red)">
            Camera access denied. Please grant permissions and reload.
        </div>`;
    }
}

// ── Canvas ────────────────────────────────────────────────────────────────────
function clearCanvas() {
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
}

function drawBoundingBoxes(detections) {
    const ctx = canvas.getContext('2d');
    clearCanvas();
    detections.forEach(det => {
        const [x1, y1, x2, y2] = det.bbox;
        ctx.strokeStyle = '#00e5a0';
        ctx.lineWidth   = 3;
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
        const label = `${det.class} ${((det.detection_confidence || det.confidence || 0) * 100).toFixed(0)}%`;
        ctx.font = '14px monospace';
        const tw = ctx.measureText(label).width;
        ctx.fillStyle = '#00e5a0';
        ctx.fillRect(x1, y1 - 22, tw + 10, 22);
        ctx.fillStyle = '#080e1a';
        ctx.fillText(label, x1 + 5, y1 - 6);
    });
}

// ── Status ────────────────────────────────────────────────────────────────────
function setStatus(state) {
    const labels = { idle: 'Idle', scanning: 'Scanning...', done: 'Done', error: 'Error' };
    statusBadge.className   = `status-badge ${state}`;
    statusBadge.textContent = labels[state] || state;
}

// ── Field Row helper ──────────────────────────────────────────────────────────
function fieldRow(label, value, colorClass) {
    const display = value
        ? `<span class="field-value ${colorClass}">${value}</span>`
        : `<span class="field-value empty">—</span>`;
    return `
        <div class="field-row">
            <span class="field-label">${label}</span>
            <span class="field-sep">:</span>
            ${display}
        </div>`;
}

// ── Format Results ────────────────────────────────────────────────────────────
function formatResults(data) {
    if (!data.detections || data.detections.length === 0) {
        return `<div class="placeholder-state">
                    <div class="placeholder-icon">no entry sign</div>
                    <p>No boards detected in frame.</p>
                </div>`;
    }

    return data.detections.map((det, i) => {
        // Support both key names from backend (parsed_fields or parsed)
        const p  = det.parsed_fields || det.parsed || {};
        const qr = det.qr_data || [];

        // Build QR value string
        let qrValue = null;
        if (qr.length > 0) {
            qrValue = qr.map(q => typeof q === 'object' ? q.data : q).join(' | ');
        }

        const ocrConf = det.ocr_confidence != null
            ? `${(det.ocr_confidence * 100).toFixed(0)}%`
            : '';

        return `
        <div class="field-card">
            <div class="field-card-title">
                Detection #${i + 1} &nbsp;&middot;&nbsp; ${det.class || 'board'}
                ${ocrConf ? `&nbsp;&middot;&nbsp; OCR ${ocrConf}` : ''}
            </div>

            <div class="field-table">
                ${fieldRow('&#2350;&#2366;&#2352;&#2381;&#2327;',  p.marga,       'marga')}
                ${fieldRow('Kataho Code', p.kataho_code, 'kataho')}
                ${fieldRow('KID',         p.kid,         'kid')}
                ${fieldRow('Plus Code',   p.plus_code,   'plus')}
                ${fieldRow('Ward No',     p.ward_no,     'ward')}
                ${fieldRow('Location',    p.location,    'location')}
                ${fieldRow('QR Code',     qrValue,       'qr')}
            </div>

            <details class="raw-toggle">
                <summary>&#9658; Show Raw OCR Text</summary>
                <div class="raw-text">${det.ocr_text || 'No text detected'}</div>
            </details>
        </div>`;
    }).join('');
}

// ── Capture & Process ─────────────────────────────────────────────────────────
async function captureAndProcess() {
    if (isProcessing) return;
    isProcessing = true;
    setStatus('scanning');

    output.innerHTML = `<div class="processing-state">
        <div class="spinner"></div> Processing frame...
    </div>`;

    const tempCanvas = document.createElement('canvas');
    tempCanvas.width  = video.videoWidth;
    tempCanvas.height = video.videoHeight;
    tempCanvas.getContext('2d').drawImage(video, 0, 0);

    tempCanvas.toBlob(async (blob) => {
        const formData = new FormData();
        formData.append('file', blob, 'capture.jpg');

        try {
            const response = await fetch('/api/process', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.detail || `Server error ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                drawBoundingBoxes(data.detections);
                output.innerHTML = formatResults(data);
                setStatus('done');
            } else {
                throw new Error('Invalid response from server');
            }
        } catch (err) {
            output.innerHTML = `<div class="processing-state" style="color:var(--red)">
                Error: ${err.message}
            </div>`;
            setStatus('error');
            clearCanvas();
        } finally {
            isProcessing = false;
        }
    }, 'image/jpeg');
}

// ── Auto Scan ─────────────────────────────────────────────────────────────────
function toggleAutoScan() {
    isAutoScanning = !isAutoScanning;

    if (isAutoScanning) {
        autoScanBtn.textContent = 'Stop Auto Scan';
        autoScanBtn.classList.add('active');
        captureBtn.disabled = true;
        videoWrapper.classList.add('scanning');
        captureAndProcess();
        scanInterval = setInterval(captureAndProcess, 1500);
    } else {
        autoScanBtn.innerHTML = '<span class="btn-icon">&#128260;</span> Start Auto Scan';
        autoScanBtn.classList.remove('active');
        captureBtn.disabled = false;
        videoWrapper.classList.remove('scanning');
        clearInterval(scanInterval);
        isProcessing = false;
        setStatus('idle');
        clearCanvas();
    }
}

// ── Init ──────────────────────────────────────────────────────────────────────
captureBtn.addEventListener('click', captureAndProcess);
autoScanBtn.addEventListener('click', toggleAutoScan);
startCamera();