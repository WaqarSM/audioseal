# AudioSeal Format & Sample Rate Support

## 📊 Summary

| Feature | Support | Notes |
|---------|---------|-------|
| **44.1kHz Sample Rate** | ✅ **YES** | Auto-resampled to 16kHz for processing, then back to original |
| **Multiple Sample Rates** | ✅ **YES** | Any sample rate supported (auto-resampling) |
| **WAV Format** | ✅ **YES** | Full support (input & output) |
| **FLAC Format** | ✅ **YES** | Supported via `soundfile` backend (input only) |
| **MP3 Format** | ⚠️ **CONDITIONAL** | Depends on torchaudio backend (input only) |
| **AAC Format** | ⚠️ **CONDITIONAL** | Depends on torchaudio backend (input only) |
| **Multiple Bitrates** | ✅ **YES** | Works with any bitrate (models process raw waveforms) |
| **Output Formats** | ❌ **WAV ONLY** | Currently hardcoded to WAV output |

---

## 🎵 Sample Rate Support

### How It Works

AudioSeal models are **trained at 16kHz**, but the library automatically handles other sample rates:

1. **Input**: Audio at any sample rate (e.g., 44.1kHz, 48kHz, etc.)
2. **Processing**: Automatically resampled to 16kHz internally using `julius.resample_frac()`
3. **Output**: Resampled back to the original sample rate

### Code Evidence

From `src/audioseal/models.py`:

```python
# Generator watermarking
if sample_rate != 16000:
    x = julius.resample_frac(x, old_sr=sample_rate, new_sr=16000)
# ... process at 16kHz ...
if sample_rate != 16000:
    watermark = julius.resample_frac(
        watermark, old_sr=16000, new_sr=sample_rate
    )

# Detector
if sample_rate != 16000:
    x = julius.resample_frac(x, old_sr=sample_rate, new_sr=16000)
```

### Supported Sample Rates

✅ **Any sample rate** - The resampling is automatic and transparent:
- 8kHz, 16kHz, 22.05kHz, 24kHz, 32kHz, 44.1kHz, 48kHz, 96kHz, etc.

**Note**: The server preserves the original sample rate in the output.

---

## 🎧 Audio Format Support

### Input Formats (via torchaudio)

The server uses `torchaudio.load()` which supports multiple formats depending on installed backends:

#### ✅ **Always Supported** (with `soundfile` in requirements.txt):
- **WAV** - Full support
- **FLAC** - Full support
- **OGG/VORBIS** - Supported

#### ⚠️ **Conditionally Supported** (requires additional backends):
- **MP3** - Requires `sox` or `ffmpeg` backend
  - Install: `pip install sox` or ensure `ffmpeg` is in PATH
- **AAC** - Requires `ffmpeg` backend
  - Install: `ffmpeg` system package or `pip install ffmpeg-python`
- **M4A** - Requires `ffmpeg` backend
- **OPUS** - Requires `ffmpeg` backend

### Current Server Implementation

```python
# server/server.py line 66
wav, sample_rate = torchaudio.load(tmp_path)
```

**Issue**: The server saves files with `.wav` suffix but `torchaudio.load()` can read other formats if the file extension doesn't match the actual format. However, the current implementation downloads to a temp file with `.wav` extension, which might cause issues with non-WAV files.

### Recommended Fix

The server should detect the format from the URL or Content-Type header, or use a format-agnostic approach:

```python
# Better approach - let torchaudio auto-detect
with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
    # No suffix - let torchaudio detect format
    tmp_path = tmp_file.name
```

---

## 💾 Output Format Support

### Current Status: **WAV ONLY** ❌

The server currently hardcodes WAV output:

```python
# server/server.py line 109
torchaudio.save(output_path, audio_tensor, sample_rate)
# Returns as 'audio/wav' mimetype
```

### Adding Multi-Format Output Support

To support multiple output formats, you would need to:

1. **Add format parameter** to endpoints:
```python
@app.route('/watermark', methods=['POST'])
def watermark_audio():
    data = request.get_json()
    output_format = data.get('format', 'wav')  # wav, flac, mp3, etc.
    # ...
```

2. **Use appropriate encoder**:
```python
if output_format == 'wav':
    torchaudio.save(output_path, audio_tensor, sample_rate)
elif output_format == 'flac':
    torchaudio.save(output_path, audio_tensor, sample_rate, format='flac')
elif output_format == 'mp3':
    # Requires additional encoding library like pydub or ffmpeg
    # ...
```

3. **Update mimetype**:
```python
mimetypes = {
    'wav': 'audio/wav',
    'flac': 'audio/flac',
    'mp3': 'audio/mpeg',
    'aac': 'audio/aac'
}
```

---

## 🎚️ Bitrate Support

### How Bitrates Work

AudioSeal works on **raw audio waveforms**, not compressed formats. Bitrate is only relevant when:

1. **Loading compressed files** (MP3, AAC, etc.):
   - Different bitrates decode to the same waveform format
   - Higher bitrates = better quality, but models process the decoded waveform
   - **All bitrates are supported** as long as torchaudio can decode them

2. **Saving compressed files** (if you add this feature):
   - You'd specify bitrate during encoding
   - Currently not supported (WAV is uncompressed)

### Bitrate Examples

✅ **Supported** (as input):
- MP3 @ 128kbps, 192kbps, 256kbps, 320kbps
- AAC @ 128kbps, 192kbps, 256kbps
- Any bitrate - models don't care, they work on decoded waveforms

---

## 🔧 Testing Format Support

### Test Different Formats

```python
# Test with different formats
formats_to_test = [
    "https://example.com/audio.wav",      # WAV
    "https://example.com/audio.flac",     # FLAC
    "https://example.com/audio.mp3",      # MP3 (if backend available)
    "https://example.com/audio.m4a",      # AAC/M4A (if backend available)
]

for url in formats_to_test:
    response = requests.post(
        "http://localhost:5001/watermark",
        json={"audio_url": url}
    )
    # Should work if format is supported
```

### Check Available Backends

```python
import torchaudio

# Check what backends are available
print(torchaudio.list_audio_backends())
# Should show: ['soundfile', 'sox', 'ffmpeg'] or similar
```

---

## 📝 Recommendations for Server Enhancement

### 1. **Fix Format Detection** (High Priority)

Current issue: Downloads all files with `.wav` extension, which may fail for non-WAV files.

**Fix**:
```python
def download_audio(url):
    """Download audio from URL and return tensor and sample rate."""
    # Detect format from URL or Content-Type
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
        # ... download ...
    
    # Let torchaudio auto-detect format
    wav, sample_rate = torchaudio.load(tmp_path, format=None)
    # ...
```

### 2. **Add Format Parameter** (Medium Priority)

Allow users to specify output format:
```json
{
  "audio_url": "https://example.com/audio.wav",
  "output_format": "flac"  // or "wav", "mp3", etc.
}
```

### 3. **Add Format Validation** (Low Priority)

Return clear error messages for unsupported formats:
```python
try:
    wav, sample_rate = torchaudio.load(tmp_path)
except Exception as e:
    return jsonify({
        'error': f'Unsupported audio format. Supported: WAV, FLAC, MP3 (if backend installed)',
        'details': str(e)
    }), 400
```

### 4. **Document Backend Requirements** (Documentation)

Update README to explain:
- WAV/FLAC work out of the box
- MP3/AAC require additional backends
- How to install backends

---

## 🎯 Current Server Capabilities

### ✅ What Works Now:
- **Input**: WAV, FLAC (and potentially MP3/AAC if backends installed)
- **Sample Rates**: Any (auto-resampled)
- **Output**: WAV only
- **Bitrates**: All (for compressed inputs)

### ❌ What Doesn't Work:
- **Output formats**: Only WAV
- **Format detection**: May fail for non-WAV files due to temp file naming
- **Error messages**: May be unclear for unsupported formats

---

## 🔗 Related Code Locations

- **Sample rate handling**: `src/audioseal/models.py` (lines 107-131, 228-229)
- **Audio loading**: `server/server.py` (line 66)
- **Audio saving**: `server/server.py` (line 109)
- **Requirements**: `requirements.txt` (includes `soundfile`)

---

## 📚 References

- [torchaudio.load() documentation](https://pytorch.org/audio/stable/backend.html)
- [AudioSeal README](README.md) - mentions 16kHz requirement
- [julius resampling](https://github.com/adefossez/julius) - used for resampling

