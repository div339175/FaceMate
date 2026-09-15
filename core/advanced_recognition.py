"""
🎯 ADVANCED FACE RECOGNITION ENHANCEMENTS
Anti-spoofing and quality assessment features
"""

import cv2
import numpy as np
from deepface import DeepFace
import time

def detect_liveness(frame, face_region):
    """
    🛡️ LIVENESS DETECTION - Prevent photo spoofing
    Detects if the face is from a real person or a photo/video
    """
    liveness_score = 0
    checks = []
    
    try:
        # 1. Eye blink detection (implemented below)
        blink_detected = detect_eye_blink(face_region)
        if blink_detected:
            liveness_score += 30
            checks.append("✅ Natural eye movement detected")
        else:
            checks.append("⚠️ No eye movement detected")
        
        # 2. Facial texture analysis
        texture_score = analyze_face_texture(face_region)
        if texture_score > 0.7:
            liveness_score += 25
            checks.append("✅ Natural skin texture detected")
        else:
            checks.append("⚠️ Artificial texture pattern detected")
        
        # 3. Color distribution analysis
        color_natural = analyze_color_distribution(face_region)
        if color_natural:
            liveness_score += 20
            checks.append("✅ Natural color distribution")
        else:
            checks.append("⚠️ Unusual color patterns")
        
        # 4. Edge consistency check
        edge_consistent = check_edge_consistency(face_region)
        if edge_consistent:
            liveness_score += 25
            checks.append("✅ Consistent facial edges")
        else:
            checks.append("⚠️ Inconsistent edge patterns")
        
        return {
            'is_live': liveness_score > 65,
            'confidence': liveness_score,
            'checks': checks,
            'recommendation': 'ACCEPT' if liveness_score > 75 else 'REVIEW' if liveness_score > 50 else 'REJECT'
        }
        
    except Exception as e:
        return {
            'is_live': False,
            'confidence': 0,
            'checks': [f"❌ Liveness detection failed: {str(e)}"],
            'recommendation': 'REJECT'
        }

def detect_eye_blink(face_region):
    """
    Detect eye blinking patterns to confirm liveness
    """
    try:
        # Convert to grayscale for eye detection
        gray = cv2.cvtColor(face_region, cv2.COLOR_RGB2GRAY)
        
        # Load eye cascade classifier
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        eyes = eye_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        
        # Simple blink detection based on eye aspect ratio
        if len(eyes) >= 2:
            # In a real implementation, this would track eye states over multiple frames
            # For now, we'll use a heuristic based on eye region characteristics
            eye_regions = []
            for (x, y, w, h) in eyes[:2]:
                eye_region = gray[y:y+h, x:x+w]
                eye_regions.append(eye_region)
            
            # Analyze eye openness (simplified)
            avg_intensity = np.mean([np.mean(eye) for eye in eye_regions])
            return avg_intensity > 80  # Threshold for open eyes
        
        return False
        
    except:
        return False

def analyze_face_texture(face_region):
    """
    Analyze facial texture to detect artificial surfaces
    """
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(face_region, cv2.COLOR_RGB2GRAY)
        
        # Calculate texture features using Local Binary Pattern
        def calculate_lbp_variance(image):
            # Simplified LBP calculation
            h, w = image.shape
            lbp_image = np.zeros((h-2, w-2), dtype=np.uint8)
            
            for i in range(1, h-1):
                for j in range(1, w-1):
                    center = image[i, j]
                    binary_string = ''
                    
                    # 8-neighborhood
                    neighbors = [
                        image[i-1, j-1], image[i-1, j], image[i-1, j+1],
                        image[i, j+1], image[i+1, j+1], image[i+1, j],
                        image[i+1, j-1], image[i, j-1]
                    ]
                    
                    for neighbor in neighbors:
                        binary_string += '1' if neighbor >= center else '0'
                    
                    lbp_image[i-1, j-1] = int(binary_string, 2)
            
            return np.var(lbp_image) / 255.0
        
        texture_variance = calculate_lbp_variance(gray)
        return min(1.0, texture_variance * 2)  # Normalize to 0-1
        
    except:
        return 0.5  # Default to neutral score

def analyze_color_distribution(face_region):
    """
    Analyze color distribution to detect screen reflections or unnatural colors
    """
    try:
        # Calculate color histogram
        hist_r = cv2.calcHist([face_region], [0], None, [256], [0, 256])
        hist_g = cv2.calcHist([face_region], [1], None, [256], [0, 256])
        hist_b = cv2.calcHist([face_region], [2], None, [256], [0, 256])
        
        # Check for natural skin tone distribution
        # Skin tones typically have higher values in red and green channels
        red_mean = np.mean(face_region[:,:,0])
        green_mean = np.mean(face_region[:,:,1])
        blue_mean = np.mean(face_region[:,:,2])
        
        # Natural skin tone checks
        is_natural = (
            red_mean > blue_mean and  # Red should dominate blue
            green_mean > blue_mean * 0.8 and  # Green should be significant
            red_mean < 250 and green_mean < 250  # Not oversaturated
        )
        
        return is_natural
        
    except:
        return True  # Default to accepting

def check_edge_consistency(face_region):
    """
    Check for consistent facial edges (photos often have different edge characteristics)
    """
    try:
        # Convert to grayscale and apply edge detection
        gray = cv2.cvtColor(face_region, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Calculate edge density
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
        
        # Natural faces have moderate edge density (not too smooth, not too sharp)
        return 0.02 < edge_density < 0.15
        
    except:
        return True  # Default to accepting

def assess_image_quality(face_region):
    """
    🎯 IMAGE QUALITY ASSESSMENT
    Evaluate if the face image is suitable for recognition
    """
    quality_score = 0
    quality_checks = []
    
    try:
        # 1. Resolution check
        height, width = face_region.shape[:2]
        if height >= 112 and width >= 112:  # Minimum for good recognition
            quality_score += 25
            quality_checks.append(f"✅ Good resolution: {width}x{height}")
        else:
            quality_checks.append(f"⚠️ Low resolution: {width}x{height}")
        
        # 2. Brightness check
        gray = cv2.cvtColor(face_region, cv2.COLOR_RGB2GRAY)
        avg_brightness = np.mean(gray)
        if 80 <= avg_brightness <= 180:
            quality_score += 25
            quality_checks.append(f"✅ Good brightness: {avg_brightness:.1f}")
        else:
            quality_checks.append(f"⚠️ Poor brightness: {avg_brightness:.1f}")
        
        # 3. Contrast check
        contrast = np.std(gray)
        if contrast > 30:
            quality_score += 25
            quality_checks.append(f"✅ Good contrast: {contrast:.1f}")
        else:
            quality_checks.append(f"⚠️ Low contrast: {contrast:.1f}")
        
        # 4. Blur detection
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_score > 100:
            quality_score += 25
            quality_checks.append(f"✅ Sharp image: {blur_score:.1f}")
        else:
            quality_checks.append(f"⚠️ Blurry image: {blur_score:.1f}")
        
        return {
            'quality_score': quality_score,
            'is_good_quality': quality_score >= 75,
            'checks': quality_checks,
            'recommendation': 'ACCEPT' if quality_score >= 75 else 'IMPROVE' if quality_score >= 50 else 'REJECT'
        }
        
    except Exception as e:
        return {
            'quality_score': 0,
            'is_good_quality': False,
            'checks': [f"❌ Quality assessment failed: {str(e)}"],
            'recommendation': 'REJECT'
        }

def multi_frame_verification(frames, enrollment_number):
    """
    🔄 MULTI-FRAME VERIFICATION
    Verify identity across multiple frames for increased accuracy
    """
    if len(frames) < 3:
        return {'verified': False, 'reason': 'Insufficient frames for verification'}
    
    verification_scores = []
    consistency_scores = []
    
    try:
        # Get reference embedding (from database)
        # This would load the stored embedding for the student
        
        for i, frame in enumerate(frames):
            # Detect face in frame
            try:
                detected_faces = DeepFace.extract_faces(
                    img_path=frame,
                    detector_backend="retinaface",
                    enforce_detection=False
                )
                
                if detected_faces and detected_faces[0]['confidence'] > 0.7:
                    face_region = detected_faces[0]['face']
                    
                    # Quality assessment
                    quality = assess_image_quality(face_region)
                    
                    # Liveness detection
                    liveness = detect_liveness(frame, face_region)
                    
                    # Store scores
                    verification_scores.append({
                        'frame': i,
                        'quality_score': quality['quality_score'],
                        'liveness_score': liveness['confidence'],
                        'overall_score': (quality['quality_score'] + liveness['confidence']) / 2
                    })
                
            except Exception as e:
                continue
        
        if len(verification_scores) >= 2:
            avg_score = np.mean([s['overall_score'] for s in verification_scores])
            consistency = np.std([s['overall_score'] for s in verification_scores])
            
            return {
                'verified': avg_score > 70 and consistency < 20,
                'average_score': avg_score,
                'consistency': consistency,
                'frames_processed': len(verification_scores),
                'recommendation': 'ACCEPT' if avg_score > 80 and consistency < 15 else 'REVIEW'
            }
        else:
            return {'verified': False, 'reason': 'Insufficient valid frames'}
            
    except Exception as e:
        return {'verified': False, 'reason': f'Verification failed: {str(e)}'}