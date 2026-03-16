const video        = document.getElementById('video');
const canvas       = document.getElementById('canvas');
const captureBtn   = document.getElementById('captureBtn');
const autoScanBtn  = document.getElementById('autoScanBtn');
const output       = document.getElementById('output');
const statusBadge = document.getElementById('status-badge') || document.createElement('span');
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
        // ── Draw main board bounding box ──────────────────────────────────────
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

        // ── Draw ROI boxes inside the board ───────────────────────────────────
        const roiColors = {
            street_name:    '#ff4444',
            kataho_code:    '#ff44ff',
            kid_row:        '#ffa500',
            plus_code:      '#ffff00',
            nepali_address: '#00ffff',
            qr_code:        '#8844ff',
        };

        const roiCoords = det.roi_coordinates || {};
        Object.entries(roiCoords).forEach(([name, coords]) => {
            // coords is [x, y, w, h] relative to board crop
            // offset by board bbox origin (x1, y1) to get canvas coords
            const [rx, ry, rw, rh] = coords;
            const canvasX = x1 + rx;
            const canvasY = y1 + ry;

            ctx.strokeStyle = roiColors[name] || '#ffffff';
            ctx.lineWidth   = 2;
            ctx.strokeRect(canvasX, canvasY, rw, rh);

            // ROI label
            ctx.font        = '11px monospace';
            ctx.fillStyle   = roiColors[name] || '#ffffff';
            const labelW    = ctx.measureText(name).width;
            ctx.fillRect(canvasX, canvasY - 16, labelW + 6, 16);
            ctx.fillStyle   = '#000000';
            ctx.fillText(name, canvasX + 3, canvasY - 3);
        });
    });
}

// ── Status ────────────────────────────────────────────────────────────────────
function setStatus(state) {
    const labels = { idle: 'Idle', scanning: 'Scanning...', done: 'Done', error: 'Error' };
    if (statusBadge) {
        statusBadge.className   = `status-badge ${state}`;
        statusBadge.textContent = labels[state] || state;
    }
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

// ── ROI Coordinates Table ─────────────────────────────────────────────────────
function roiTable(roiCoords, roiOcr) {
    if (!roiCoords || Object.keys(roiCoords).length === 0) return '';

    const roiColors = {
        street_name:    '#ff4444',
        kataho_code:    '#ff44ff',
        kid_row:        '#ffa500',
        plus_code:      '#ffff00',
        nepali_address: '#00ffff',
        qr_code:        '#8844ff',
    };

    const rows = Object.entries(roiCoords).map(([name, coords]) => {
        const [x, y, w, h] = coords;
        const color = roiColors[name] || '#ffffff';
        const ocrText = roiOcr && roiOcr[name] ? roiOcr[name].text : '—';
        const ocrConf = roiOcr && roiOcr[name]
            ? `${(roiOcr[name].confidence * 100).toFixed(0)}%` : '—';

        return `
        <tr>
            <td><span style="color:${color}; font-weight:bold;">■</span> ${name}</td>
            <td style="font-family:monospace">${x}, ${y}</td>
            <td style="font-family:monospace">${w} × ${h}</td>
            <td style="color:#aaa; font-size:0.85em">${ocrText.substring(0, 30)}${ocrText.length > 30 ? '…' : ''}</td>
            <td style="color:#aaa">${ocrConf}</td>
        </tr>`;
    }).join('');

    return `
    <details class="roi-toggle" open>
        <summary>&#9658; ROI Regions &amp; Coordinates</summary>
        <div class="roi-table-wrapper">
            <table class="roi-table">
                <thead>
                    <tr>
                        <th>Region</th>
                        <th>Origin (x, y)</th>
                        <th>Size (w × h)</th>
                        <th>OCR Text</th>
                        <th>Confidence</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    </details>`;
}

// ── Format Results ────────────────────────────────────────────────────────────
function formatResults(data) {
    if (!data.detections || data.detections.length === 0) {
        return `<div class="placeholder-state">
                    <div class="placeholder-icon">🚫</div>
                    <p>No boards detected in frame.</p>
                </div>`;
    }

    return data.detections.map((det, i) => {
        const p  = det.parsed_fields || det.parsed || {};
        const qr = det.qr_data || [];

        let qrValue = null;
        if (qr.length > 0) {
            qrValue = qr.map(q => typeof q === 'object' ? q.data : q).join(' | ');
        }

        const ocrConf = det.ocr_confidence != null
            ? `${(det.ocr_confidence * 100).toFixed(0)}%` : '';

        // Board bbox coordinates
        const [bx1, by1, bx2, by2] = det.bbox || [0,0,0,0];
        const bboxStr = `(${bx1}, ${by1}) → (${bx2}, ${by2})  [${bx2-bx1} × ${by2-by1}]`;

        return `
        <div class="field-card">
            <div class="field-card-title">
                Detection #${i + 1} &nbsp;&middot;&nbsp; ${det.class || 'board'}
                ${ocrConf ? `&nbsp;&middot;&nbsp; OCR ${ocrConf}` : ''}
            </div>

            <!-- Board bbox -->
            <div class="bbox-row">
                <span class="bbox-label">Board BBox</span>
                <span class="bbox-value" style="font-family:monospace; color:#00e5a0">${bboxStr}</span>
            </div>

            <!-- Parsed fields -->
            <div class="field-table">
                ${fieldRow('&#2350;&#2366;&#2352;&#2381;&#2327;',  p.marga,       'marga')}
                ${fieldRow('Kataho Code', p.kataho_code, 'kataho')}
                ${fieldRow('KID',         p.kid,         'kid')}
                ${fieldRow('Plus Code',   p.plus_code,   'plus')}
                ${fieldRow('Ward No',     p.ward_no,     'ward')}
                ${fieldRow('Location',    p.location,    'location')}
                ${fieldRow('QR Code',     qrValue,       'qr')}
            </div>

            <!-- ROI coordinates table -->
            ${roiTable(det.roi_coordinates, det.roi_ocr)}

            <!-- Raw OCR -->
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