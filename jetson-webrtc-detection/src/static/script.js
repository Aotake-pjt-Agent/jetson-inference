// This file contains the JavaScript code that handles the client-side WebRTC functionality.
// It establishes a connection to the WebRTC server, receives the video stream, and displays it in the browser.

const videoElement = document.getElementById('video');
const startButton = document.getElementById('startButton');
const stopButton = document.getElementById('stopButton');
let localStream;

// Function to start the video stream
async function startStream() {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({ video: true });
        videoElement.srcObject = localStream;
        videoElement.play();
        // Here you would typically connect to the WebRTC server
        // and start sending the video stream
    } catch (error) {
        console.error('Error accessing media devices.', error);
    }
}

// Function to stop the video stream
function stopStream() {
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        videoElement.srcObject = null;
    }
}

// Event listeners for the start and stop buttons
startButton.addEventListener('click', startStream);
stopButton.addEventListener('click', stopStream);