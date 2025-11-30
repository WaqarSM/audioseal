# AudioSeal Flask Server

REST API server for AudioSeal watermarking system.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r ../requirements.txt

# Start the server
python server.py

# Server runs on http://0.0.0.0:5001
```

## 📋 Requirements

### Core Dependencies
- Python >= 3.8
- Flask
- PyTorch >= 1.13.0
- torchaudio
- audioseal (this package)

### Audio Format Support

The server supports different audio formats depending on installed backends:

#### ✅ Always Available (with `soundfile`):
- **WAV** - Full support (input & output)
- **FLAC** - Full support (input & output)

#### ⚠️ Requires Additional Backends:
- **MP3** - Requires `sox` or `ffmpeg` backend
- **AAC/M4A** - Requires `ffmpeg` backend
- **OPUS** - Requires `ffmpeg` backend

### Installing Additional Backends

#### For MP3 Support (Option 1 - Sox):
```bash
# macOS
brew install sox

# Linux (Ubuntu/Debian)
sudo apt-get install sox libsox-dev

# Then install Python bindings
pip install sox
```

#### For MP3/AAC Support (Option 2 - FFmpeg):
```bash
# macOS
brew install ffmpeg

# Linux (Ubuntu/Debian)
sudo apt-get install ffmpeg

# Python bindings (optional, for programmatic access)
pip install ffmpeg-python
```

### Verify Backend Installation

Check available backends:
```bash
python -c "import torchaudio; print(torchaudio.list_audio_backends())"
```

Or use the health endpoint:
```bash
curl http://localhost:5001/health | jq
```

## 🎵 Audio Format Support

### Input Formats
- **WAV**: ✅ Always supported
- **FLAC**: ✅ Always supported
- **MP3**: ✅ If `sox` or `ffmpeg` backend installed
- **AAC/M4A**: ✅ If `ffmpeg` backend installed
- **Any sample rate**: ✅ Automatically resampled to 16kHz for processing

### Output Formats
- **WAV**: ✅ Default format
- **FLAC**: ✅ Supported (specify `"output_format": "flac"`)

### Example Usage

#### Watermark with WAV output (default):
```bash
curl -X POST http://localhost:5001/watermark \
  -H "Content-Type: application/json" \
  -d '{"audio_url": "https://example.com/audio.mp3", "alpha": 1.0}' \
  --output watermarked.wav
```

#### Watermark with FLAC output:
```bash
curl -X POST http://localhost:5001/watermark \
  -H "Content-Type: application/json" \
  -d '{
    "audio_url": "https://example.com/audio.wav",
    "output_format": "flac",
    "alpha": 1.0
  }' \
  --output watermarked.flac
```

## 📡 API Endpoints

See [SERVER_OVERVIEW.md](./SERVER_OVERVIEW.md) for complete API documentation.

### Key Endpoints:
- `POST /watermark` - Watermark audio files
- `POST /detect` - Detect watermarks
- `POST /test/pink_noise` - Test robustness against noise
- `POST /test/filters` - Test robustness against filters
- `GET /health` - Health check and backend info

## 🔧 Recent Improvements

### ✅ Format Detection Fix
- Removed hardcoded `.wav` extension requirement
- Auto-detects format from URL or file content
- Supports WAV, FLAC, MP3, AAC, and other formats

### ✅ Output Format Selection
- Added `output_format` parameter to `/watermark` endpoint
- Supports WAV and FLAC output formats
- Defaults to WAV for backward compatibility

### ✅ Better Error Messages
- Clear error messages for unsupported formats
- Lists available backends in error responses
- Helpful guidance on installing missing backends

### ✅ Enhanced Health Endpoint
- Shows available audio backends
- Lists supported input/output formats
- Useful for debugging format support issues

## 🧪 Testing

Run the test suite:
```bash
python test_endpoints.py
```

Test with custom audio:
```bash
python test_endpoints.py --audio-url https://example.com/test.mp3
```

## 🐛 Troubleshooting

### "Failed to load audio file" Error

**Problem**: Server can't load your audio file.

**Solutions**:
1. Check if format is supported:
   ```bash
   curl http://localhost:5001/health | jq '.supported_input_formats'
   ```

2. For MP3/AAC files, install required backend:
   ```bash
   # Option 1: Install sox
   brew install sox  # macOS
   pip install sox
   
   # Option 2: Install ffmpeg
   brew install ffmpeg  # macOS
   ```

3. Verify backend installation:
   ```bash
   python -c "import torchaudio; print(torchaudio.list_audio_backends())"
   ```

### "Unsupported output format" Error

**Problem**: Requested output format not supported.

**Solution**: Currently only `wav` and `flac` are supported. Use:
```json
{
  "output_format": "wav"  // or "flac"
}
```

### Sample Rate Issues

**Note**: AudioSeal models work at 16kHz internally, but the server automatically handles any input sample rate. Your audio will be:
1. Resampled to 16kHz for processing
2. Resampled back to original sample rate for output

No action needed - this is automatic!

## 📚 Additional Documentation

- [SERVER_OVERVIEW.md](./SERVER_OVERVIEW.md) - Complete API documentation
- [FORMAT_SUPPORT.md](./FORMAT_SUPPORT.md) - Detailed format support information

## 🔐 Security Notes

⚠️ **This server is for development/testing**. For production:
- Add authentication
- Implement rate limiting
- Disable debug mode
- Validate/whitelist URLs
- Use HTTPS
- Add logging and monitoring

See [SERVER_OVERVIEW.md](./SERVER_OVERVIEW.md) for security recommendations.

