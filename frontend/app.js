// Navigation
document.getElementById('btn-search').addEventListener('click', () => switchSection('search'));
document.getElementById('btn-register').addEventListener('click', () => switchSection('register'));

function switchSection(sectionId) {
    // Update buttons
    document.querySelectorAll('.menu-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`btn-${sectionId}`).classList.add('active');
    
    // Update sections
    document.querySelectorAll('.action-section').forEach(sec => sec.classList.add('hidden'));
    document.getElementById(`section-${sectionId}`).classList.remove('hidden');
}

// WebSocket for Real-Time Logs
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${wsProtocol}//${window.location.host}/ws/logs`;
let ws;

function connectWebSocket() {
    ws = new WebSocket(wsUrl);
    ws.onmessage = function(event) {
        const log = event.data;
        const isError = log.toLowerCase().includes('error') || log.toLowerCase().includes('fail');
        const isSuccess = log.toLowerCase().includes('success') || log.toLowerCase().includes('found') || log.toLowerCase().includes('exitos');
        const typeClass = isError ? 'error' : isSuccess ? 'success' : 'info';
        
        const consoleBox = document.getElementById('console-output');
        const div = document.createElement('div');
        div.className = `log-line ${typeClass}`;
        div.innerText = `> ${log}`;
        consoleBox.appendChild(div);
        consoleBox.scrollTop = consoleBox.scrollHeight;
    };
    ws.onclose = function(e) {
        setTimeout(connectWebSocket, 5000);
    };
}
connectWebSocket();

// Console & Metrics Updater
let isFirstLoad = true;

async function fetchMetrics() {
    try {
        const res = await fetch('/api/metrics');
        const data = await res.json();
        
        document.getElementById('m-scanned').innerText = data.jobs_scanned;
        document.getElementById('m-accounts').innerText = data.accounts_created;
        document.getElementById('m-logins').innerText = data.successful_logins;
        document.getElementById('m-applications').innerText = data.applications_sent;
        
        // Load initial history on first load
        const consoleBox = document.getElementById('console-output');
        if (isFirstLoad && data.recent_logs && data.recent_logs.length > 0) {
            data.recent_logs.forEach(log => {
                const isError = log.toLowerCase().includes('error') || log.toLowerCase().includes('fail');
                const isSuccess = log.toLowerCase().includes('success') || log.toLowerCase().includes('found') || log.toLowerCase().includes('exitos');
                const typeClass = isError ? 'error' : isSuccess ? 'success' : 'info';
                
                const div = document.createElement('div');
                div.className = `log-line ${typeClass}`;
                div.innerText = `> ${log}`;
                consoleBox.appendChild(div);
            });
            consoleBox.scrollTop = consoleBox.scrollHeight;
            isFirstLoad = false;
        }
    } catch(e) {
        console.error("Error fetching metrics", e);
    }
}

// Poll metrics every 2 seconds
setInterval(fetchMetrics, 2000);
fetchMetrics();

// Actions
async function startScan() {
    const query = document.getElementById('search-query').value || 'Desarrollador';
    const location = document.getElementById('search-location').value || 'Chile';
    const filterDate = document.getElementById('filter-date').value;
    const filterModality = document.getElementById('filter-modality').value;
    
    // Convert to remote_only boolean for backwards compatibility with the old checkbox
    const remote_only = filterModality === 'remote';
    
    const filters = {
        date: filterDate !== 'any' ? filterDate : null,
        modality: filterModality !== 'any' ? filterModality : null
    };
    
    logToConsole(`Iniciando escaneo para: ${query} en ${location}...`, 'info');
    document.getElementById('results-body').innerHTML = `<tr><td colspan="6" style="text-align:center;">Buscando...</td></tr>`;
    
    try {
        const res = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, location, remote_only, filters })
        });
        
        const json = await res.json();
        
        if (json.status === 'accepted') {
            const taskId = json.task_id;
            pollTask(taskId, (data) => {
                document.getElementById('results-count').innerText = data.length;
                renderTable(data);
                logToConsole(`Búsqueda finalizada. ${data.length} resultados encontrados.`, 'success');
            }, (errorMsg) => {
                logToConsole(`Error en la búsqueda: ${errorMsg}`, 'error');
                document.getElementById('results-body').innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--danger);">Error: ${errorMsg}</td></tr>`;
            });
        } else if (json.status === 'success') {
            // Fallback for immediate response
            document.getElementById('results-count').innerText = json.data.length;
            renderTable(json.data);
            logToConsole(`Búsqueda finalizada. ${json.data.length} resultados encontrados.`, 'success');
        } else {
            logToConsole(`Error en la búsqueda: ${json.message}`, 'error');
            document.getElementById('results-body').innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--danger);">Error: ${json.message}</td></tr>`;
        }
    } catch(e) {
        logToConsole(`Error de red: ${e}`, 'error');
    }
}

function pollTask(taskId, onSuccess, onError) {
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`/api/tasks/${taskId}`);
            const json = await res.json();
            if (json.status === 'success') {
                clearInterval(interval);
                onSuccess(json.data);
            } else if (json.status === 'error') {
                clearInterval(interval);
                onError(json.data && json.data.message ? json.data.message : "Error desconocido");
            }
        } catch(e) {
            clearInterval(interval);
            onError(`Error polling task: ${e}`);
        }
    }, 2000);
}

async function startRegister() {
    const urlsText = document.getElementById('input-urls').value;
    const urls = urlsText.split(',').map(u => u.trim()).filter(u => u);
    
    if(urls.length === 0) {
        logToConsole("Por favor, ingresa al menos una URL.", "error");
        return;
    }
    
    logToConsole(`Iniciando registro masivo en ${urls.length} portales...`, 'info');
    
    try {
        const res = await fetch('/api/register', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ urls })
        });
        
        const json = await res.json();
        if(json.status === 'accepted') {
            pollTask(json.task_id, (data) => {
                logToConsole(`Registro masivo completado.`, 'success');
                for(const [url, result] of Object.entries(data)) {
                    logToConsole(`${url}: ${result}`, result === 'SUCCESS' ? 'success' : 'error');
                }
            }, (errorMsg) => {
                logToConsole(`Error en registro: ${errorMsg}`, 'error');
            });
        } else if(json.status === 'success') {
            logToConsole(`Registro masivo completado.`, 'success');
            for(const [url, result] of Object.entries(json.data)) {
                logToConsole(`${url}: ${result}`, result === 'SUCCESS' ? 'success' : 'error');
            }
        } else {
            logToConsole(`Error en registro: ${json.message}`, 'error');
        }
    } catch(e) {
        logToConsole(`Error de red: ${e}`, 'error');
    }
}

function renderTable(data) {
    const tbody = document.getElementById('results-body');
    tbody.innerHTML = '';
    
    if(data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="empty-state">No se encontraron resultados.</td></tr>`;
        return;
    }
    
    data.forEach(job => {
        const tr = document.createElement('tr');
        
        const score = job.aiScore || job.matchScore || 0;
        
        tr.innerHTML = `
            <td><a href="${job.url}" target="_blank" style="color: var(--accent); text-decoration: none;">${job.title}</a></td>
            <td>${job.company}</td>
            <td>${job.location}</td>
            <td><span class="badge" style="background: rgba(122, 40, 203, 0.4);">${job.source || 'N/A'}</span></td>
            <td class="match-score">${score}%</td>
            <td><button class="btn-primary" style="padding: 0.4rem 0.8rem; font-size: 0.8rem;" onclick="startApply('${job.url}')">Postular</button></td>
        `;
        tbody.appendChild(tr);
    });
}

async function startApply(url) {
    logToConsole(`Iniciando postulación pre-vuelo para: ${url}`, 'info');
    try {
        const res = await fetch('/api/apply', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ url })
        });
        
        const json = await res.json();
        if(json.status === 'success') {
            logToConsole(`Postulación exitosa a: ${url}`, 'success');
        } else {
            logToConsole(`Postulación abortada/fallida: ${json.message}`, 'error');
        }
    } catch(e) {
        logToConsole(`Error de red al postular: ${e}`, 'error');
    }
}

function logToConsole(msg, type='info') {
    const consoleBox = document.getElementById('console-output');
    const div = document.createElement('div');
    div.className = `log-line ${type}`;
    div.innerText = `> ${msg}`;
    consoleBox.appendChild(div);
    consoleBox.scrollTop = consoleBox.scrollHeight;
}
