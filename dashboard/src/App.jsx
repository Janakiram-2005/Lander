import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { io } from 'socket.io-client';
import { QRCodeCanvas } from 'qrcode.react';
import { ShieldAlert, Zap, Camera, Upload, AlertTriangle, AlertCircle, Search, Thermometer, Radio, Compass, BarChart3, Flame, Smartphone, Video, Play, Pause, FastForward, Rewind } from 'lucide-react';

const API_BASE = `${window.location.protocol}//${window.location.hostname}:5000`;

// Initialize Socket outside component to avoid multiple connections
const socket = io(API_BASE);

function App() {
    const [data, setData] = useState(null);
    const [status, setStatus] = useState({ status: 'CONNECTING...' });
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('original');
    const [emergencyMode, setEmergencyMode] = useState(false);
    const [showQR, setShowQR] = useState(false);
    const [videoMode, setVideoMode] = useState(false);
    const [mobileUrl, setMobileUrl] = useState('');
    const [localIp, setLocalIp] = useState('');

    // Video Controls State
    const [videoSpeed, setVideoSpeed] = useState(1.0);

    useEffect(() => {
        // Fetch initialization status including network info
        const fetchStatus = async () => {
            try {
                const res = await axios.get(`${API_BASE}/status`);
                if (res.data.network) {
                    setLocalIp(res.data.network.local_ip);
                    const url = `http://${res.data.network.local_ip}:5000/mobile`;
                    setMobileUrl(url);
                }
            } catch (e) {
                console.error("Failed to fetch status", e);
            }
        };
        fetchStatus();

        // SocketIO Event Listeners
        socket.on('connect', () => {
            console.log("Connected to VBAL Uplink");
            setStatus(prev => ({ ...prev, status: 'OPERATIONAL', mode: 'REAL-TIME LINK' }));
        });

        socket.on('terrain_update', (newData) => {
            // Automatically update state with new data from mobile or video
            setData(newData);
            setLoading(false);
            // If it's a video frame, ensure we are in a mode that shows it smoothly
            if (newData.is_video_frame) {
                setVideoMode(true);
            }
        });

        socket.on('processing_complete', () => {
            setVideoMode(false);
            alert("Video Simulation Complete");
        });

        return () => {
            socket.off('connect');
            socket.off('terrain_update');
            socket.off('processing_complete');
        };
    }, []);

    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setLoading(true);
        const formData = new FormData();
        formData.append('image', file);
        formData.append('emergency', emergencyMode);

        try {
            const res = await axios.post(`${API_BASE}/analyze`, formData);
            // Update immediately on response, SocketIO will handle subsequent real-time updates
            setData(res.data);
        } catch (e) {
            console.error(e);
            alert("Upload failed. See console for details.");
            setLoading(false);
        }
    };

    const handleVideoUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setVideoMode(true);
        const formData = new FormData();
        formData.append('video', file);
        formData.append('emergency', emergencyMode);

        try {
            await axios.post(`${API_BASE}/upload_video`, formData);
        } catch (e) {
            alert("Video upload failed");
            setVideoMode(false);
        }
    };

    const sendVideoControl = async (payload) => {
        try {
            await axios.post(`${API_BASE}/video/control`, payload);
        } catch (e) {
            console.error("Video control failed", e);
        }
    };

    const handleSpeedChange = (newSpeed) => {
        setVideoSpeed(newSpeed);
        sendVideoControl({ speed: newSpeed });
    };

    const handleSkip = (seconds) => {
        sendVideoControl({ skip: seconds });
    };

    const toggleEmergency = () => {
        // For immediate local feedback
        setEmergencyMode(!emergencyMode);
        // In a real system, we'd emit this change to the backend to re-process current frame
        // For now, next frame/upload will respect this flag
    };

    const getLegStyle = (leg) => {
        if (!data) return { height: '80px', '--spread': '0deg' };
        const g = data.gear[leg];
        const spreadSide = leg.endsWith('L') ? -1 : 1;

        // Telescopic Visuals: Map CM directly to pixels for the overlay
        // Base height 100px, + height_cm * 2
        const baseHeight = 100;
        const extension = g.height_cm * 4;

        return {
            height: `${baseHeight + extension}px`,
            '--spread': `${g.spread_angle * spreadSide}deg`
        };
    };

    return (
        <div className="dashboard-container">
            {/* COLUMN 1: SIDEBAR (CONTROLS) */}
            <aside className="sidebar">
                <div className="sidebar-scroll-content">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '0.5rem' }}>
                        <Radio size={24} color="var(--accent-color)" />
                        <h1 style={{ fontSize: '1.4rem', fontWeight: '800', letterSpacing: '-0.5px' }}>VBAL-X2 PRO</h1>
                    </div>
                    <p style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', letterSpacing: '2px', fontWeight: '700', marginBottom: '2.5rem' }}>ADVANCED MISSION CONTROL</p>

                    <div className="system-status">
                        <div className="status-indicator" style={{ backgroundColor: status.status === 'OPERATIONAL' ? 'var(--success)' : '#555' }}></div>
                        <span style={{ fontSize: '0.75rem', fontWeight: '800' }}>{status.status}</span>
                        {videoMode && <span style={{ fontSize: '0.6rem', color: 'var(--accent-color)', marginLeft: '10px' }}>LIVE FEED</span>}
                    </div>

                    <div className="emergency-toggle-container">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.7rem', fontWeight: '700', color: '#ff4d4d' }}>
                            <Flame size={14} /> STABILIZATION OVERRIDE
                        </div>
                        <button
                            className={`emergency-btn ${emergencyMode ? 'active' : ''}`}
                            onClick={toggleEmergency}
                        >
                            {emergencyMode ? "DEACTIVATE EMERGENCY" : "ACTIVATE EMERGENCY"}
                        </button>
                    </div>

                    <button className="link-device-btn" onClick={() => setShowQR(!showQR)}>
                        <Smartphone size={16} />
                        {showQR ? "HIDE UPLINK" : "LINK MOBILE DEVICE"}
                    </button>

                    {showQR && (
                        <div className="qr-panel">
                            <QRCodeCanvas value={mobileUrl || "Scanning..."} size={120} fgColor="#00f2ff" bgColor="transparent" />
                            <p>SCAN TO CONNECT</p>
                            <div style={{ marginTop: '10px', fontSize: '0.65rem', color: '#555', textAlign: 'center' }}>
                                <strong>OFFLINE MODE:</strong><br />
                                Connect phone to same Hotspot/WiFi.<br />
                                Local IP: <span style={{ fontFamily: 'monospace' }}>{localIp || "Locating..."}</span>
                            </div>
                        </div>
                    )}

                    <label className="link-device-btn" style={{ marginTop: '10px', background: 'rgba(255,255,255,0.05)' }}>
                        <Video size={16} />
                        SIMULATE VIDEO FEED
                        <input type="file" hidden accept="video/*" onChange={handleVideoUpload} />
                    </label>

                    {/* VIDEO CONTROLS */}
                    {videoMode && (
                        <div className="glass-card" style={{ marginTop: '1rem', padding: '1rem' }}>
                            <div style={{ fontSize: '0.7rem', fontWeight: 'bold', color: 'var(--accent-color)', marginBottom: '0.5rem' }}>PLAYBACK CONTROL</div>

                            <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginBottom: '10px' }}>
                                <button className="tab-btn" onClick={() => handleSkip(-5)}><Rewind size={16} /></button>
                                <button className="tab-btn" onClick={() => sendVideoControl({ action: 'stop' })} style={{ color: 'var(--danger)' }}><Pause size={16} /></button>
                                <button className="tab-btn" onClick={() => handleSkip(5)}><FastForward size={16} /></button>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.7rem' }}>
                                <span>SPEED:</span>
                                <input
                                    type="range"
                                    min="0.5"
                                    max="4.0"
                                    step="0.5"
                                    value={videoSpeed}
                                    onChange={(e) => handleSpeedChange(parseFloat(e.target.value))}
                                    style={{ flex: 1 }}
                                />
                                <span style={{ width: '30px', textAlign: 'right' }}>{videoSpeed}x</span>
                            </div>
                        </div>
                    )}

                    {data && (
                        <div style={{ marginTop: '2rem' }}>
                            <div className="holistic-score">
                                <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginBottom: '5px' }}>STABILITY INDEX</div>
                                <div style={{ fontSize: '1.2rem', fontWeight: '900', color: 'var(--accent-color)' }}>{data.overall.stability}</div>
                            </div>
                            <div className="recommendation-banner" style={{ borderColor: emergencyMode ? '#ff4d4d' : 'var(--accent-color)', color: emergencyMode ? '#ff4d4d' : 'var(--accent-color)' }}>
                                {data.overall.recommendation}
                            </div>
                        </div>
                    )}
                </div>

                <label className="file-upload-btn">
                    <Upload size={18} />
                    ACQUIRE TERRAIN
                    <input type="file" hidden onChange={handleFileUpload} accept="image/*" />
                </label>
            </aside>

            {/* COLUMN 2: CENTER (ROVER VISUALIZATION) */}
            <div className="rover-viewport">
                <div className="rover-grid-lines"></div>

                {/* ROVER UNIT */}
                <div className={`lander-center-stage ${emergencyMode ? 'lander-emergency-active' : ''}`}>
                    <div className="ship-body">
                        <div className="ship-wing wing-l"></div>
                        <div className="ship-wing wing-r"></div>
                        <div className="thruster thruster-l"><div className="thruster-glow"></div></div>
                        <div className="thruster thruster-r"><div className="thruster-glow"></div></div>
                    </div>
                    <div className="leg leg-rl" style={getLegStyle('RL')}></div>
                    <div className="leg leg-rr" style={getLegStyle('RR')}></div>
                    <div className="leg leg-fl" style={getLegStyle('FL')}></div>
                    <div className="leg leg-fr" style={getLegStyle('FR')}></div>
                </div>
            </div>

            {/* COLUMN 3: RIGHT PANEL (DATA & IMAGE) */}
            <div className="data-panel">
                {/* TOP: IMAGE FEED / MAP */}
                <div className="data-top">
                    {/* Visual Tabs floating in top right */}
                    <div className="visual-tabs">
                        {['original', 'slope', 'depth'].map(tab => (
                            <button key={tab} className={`tab-btn ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)}>
                                {tab.charAt(0).toUpperCase() + tab.slice(1)}
                            </button>
                        ))}
                    </div>

                    <div className="image-feed-container">
                        {!data ? (
                            <div className="no-signal">
                                <Camera size={48} style={{ opacity: 0.1, marginBottom: '1rem' }} />
                                <p>WAITING FOR UPLINK...</p>
                            </div>
                        ) : (
                            <img
                                src={`data:image/jpeg;base64,${data.visuals[activeTab === 'original' ? 'original_gray' : activeTab === 'slope' ? 'slope_map' : 'depth_map']}`}
                                className="feed-image"
                                alt="Terrain"
                            />
                        )}
                        <div className="scanning-bar"></div>
                    </div>
                </div>

                {/* BOTTOM: TELEMETRY */}
                <div className="data-bottom">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1.5rem' }}>
                        <Thermometer size={18} color="var(--accent-color)" />
                        <h3 style={{ fontSize: '0.9rem' }}>HYDRAULIC TELEMETRY</h3>
                    </div>

                    {!data ? (
                        <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>No telemetry available.</div>
                    ) : (
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                            {Object.entries(data.gear).map(([leg, g]) => (
                                <div key={leg} className="stat-item">
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                        <strong style={{ fontSize: '0.8rem', opacity: 0.8 }}>LEG {leg}</strong>
                                        <span style={{ color: g.status === 'SAFE' ? 'var(--success)' : 'var(--danger)', fontWeight: '800' }}>{g.height_cm}cm</span>
                                    </div>
                                    <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>SLOPE: {(g.raw_features.slope_index * 100).toFixed(0)}%</div>
                                    <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>SPREAD: {g.spread_angle}°</div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default App;
