"""
License plate recognition using OpenCV.
This is a simplified placeholder. For production use a proper OCR library
like EasyOCR or Tesseract.
"""
import cv2
import re

def recognize_plate(image):
    """
    Simulates license plate recognition.
    In a real system, you would preprocess the image, detect the plate
    region, and run OCR (e.g., with pytesseract or easyocr).
    Returns a fake plate string like "51H-12345".
    """
    # Placeholder – return a random plate for demo
    import random
    region = random.choice(["51", "30", "59", "60"])
    letters = random.choice(["A", "B", "C", "D"])
    numbers = random.randint(10000, 99999)
    return f"{region}-{letters}{numbers}"

def start_camera_recognition(callback, camera_index=0):
    """
    Opens the default camera and continuously scans for plates.
    When a new plate is detected, calls callback(plate).
    """
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # In a real system: detect plate, crop, OCR
            # For now, just simulate a detection every few seconds
            plate = recognize_plate(frame)
            callback(plate)
            # Show the frame (optional)
            cv2.imshow('Camera', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()