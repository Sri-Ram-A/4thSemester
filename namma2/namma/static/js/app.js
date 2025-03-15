// Typewriter effect for the intro screen
function typeWriter(text, element, speed) {
    let i = 0;
    element.innerHTML = '';
    function typing() {
        if (i < text.length) {
            element.innerHTML += text.charAt(i);
            i++;
            setTimeout(typing, speed);
        }
    }
    typing();
}

// Function to switch between modes
function switchMode(mode) {
    const offlineBtn = document.getElementById('offline-btn');
    const silentBtn = document.getElementById('silent-btn');
    const onlineBtn = document.getElementById('online-btn');
    
    // Reset all buttons
    offlineBtn.classList.remove('btn-error', 'btn-info', 'btn-success');
    offlineBtn.classList.add('btn-ghost');
    silentBtn.classList.remove('btn-error', 'btn-info', 'btn-success');
    silentBtn.classList.add('btn-ghost');
    onlineBtn.classList.remove('btn-error', 'btn-info', 'btn-success');
    onlineBtn.classList.add('btn-ghost');
    
    // Set active button
    if (mode === 'offline') {
        offlineBtn.classList.remove('btn-ghost');
        offlineBtn.classList.add('btn-error');
    } else if (mode === 'silent') {
        silentBtn.classList.remove('btn-ghost');
        silentBtn.classList.add('btn-info');
    } else if (mode === 'online') {
        onlineBtn.classList.remove('btn-ghost');
        onlineBtn.classList.add('btn-success');
    }
}