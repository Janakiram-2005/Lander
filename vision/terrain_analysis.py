import cv2
import numpy as np
import base64

def image_to_base64(img):
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode('utf-8')

def add_direction_indicator(img, label="UP"):
    # Draw a directional arrow (North/UP)
    h, w = img.shape[:2]
    color = (0, 255, 255) if len(img.shape) == 3 else 255
    # Arrow
    cv2.arrowedLine(img, (w - 30, 40), (w - 30, 10), color, 2, tipLength=0.5)
    # Text
    cv2.putText(img, label, (w - 45, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    return img

def analyze_surface(image_path):
    # Read image
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise ValueError(f"Could not read image at {image_path}")
    
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    img_gray = cv2.resize(img_gray, (512, 512))
    
    # 1. Slope Map (Stronger Gradients)
    gx = cv2.Sobel(img_gray, cv2.CV_64F, 1, 0, ksize=5) # Larger ksize for smoother gradients
    gy = cv2.Sobel(img_gray, cv2.CV_64F, 0, 1, ksize=5)
    slope_map = np.sqrt(gx**2 + gy**2)
    slope_map_norm = cv2.normalize(slope_map, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    slope_color = cv2.applyColorMap(slope_map_norm, cv2.COLORMAP_MAGMA)
    slope_color = add_direction_indicator(slope_color)

    # 2. Depth/Shadow Map (Enhanced Contrast)
    depth_map = 255 - img_gray
    # Enhance contrast using CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    depth_enhanced = clahe.apply(depth_map)
    depth_color = cv2.applyColorMap(depth_enhanced, cv2.COLORMAP_TWILIGHT_SHIFTED)
    depth_color = add_direction_indicator(depth_color)

    # Original with indicator
    original_marked = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)
    original_marked = add_direction_indicator(original_marked)

    # 3. Quadrant Analysis
    h, w = img_gray.shape
    regions = {
        "FL": img_gray[0:h//2, 0:w//2],
        "FR": img_gray[0:h//2, w//2:w],
        "RL": img_gray[h//2:h, 0:w//2],
        "RR": img_gray[h//2:h, w//2:w]
    }

    features = {}
    for leg, region in regions.items():
        edges = cv2.Canny(region, 30, 100)
        hazard_density = np.count_nonzero(edges) / edges.size
        mean_brightness = np.mean(region)
        
        gx_r = cv2.Sobel(region, cv2.CV_64F, 1, 0, ksize=3)
        gy_r = cv2.Sobel(region, cv2.CV_64F, 0, 1, ksize=3)
        slope_index = np.mean(np.sqrt(gx_r**2 + gy_r**2)) / 255

        features[leg] = {
            "hazard_density": round(hazard_density, 3),
            "slope_index": round(slope_index, 3),
            "mean_brightness": round(mean_brightness, 2)
        }

    return {
        "leg_features": features,
        "visuals": {
            "slope_map": image_to_base64(slope_color),
            "depth_map": image_to_base64(depth_color),
            "original_gray": image_to_base64(original_marked)
        }
    }
