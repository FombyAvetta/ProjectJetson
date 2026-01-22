// ===== State Management =====
let ws = null;
let wsReconnectTimer = null;
let isEnabled = true;
let currentBrightness = 100;

// ===== Toast Notifications =====
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => container.removeChild(toast), 300);
    }, 3000);
}

// ===== API Calls =====
async function apiCall(endpoint, method = "GET", data = null) {
    try {
        const options = {
            method,
            headers: {
                "Content-Type": "application/json",
            },
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(`/api/${endpoint}`, options);
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || "Request failed");
        }
        
        return result;
    } catch (error) {
        showToast(`Error: ${error.message}`, "error");
        throw error;
    }
}

// ===== WebSocket Connection =====
function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/updates`;
    
    console.log("Connecting to WebSocket:", wsUrl);
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log("WebSocket connected");
        updateConnectionStatus(true);
        showToast("Connected to Light Bar", "success");
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            updateMetrics(data.metrics);
            updateCurrentEffect(data.effect);
        } catch (error) {
            console.error("WebSocket message error:", error);
        }
    };
    
    ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        updateConnectionStatus(false);
    };
    
    ws.onclose = () => {
        console.log("WebSocket disconnected");
        updateConnectionStatus(false);
        
        // Attempt reconnection
        wsReconnectTimer = setTimeout(() => {
            console.log("Attempting to reconnect...");
            connectWebSocket();
        }, 5000);
    };
}

function updateConnectionStatus(connected) {
    const indicator = document.getElementById("connection-status");
    const text = document.getElementById("connection-text");
    
    if (connected) {
        indicator.className = "status-indicator connected";
        text.textContent = "Connected";
    } else {
        indicator.className = "status-indicator disconnected";
        text.textContent = "Disconnected";
    }
}

// ===== Metrics Updates =====
function updateMetrics(metrics) {
    // CPU
    document.getElementById("cpu-value").textContent = `${metrics.cpu_percent.toFixed(1)}%`;
    document.getElementById("cpu-bar").style.width = `${metrics.cpu_percent}%`;
    document.getElementById("cpu-bar").style.background = getGradientForValue(metrics.cpu_percent);
    
    // RAM
    document.getElementById("ram-value").textContent = `${metrics.ram_percent.toFixed(1)}%`;
    document.getElementById("ram-bar").style.width = `${metrics.ram_percent}%`;
    document.getElementById("ram-bar").style.background = getGradientForValue(metrics.ram_percent);
    
    // Temperature
    document.getElementById("temp-value").textContent = `${metrics.temperature.toFixed(1)}°C`;
    const tempPercent = Math.min(100, (metrics.temperature / 85) * 100);
    document.getElementById("temp-bar").style.width = `${tempPercent}%`;
    document.getElementById("temp-bar").style.background = getGradientForValue(tempPercent);
    
    // System Load
    const loadPercent = metrics.system_load * 100;
    document.getElementById("load-value").textContent = `${loadPercent.toFixed(0)}%`;
    document.getElementById("load-bar").style.width = `${loadPercent}%`;
    document.getElementById("load-bar").style.background = getGradientForValue(loadPercent);
}

function getGradientForValue(percent) {
    if (percent < 30) {
        return "linear-gradient(90deg, #00ff88, #00d9ff)";
    } else if (percent < 60) {
        return "linear-gradient(90deg, #00d9ff, #ffaa00)";
    } else if (percent < 80) {
        return "linear-gradient(90deg, #ffaa00, #ff6600)";
    } else {
        return "linear-gradient(90deg, #ff6600, #ff3366)";
    }
}

function updateCurrentEffect(effect) {
    document.getElementById("current-effect").textContent = effect;
}

// ===== Effect Selection =====
function setupEffectControls() {
    const effectInputs = document.querySelectorAll('input[name="effect"]');
    
    effectInputs.forEach(input => {
        input.addEventListener("change", async () => {
            if (input.checked) {
                try {
                    await apiCall("mode", "POST", { mode: input.value });
                    showToast(`Effect changed to: ${input.value}`, "success");
                } catch (error) {
                    console.error("Failed to change effect:", error);
                }
            }
        });
    });
}

// ===== Brightness Control =====
function setupBrightnessControl() {
    const slider = document.getElementById("brightness-slider");
    const display = document.getElementById("brightness-display");
    
    let debounceTimer;
    
    slider.addEventListener("input", () => {
        const value = slider.value;
        display.textContent = `${value}%`;
        currentBrightness = value;
        
        // Debounce API calls
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(async () => {
            try {
                await apiCall("brightness", "POST", { brightness: value });
            } catch (error) {
                console.error("Failed to set brightness:", error);
            }
        }, 300);
    });
}

// ===== Toggle Button =====
function setupToggleButton() {
    const btn = document.getElementById("toggle-btn");
    const icon = document.getElementById("toggle-icon");
    const text = document.getElementById("toggle-text");
    
    btn.addEventListener("click", async () => {
        isEnabled = !isEnabled;
        
        try {
            await apiCall("toggle", "POST", { enabled: isEnabled });
            
            if (isEnabled) {
                icon.textContent = "💡";
                text.textContent = "Turn Off";
                showToast("Lights enabled", "success");
            } else {
                icon.textContent = "🌙";
                text.textContent = "Turn On";
                showToast("Lights disabled", "success");
            }
        } catch (error) {
            // Revert on error
            isEnabled = !isEnabled;
            console.error("Failed to toggle lights:", error);
        }
    });
}

// ===== Demo Mode =====
function setupDemoButton() {
    const btn = document.getElementById("demo-btn");
    
    btn.addEventListener("click", async () => {
        try {
            await apiCall("demo", "POST");
            showToast("Demo mode started (30 seconds)", "success");
        } catch (error) {
            console.error("Failed to start demo:", error);
        }
    });
}

// ===== Override Controls =====
function setupOverrideControls() {
    // 1 hour override
    document.getElementById("override-1h").addEventListener("click", async () => {
        try {
            await apiCall("override", "POST", { turn_on: true, duration: 3600 });
            showToast("Override set for 1 hour", "success");
        } catch (error) {
            console.error("Failed to set override:", error);
        }
    });
    
    // Clear override
    document.getElementById("clear-override").addEventListener("click", async () => {
        try {
            await apiCall("override/clear", "POST");
            showToast("Override cleared", "success");
        } catch (error) {
            console.error("Failed to clear override:", error);
        }
    });
}

// ===== Initial Load =====
async function loadInitialState() {
    try {
        const result = await apiCall("status");
        const state = result.data;
        
        // Set effect radio button
        const effectInput = document.querySelector(`input[value="${state.effect}"]`);
        if (effectInput) {
            effectInput.checked = true;
        }
        
        // Set brightness
        document.getElementById("brightness-slider").value = state.brightness;
        document.getElementById("brightness-display").textContent = `${state.brightness}%`;
        currentBrightness = state.brightness;
        
        // Set toggle state
        isEnabled = state.enabled;
        const toggleIcon = document.getElementById("toggle-icon");
        const toggleText = document.getElementById("toggle-text");
        
        if (isEnabled) {
            toggleIcon.textContent = "💡";
            toggleText.textContent = "Turn Off";
        } else {
            toggleIcon.textContent = "🌙";
            toggleText.textContent = "Turn On";
        }
        
        // Update metrics if available
        if (state.metrics) {
            updateMetrics(state.metrics);
        }
        
    } catch (error) {
        console.error("Failed to load initial state:", error);
        showToast("Failed to load initial state", "error");
    }
}

// ===== Initialize =====
document.addEventListener("DOMContentLoaded", () => {
    console.log("Initializing Light Bar Control Panel...");
    
    // Setup all controls
    setupEffectControls();
    setupBrightnessControl();
    setupToggleButton();
    setupDemoButton();
    setupOverrideControls();
    
    // Load initial state
    loadInitialState();
    
    // Connect WebSocket
    connectWebSocket();
    
    console.log("✓ Initialization complete");
});

// ===== Cleanup on page unload =====
window.addEventListener("beforeunload", () => {
    if (ws) {
        ws.close();
    }
    if (wsReconnectTimer) {
        clearTimeout(wsReconnectTimer);
    }
});
