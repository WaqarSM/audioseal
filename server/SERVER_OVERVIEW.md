# AudioSeal Flask Server - Overview

## Purpose
This Flask server provides a REST API for the AudioSeal watermarking system, allowing you to:
- Watermark audio files with secret messages
- Detect watermarks in audio files
- Test watermark robustness against various attacks
- Visualize audio waveforms and spectrograms

## Architecture

### Core Components

1. **Models** (loaded at startup):
   - **Generator** (`audioseal_wm_16bits`): Embeds watermarks into audio
   - **Detector** (`audioseal_detector_16bits`): Detects watermarks in audio
   - Models are loaded once when the server starts for efficiency

2. **Device Detection**:
   - Automatically detects and uses:
     - MPS (Apple Silicon GPU) if available
     - CUDA (NVIDIA GPU) if available
     - CPU as fallback

3. **Audio Processing**:
   - Downloads audio from URLs (HTTP/HTTPS or file://)
   - Converts stereo to mono automatically
   - Handles temporary file cleanup

## API Endpoints

### 1. `POST /watermark`
**Purpose**: Embed a watermark into an audio file

**Request Body**:
```json
{
  "audio_url": "https://example.com/audio.wav",
  "message": [0, 1, 0, 1, ...],  // Optional: 16-bit binary array
  "alpha": 1.0                    // Optional: watermark strength (default: 1.0)
}
```

**Response**: 
- Returns a WAV file (binary) with the watermarked audio
- Content-Type: `audio/wav`
- Filename: `watermarked_audio.wav`

**Notes**:
- If `message` is not provided, a random watermark is generated
- `message` must be exactly 16 bits if provided
- `alpha` controls watermark strength (higher = more visible but more robust)

---

### 2. `POST /detect`
**Purpose**: Detect if an audio file contains a watermark

**Request Body**:
```json
{
  "audio_url": "https://example.com/audio.wav",
  "message_threshold": 0.5  // Optional: detection threshold (default: 0.5)
}
```

**Response**:
```json
{
  "is_watermarked": true,
  "detection_probability": 0.95,
  "decoded_message": [1, 0, 1, 1, ...]  // 16-bit array
}
```

**Notes**:
- `detection_probability` is a float between 0 and 1
- `is_watermarked` is `true` if probability > `message_threshold`
- `decoded_message` contains the extracted 16-bit message

---

### 3. `POST /test/pink_noise`
**Purpose**: Test watermark robustness against pink noise attack

**Request Body**:
```json
{
  "audio_url": "https://example.com/audio.wav",
  "noise_std": 0.1  // Optional: noise standard deviation (default: 0.1)
}
```

**Response**:
```json
{
  "detection_probability": 0.87,
  "is_watermarked": true,
  "decoded_message": [1, 0, 1, ...],
  "plot": "base64_encoded_png_image",
  "noise_std": 0.1
}
```

**Notes**:
- Applies pink noise to the audio
- Tests if watermark is still detectable after attack
- Returns a visualization plot (base64 PNG)

---

### 4. `POST /test/filters`
**Purpose**: Test watermark robustness against highpass and lowpass filters

**Request Body**:
```json
{
  "audio_url": "https://example.com/audio.wav",
  "cutoff_freq": 5000,      // Optional: filter cutoff frequency (default: 5000 Hz)
  "sample_rate": 16000      // Optional: sample rate (auto-detected if not provided)
}
```

**Response**:
```json
{
  "highpass": {
    "detection_probability": 0.82,
    "is_watermarked": true,
    "decoded_message": [1, 0, ...],
    "plot": "base64_encoded_png",
    "cutoff_freq": 5000
  },
  "lowpass": {
    "detection_probability": 0.91,
    "is_watermarked": true,
    "decoded_message": [1, 0, ...],
    "plot": "base64_encoded_png",
    "cutoff_freq": 5000
  }
}
```

**Notes**:
- Tests both highpass (removes low frequencies) and lowpass (removes high frequencies)
- Returns separate results and plots for each filter

---

### 5. `POST /test/waveform_and_specgram`
**Purpose**: Generate waveform and spectrogram visualization

**Request Body**:
```json
{
  "audio_url": "https://example.com/audio.wav",
  "title": "My Audio"  // Optional: plot title
}
```

**Response**:
```json
{
  "plot": "base64_encoded_png_image",
  "sample_rate": 16000,
  "duration": 5.2,
  "title": "My Audio"
}
```

**Notes**:
- Creates a 2-panel plot: waveform (time domain) and spectrogram (frequency domain)
- Useful for debugging and visualization

---

### 6. `POST /test/waveform_and_specgram_difference`
**Purpose**: Compare two audio files side-by-side

**Request Body**:
```json
{
  "audio_url_1": "https://example.com/original.wav",
  "audio_url_2": "https://example.com/watermarked.wav",
  "title_1": "Original",      // Optional
  "title_2": "Watermarked"    // Optional
}
```

**Response**:
```json
{
  "plot": "base64_encoded_png_image",
  "sample_rate": 16000,
  "duration": 5.2,
  "difference_stats": {
    "max_absolute_difference": 0.023,
    "mean_absolute_difference": 0.001,
    "rms_difference": 0.005
  },
  "audio1_title": "Original",
  "audio2_title": "Watermarked"
}
```

**Notes**:
- Creates a 3-row comparison: audio1, audio2, and their difference
- Automatically handles sample rate mismatches and length differences
- Provides statistics on the difference between the two files

---

### 7. `GET /health`
**Purpose**: Health check endpoint

**Response**:
```json
{
  "status": "healthy",
  "device": "mps"  // or "cuda" or "cpu"
}
```

**Notes**:
- Useful for monitoring and load balancers
- Shows which device (GPU/CPU) is being used

---

## Helper Functions

### `download_audio(url)`
- Downloads audio from HTTP/HTTPS URLs or reads from `file://` URLs
- Converts stereo to mono automatically
- Returns PyTorch tensor and sample rate
- Handles temporary file cleanup

### `plot_waveform_and_specgram(waveform, sample_rate, title)`
- Creates matplotlib visualization
- Returns base64-encoded PNG image
- Uses non-interactive backend (Agg) for server use

### `save_audio_tensor(audio_tensor, sample_rate, output_path)`
- Saves PyTorch audio tensor to WAV file
- Uses torchaudio for saving

## Testing

The `test_endpoints.py` script provides comprehensive testing:

```bash
# Run all tests
python server/test_endpoints.py

# Customize test parameters
python server/test_endpoints.py --base-url http://localhost:5001 --audio-url https://example.com/test.wav
```

**Test Coverage**:
- Health check
- Watermarking (with and without message)
- Detection (original and watermarked audio)
- Pink noise attack
- Filter attacks (highpass/lowpass)
- Waveform/spectrogram generation
- Difference comparison
- Error handling

**Test Results**:
- Saved to `test_results/YYYYMMDD_HHMMSS/`
- Includes plots, audio files, and JSON summary

## Running the Server

```bash
# Start the server
python server/server.py

# Server runs on:
# - Host: 0.0.0.0 (all interfaces)
# - Port: 5001
# - Debug mode: enabled
```

**Note**: Models are loaded at startup, which may take a minute or two.

## 📦 Dependencies

Key dependencies (from `requirements.txt`):
- `flask` - Web framework
- `torch` - PyTorch for ML models
- `torchaudio` - Audio processing
- `matplotlib` - Plotting
- `audioseal` - AudioSeal library (from this repo)
- `julius` - Audio effects (via attacks.py)

## 🔍 Key Implementation Details

1. **Batch Processing**: All audio is processed with a batch dimension (`unsqueeze(0)`)
2. **Device Management**: Detector runs on GPU if available, generator on CPU
3. **Error Handling**: All endpoints return JSON errors with appropriate HTTP status codes
4. **Temporary Files**: Uses Python's `tempfile` module for safe file handling
5. **Base64 Encoding**: Plots are encoded as base64 strings for JSON responses
6. **Audio Format**: Supports multiple input formats (WAV, FLAC, MP3, AAC with proper backends), outputs WAV only

## Audio Format & Sample Rate Support

### Quick Summary:
-  **Sample Rates**: Any sample rate supported (44.1kHz, 48kHz, etc.) - automatically resampled to 16kHz for processing
-  **Input Formats**: WAV, FLAC (always), MP3/AAC (if backends installed)
-  **Bitrates**: All bitrates supported (models work on decoded waveforms)
-  **Output Format**: WAV only (currently)

**For detailed format support information, see [FORMAT_SUPPORT.md](./FORMAT_SUPPORT.md)**

### Key Points:
- AudioSeal models are trained at 16kHz but automatically handle other sample rates
- The server uses `torchaudio.load()` which supports multiple formats
- Output is currently hardcoded to WAV format
- Different bitrates work fine - models process raw waveforms after decoding

## Common Issues

1. **Model Loading**: First request may be slow if models aren't cached
2. **Memory**: Large audio files may cause OOM errors
3. **URL Access**: `file://` URLs must use absolute paths
4. **Sample Rate**: Audio is automatically resampled to 16kHz internally (any input sample rate works)
5. **Format Support**: MP3/AAC require additional backends (sox/ffmpeg) - see FORMAT_SUPPORT.md

## Example Usage

### Watermark an audio file:
```bash
curl -X POST http://localhost:5001/watermark \
  -H "Content-Type: application/json" \
  -d '{"audio_url": "https://example.com/audio.wav", "alpha": 1.0}' \
  --output watermarked.wav
```

### Detect watermark:
```bash
curl -X POST http://localhost:5001/detect \
  -H "Content-Type: application/json" \
  -d '{"audio_url": "https://example.com/audio.wav"}' | jq
```

### Test pink noise attack:
```bash
curl -X POST http://localhost:5001/test/pink_noise \
  -H "Content-Type: application/json" \
  -d '{"audio_url": "https://example.com/audio.wav", "noise_std": 0.1}' | jq
```

## Security Considerations

 **Current Implementation**:
- No authentication/authorization
- No rate limiting
- Debug mode enabled
- Accepts arbitrary URLs (potential SSRF risk)

**For Production**:
- Add authentication (API keys, OAuth, etc.)
- Implement rate limiting
- Disable debug mode
- Validate/whitelist URLs
- Add request size limits
- Use HTTPS
- Add logging and monitoring

