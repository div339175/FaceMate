import numpy as np
import os
import tempfile
import logging
from scipy.spatial.distance import cosine
from django.conf import settings
import cv2
cv2.setNumThreads(1)
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import threading

try:
    from django.conf import settings
    base_dir = getattr(settings, "BASE_DIR", None)
except Exception:
    settings = None
    base_dir = None

if base_dir:
    os.environ.setdefault("KERAS_HOME", os.path.join(str(base_dir), ".keras"))
    os.environ.setdefault("DEEPFACE_HOME", os.path.join(str(base_dir), ".deepface"))
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

_INFERENCE_LOCK = threading.Lock()
_RECOGNITION_LOCK = _INFERENCE_LOCK  # Backwards-compatibility alias
_FACE_CASCADE = None


def _get_face_cascade():
    global _FACE_CASCADE
    if _FACE_CASCADE is None:
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        _FACE_CASCADE = cv2.CascadeClassifier(cascade_path)
    return _FACE_CASCADE


def _get_deepface():
    # Import DeepFace lazily so Django can start even if TensorFlow is unstable.
    from deepface import DeepFace
    return DeepFace

logger = logging.getLogger(__name__)

def generate_avatar_from_initials(name, size=(150, 150)):
    """
    Generates a profile avatar using student's initials.
    Returns base64 encoded image for embedding-only storage approach.
    """
    # Extract initials
    words = name.strip().split()
    if len(words) >= 2:
        initials = f"{words[0][0]}{words[1][0]}".upper()
    else:
        initials = words[0][:2].upper() if words else "ST"
    
    # Create avatar
    img = Image.new('RGB', size, color='#4A90E2')  # Professional blue
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fallback to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 60)
    except:
        font = ImageFont.load_default()
    
    # Center the initials
    bbox = draw.textbbox((0, 0), initials, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    
    draw.text((x, y), initials, fill='white', font=font)
    
    # Convert to base64 for storage efficiency
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"

def enroll_student_face(enrollment_number, image_files, student_name=None):
    """
    🚀 EMBEDDING-ONLY APPROACH 🚀
    Processes student's photos, generates embeddings, saves only .npy file.
    Automatically deletes all photos after processing for 99.9% storage reduction.
    Returns: (embedding_path, processed_count, avatar_data)
    """
    with _INFERENCE_LOCK:
        DeepFace = _get_deepface()
        embeddings = []
        logger.info("Processing %s enrollment images", len(image_files))
        
        for image_file in image_files:
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(prefix="facemate_", suffix=".upload", delete=False) as f:
                    temp_path = f.name
                    for chunk in image_file.chunks():
                        f.write(chunk)
                
                try:
                    embedding_obj = DeepFace.represent(
                        img_path=temp_path, model_name='ArcFace', 
                        enforce_detection=True, detector_backend='retinaface'
                    )
                except Exception:
                    # Fallback to faster opencv detector if retinaface fails
                    embedding_obj = DeepFace.represent(
                        img_path=temp_path, model_name='ArcFace', 
                        enforce_detection=True, detector_backend='opencv'
                    )
                embeddings.append(embedding_obj[0]["embedding"])
                logger.info("Processed enrollment image successfully")
                
            except Exception as e:
                logger.info("Skipped an enrollment image: %s", e)
                continue
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)

        avatar_data = None
        if student_name:
            avatar_data = generate_avatar_from_initials(student_name)

        if len(embeddings) >= 3:
            all_embeddings = np.array(embeddings)
            static_dir = os.path.join(settings.STATICFILES_DIRS[0], 'trained_data')
            os.makedirs(static_dir, exist_ok=True)
            
            embedding_filename = f"{enrollment_number}.npy"
            embedding_path = os.path.join(static_dir, embedding_filename)
            np.save(embedding_path, all_embeddings)
            
            embedding_size = os.path.getsize(embedding_path)
            logger.info("Saved enrollment embedding of %.1f KB", embedding_size / 1024)
            
            return (os.path.join('trained_data', embedding_filename), len(embeddings), avatar_data)
            
        return (None, len(embeddings), avatar_data)


def recognize_faces_in_frame(frame, all_student_embeddings):
    """
    Recognizes students using stored embeddings (.npy files)
    and returns the identities recognized in this frame.
    Non-blocking inference guard drops overlapping frames instantly
    to prevent worker thread saturation.
    """
    if not all_student_embeddings:
        return {"recognized": [], "newly_present": []}

    # Drop frame immediately if an inference operation is already active
    if not _INFERENCE_LOCK.acquire(blocking=False):
        logger.debug("Frame dropped: recognition inference already in progress")
        return {"recognized": [], "newly_present": []}


    try:
        # Fast local pre-detection with OpenCV Haar Cascade (~10ms)
        # Avoids invoking DeepFace when no face is visible in the frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_cascade = _get_face_cascade()
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4, minSize=(50, 50))
        if len(faces) == 0:
            return {"recognized": [], "newly_present": []}

        DeepFace = _get_deepface()
        detector = getattr(settings, 'LIVE_DETECTOR_BACKEND', 'opencv')
        live_reps = DeepFace.represent(
            img_path=frame,
            model_name="ArcFace",
            detector_backend=detector,
            enforce_detection=False
        )

        recognized_enrollment_numbers = []
        for rep in live_reps:
            # Check confidence (if detector returned confidence, skip low-confidence noise)
            confidence = rep.get("face_confidence", 1.0)
            if confidence is not None and confidence < 0.60:
                continue

            live_embedding = rep.get("embedding")
            if not live_embedding:
                continue

            live_embedding = np.asarray(live_embedding, dtype=float)
            best_match_enrollment, best_distance = None, float("inf")

            for enrollment_number, stored_embeddings_list in all_student_embeddings.items():
                candidates = np.asarray(stored_embeddings_list, dtype=float)
                if candidates.ndim == 1:
                    candidates = candidates.reshape(1, -1)
                distances = [cosine(live_embedding, item) for item in candidates]
                distance = float(np.nanmin(distances)) if distances else float("inf")
                if distance < best_distance:
                    best_distance, best_match_enrollment = distance, enrollment_number

            if best_match_enrollment and best_distance <= settings.FACE_MATCH_THRESHOLD:
                if best_match_enrollment not in recognized_enrollment_numbers:
                    recognized_enrollment_numbers.append(best_match_enrollment)

        return {
            "recognized": recognized_enrollment_numbers,  # Seen this frame
            "newly_present": recognized_enrollment_numbers,
        }
    except Exception as exc:
        logger.warning("Face recognition failed gracefully for submitted frame: %s", exc)
        return {"recognized": [], "newly_present": []}
    finally:
        _INFERENCE_LOCK.release()

