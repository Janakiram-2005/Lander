from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import cv2
import base64
import numpy as np
import time
import socket
from vision.terrain_analysis import analyze_surface
from ornion_ai.decision_engine import ornion_decide

app = Flask(__name__)
CORS(app)
# Use threading mode for better compatibility on Windows during dev
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- GLOBAL STATE ---
video_state = {
    "playing": False,
    "speed": 1.0,  # Multiplier: 0.5, 1.0, 2.0, etc.
    "skip_flag": 0, # +N or -N seconds to skip
    "current_frame_time": 0.0,
    "playback_session_id": 0  # Unique ID for the current playback session
}

def get_local_ip():
    """Try to determine the likely local network IP for external access."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't have to be reachable
        s.connect(('8.8.8.8', 1)) 
        IP = s.getsockname()[0]
        s.close()
    except Exception:
        IP = '127.0.0.1'
    return IP

# --- HELPER FUNCTIONS ---
def process_and_broadcast(image_path, emergency_mode=False, is_video_frame=False):
    """Analyzes an image and broadcasts the result via SocketIO."""
    try:
        result = analyze_surface(image_path)
        features = result["leg_features"]
        visuals = result["visuals"]
        
        decision = ornion_decide(features, emergency_mode=emergency_mode)
        
        response_data = {
            "features": features,
            "gear": decision["gear"],
            "overall": decision["overall"],
            "visuals": visuals,
            "is_video_frame": is_video_frame
        }
        
        socketio.emit('terrain_update', response_data)
        return response_data
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error processing frame: {e}")
        return None

def video_processing_task(video_path, emergency_mode=False, session_id=0):
    """Background task to process video frames with controls."""
    global video_state
    
    # Check if this task is still relevant before starting
    if video_state["playback_session_id"] != session_id:
        print(f"Aborting session {session_id} because a new session {video_state['playback_session_id']} started.")
        return

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Reset state
    video_state["playing"] = True
    video_state["skip_flag"] = 0
    video_state["current_frame_time"] = 0.0
    
    print(f"Starting video processing: {video_path} (FPS: {fps}, Session: {session_id})")
    
    current_frame_index = 0
    
    while cap.isOpened():
        # CHECK CONCURRENCY: Stop if a new video started
        if video_state["playback_session_id"] != session_id:
            print(f"Session {session_id} preempted.")
            break
            
        # CHECK PAUSE/STOP
        if not video_state["playing"]:
            # If manually stopped, break loop
            # Note: If we wanted to support 'Pause' we would just sleep and continue here
            break

        # 1. Handle Skipping
        if video_state["skip_flag"] != 0:
            skip_frames = int(video_state["skip_flag"] * fps)
            current_frame_index += skip_frames
            # Clamp
            current_frame_index = max(0, min(current_frame_index, total_frames - 1))
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_index)
            video_state["skip_flag"] = 0 # Reset flag
            print(f"Skipped to frame {current_frame_index}")

        # 2. Read Frame
        ret, frame = cap.read()
        if not ret:
            print("Video ended.")
            break
            
        current_frame_index += 1
        video_state["current_frame_time"] = current_frame_index / fps

        # 3. Process & Broadcast
        # Save frame temporarily
        temp_frame_path = os.path.join(UPLOAD_FOLDER, 'temp_frame.jpg')
        cv2.imwrite(temp_frame_path, frame)
        
        process_and_broadcast(temp_frame_path, emergency_mode, is_video_frame=True)
        
        # 4. Handle Speed / Sleep
        base_delay = 1.0 / fps
        actual_delay = base_delay / max(0.1, video_state["speed"])
        
        socketio.sleep(actual_delay)

    cap.release()
    if video_state["playback_session_id"] == session_id:
        # Only set playing to false if WE are the active session
        video_state["playing"] = False
        socketio.emit('processing_complete', {'status': 'done'})
    print(f"Session {session_id} ended.")


# --- ROUTES ---

@app.route('/mobile')
def mobile_ui():
    return render_template('mobile.html')

@app.route('/upload_mobile', methods=['POST'])
def upload_mobile():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    filepath = os.path.join(UPLOAD_FOLDER, "mobile_upload.jpg")
    file.save(filepath)
    
    # Broadcast to dashboard
    process_and_broadcast(filepath, emergency_mode=False) # Default to normal mode for mobile scan
    
    return jsonify({"status": "sent_to_dashboard"})

@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({"error": "No video uploaded"}), 400
        
    file = request.files['video']
    
    # Use unique filename to prevent file locking issues on Windows
    unique_name = f"video_{int(time.time())}.mp4"
    filepath = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(filepath)
    
    emergency_mode = request.form.get('emergency') == 'true'
    
    # Increment Session ID to invalidate previous tasks
    video_state["playback_session_id"] += 1
    current_session = video_state["playback_session_id"]
    
    # Start background task
    socketio.start_background_task(video_processing_task, filepath, emergency_mode, current_session)
    
    return jsonify({"status": "processing_started", "session_id": current_session})

@app.route('/video/control', methods=['POST'])
def video_control():
    global video_state
    data = request.json
    
    if "action" in data:
        action = data["action"]
        if action == "pause" or action == "stop":
            video_state["playing"] = False
            
    if "speed" in data:
        try:
            video_state["speed"] = float(data["speed"])
        except:
            pass
            
    if "skip" in data:
        try:
            video_state["skip_flag"] = float(data["skip"]) # seconds
        except:
            pass
            
    return jsonify(video_state)

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    emergency_mode = request.form.get('emergency') == 'true'
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    
    data = process_and_broadcast(filepath, emergency_mode)
    if data is None:
        return jsonify({"error": "Processing failed"}), 500
    return jsonify(data)

@app.route('/status', methods=['GET'])
def get_status():
    local_ip = get_local_ip()
    return jsonify({
        "status": "OPERATIONAL",
        "mode": "REAL-TIME SOCKET",
        "sensors": ["LIDAR", "OPTICAL", "RADAR", "SOCKET_IO"],
        "network": {
            "local_ip": local_ip,
            "mobile_url": f"http://{local_ip}:5000/mobile"
        }
    })

if __name__ == '__main__':
    host_ip = '0.0.0.0'
    print(f"SERVER STARTING ON http://{host_ip}:5000")
    print(f"LOCAL NETWORK IP: {get_local_ip()}")
    socketio.run(app, debug=True, port=5000, host=host_ip)
