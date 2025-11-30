#server.py
# POST /watermark — Watermark audio with a secret message
# Input: audio_url, optional message (16-bit array), optional alpha (watermark strength)
# Output: Watermarked audio file (WAV)
# POST /detect — Detect watermark in audio
# Input: audio_url, optional message_threshold (default 0.5)
# Output: Detection probability, decoded message, and whether it's watermarked
# POST /test/pink_noise — Test against pink noise attack
# Input: audio_url, optional noise_std (default 0.1)
# Output: Detection results and a base64-encoded plot
# POST /test/filters — Test against highpass and lowpass filters
# Input: audio_url, optional cutoff_freq (default 5000), optional sample_rate
# Output: Results for both filters with base64-encoded plots


import os
import io
import base64
import urllib.request
import tempfile
from flask import Flask, request, jsonify, send_file
import torch
import torchaudio
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from audioseal import AudioSeal
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'examples'))
from attacks import AudioEffects as af

app = Flask(__name__)

# Set device for M1 Mac (MPS) or CPU
if torch.backends.mps.is_available():
    device = torch.device("mps")
    print(f"Using MPS device (Apple Silicon GPU)")
elif torch.cuda.is_available():
    device = torch.device("cuda")
    print(f"Using CUDA device")
else:
    device = torch.device("cpu")
    print(f"Using CPU device")

# Load models once at startup
print("Loading generator model...")
generator = AudioSeal.load_generator("audioseal_wm_16bits")
print("Loading detector model...")
detector = AudioSeal.load_detector("audioseal_detector_16bits", device=device)
detector = detector.to(device)
print("Models loaded successfully!")


def download_audio(url):
    """Download audio from URL and return tensor and sample rate."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
        tmp_path = tmp_file.name
        try:
            resp = urllib.request.urlopen(url)
            tmp_file.write(resp.read())
        except Exception as e:
            os.unlink(tmp_path)
            raise Exception(f"Failed to download audio from URL: {str(e)}")
    
    try:
        wav, sample_rate = torchaudio.load(tmp_path)
        # Convert to mono if stereo
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)
        os.unlink(tmp_path)
        return wav, sample_rate
    except Exception as e:
        os.unlink(tmp_path)
        raise Exception(f"Failed to load audio file: {str(e)}")


def plot_waveform_and_specgram(waveform, sample_rate, title):
    """Create plot and return as base64 encoded image."""
    waveform = waveform.squeeze().detach().cpu().numpy()
    
    num_frames = waveform.shape[-1]
    time_axis = torch.arange(0, num_frames) / sample_rate
    
    figure, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    
    ax1.plot(time_axis, waveform, linewidth=1)
    ax1.grid(True)
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Amplitude')
    ax2.specgram(waveform, Fs=sample_rate)
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Frequency (Hz)')
    
    figure.suptitle(f"{title} - Waveform and specgram")
    plt.tight_layout()
    
    # Convert plot to base64
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
    img_buffer.seek(0)
    plt.close()
    
    img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
    return img_base64


def save_audio_tensor(audio_tensor, sample_rate, output_path):
    """Save audio tensor to file."""
    torchaudio.save(output_path, audio_tensor, sample_rate)


@app.route('/watermark', methods=['POST'])
def watermark_audio():
    """
    Watermark audio with secret message.
    
    Expected JSON:
    {
        "audio_url": "https://example.com/audio.wav",
        "message": [0, 1, 0, 1, ...] (optional, 16 bits),
        "alpha": 1.0 (optional, watermark strength)
    }
    """
    try:
        data = request.get_json()
        if not data or 'audio_url' not in data:
            return jsonify({'error': 'Missing audio_url parameter'}), 400
        
        audio_url = data['audio_url']
        message = data.get('message')
        alpha = data.get('alpha', 1.0)
        
        # Download and load audio
        audio, sr = download_audio(audio_url)
        audios = audio.unsqueeze(0)  # Add batch dimension
        
        # Prepare message if provided
        if message:
            if len(message) != 16:
                return jsonify({'error': 'Message must be 16 bits'}), 400
            secret_message = torch.tensor([message], dtype=torch.int32)
            watermarked_audio = generator(audios, sample_rate=sr, message=secret_message, alpha=alpha)
        else:
            watermarked_audio = generator(audios, sample_rate=sr, alpha=alpha)
        
        # Save watermarked audio to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            output_path = tmp_file.name
            save_audio_tensor(watermarked_audio.squeeze(0), sr, output_path)
        
        return send_file(
            output_path,
            mimetype='audio/wav',
            as_attachment=True,
            download_name='watermarked_audio.wav'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/detect', methods=['POST'])
def detect_watermark():
    """
    Detect watermark in audio.
    
    Expected JSON:
    {
        "audio_url": "https://example.com/audio.wav",
        "message_threshold": 0.5 (optional)
    }
    """
    try:
        data = request.get_json()
        if not data or 'audio_url' not in data:
            return jsonify({'error': 'Missing audio_url parameter'}), 400
        
        audio_url = data['audio_url']
        message_threshold = data.get('message_threshold', 0.5)
        
        # Download and load audio
        audio, sr = download_audio(audio_url)
        audios = audio.unsqueeze(0)  # Add batch dimension
        
        # Detect watermark
        result, message = detector.detect_watermark(
            audios.to(device),
            sample_rate=sr,
            message_threshold=message_threshold
        )
        
        # Convert message tensor to list
        message_list = message.squeeze().detach().cpu().tolist()
        if isinstance(message_list, float):
            message_list = [message_list]
        
        return jsonify({
            'is_watermarked': bool(result > message_threshold),
            'detection_probability': float(result),
            'decoded_message': message_list
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test/waveform_and_specgram', methods=['POST'])
def test_waveform_and_specgram():
    """
    Generate waveform and spectrogram plot for an audio file.
    
    Expected JSON:
    {
        "audio_url": "https://example.com/audio.wav",
        "title": "Custom title" (optional)
    }
    """
    try:
        data = request.get_json()
        if not data or 'audio_url' not in data:
            return jsonify({'error': 'Missing audio_url parameter'}), 400
        
        audio_url = data['audio_url']
        title = data.get('title', 'Audio')
        
        # Download and load audio
        audio, sr = download_audio(audio_url)
        
        # Generate plot
        plot_base64 = plot_waveform_and_specgram(
            audio,
            sample_rate=sr,
            title=title
        )
        
        return jsonify({
            'plot': plot_base64,
            'sample_rate': int(sr),
            'duration': float(audio.shape[-1] / sr),
            'title': title
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/test/waveform_and_specgram_difference', methods=['POST'])
def test_waveform_and_specgram_difference():
    """
    Generate waveform and spectrogram difference plot comparing two audio files.
    
    Expected JSON:
    {
        "audio_url_1": "https://example.com/audio1.wav",
        "audio_url_2": "https://example.com/audio2.wav",
        "title_1": "Original" (optional),
        "title_2": "Watermarked" (optional)
    }
    """
    try:
        data = request.get_json()
        if not data or 'audio_url_1' not in data or 'audio_url_2' not in data:
            return jsonify({'error': 'Missing audio_url_1 or audio_url_2 parameter'}), 400
        
        audio_url_1 = data['audio_url_1']
        audio_url_2 = data['audio_url_2']
        title_1 = data.get('title_1', 'Audio 1')
        title_2 = data.get('title_2', 'Audio 2')
        
        # Download and load both audio files
        audio1, sr1 = download_audio(audio_url_1)
        audio2, sr2 = download_audio(audio_url_2)
        
        # Ensure same sample rate (resample if needed)
        if sr1 != sr2:
            if sr1 > sr2:
                audio2 = torchaudio.functional.resample(audio2, sr2, sr1)
                sr = sr1
            else:
                audio1 = torchaudio.functional.resample(audio1, sr1, sr2)
                sr = sr2
        else:
            sr = sr1
        
        # Ensure same length (pad or trim to shorter length)
        min_len = min(audio1.shape[-1], audio2.shape[-1])
        audio1 = audio1[..., :min_len]
        audio2 = audio2[..., :min_len]
        
        # Calculate difference
        audio_diff = audio1 - audio2
        
        # Convert to numpy for plotting
        audio1_np = audio1.squeeze().detach().cpu().numpy()
        audio2_np = audio2.squeeze().detach().cpu().numpy()
        audio_diff_np = audio_diff.squeeze().detach().cpu().numpy()
        
        num_frames = audio1_np.shape[-1]
        time_axis = torch.arange(0, num_frames) / sr
        
        # Create comparison plot with 3 rows: audio1, audio2, difference
        figure, axes = plt.subplots(3, 2, figsize=(14, 10))
        
        # Row 1: Audio 1
        axes[0, 0].plot(time_axis, audio1_np, linewidth=1)
        axes[0, 0].grid(True)
        axes[0, 0].set_xlabel('Time (s)')
        axes[0, 0].set_ylabel('Amplitude')
        axes[0, 0].set_title(f'{title_1} - Waveform')
        axes[0, 1].specgram(audio1_np, Fs=sr)
        axes[0, 1].set_xlabel('Time (s)')
        axes[0, 1].set_ylabel('Frequency (Hz)')
        axes[0, 1].set_title(f'{title_1} - Spectrogram')
        
        # Row 2: Audio 2
        axes[1, 0].plot(time_axis, audio2_np, linewidth=1)
        axes[1, 0].grid(True)
        axes[1, 0].set_xlabel('Time (s)')
        axes[1, 0].set_ylabel('Amplitude')
        axes[1, 0].set_title(f'{title_2} - Waveform')
        axes[1, 1].specgram(audio2_np, Fs=sr)
        axes[1, 1].set_xlabel('Time (s)')
        axes[1, 1].set_ylabel('Frequency (Hz)')
        axes[1, 1].set_title(f'{title_2} - Spectrogram')
        
        # Row 3: Difference
        axes[2, 0].plot(time_axis, audio_diff_np, linewidth=1, color='red')
        axes[2, 0].grid(True)
        axes[2, 0].set_xlabel('Time (s)')
        axes[2, 0].set_ylabel('Amplitude')
        axes[2, 0].set_title('Difference - Waveform')
        axes[2, 1].specgram(audio_diff_np, Fs=sr)
        axes[2, 1].set_xlabel('Time (s)')
        axes[2, 1].set_ylabel('Frequency (Hz)')
        axes[2, 1].set_title('Difference - Spectrogram')
        
        figure.suptitle(f'Comparison: {title_1} vs {title_2}', fontsize=14)
        plt.tight_layout()
        
        # Convert plot to base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()
        
        img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
        
        # Calculate statistics
        max_diff = float(torch.max(torch.abs(audio_diff)).item())
        mean_diff = float(torch.mean(torch.abs(audio_diff)).item())
        rms_diff = float(torch.sqrt(torch.mean(audio_diff ** 2)).item())
        
        return jsonify({
            'plot': img_base64,
            'sample_rate': int(sr),
            'duration': float(min_len / sr),
            'difference_stats': {
                'max_absolute_difference': max_diff,
                'mean_absolute_difference': mean_diff,
                'rms_difference': rms_diff
            },
            'audio1_title': title_1,
            'audio2_title': title_2
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test/pink_noise', methods=['POST'])
def test_pink_noise():
    """
    Test watermark detection against pink noise attack.
    
    Expected JSON:
    {
        "audio_url": "https://example.com/audio.wav",
        "noise_std": 0.1 (optional)
    }
    """
    try:
        data = request.get_json()
        if not data or 'audio_url' not in data:
            return jsonify({'error': 'Missing audio_url parameter'}), 400
        
        audio_url = data['audio_url']
        noise_std = data.get('noise_std', 0.1)
        
        # Download and load audio
        audio, sr = download_audio(audio_url)
        audios = audio.unsqueeze(0)  # Add batch dimension
        
        # Apply pink noise attack
        pink_noised_audio = af.pink_noise(audios, noise_std=noise_std)
        
        # Detect watermark
        result, message = detector.detect_watermark(
            pink_noised_audio.to(device),
            sample_rate=sr
        )
        
        # Generate plot
        plot_base64 = plot_waveform_and_specgram(
            pink_noised_audio.squeeze(),
            sample_rate=sr,
            title="Audio with pink noise"
        )
        
        # Convert message tensor to list
        message_list = message.squeeze().detach().cpu().tolist()
        if isinstance(message_list, float):
            message_list = [message_list]
        
        return jsonify({
            'detection_probability': float(result),
            'is_watermarked': bool(result > 0.5),
            'decoded_message': message_list,
            'plot': plot_base64,
            'noise_std': noise_std
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/test/filters', methods=['POST'])
def test_filters():
    """
    Test watermark detection against highpass and lowpass filters.
    
    Expected JSON:
    {
        "audio_url": "https://example.com/audio.wav",
        "cutoff_freq": 5000 (optional),
        "sample_rate": 16000 (optional, will be detected from audio if not provided)
    }
    """
    try:
        data = request.get_json()
        if not data or 'audio_url' not in data:
            return jsonify({'error': 'Missing audio_url parameter'}), 400
        
        audio_url = data['audio_url']
        cutoff_freq = data.get('cutoff_freq', 5000)
        
        # Download and load audio
        audio, sr = download_audio(audio_url)
        audios = audio.unsqueeze(0)  # Add batch dimension
        
        # Use provided sample_rate or detected one
        sample_rate = data.get('sample_rate', sr)
        
        results = {}
        
        # Test highpass filter
        highpass_filtered = af.highpass_filter(
            audios,
            cutoff_freq=cutoff_freq,
            sample_rate=sample_rate
        )
        result_highpass, message_highpass = detector.detect_watermark(
            highpass_filtered.to(device),
            sample_rate=sample_rate
        )
        plot_highpass = plot_waveform_and_specgram(
            highpass_filtered.squeeze(),
            sample_rate=sample_rate,
            title="Audio with highpass filter"
        )
        
        message_highpass_list = message_highpass.squeeze().detach().cpu().tolist()
        if isinstance(message_highpass_list, float):
            message_highpass_list = [message_highpass_list]
        
        results['highpass'] = {
            'detection_probability': float(result_highpass),
            'is_watermarked': bool(result_highpass > 0.5),
            'decoded_message': message_highpass_list,
            'plot': plot_highpass,
            'cutoff_freq': cutoff_freq
        }
        
        # Test lowpass filter
        lowpass_filtered = af.lowpass_filter(
            audios,
            cutoff_freq=cutoff_freq,
            sample_rate=sample_rate
        )
        result_lowpass, message_lowpass = detector.detect_watermark(
            lowpass_filtered.to(device),
            sample_rate=sample_rate
        )
        plot_lowpass = plot_waveform_and_specgram(
            lowpass_filtered.squeeze(),
            sample_rate=sample_rate,
            title="Audio with lowpass filter"
        )
        
        message_lowpass_list = message_lowpass.squeeze().detach().cpu().tolist()
        if isinstance(message_lowpass_list, float):
            message_lowpass_list = [message_lowpass_list]
        
        results['lowpass'] = {
            'detection_probability': float(result_lowpass),
            'is_watermarked': bool(result_lowpass > 0.5),
            'decoded_message': message_lowpass_list,
            'plot': plot_lowpass,
            'cutoff_freq': cutoff_freq
        }
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'device': str(device)})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
