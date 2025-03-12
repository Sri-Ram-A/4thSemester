// Navigation functions
function goToHome() {
    window.location.href = '/home';
}

function goToRideRequest() {
    window.location.href = '/ride-request';
}

function goToRideDetails() {
    window.location.href = '/ride-details';
}

function goToOTP() {
    window.location.href = '/otp';
}

// Animation for the splash screen
function animateSplashScreen() {
    const phrases = [
        "happy drivers",
        "eager riders",
        "urban mobility",
        "safe journeys"
    ];
    let currentIndex = 0;
    const textElement = document.getElementById('dynamic-text');
    
    if (!textElement) return;
    
    setInterval(() => {
        textElement.style.opacity = 0;
        setTimeout(() => {
            currentIndex = (currentIndex + 1) % phrases.length;
            textElement.textContent = phrases[currentIndex];
            textElement.style.opacity = 1;
        }, 500);
    }, 2000);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    animateSplashScreen();
});