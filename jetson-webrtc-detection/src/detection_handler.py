from flask import Response
import cv2
import numpy as np
import tensorflow as tf

class DetectionHandler:
    def __init__(self, model_path):
        self.model = tf.saved_model.load(model_path)
        self.category_index = self.load_category_index()

    def load_category_index(self):
        # Load the category index for the model
        # This is a placeholder for loading the actual category index
        return {1: 'person', 2: 'bicycle', 3: 'car', 4: 'motorcycle', 5: 'airplane'}

    def process_frame(self, frame):
        # Convert the frame to a tensor
        input_tensor = tf.convert_to_tensor(frame)
        input_tensor = input_tensor[tf.newaxis, ...]

        # Perform detection
        detections = self.model(input_tensor)

        # Process the detections
        return self.process_detections(detections)

    def process_detections(self, detections):
        # Extract detection results
        boxes = detections['detection_boxes'][0].numpy()
        scores = detections['detection_scores'][0].numpy()
        classes = detections['detection_classes'][0].numpy().astype(int)

        results = []
        for i in range(len(scores)):
            if scores[i] > 0.5:  # Confidence threshold
                box = boxes[i]
                class_id = classes[i]
                results.append({
                    'box': box.tolist(),
                    'score': scores[i].tolist(),
                    'class': self.category_index[class_id]
                })
        return results

    def generate_frames(self, video_source):
        cap = cv2.VideoCapture(video_source)
        while True:
            success, frame = cap.read()
            if not success:
                break

            # Resize frame for the model
            frame_resized = cv2.resize(frame, (300, 300))
            detections = self.process_frame(frame_resized)

            # Draw bounding boxes on the frame
            for detection in detections:
                box = detection['box']
                class_name = detection['class']
                score = detection['score']
                cv2.rectangle(frame, 
                              (int(box[1] * frame.shape[1]), int(box[0] * frame.shape[0])),
                               (int(box[3] * frame.shape[1]), int(box[2] * frame.shape[0])), 
                               (0, 255, 0), 2)
                cv2.putText(frame, f"{class_name}: {score:.2f}", 
                            (int(box[1] * frame.shape[1]), int(box[0] * frame.shape[0]) - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

            # Encode the frame in JPEG format
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')