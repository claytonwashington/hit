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
    quickstartBody: document.getElementById("quickstart-body"),
    friendsList: document.getElementById("friends-list"),
    friendAlias: document.getElementById("friend-alias"),
    friendUsername: document.getElementById("friend-username"),
    addFriendBtn: document.getElementById("add-friend-btn")
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

        // Render Friends List
        renderFriends(data.friends || {});
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
    
    // Fetch the current config to keep the friends dictionary intact
    const config = await apiCall("/api/config");
    const currentFriends = config ? (config.friends || {}) : {};
    
    const payload = {
        username: dom.cfgUsername.value.trim(),
        drive_folder: dom.cfgDrive.value.trim(),
        music_dir: dom.cfgMusicDir.value.trim(),
        friends: currentFriends
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
// Render Friends List
function renderFriends(friends) {
    let hasFriends = false;
    let itemsHtml = "";
    
    // Normalize friends to object format
    let friendsObj = {};
    if (Array.isArray(friends)) {
        friends.forEach(f => {
            friendsObj[f] = f;
        });
    } else if (typeof friends === 'object') {
        friendsObj = friends;
    }
    
    const entries = Object.entries(friendsObj);
    if (entries.length > 0) {
        hasFriends = true;
        const isSongActive = state.activeSong && state.activeSong !== "None" && state.hasGit;
        
        itemsHtml = entries.map(([alias, username]) => {
            const shareBtnDisabled = isSongActive ? "" : "disabled";
            const shareBtnClass = isSongActive ? "btn-secondary" : "btn-outline";
            return `
                <div class="friend-item">
                    <div class="friend-info">
                        <span class="friend-name">${alias}</span>
                        <span class="friend-username-sub">@${username}</span>
                    </div>
                    <div class="friend-actions">
                        <button class="btn btn-xs ${shareBtnClass} friend-share-btn" data-username="${username}" data-alias="${alias}" ${shareBtnDisabled}>
                            Share Song
                        </button>
                        <button class="friend-remove-btn" data-alias="${alias}" title="Remove Friend">
                            &times;
                        </button>
                    </div>
                </div>
            `;
        }).join("");
    }
    
    if (!hasFriends) {
        dom.friendsList.innerHTML = `<small class="helper-text">No friends added yet. Add them above!</small>`;
    } else {
        dom.friendsList.innerHTML = itemsHtml;
        
        // Wire Share Song buttons
        document.querySelectorAll(".friend-share-btn").forEach(btn => {
            btn.addEventListener("click", async (e) => {
                e.stopPropagation();
                const username = btn.getAttribute("data-username");
                const alias = btn.getAttribute("data-alias");
                const originalText = btn.textContent;
                
                btn.disabled = true;
                btn.textContent = "Sharing...";
                showToast(`Inviting ${alias} (${username}) to '${state.activeSong}' repo...`, "info");
                
                const res = await apiCall("/api/songs/share", "POST", { name: state.activeSong, collaborator: username });
                
                btn.disabled = false;
                btn.textContent = originalText;
                
                if (res && res.success) {
                    showToast(`Invitation sent to ${alias} (${username}) successfully!`, "success");
                } else {
                    showToast(`Failed to invite ${alias}: ${res ? (res.error || res.output) : "Unknown error"}`, "error");
                }
            });
        });
        
        // Wire Remove Friend buttons
        document.querySelectorAll(".friend-remove-btn").forEach(btn => {
            btn.addEventListener("click", async (e) => {
                e.stopPropagation();
                const alias = btn.getAttribute("data-alias");
                
                showToast(`Removing ${alias} from friends...`, "info");
                
                // Fetch existing config, delete friend, and POST
                const config = await apiCall("/api/config");
                if (config) {
                    let currentFriends = config.friends || {};
                    if (Array.isArray(currentFriends)) {
                        currentFriends = currentFriends.filter(f => f !== alias);
                    } else if (typeof currentFriends === 'object') {
                        delete currentFriends[alias];
                    }
                    
                    const payload = {
                        username: config.username,
                        drive_folder: config.drive_folder,
                        music_dir: config.music_dir,
                        friends: currentFriends
                    };
                    
                    const res = await apiCall("/api/config", "POST", payload);
                    if (res && res.success) {
                        showToast(`Removed ${alias} from friends list`, "success");
                        fetchStatus(); // Refreshes the view
                    }
                }
            });
        });
    }
}

// Add Friend
dom.addFriendBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    const alias = dom.friendAlias.value.trim();
    const username = dom.friendUsername.value.trim();
    
    if (!alias || !username) {
        showToast("Please enter both alias and username", "error");
        return;
    }
    
    showToast(`Adding ${alias} to friends...`, "info");
    
    // Fetch current config, add new friend, and save
    const config = await apiCall("/api/config");
    if (config) {
        let currentFriends = config.friends || {};
        
        // Normalize to object if it was array
        if (Array.isArray(currentFriends)) {
            const temp = {};
            currentFriends.forEach(f => temp[f] = f);
            currentFriends = temp;
        } else if (typeof currentFriends !== 'object') {
            currentFriends = {};
        }
        
        currentFriends[alias] = username;
        
        const payload = {
            username: config.username,
            drive_folder: config.drive_folder,
            music_dir: config.music_dir,
            friends: currentFriends
        };
        
        const res = await apiCall("/api/config", "POST", payload);
        if (res && res.success) {
            showToast(`Added ${alias} successfully!`, "success");
            dom.friendAlias.value = "";
            dom.friendUsername.value = "";
            fetchStatus(); // Refreshes status which calls renderFriends
        }
    }
});
// Theme Customizer Logic
const themeInputs = {
    '--bg-dark': document.getElementById("color-bg-dark"),
    '--accent-cyan': document.getElementById("color-accent-cyan"),
    '--accent-green': document.getElementById("color-accent-green"),
    '--accent-magenta': document.getElementById("color-accent-magenta"),
    '--accent-yellow': document.getElementById("color-accent-yellow")
};

// Default Theme Values
const defaultTheme = {
    '--bg-dark': '#0a0c10',
    '--accent-cyan': '#00d8f6',
    '--accent-green': '#2de27b',
    '--accent-magenta': '#ff007f',
    '--accent-yellow': '#ffc83b'
};

// Preset Themes
const presets = {
    cyberpunk: {
        '--bg-dark': '#0f0c1b',
        '--accent-cyan': '#00f0ff',
        '--accent-green': '#39ff14',
        '--accent-magenta': '#ff007f',
        '--accent-yellow': '#fffb00'
    },
    matrix: {
        '--bg-dark': '#050a05',
        '--accent-cyan': '#00ff41',
        '--accent-green': '#00ff41',
        '--accent-magenta': '#ff3333',
        '--accent-yellow': '#88ff88'
    },
    synthwave: {
        '--bg-dark': '#1a0b2e',
        '--accent-cyan': '#ff007f',
        '--accent-green': '#00f0ff',
        '--accent-magenta': '#9b5de5',
        '--accent-yellow': '#f15bb5'
    },
    ocean: {
        '--bg-dark': '#030e1a',
        '--accent-cyan': '#0077b6',
        '--accent-green': '#00b4d8',
        '--accent-magenta': '#90e0ef',
        '--accent-yellow': '#caf0f8'
    }
};

// Helper: Hex to RGBA
function hexToRgba(hex, alpha) {
    hex = hex.replace('#', '');
    if (hex.length === 3) {
        hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
    }
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// Apply theme custom property
function applyThemeProperty(property, hexValue) {
    document.documentElement.style.setProperty(property, hexValue);
    
    // Auto-update dependent glow styles
    if (property === '--accent-cyan') {
        document.documentElement.style.setProperty('--accent-cyan-glow', hexToRgba(hexValue, 0.2));
    } else if (property === '--accent-green') {
        document.documentElement.style.setProperty('--accent-green-glow', hexToRgba(hexValue, 0.15));
    } else if (property === '--accent-magenta') {
        document.documentElement.style.setProperty('--accent-magenta-glow', hexToRgba(hexValue, 0.2));
    }
    
    // Update the visual hex label next to color picker
    const input = themeInputs[property];
    if (input) {
        input.value = hexValue;
        const hexLabel = input.nextElementSibling;
        if (hexLabel) hexLabel.textContent = hexValue.toUpperCase();
    }
}

// Load and apply saved theme
function loadSavedTheme() {
    const saved = localStorage.getItem("custom_theme");
    let themeObj = {...defaultTheme};
    if (saved) {
        try {
            themeObj = {...defaultTheme, ...JSON.parse(saved)};
        } catch (e) {}
    }
    
    Object.entries(themeObj).forEach(([prop, val]) => {
        applyThemeProperty(prop, val);
    });
}

// Save current theme state
function saveCurrentTheme() {
    const themeObj = {};
    Object.entries(themeInputs).forEach(([prop, input]) => {
        if (input) themeObj[prop] = input.value;
    });
    localStorage.setItem("custom_theme", JSON.stringify(themeObj));
}

// Wire Event Listeners for Theme Sidebar
const themeSidebar = document.getElementById("theme-sidebar");
const themeToggleBtn = document.getElementById("theme-toggle-btn");
const themeSidebarClose = document.getElementById("theme-sidebar-close");
const themeResetBtn = document.getElementById("theme-reset-btn");

if (themeToggleBtn && themeSidebar && themeSidebarClose) {
    // Open Sidebar
    themeToggleBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        themeSidebar.classList.toggle("open");
    });
    
    // Close Sidebar
    themeSidebarClose.addEventListener("click", () => {
        themeSidebar.classList.remove("open");
    });
    
    // Close Sidebar clicking outside
    document.addEventListener("click", (e) => {
        if (!themeSidebar.contains(e.target) && e.target !== themeToggleBtn) {
            themeSidebar.classList.remove("open");
        }
    });
    
    // Listen for color changes
    Object.entries(themeInputs).forEach(([prop, input]) => {
        if (input) {
            input.addEventListener("input", (e) => {
                applyThemeProperty(prop, e.target.value);
                saveCurrentTheme();
            });
        }
    });
    
    // Wire Presets
    document.querySelectorAll(".preset-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const pName = btn.getAttribute("data-preset");
            const presetTheme = presets[pName];
            if (presetTheme) {
                Object.entries(presetTheme).forEach(([prop, val]) => {
                    applyThemeProperty(prop, val);
                });
                saveCurrentTheme();
                showToast(`Applied ${pName} theme preset!`, "success");
            }
        });
    });
    
    // Reset to defaults
    if (themeResetBtn) {
        themeResetBtn.addEventListener("click", () => {
            Object.entries(defaultTheme).forEach(([prop, val]) => {
                applyThemeProperty(prop, val);
            });
            localStorage.removeItem("custom_theme");
            showToast("Theme reset to defaults", "info");
        });
    }
}

// --- Setup Wizard Modal Logic ---
let wizardCurrentStep = 1;
const wizardModal = document.getElementById("setup-wizard-modal");
const openWizardBtn = document.getElementById("open-wizard-btn");
const wizardNextBtn = document.getElementById("wizard-next-btn");
const wizardPrevBtn = document.getElementById("wizard-prev-btn");
const wizardSkipBtn = document.getElementById("wizard-skip-btn");

// Form inputs inside wizard
const wizUsername = document.getElementById("wizard-username");
const wizMusicDir = document.getElementById("wizard-music-dir");
const wizDriveFolder = document.getElementById("wizard-drive-folder");

// Upload elements
const uploadGdriveCreds = document.getElementById("upload-gdrive-creds");
const uploadGdriveToken = document.getElementById("upload-gdrive-token");
const wizGdriveAuthBtn = document.getElementById("wiz-gdrive-auth-btn");

// Status rows
const wizGdriveCredsIndicator = document.getElementById("wiz-gdrive-creds-indicator");
const wizGdriveTokenIndicator = document.getElementById("wiz-gdrive-token-indicator");
const wizGithubIndicator = document.getElementById("wiz-github-indicator");
const wizGithubVerifyBtn = document.getElementById("wiz-github-verify-btn");

// Files uploaded state
let uploadedCredsContent = null;
let uploadedTokenContent = null;

function openSetupWizard() {
    wizardCurrentStep = 1;
    updateWizardStepUI();
    
    // Pre-populate fields with current config/settings
    wizUsername.value = dom.cfgUsername.value || "";
    wizMusicDir.value = dom.cfgMusicDir.value || "~/Desktop/Music";
    wizDriveFolder.value = dom.cfgDrive.value || "HIT_DAW_Shared_Projects";
    
    // Check initial files status
    updateWizardStatusIndicators();
    
    wizardModal.classList.add("open");
}

function closeSetupWizard() {
    wizardModal.classList.remove("open");
}

async function updateWizardStatusIndicators() {
    const statusData = await apiCall("/api/status");
    if (!statusData) return;
    
    // Gdrive Credentials
    if (statusData.has_gdrive_creds || uploadedCredsContent) {
        wizGdriveCredsIndicator.textContent = "🟢 Credentials Configured";
        wizGdriveCredsIndicator.style.color = "var(--accent-green)";
        document.getElementById("upload-creds-card").classList.add("success");
        wizGdriveAuthBtn.disabled = false;
    } else {
        wizGdriveCredsIndicator.textContent = "🔴 Credentials Missing";
        wizGdriveCredsIndicator.style.color = "var(--accent-magenta)";
        document.getElementById("upload-creds-card").classList.remove("success");
        wizGdriveAuthBtn.disabled = true;
    }
    
    // Gdrive Token
    if (statusData.has_gdrive_token || uploadedTokenContent) {
        wizGdriveTokenIndicator.textContent = "🟢 Access Token Configured";
        wizGdriveTokenIndicator.style.color = "var(--accent-green)";
        document.getElementById("upload-token-card").classList.add("success");
    } else {
        wizGdriveTokenIndicator.textContent = "🔴 Access Token Missing";
        wizGdriveTokenIndicator.style.color = "var(--accent-magenta)";
        document.getElementById("upload-token-card").classList.remove("success");
    }
    
    // GitHub CLI Auth status
    if (statusData.is_gh_auth) {
        wizGithubIndicator.textContent = "🟢 GitHub CLI: Authenticated";
        wizGithubIndicator.style.color = "var(--accent-green)";
    } else {
        wizGithubIndicator.textContent = "🔴 GitHub CLI: Not Authenticated";
        wizGithubIndicator.style.color = "var(--accent-magenta)";
    }
}

function updateWizardStepUI() {
    // Hide all step panes
    document.querySelectorAll(".wizard-step-pane").forEach(pane => {
        pane.style.display = "none";
    });
    
    // Show current step pane
    document.getElementById(`wizard-step-${wizardCurrentStep}`).style.display = "block";
    
    // Update step indicators
    document.querySelectorAll(".step-indicator-node").forEach(node => {
        const stepNum = parseInt(node.getAttribute("data-step"));
        node.className = "step-indicator-node";
        if (stepNum === wizardCurrentStep) {
            node.classList.add("active");
        } else if (stepNum < wizardCurrentStep) {
            node.classList.add("completed");
            node.textContent = "✓";
        } else {
            node.textContent = stepNum;
        }
    });
    
    // Update footer buttons
    if (wizardCurrentStep === 1) {
        wizardPrevBtn.style.visibility = "hidden";
        wizardNextBtn.textContent = "Next Step";
    } else if (wizardCurrentStep === 3) {
        wizardPrevBtn.style.visibility = "visible";
        wizardNextBtn.textContent = "Finish Setup";
    } else {
        wizardPrevBtn.style.visibility = "visible";
        wizardNextBtn.textContent = "Next Step";
    }
}

// Handle file loading for GDrive files
function handleWizardFileSelect(e, type) {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(evt) {
        try {
            // Test if it's valid JSON
            JSON.parse(evt.target.result);
            if (type === 'creds') {
                uploadedCredsContent = evt.target.result;
                showToast("Google credentials file loaded!", "success");
            } else if (type === 'token') {
                uploadedTokenContent = evt.target.result;
                showToast("Google OAuth token loaded!", "success");
            }
            updateWizardStatusIndicators();
        } catch (err) {
            showToast("Invalid JSON file uploaded.", "error");
        }
    };
    reader.readAsText(file);
}

// Wire wizard events
if (openWizardBtn) {
    openWizardBtn.addEventListener("click", openSetupWizard);
}
if (wizardPrevBtn) {
    wizardPrevBtn.addEventListener("click", () => {
        if (wizardCurrentStep > 1) {
            wizardCurrentStep--;
            updateWizardStepUI();
        }
    });
}
if (wizardSkipBtn) {
    wizardSkipBtn.addEventListener("click", closeSetupWizard);
}

if (uploadGdriveCreds) {
    uploadGdriveCreds.addEventListener("change", (e) => handleWizardFileSelect(e, 'creds'));
}
if (uploadGdriveToken) {
    uploadGdriveToken.addEventListener("change", (e) => handleWizardFileSelect(e, 'token'));
}

if (wizGdriveAuthBtn) {
    wizGdriveAuthBtn.addEventListener("click", async () => {
        await saveWizardConfig();
        showToast("Starting Google Drive Auth flow. Please check your browser...", "info");
        const res = await apiCall("/api/sync", "POST");
        await updateWizardStatusIndicators();
    });
}

if (wizGithubVerifyBtn) {
    wizGithubVerifyBtn.addEventListener("click", async () => {
        showToast("Verifying GitHub CLI connection...", "info");
        await updateWizardStatusIndicators();
    });
}

async function saveWizardConfig() {
    const configData = {
        username: wizUsername.value.trim(),
        music_dir: wizMusicDir.value.trim(),
        drive_folder: wizDriveFolder.value.trim()
    };
    await apiCall("/api/config", "POST", configData);
}

if (wizardNextBtn) {
    wizardNextBtn.addEventListener("click", async () => {
        if (wizardCurrentStep === 1) {
            if (!wizUsername.value.trim()) {
                showToast("Please enter your collaborator name.", "error");
                return;
            }
            if (!wizMusicDir.value.trim()) {
                showToast("Please enter your music projects directory.", "error");
                return;
            }
            if (!wizDriveFolder.value.trim()) {
                showToast("Please enter your Google Drive folder name.", "error");
                return;
            }
            
            await saveWizardConfig();
            
            wizardCurrentStep = 2;
            updateWizardStepUI();
        } else if (wizardCurrentStep === 2) {
            if (uploadedCredsContent || uploadedTokenContent) {
                showToast("Uploading credentials files...", "info");
                const uploadRes = await apiCall("/api/setup/upload", "POST", {
                    "google_drive_hit.json": uploadedCredsContent,
                    "token.json": uploadedTokenContent
                });
                
                if (uploadRes && uploadRes.success) {
                    showToast("Credentials files saved successfully!", "success");
                    uploadedCredsContent = null;
                    uploadedTokenContent = null;
                } else {
                    const errStr = uploadRes ? uploadRes.errors.join(", ") : "Upload failed";
                    showToast(`Failed to upload files: ${errStr}`, "error");
                    return;
                }
            }
            
            wizardCurrentStep = 3;
            updateWizardStepUI();
        } else if (wizardCurrentStep === 3) {
            showToast("Setup Wizard completed successfully!", "success");
            closeSetupWizard();
            
            await fetchStatus();
            await fetchConfig();
            await fetchSongs();
            await fetchBranches();
            await fetchHistory();
            
            const statusData = await apiCall("/api/status");
            if (statusData && statusData.drive_sync_healthy && !statusData.daemon_running) {
                showToast("Auto-launching HIT Sync Daemon...", "info");
                await apiCall("/api/daemon/toggle", "POST");
                await fetchStatus();
            }
        }
    });
}

// --- Bootstrapping Execution ---
async function init() {
    loadSavedTheme();
    
    await fetchStatus();
    await fetchConfig();
    await fetchSongs();
    await fetchBranches();
    await fetchHistory();
    
    // Auto-pop setup wizard if username is default/empty, or drive credentials are missing
    const statusData = await apiCall("/api/status");
    if (statusData && (!statusData.username || statusData.username === "claytonwashington" || !statusData.has_gdrive_creds)) {
        openSetupWizard();
    }
    
    setInterval(async () => {
        await fetchStatus();
        await fetchHistory();
    }, 2000);
}

document.addEventListener("DOMContentLoaded", init);
