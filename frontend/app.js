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

// Ensure the apply button in sidebar works
document.getElementById('btn-apply').addEventListener('click', () => switchSection('apply'));

// Console clear button
document.getElementById('btn-clear-console').addEventListener('click', () => {
    document.getElementById('console-output').innerHTML = '';
});

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
        div.textContent = `> ${log}`;
        consoleBox.appendChild(div);
        consoleBox.scrollTop = consoleBox.scrollHeight;
    };
    ws.onclose = function(e) {
        setTimeout(connectWebSocket, wsReconnectDelay);
        wsReconnectDelay = Math.min(wsReconnectDelay * 2, 30000); // Backoff up to 30s
    };
}
let wsReconnectDelay = 5000;
connectWebSocket();

// Models Loader
async function loadModels() {
    try {
        const res = await fetch('/api/models');
        const data = await res.json();
        const select = document.getElementById('ai-model-select');
        select.innerHTML = '';
        data.models.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.id;
            opt.innerText = `${m.name} (${m.provider})`;
            select.appendChild(opt);
        });
        
        select.addEventListener('change', async (e) => {
            const model_id = e.target.value;
            await fetch('/api/settings/model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_id })
            });
            logToConsole(`Modelo AI cambiado a: ${model_id}`, 'info');
        });
    } catch(e) {
        console.error("Error loading models", e);
    }
}
loadModels();

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
    const query = document.getElementById('search-query').value || '';
    const location = document.getElementById('search-location').value || '';
    const filterDate = document.getElementById('filter-date').value;
    const filterModality = document.getElementById('filter-modality').value;
    const filterExclude = document.getElementById('search-exclude')?.value || '';
    
    // Get selected scrapers from checkboxes
    const checkedScrapers = Array.from(document.querySelectorAll('.scraper-cb:checked')).map(cb => cb.value);
    const selectedScrapers = checkedScrapers.length > 0 ? checkedScrapers : ['all'];
    
    // Convert to remote_only boolean for backwards compatibility with the old checkbox
    const remote_only = filterModality === 'remote';
    
    const filters = {
        date: filterDate !== 'any' ? filterDate : null,
        modality: filterModality !== 'any' ? filterModality : null,
        scrapers: selectedScrapers.includes('all') ? null : selectedScrapers,
        exclude: filterExclude.trim() || null
    };
    
    logToConsole(`Iniciando escaneo para: ${query} en ${location}...`, 'info');
    
    const tbody = document.getElementById('results-body');
    tbody.innerHTML = '';
    const loadingTr = document.createElement('tr');
    const loadingTd = document.createElement('td');
    loadingTd.colSpan = 6;
    loadingTd.style.textAlign = 'center';
    loadingTd.textContent = 'Buscando...';
    loadingTr.appendChild(loadingTd);
    tbody.appendChild(loadingTr);
    
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
                document.getElementById('results-count').textContent = data.length;
                renderTable(data);
                logToConsole(`Búsqueda finalizada. ${data.length} resultados encontrados.`, 'success');
            }, (errorMsg) => {
                logToConsole(`Error en la búsqueda: ${errorMsg}`, 'error');
                showErrorInTable(`Error: ${errorMsg}`);
            });
        } else if (json.status === 'success') {
            // Fallback for immediate response
            document.getElementById('results-count').textContent = json.data.length;
            renderTable(json.data);
            logToConsole(`Búsqueda finalizada. ${json.data.length} resultados encontrados.`, 'success');
        } else {
            logToConsole(`Error en la búsqueda: ${json.message}`, 'error');
            showErrorInTable(`Error: ${json.message}`);
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
            document.getElementById('input-urls').value = '';
        }
    } catch(e) {
        logToConsole(`Error de red: ${e}`, 'error');
    }
}

async function startBatchApply() {
    const queriesText = document.getElementById('apply-queries').value || '';
    const limit = parseInt(document.getElementById('apply-limit').value || '50');
    
    if (!queriesText.trim()) {
        logToConsole('Por favor ingresa términos de búsqueda válidos', 'error');
        return;
    }
    
    const queries = queriesText.split(',').map(q => q.trim()).filter(q => q);
    
    logToConsole(`Iniciando Auto Apply Masivo para: ${queries.join(', ')}...`, 'info');
    
    try {
        const res = await fetch('/api/batch-apply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ queries, limit })
        });
        const json = await res.json();
        
        if (json.status === 'accepted') {
            logToConsole(`Proceso de Auto Apply iniciado en segundo plano. Observa la consola.`, 'success');
        } else {
            logToConsole(`Error iniciando Auto Apply: ${json.message}`, 'error');
        }
    } catch(e) {
        logToConsole(`Error de red: ${e}`, 'error');
    }
}

// Helper function for errors
function showErrorInTable(msg) {
    const tbody = document.getElementById('results-body');
    tbody.innerHTML = '';
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = 6;
    td.style.textAlign = 'center';
    td.style.color = 'var(--danger)';
    td.textContent = msg;
    tr.appendChild(td);
    tbody.appendChild(tr);
}

// Table rendering
function renderTable(data) {
    const tbody = document.getElementById('results-body');
    tbody.innerHTML = '';
    
    if(data.length === 0) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 6;
        td.className = 'empty-state';
        td.textContent = 'No se encontraron resultados.';
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }
    
    data.forEach(job => {
        const tr = document.createElement('tr');
        
        const score = job.aiScore || job.matchScore || 0;
        
        // 1. Title cell
        const tdTitle = document.createElement('td');
        const aTitle = document.createElement('a');
        aTitle.href = job.url;
        aTitle.target = '_blank';
        aTitle.style.color = 'var(--accent)';
        aTitle.style.textDecoration = 'none';
        aTitle.textContent = job.title;
        tdTitle.appendChild(aTitle);
        tr.appendChild(tdTitle);
        
        // 2. Company cell
        const tdCompany = document.createElement('td');
        tdCompany.textContent = job.company;
        tr.appendChild(tdCompany);
        
        // 3. Location cell
        const tdLocation = document.createElement('td');
        tdLocation.textContent = job.location;
        tr.appendChild(tdLocation);
        
        // 4. Source cell
        const tdSource = document.createElement('td');
        const spanSource = document.createElement('span');
        spanSource.className = 'badge';
        spanSource.style.background = 'rgba(122, 40, 203, 0.4)';
        spanSource.textContent = job.source || 'N/A';
        tdSource.appendChild(spanSource);
        tr.appendChild(tdSource);
        
        // 5. Score cell
        const tdScore = document.createElement('td');
        tdScore.className = 'match-score';
        tdScore.textContent = `${score}%`;
        tr.appendChild(tdScore);
        
        // 6. Action cell
        const tdAction = document.createElement('td');
        const btnApply = document.createElement('button');
        btnApply.className = 'btn-primary';
        btnApply.style.padding = '0.4rem 0.8rem';
        btnApply.style.fontSize = '0.8rem';
        btnApply.textContent = 'Postular';
        btnApply.onclick = () => startApply(job.url);
        tdAction.appendChild(btnApply);
        tr.appendChild(tdAction);
        
        tbody.appendChild(tr);
    });
}
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
