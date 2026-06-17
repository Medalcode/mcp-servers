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

// Console & Metrics Updater
let lastLogCount = 0;

async function fetchMetrics() {
    try {
        const res = await fetch('/api/metrics');
        const data = await res.json();
        
        document.getElementById('m-scanned').innerText = data.jobs_scanned;
        document.getElementById('m-accounts').innerText = data.accounts_created;
        document.getElementById('m-logins').innerText = data.successful_logins;
        document.getElementById('m-applications').innerText = data.applications_sent;
        
        // Update console
        const consoleBox = document.getElementById('console-output');
        if (data.recent_logs.length > lastLogCount) {
            const newLogs = data.recent_logs.slice(lastLogCount);
            newLogs.forEach(log => {
                const isError = log.toLowerCase().includes('error') || log.toLowerCase().includes('fail');
                const isSuccess = log.toLowerCase().includes('success') || log.toLowerCase().includes('found');
                const typeClass = isError ? 'error' : isSuccess ? 'success' : 'info';
                
                const div = document.createElement('div');
                div.className = `log-line ${typeClass}`;
                div.innerText = `> ${log}`;
                consoleBox.appendChild(div);
            });
            consoleBox.scrollTop = consoleBox.scrollHeight;
            lastLogCount = data.recent_logs.length;
        }
    } catch(e) {
        console.error("Error fetching metrics", e);
    }
}

// Poll metrics every 2 seconds
setInterval(fetchMetrics, 2000);
fetchMetrics();

// Actions
async function startSearch() {
    const query = document.getElementById('input-query').value;
    const location = document.getElementById('input-location').value;
    const remote_only = document.getElementById('check-remote').checked;
    
    logToConsole(`Iniciando escaneo para: ${query} en ${location}...`, 'info');
    document.getElementById('results-body').innerHTML = `<tr><td colspan="6" style="text-align:center;">Buscando...</td></tr>`;
    
    try {
        const res = await fetch('/api/search', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ query, location, remote_only })
        });
        
        const json = await res.json();
        
        if (json.status === 'success') {
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
        if(json.status === 'success') {
            logToConsole(`Registro masivo completado.`, 'success');
            // Show details in console
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
