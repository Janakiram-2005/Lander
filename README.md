# Orion Lander1

**Orion Lander1** is a compact, real-time terrain analysis and decision-support prototype intended to assist autonomous lander systems during approach and touchdown. It combines a lightweight Flask web backend, a vision-based terrain analysis pipeline, and an AI-driven decision engine to analyze images and video frames and provide concise landing recommendations and visual diagnostics to operators or higher-level autonomy modules.

## Features
- Real-time image and video ingestion via HTTP uploads and mobile-friendly endpoints
- Background video processing with playback controls (pause, speed, skip) and session isolation
- Vision-based surface analysis producing leg and ground features and visual overlays
- AI decision engine (`ornion_decide`) that proposes gear/status and an overall landing assessment
- Low-latency streaming of results to dashboards using Socket.IO
- Simple `/status` endpoint reporting operational state and mobile UI URL

## Quick Start
Requirements: Python 3.9+, system OpenCV, and the Python requirements listed in `requirements.txt`.

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/Scripts/activate    # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

2. Run the server locally (binds to all interfaces by default):

```bash
python app.py
```

3. Open the mobile upload UI reported by the `/status` endpoint (e.g., `http://<local-ip>:5000/mobile`) or connect a Socket.IO client to receive `terrain_update` events.

## API Endpoints
- `GET /status` — returns server status, available sensors, and mobile UI URL
- `GET /mobile` — mobile-friendly upload UI
- `POST /analyze` — upload a single image (multipart form `image`) and optional `emergency=true` flag for emergency-mode analysis
- `POST /upload_video` — upload a video (multipart form `video`) to start background processing; include `emergency=true` to enable emergency mode
- `POST /video/control` — control playback: JSON fields `action` (`pause`/`stop`), `speed` (float), and `skip` (seconds)

Socket.IO events:
- `terrain_update` — emits analysis result, gear recommendation, and visuals
- `processing_complete` — emitted when a video processing session finishes

## Architecture Notes
The backend saves transient frames to an `uploads/` directory and uses OpenCV to capture and step through video. The vision logic is implemented in `vision/terrain_analysis`, while the decision logic lives in `ornion_ai/decision_engine`. Video processing runs as a Socket.IO background task with a `playback_session_id` to prevent cross-session interference.

This repository is intended as a testbed for rapid iteration on perception-to-decision workflows for landing systems, suitable for simulation and hardware-in-the-loop testing.

## Contributing
Issues and pull requests are welcome. For changes that affect the perception or decision modules, include before/after examples and, when possible, unit tests for algorithmic behavior.

## License
Specify your preferred license here. If undecided, add a `LICENSE` file or consult your project policies.
