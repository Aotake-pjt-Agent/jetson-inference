# Jetson WebRTC Detection

Welcome to the Jetson WebRTC Detection project! This project enables real-time object detection using the SSD MobileNet V2 model on NVIDIA Jetson devices, streaming the results to a web browser via a WebRTC server.

## Project Structure

The project is organized as follows:

```
jetson-webrtc-detection
├── src
│   ├── webrtc_server.py        # WebRTC server for handling client connections and video streaming
│   ├── detection_handler.py     # Logic for real-time object detection
│   └── static
│       ├── index.html          # Main HTML page for displaying the video stream
│       ├── style.css           # Styles for the HTML page
│       └── script.js           # Client-side JavaScript for WebRTC functionality
├── models
│   └── ssd-mobilenet-v2        # Pre-trained model files for SSD MobileNet V2
├── requirements.txt            # Python dependencies for the project
├── config.yaml                 # Configuration settings for the application
└── README.md                   # Documentation for the project
```

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd jetson-webrtc-detection
   ```

2. **Install dependencies:**
   Make sure you have Python 3 and pip installed. Then, run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the application:**
   Edit the `config.yaml` file to set the necessary parameters, such as model paths and server settings.

4. **Run the WebRTC server:**
   Start the server by executing:
   ```bash
   python src/webrtc_server.py
   ```

5. **Access the application:**
   Open a web browser and navigate to `http://<jetson-ip>:<port>/` to view the video stream and interact with the object detection functionality.

## Usage Guidelines

- Ensure that your Jetson device has a camera connected and properly configured.
- The application will stream the video feed from the camera, performing real-time object detection and displaying the results in the browser.
- You can modify the detection logic in `src/detection_handler.py` to customize the behavior of the object detection process.

## Additional Information

For more details on the WebRTC protocol and how it works, refer to the [WebRTC documentation](https://webrtc.org/).

For any issues or contributions, please refer to the project's GitHub page or contact the maintainers.

Happy coding!