// State Management
let state = {
    username: "",
    daemonRunning: false,
    activeSong: "",
    songDir: "",
    branch: "",
    lockOwner: null,
    hasGit: false,
    isClean: true
};

// DOM Cache
const dom = {
    quickStatusText: document.getElementById("quick-status-text"),
    quickStatusBadge: document.getElementById("quick-status-badge"),
    quickToggleBtn: document.getElementById("quick-toggle-btn"),
    
    driveStatusText: document.getElementById("drive-status-text"),
    driveStatusBadge: document.getElementById("drive-status-badge"),
    
    songTitle: document.getElementById("song-title"),
    songPathText: document.getElementById("song-path-text"),
    activeBranchName: document.getElementById("active-branch-name"),
    lockBadge: document.getElementById("lock-badge"),
    lockBtn: document.getElementById("lock-btn"),
    syncBtn: document.getElementById("sync-btn"),
    
    songsList: document.getElementById("songs-list"),
    collabList: document.getElementById("collab-list"),
    timeline: document.getElementById("timeline"),
    
    branchSelector: document.getElementById("branch-selector"),
    switchBranchBtn: document.getElementById("switch-branch-btn"),
    newBranchName: document.getElementById("new-branch-name"),
    createBranchBtn: document.getElementById("create-branch-btn"),
    
    cpMessage: document.getElementById("cp-message"),
    cpTag: document.getElementById("cp-tag"),
    cpSubmitBtn: document.getElementById("cp-submit-btn"),
    
    configForm: document.getElementById("config-form"),
    cfgUsername: document.getElementById("cfg-username"),
    cfgDrive: document.getElementById("cfg-drive"),
    
    importModal: document.getElementById("import-modal"),
    modalFileName: document.getElementById("modal-file-name"),
    modalFileNameDesc: document.getElementById("modal-file-name-desc"),
    modalProjectPath: document.getElementById("modal-project-path"),
    toastContainer: document.getElementById("toast-container"),
    cfgMusicDir: document.getElementById("cfg-music-dir"),
    quickstartToggle: document.getElementById("quickstart-toggle"),
    quickstartBody: document.getElementById("quickstart-body")
};

// Toast Notifications Helper
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    
    let icon = "ℹ️";
    if (type === "success") icon = "🟢";
    if (type === "error") icon = "❌";
    
    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <div class="toast-content">${message}</div>
    `;
    
    dom.toastContainer.appendChild(toast);
    
    // Auto-remove toast
    setTimeout(() => {
        toast.classList.add("fade-out");
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// REST API Helper
async function apiCall(endpoint, method = "GET", body = null) {
    const options = { method, headers: { "Content-Type": "application/json" } };
    if (body) options.body = JSON.stringify(body);
    
    try {
        const response = await fetch(endpoint, options);
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || `HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API Call failed (${endpoint}):`, error);
        showToast(error.message, "error");
        return null;
    }
}

// 1. Fetch & Render System Status
async function fetchStatus() {
    const data = await apiCall("/api/status");
    if (!data) return;
    
    // Update global state cache
    const daemonStateChanged = state.daemonRunning !== data.daemon_running;
    state = {
        username: data.username,
        daemonRunning: data.daemon_running,
        activeSong: data.active_song,
        songDir: data.song_dir,
        branch: data.branch,
        lockOwner: data.lock_owner,
        hasGit: data.has_git,
        isClean: data.is_clean
    };

    // Update Header Status Badge
    if (state.daemonRunning) {
        dom.quickStatusBadge.className = "status-badge running";
        dom.quickStatusText.textContent = "RUNNING";
        dom.quickToggleBtn.textContent = "Stop Daemon";
        dom.quickToggleBtn.className = "btn btn-sm btn-secondary";
    } else {
        dom.quickStatusBadge.className = "status-badge stopped";
        dom.quickStatusText.textContent = "STOPPED";
        dom.quickToggleBtn.textContent = "Start Daemon";
        dom.quickToggleBtn.className = "btn btn-sm btn-primary";
    }
    
    // Update Google Drive status badge
    if (data.drive_sync_healthy) {
        dom.driveStatusBadge.className = "status-badge running";
        dom.driveStatusText.textContent = "CONNECTED";
    } else {
        dom.driveStatusBadge.className = "status-badge stopped";
        dom.driveStatusText.textContent = "OFFLINE";
    }
    
    if (daemonStateChanged) {
        showToast(`Sync Daemon is now ${state.daemonRunning ? 'running' : 'stopped'}.`, state.daemonRunning ? "success" : "info");
    }

    // Update Active Song Panel
    if (state.activeSong && state.activeSong !== "None") {
        dom.songTitle.textContent = state.activeSong;
        dom.songPathText.textContent = state.songDir || "Loading song path...";
        dom.activeBranchName.textContent = state.branch;
        dom.activeBranchName.style.display = "inline-block";
        
        // Disable state updates
        dom.syncBtn.disabled = !state.hasGit;
        dom.branchSelector.disabled = false;
        dom.switchBranchBtn.disabled = false;
        dom.newBranchName.disabled = false;
        dom.createBranchBtn.disabled = false;
        dom.cpMessage.disabled = false;
        dom.cpTag.disabled = false;
        dom.cpSubmitBtn.disabled = false;

        // Lock Badge Status
        dom.lockBtn.disabled = !state.hasGit;
        if (state.lockOwner) {
            const isMine = state.lockOwner.toLowerCase() === state.username.toLowerCase();
            dom.lockBadge.className = `lock-badge locked`;
            dom.lockBadge.textContent = isMine ? "🔒 Locked by You" : `🔒 Locked by ${state.lockOwner}`;
            dom.lockBtn.textContent = isMine ? "Unlock Project" : "Locked (Force Unlock)";
            dom.lockBtn.className = "btn btn-secondary";
        } else {
            dom.lockBadge.className = "lock-badge unlocked";
            dom.lockBadge.textContent = "🔓 Unlocked";
            dom.lockBtn.textContent = "Lock Project";
            dom.lockBtn.className = "btn btn-primary";
        }
    } else {
        dom.songTitle.textContent = "No Song Active";
        dom.songPathText.textContent = "Please select or register a song project.";
        dom.activeBranchName.style.display = "none";
        dom.lockBadge.className = "lock-badge unlocked";
        dom.lockBadge.textContent = "🔓 No Song";
        dom.lockBtn.disabled = true;
        dom.syncBtn.disabled = true;
        
        // Disable forms
        dom.branchSelector.disabled = true;
        dom.switchBranchBtn.disabled = true;
        dom.newBranchName.disabled = true;
        dom.createBranchBtn.disabled = true;
        dom.cpMessage.disabled = true;
        dom.cpTag.disabled = true;
        dom.cpSubmitBtn.disabled = true;
    }
}

// 2. Fetch & Render History Timeline
async function fetchHistory() {
    if (!state.activeSong || state.activeSong === "None" || !state.hasGit) {
        dom.timeline.innerHTML = `<p class="empty-state">No Git repository history for this project.</p>`;
        return;
    }
    
    const history = await apiCall("/api/history");
    if (!history) return;
    
    if (history.length === 0) {
        dom.timeline.innerHTML = `<p class="empty-state">No timeline events found. Record edits in Ableton or create a checkpoint!</p>`;
        return;
    }

    dom.timeline.innerHTML = history.map(item => {
        const isSelf = item.author.toLowerCase() === state.username.toLowerCase() || item.author.toLowerCase().includes("you");
        const authorName = isSelf ? `${item.author} (You)` : item.author;
        
        let typeClass = item.type; // "save", "checkpoint", "init", "sync"
        let icon = "🟢";
        if (item.type === "checkpoint") icon = "✨";
        if (item.type === "init") icon = "🎬";
        if (item.type === "sync") icon = "💾";

        const refsHtml = item.refs.map(ref => {
            if (ref.includes("HEAD")) return `<span class="ref-tag head-item">${ref}</span>`;
            if (ref.includes("tag:")) return `<span class="ref-tag tag-item">${ref.replace("tag:", "🏷️ ")}</span>`;
            return `<span class="ref-tag">${ref}</span>`;
        }).join("");

        return `
            <div class="timeline-item ${item.is_head ? 'head' : ''} ${item.type}">
                <div class="timeline-dot"></div>
                <div class="timeline-content">
                    <div class="timeline-header">
                        <span class="timeline-author ${isSelf ? 'self' : ''}">${authorName}</span>
                        <span class="timeline-time">${item.relative_time}</span>
                    </div>
                    <div class="timeline-msg">${icon} ${item.message}</div>
                    ${refsHtml ? `<div class="timeline-refs">${refsHtml}</div>` : ''}
                </div>
            </div>
        `;
    }).join("");
}

// 3. Fetch Branches & Render Dropdown / Collaborator Import Grid
async function fetchBranches() {
    if (!state.activeSong || state.activeSong === "None" || !state.hasGit) {
        dom.branchSelector.innerHTML = `<option value="">No Active Project</option>`;
        dom.collabList.innerHTML = `<p class="empty-state">No collaborators found.</p>`;
        return;
    }

    const branches = await apiCall("/api/branches");
    if (!branches) return;

    // Populate Selector Dropdown
    dom.branchSelector.innerHTML = branches.map(b => 
        `<option value="${b.name}" ${b.is_active ? 'selected' : ''}>${b.name} ${b.is_active ? '(Active)' : ''}</option>`
    ).join("");

    // Populate Collaborator Import List
    // Filter branches: show any branch (collab, main, etc.) except the currently active branch
    const collabs = branches.filter(b => {
        return !b.is_active;
    });

    if (collabs.length === 0) {
        dom.collabList.innerHTML = `<p class="empty-state">No other collaborator branches found. Push branches to share!</p>`;
        return;
    }

    dom.collabList.innerHTML = collabs.map(collab => {
        // Extract display name (e.g. collab/nik-vox -> nik)
        let displayName = collab.name;
        if (displayName.startsWith("collab/")) {
            displayName = displayName.replace("collab/", "");
        }
        
        // Avatar initials
        const initial = displayName.charAt(0).toUpperCase();

        return `
            <div class="collab-item">
                <div class="collab-name">
                    <div class="collab-avatar">${initial}</div>
                    <span>${collab.name}</span>
                </div>
                <button class="btn btn-sm btn-secondary import-action-btn" data-target="${collab.name}">Import Tracks</button>
            </div>
        `;
    }).join("");

    // Wire click handlers for dynamic import buttons
    document.querySelectorAll(".import-action-btn").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            const target = e.target.getAttribute("data-target");
            e.target.disabled = true;
            e.target.textContent = "Importing...";
            
            showToast(`Importing set from ${target}...`, "info");
            const res = await apiCall("/api/import", "POST", { target });
            
            e.target.disabled = false;
            e.target.textContent = "Import Tracks";
            
            if (res && res.success) {
                showToast("Set imported successfully!", "success");
                
                // Show modal instructions
                const branchClean = target.replace("remotes/origin/", "").replace("collab/", "").replace("/", "_");
                const mainAls = state.activeSong + ".als";
                const importedFile = `${state.activeSong}_collab_${branchClean}.als`;
                
                dom.modalFileName.textContent = importedFile;
                dom.modalFileNameDesc.textContent = importedFile;
                dom.modalProjectPath.textContent = state.songDir;
                
                dom.importModal.classList.add("open");
                fetchHistory();
            } else {
                showToast(res ? res.output : "Import failed", "error");
            }
        });
    });
}

// 4. Fetch Songs & Render Selector List
async function fetchSongs() {
    const data = await apiCall("/api/songs");
    if (!data) return;

    const songs = data.songs || {};
    const active = data.active_project || "";
    
    if (Object.keys(songs).length === 0) {
        dom.songsList.innerHTML = `<p class="empty-state">No songs registered. Add Ableton project folders to your music directory.</p>`;
        return;
    }

    dom.songsList.innerHTML = Object.keys(songs).map(name => {
        const song = songs[name];
        const isActive = name === active;
        return `
            <div class="song-item ${isActive ? 'active' : ''}" data-name="${name}">
                <div class="song-info">
                    <div class="song-name">${name}</div>
                    <div class="song-meta">${isActive ? 'Active' : `BPM: ${song.bpm}`}</div>
                </div>
                <div class="song-actions">
                    ${song.has_git ? 
                        `<span class="badge badge-collab">🔗 Collab</span>` : 
                        `<button class="btn btn-sm btn-outline init-git-btn" data-name="${name}">Init Git</button>`
                    }
                </div>
            </div>
        `;
    }).join("");

    // Wire click handlers for songs selection
    document.querySelectorAll(".song-item").forEach(item => {
        item.addEventListener("click", async (e) => {
            const songName = e.currentTarget.getAttribute("data-name");
            if (songName === state.activeSong) return;
            
            showToast(`Switching active song to ${songName}...`, "info");
            const res = await apiCall("/api/songs/active", "POST", { name: songName });
            if (res && res.success) {
                showToast(`Switched active song to ${songName}!`, "success");
                
                // Full reload
                await fetchStatus();
                await fetchBranches();
                await fetchHistory();
                await fetchSongs();
            }
        });
    });

    // Wire click handlers for song Git initialization
    document.querySelectorAll(".init-git-btn").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            e.stopPropagation(); // Prevents setting active song on click
            const songName = e.currentTarget.getAttribute("data-name");
            
            btn.disabled = true;
            btn.textContent = "Initing...";
            showToast(`Initializing collaborative repo for '${songName}'...`, "info");
            
            const res = await apiCall("/api/songs/initialize", "POST", { name: songName });
            
            btn.disabled = false;
            btn.textContent = "Init Git";
            
            if (res && res.success) {
                showToast(`Collaborative Git repository initialized for '${songName}'!`, "success");
                await fetchStatus();
                await fetchBranches();
                await fetchHistory();
                await fetchSongs();
            } else {
                showToast(res ? res.output : "Initialization failed", "error");
            }
        });
    });
}

// 5. Fetch Global Config & Populate Form
async function fetchConfig() {
    const config = await apiCall("/api/config");
    if (!config) return;
    
    dom.cfgUsername.value = config.username || "";
    dom.cfgDrive.value = config.drive_folder || "";
    dom.cfgMusicDir.value = config.music_dir || "";
}

// --- Event Listeners Setup ---

// Toggle Daemon
dom.quickToggleBtn.addEventListener("click", async () => {
    dom.quickToggleBtn.disabled = true;
    const res = await apiCall("/api/daemon/toggle", "POST");
    dom.quickToggleBtn.disabled = false;
    if (res) {
        fetchStatus();
    }
});

// Lock/Unlock Branch
dom.lockBtn.addEventListener("click", async () => {
    dom.lockBtn.disabled = true;
    showToast("Processing project lock change...", "info");
    const res = await apiCall("/api/lock/toggle", "POST");
    dom.lockBtn.disabled = false;
    if (res && res.success) {
        showToast(res.output, "success");
        fetchStatus();
    }
});

// Sync Now
dom.syncBtn.addEventListener("click", async () => {
    dom.syncBtn.disabled = true;
    showToast("Starting bidirectional sync...", "info");
    const res = await apiCall("/api/sync", "POST");
    dom.syncBtn.disabled = false;
    if (res && res.success) {
        showToast("Sync finished successfully!", "success");
        fetchStatus();
        fetchHistory();
    } else {
        showToast(res ? res.output : "Sync completed with warnings", "info");
    }
});

// Checkout Branch
dom.switchBranchBtn.addEventListener("click", async () => {
    if (!state.isClean) {
        showToast("⚠️ Unsaved changes in project! Please save/checkpoint in Ableton first.", "error");
        return;
    }
    const selectedBranch = dom.branchSelector.value;
    if (!selectedBranch) return;
    
    dom.switchBranchBtn.disabled = true;
    showToast(`Checking out branch: ${selectedBranch}...`, "info");
    const res = await apiCall("/api/branch/switch", "POST", { name: selectedBranch });
    dom.switchBranchBtn.disabled = false;
    
    if (res && res.success) {
        showToast(`Checked out branch ${selectedBranch}!`, "success");
        fetchStatus();
        fetchBranches();
        fetchHistory();
    }
});

// Create Branch Form
dom.createBranchBtn.addEventListener("click", async () => {
    if (!state.isClean) {
        showToast("⚠️ Unsaved changes in project! Please save/checkpoint in Ableton first.", "error");
        return;
    }
    const newName = dom.newBranchName.value.trim();
    if (!newName) {
        showToast("Please enter a branch name", "error");
        return;
    }
    
    dom.createBranchBtn.disabled = true;
    showToast(`Creating branch: ${newName}...`, "info");
    const res = await apiCall("/api/branch/switch", "POST", { name: newName });
    dom.createBranchBtn.disabled = false;
    
    if (res && res.success) {
        showToast(`New collaboration branch created successfully!`, "success");
        dom.newBranchName.value = "";
        fetchStatus();
        fetchBranches();
        fetchHistory();
    }
});

// Checkpoint Form Submit
document.getElementById("checkpoint-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = dom.cpMessage.value.trim();
    const tag = dom.cpTag.value.trim();
    
    dom.cpSubmitBtn.disabled = true;
    showToast("Publishing checkpoint to GitHub...", "info");
    const res = await apiCall("/api/checkpoint", "POST", { message: msg, tag });
    dom.cpSubmitBtn.disabled = false;
    
    if (res && res.success) {
        showToast("Checkpoint published and pushed to origin!", "success");
        dom.cpMessage.value = "";
        dom.cpTag.value = "";
        fetchStatus();
        fetchHistory();
    }
});

// Save Settings Config Form
dom.configForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
        username: dom.cfgUsername.value.trim(),
        drive_folder: dom.cfgDrive.value.trim(),
        music_dir: dom.cfgMusicDir.value.trim()
    };
    
    const res = await apiCall("/api/config", "POST", payload);
    if (res && res.success) {
        showToast("Configuration settings updated!", "success");
        fetchStatus();
        fetchBranches();
    }
});

// Modal Dialog Handlers
document.querySelectorAll(".modal-close-btn, .modal-close-btn-ok").forEach(btn => {
    btn.addEventListener("click", () => {
        dom.importModal.classList.remove("open");
    });
});

// Close modal clicking outside content
window.addEventListener("click", (e) => {
    if (e.target === dom.importModal) {
        dom.importModal.classList.remove("open");
    }
});

// Toggle Quickstart Pane collapse/expand state
if (dom.quickstartToggle && dom.quickstartBody) {
    const qsState = localStorage.getItem("quickstart_collapsed");
    if (qsState === "true") {
        dom.quickstartBody.classList.add("collapsed");
        dom.quickstartToggle.textContent = "Expand";
    }

    dom.quickstartToggle.addEventListener("click", () => {
        const isCollapsed = dom.quickstartBody.classList.toggle("collapsed");
        dom.quickstartToggle.textContent = isCollapsed ? "Expand" : "Collapse";
        localStorage.setItem("quickstart_collapsed", isCollapsed.toString());
    });
}

// --- Bootstrapping Execution ---
async function init() {
    // 1. Initial fetches
    await fetchStatus();
    await fetchConfig();
    await fetchSongs();
    await fetchBranches();
    await fetchHistory();
    
    // 2. Set polling intervals
    setInterval(async () => {
        await fetchStatus();
        await fetchHistory();
    }, 2000);
}

document.addEventListener("DOMContentLoaded", init);
