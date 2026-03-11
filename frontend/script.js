const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const captureBtn = document.getElementById('captureBtn');
const autoScanBtn = document.getElementById('autoScanBtn');
const output = document.getElementById('output');

let isAutoScanning = false;
let scanInterval = null;
let isProcessing = false;

// Access the camera
async function startCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        video.srcObject = stream;
        
        // Wait for video to be ready before setting canvas size
        video.onloadedmetadata = () => {
            adjustCanvasSize();
        };
        
        // Adjust canvas size on window resize to keep it perfectly overlapping the video
        window.addEventListener('resize', adjustCanvasSize);
    } catch (err) {
        console.error("Camera access error:", err);
        alert("Could not access camera. Please make sure you have granted permissions.");
    }
}

function adjustCanvasSize() {
    // Make internal canvas resolution match the video stream resolution
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
}

function clearCanvas() {
    const context = canvas.getContext('2d');
    context.clearRect(0, 0, canvas.width, canvas.height);
}

function drawBoundingBoxes(detections) {
    const context = canvas.getContext('2d');
    clearCanvas();

    detections.forEach(det => {
        const [x1, y1, x2, y2] = det.bbox;
        const width = x2 - x1;
        const height = y2 - y1;

        // Draw rectangle
        context.strokeStyle = '#10b981'; // Success primary color
        context.lineWidth = 4;
        context.strokeRect(x1, y1, width, height);
        
        // Draw background for label
        const label = `${det.class} (${(det.confidence * 100).toFixed(1)}%)`;
        context.fillStyle = '#10b981';
        context.font = '18px Inter, sans-serif';
        const textWidth = context.measureText(label).width;
        context.fillRect(x1, y1 - 24, textWidth + 8, 24);

        // Draw label text
        context.fillStyle = '#ffffff';
        context.fillText(label, x1 + 4, y1 - 6);
    });
}

function formatResults(data) {
    if (!data.detections || data.detections.length === 0) {
        return '<p class="placeholder">No boards detected in the current frame.</p>';
    }

    let html = '';
    data.detections.forEach((det, index) => {
        html += `<div class="detection-result" style="margin-bottom: 1.5rem; padding: 1rem; background: rgba(255,255,255,0.05); border-radius: 0.5rem; border: 1px solid rgba(255,255,255,0.1);">`;
        html += `<h3 style="margin-top: 0; color: #60a5fa; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 0.5rem;">Detection #${index + 1} <span style="font-size: 0.8em; color: #94a3b8;">(${det.class} - ${(det.confidence*100).toFixed(1)}%)</span></h3>`;
        
        // Parsed Fields
        html += `<div style="margin-bottom: 1rem;">`;
        if (det.parsed) {
            if (det.parsed.marga) {
                html += `<div style="margin-bottom: 0.4rem; font-size: 1.1em;"><span style="color: #94a3b8; display: inline-block; width: 120px;">मार्ग:</span> <strong style="color: #f8fafc;">${det.parsed.marga}</strong></div>`;
            }
            if (det.parsed.kataho_code) {
                html += `<div style="margin-bottom: 0.4rem; font-size: 1.1em;"><span style="color: #94a3b8; display: inline-block; width: 120px;">Kataho Code:</span> <strong style="color: #10b981;">${det.parsed.kataho_code}</strong></div>`;
            }
            if (det.parsed.kid) {
                html += `<div style="margin-bottom: 0.4rem; font-size: 1.1em;"><span style="color: #94a3b8; display: inline-block; width: 120px;">KID:</span> <strong style="color: #60a5fa;">${det.parsed.kid}</strong></div>`;
            }
            if (det.parsed.plus_code) {
                html += `<div style="margin-bottom: 0.4rem; font-size: 1.1em;"><span style="color: #94a3b8; display: inline-block; width: 120px;">Plus code:</span> <strong style="color: #f59e0b;">${det.parsed.plus_code}</strong></div>`;
            }
        }
        html += `</div>`;

        if (det.qr_data && det.qr_data.length > 0) {
            html += `<div style="margin-bottom: 0.5rem;"><span style="color: #94a3b8;">QR Data:</span> <span style="color: white; background: rgba(0,0,0,0.5); padding: 0.2rem 0.5rem; border-radius: 0.25rem;">${det.qr_data.join(', ')}</span></div>`;
        }
        
        html += `<details style="margin-top: 0.5rem;">`;
        html += `<summary style="color: #94a3b8; cursor: pointer; font-size: 0.9em;">Show Raw OCR Text</summary>`;
        html += `<div style="margin-top: 0.5rem; color: #cbd5e1; font-size: 0.85em; background: rgba(0,0,0,0.3); padding: 0.5rem; border-radius: 0.25rem;">${det.ocr_text || 'None'}</div>`;
        html += `</details>`;
        
        html += `</div>`;
    });
    return html;
}

// Capture a frame and send to backend
async function captureAndProcess() {
    if (isProcessing) return; // Prevent overlapping requests
    isProcessing = true;

    // We use a temporary canvas to get the exact video frame for sending to API
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = video.videoWidth;
    tempCanvas.height = video.videoHeight;
    const context = tempCanvas.getContext('2d');
    context.drawImage(video, 0, 0, tempCanvas.width, tempCanvas.height);

    // Convert canvas to blob
    tempCanvas.toBlob(async (blob) => {
        const formData = new FormData();
        formData.append('file', blob, 'capture.jpg');

        try {
            output.innerHTML = '<span style="color: #94a3b8;">Processing...</span>';
            const response = await fetch('/api/process', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (data.success) {
                drawBoundingBoxes(data.detections);
                output.innerHTML = formatResults(data);
            } else {
                output.innerHTML = '<span style="color: #ef4444;">Error: Invalid response from server.</span>';
                clearCanvas();
            }
        } catch (err) {
            console.error("API error:", err);
            output.innerHTML = '<span style="color: #ef4444;">Connection error. Make sure the backend is running.</span>';
            clearCanvas();
        } finally {
            isProcessing = false;
        }
    }, 'image/jpeg');
}

function toggleAutoScan() {
    isAutoScanning = !isAutoScanning;
    
    if (isAutoScanning) {
        autoScanBtn.textContent = 'Stop Auto Scan';
        autoScanBtn.classList.add('active');
        captureBtn.disabled = true;
        captureBtn.style.opacity = '0.5';
        
        // Immediate first scan, then set interval
        captureAndProcess();
        scanInterval = setInterval(captureAndProcess, 1500); // 1.5 seconds interval
    } else {
        autoScanBtn.textContent = 'Start Auto Scan';
        autoScanBtn.classList.remove('active');
        captureBtn.disabled = false;
        captureBtn.style.opacity = '1';
        
        clearInterval(scanInterval);
        isProcessing = false;
        clearCanvas(); // Clear bounding boxes when stopping
    }
}

// Event listeners
captureBtn.addEventListener('click', captureAndProcess);
autoScanBtn.addEventListener('click', toggleAutoScan);

// Start camera on page load
startCamera();