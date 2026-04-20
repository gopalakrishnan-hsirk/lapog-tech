import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image
import os
from django.core.files.base import ContentFile

# Initialize Face Detector (Haar Cascade is lightweight and fast)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

from django.core.mail import send_mail
from django.conf import settings


from django.core.mail import EmailMessage

def send_system_email(subject, message, recipient_list, attachment_content=None, attachment_filename=None):
    try:
        email = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
        )
        if attachment_content and attachment_filename:
            email.attach(attachment_filename, attachment_content, 'image/jpeg')
            
        email.send(fail_silently=False)
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False

def get_grayscale_face(base64_str):
    """
    Extracts, grayscales, and resizes a face from a base64 image.
    Returns (face_img, error_msg)
    """
    try:
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        
        img_data = base64.b64decode(base64_str)
        img = Image.open(BytesIO(img_data))
        opencv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(opencv_img, cv2.COLOR_BGR2GRAY)
        
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) == 0:
            return None, "No face detected"
            
        (x, y, w, h) = faces[0]
        face_img = gray[y:y+h, x:x+w]
        face_img = cv2.resize(face_img, (200, 200))
        
        return face_img, None
    except Exception as e:
        return None, str(e)

def train_recognizer(face_samples):
    """
    Trains an LBPH recognizer with a list of face images (as base64 or numpy arrays).
    For this simple implementation, we'll store samples and re-train/match.
    """
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    faces = []
    labels = []
    
    for i, base64_sample in enumerate(face_samples):
        face, err = get_grayscale_face(base64_sample)
        if face is not None:
            faces.append(face)
            labels.append(1) # All samples are the same user
            
    if not faces:
        return None
        
    recognizer.train(faces, np.array(labels))
    return recognizer

def verify_face(stored_samples, candidate_base64):
    """
    Verifies a candidate face against stored samples.
    """
    if not stored_samples:
        return False, "No enrolled face data"
        
    recognizer = train_recognizer(stored_samples)
    if not recognizer:
        return False, "Failed to initialize recognizer"
        
    candidate_face, err = get_grayscale_face(candidate_base64)
    if candidate_face is None:
        return False, err
        
    label, confidence = recognizer.predict(candidate_face)
    
    # In LBPH, lower confidence means better match. 
    # Usually < 50-70 is a good match.
    if confidence < 70:
        return True, f"Confidence: {confidence:.2f}"
    else:
        return False, f"Face mismatch (Confidence: {confidence:.2f})"

def validate_password(password):
    """
    Validates that a password meets the following criteria:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one number
    - Contains at least one symbol
    """
    import re
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one symbol."
    
    return True, None
