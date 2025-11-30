#!/usr/bin/env python3
"""
Test script for AudioSeal Flask API endpoints.
Run this after starting the Flask server with: python server/server.py
"""

import argparse
import base64
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# Default Configuration
DEFAULT_BASE_URL = "http://localhost:5001"
# DEFAULT_AUDIO_URL = "https://huggingface.co/datasets/flexthink/ljspeech/resolve/main/wavs/LJ001-0001.wav"
DEFAULT_AUDIO_URL = "file:///Users/waqarm/Downloads/KENDRICK.wav"
DEFAULT_TIMEOUT = 120

# Results configuration
RESULTS_BASE_DIR = Path("test_results")
CURRENT_RESULTS_DIR = RESULTS_BASE_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")

def setup_results_dir():
    if not CURRENT_RESULTS_DIR.exists():
        CURRENT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Results will be saved to: {CURRENT_RESULTS_DIR}")
    return CURRENT_RESULTS_DIR

def get_file_url(file_path: str | Path) -> str:
    """Convert a file path to a file:// URL if it's a local file."""
    path_str = str(file_path)
    if path_str.startswith("http://") or path_str.startswith("https://"):
        return path_str
    
    if path_str.startswith("file://"):
        return path_str
        
    abs_path = Path(file_path).resolve()
    return f"file://{abs_path}"

def print_header(title: str):
    print("\n" + "="*60)
    print(title)
    print("="*60)

def save_plot(base64_data: str, filename: str) -> Path:
    if not base64_data:
        return None
    try:
        plot_data = base64.b64decode(base64_data)
        output_file = CURRENT_RESULTS_DIR / filename
        with open(output_file, 'wb') as f:
            f.write(plot_data)
        print(f"  Plot saved to: {output_file}")
        return output_file
    except Exception as e:
        print(f"  Warning: Failed to save plot {filename}: {e}")
        return None

def test_health(base_url):
    """Test the health check endpoint."""
    print_header("Testing /health endpoint")
    
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✓ Health check passed")
        print(f"  Status: {data.get('status')}")
        print(f"  Device: {data.get('device')}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_watermark(base_url, audio_url):
    """Test the watermark endpoint."""
    print_header("Testing /watermark endpoint")
    
    try:
        # Test 1: Watermark without secret message
        print("\n1. Watermarking audio without secret message...")
        payload = {
            "audio_url": audio_url,
            "alpha": 1.0
        }
        response = requests.post(
            f"{base_url}/watermark",
            json=payload,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        
        # Save the watermarked audio
        output_file = CURRENT_RESULTS_DIR / "watermarked.wav"
        with open(output_file, 'wb') as f:
            f.write(response.content)
        print(f"✓ Watermarking successful")
        print(f"  Saved to: {output_file}")
        print(f"  File size: {output_file.stat().st_size} bytes")
        
        # Test 2: Watermark with secret message
        print("\n2. Watermarking audio with secret message...")
        secret_message = [1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0]
        payload = {
            "audio_url": audio_url,
            "message": secret_message,
            "alpha": 1.0
        }
        response = requests.post(
            f"{base_url}/watermark",
            json=payload,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        
        output_file_msg = CURRENT_RESULTS_DIR / "test_watermarked_with_message.wav"
        with open(output_file_msg, 'wb') as f:
            f.write(response.content)
        print(f"✓ Watermarking with message successful")
        print(f"  Secret message: {secret_message}")
        print(f"  Saved to: {output_file_msg}")
        print(f"  File size: {output_file_msg.stat().st_size} bytes")
        
        return True, str(output_file_msg.resolve())
        
    except Exception as e:
        print(f"✗ Watermarking failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"  Error details: {e.response.json()}")
            except:
                print(f"  Response: {e.response.text}")
        return False, None

def test_detect(base_url, audio_url, watermarked_file=None):
    """Test the detect endpoint."""
    print_header("Testing /detect endpoint")
    
    try:
        # Test 1: Detect on original (unwatermarked) audio
        print("\n1. Detecting watermark on original (unwatermarked) audio...")
        payload = {
            "audio_url": audio_url,
            "message_threshold": 0.5
        }
        response = requests.post(
            f"{base_url}/detect",
            json=payload,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        print(f"✓ Detection completed")
        print(f"  Is watermarked: {data.get('is_watermarked')}")
        print(f"  Detection probability: {data.get('detection_probability'):.6f}")
        print(f"  Decoded message: {data.get('decoded_message')}")
        
        # Test 2: Detect on watermarked audio
        if watermarked_file and os.path.exists(str(watermarked_file)):
            print("\n2. Detecting watermark on watermarked audio...")
            watermarked_url = get_file_url(watermarked_file)
            print(f"  Using watermarked file: {watermarked_file}")
            
            payload = {
                "audio_url": watermarked_url,
                "message_threshold": 0.5
            }
            response = requests.post(
                f"{base_url}/detect",
                json=payload,
                timeout=DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            print(f"✓ Detection on watermarked audio completed")
            print(f"  Is watermarked: {data.get('is_watermarked')}")
            print(f"  Detection probability: {data.get('detection_probability'):.6f}")
            print(f"  Decoded message: {data.get('decoded_message')}")
        else:
            print(f"\n2. Skipping watermarked detection (no watermarked file provided)")
        
        return True
        
    except Exception as e:
        print(f"✗ Detection failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"  Error details: {e.response.json()}")
            except:
                print(f"  Response: {e.response.text}")
        return False

def test_pink_noise(base_url, original_url, watermarked_file=None):
    """Test the pink noise attack endpoint."""
    print_header("Testing /test/pink_noise endpoint")
    
    try:
        # Use watermarked file if available, otherwise use original
        if watermarked_file and os.path.exists(str(watermarked_file)):
            audio_url = get_file_url(watermarked_file)
            print(f"\nTesting pink noise attack on watermarked audio...")
            print(f"  Using watermarked file: {watermarked_file}")
        else:
            audio_url = original_url
            print("\nTesting pink noise attack on original audio...")
            print("  Note: Using original audio (watermarked file not available)")
        
        payload = {
            "audio_url": audio_url,
            "noise_std": 0.1
        }
        response = requests.post(
            f"{base_url}/test/pink_noise",
            json=payload,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Pink noise test completed")
        print(f"  Detection probability: {data.get('detection_probability'):.6f}")
        print(f"  Is watermarked: {data.get('is_watermarked')}")
        print(f"  Noise std: {data.get('noise_std')}")
        print(f"  Decoded message: {data.get('decoded_message')}")
        
        save_plot(data.get('plot'), "pink_noise_plot.png")
        return True
        
    except Exception as e:
        print(f"✗ Pink noise test failed: {e}")
        return False

def test_filters(base_url, original_url, watermarked_file=None):
    """Test the filters endpoint."""
    print_header("Testing /test/filters endpoint")
    
    try:
        if watermarked_file and os.path.exists(str(watermarked_file)):
            audio_url = get_file_url(watermarked_file)
            print(f"\nTesting filters on watermarked audio...")
        else:
            audio_url = original_url
            print("\nTesting filters on original audio...")
        
        payload = {
            "audio_url": audio_url,
            "cutoff_freq": 5000,
            "sample_rate": 16000
        }
        response = requests.post(
            f"{base_url}/test/filters",
            json=payload,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        
        for filter_type in ['highpass', 'lowpass']:
            if filter_type in data:
                result = data[filter_type]
                print(f"\n✓ {filter_type.capitalize()} filter test completed")
                print(f"  Detection probability: {result.get('detection_probability'):.6f}")
                print(f"  Is watermarked: {result.get('is_watermarked')}")
                save_plot(result.get('plot'), f"{filter_type}_plot.png")
        
        return True
    except Exception as e:
        print(f"✗ Filters test failed: {e}")
        return False

def test_waveform_and_specgram(base_url, audio_url):
    """Test the waveform and spectrogram endpoint."""
    print_header("Testing /test/waveform_and_specgram endpoint")
    
    try:
        print("\nGenerating waveform and spectrogram plot...")
        payload = {
            "audio_url": audio_url,
            "title": "Test Audio"
        }
        response = requests.post(
            f"{base_url}/test/waveform_and_specgram",
            json=payload,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Waveform and spectrogram generation successful")
        print(f"  Sample rate: {data.get('sample_rate')} Hz")
        print(f"  Duration: {data.get('duration'):.2f} seconds")
        
        save_plot(data.get('plot'), "waveform_specgram.png")
        return True
    except Exception as e:
        print(f"✗ Waveform and spectrogram test failed: {e}")
        return False

def test_waveform_and_specgram_difference(base_url, original_url, watermarked_file=None):
    """Test the waveform and spectrogram difference endpoint."""
    print_header("Testing /test/waveform_and_specgram_difference endpoint")
    
    try:
        if watermarked_file and os.path.exists(str(watermarked_file)):
            print(f"\n1. Using existing watermarked file: {watermarked_file}")
            watermarked_url = get_file_url(watermarked_file)
        else:
            print("\n1. Creating watermarked audio for comparison...")
            # Fallback if no file exists (simplification: just use original to avoid complex logic here)
            watermarked_url = original_url
            print("   Warning: Using original audio as fallback for comparison")

        print("\n2. Comparing original and watermarked audio...")
        payload = {
            "audio_url_1": original_url,
            "audio_url_2": watermarked_url,
            "title_1": "Original Audio",
            "title_2": "Watermarked Audio"
        }
        response = requests.post(
            f"{base_url}/test/waveform_and_specgram_difference",
            json=payload,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Difference comparison successful")
        diff_stats = data.get('difference_stats', {})
        print(f"  Max absolute difference: {diff_stats.get('max_absolute_difference', 0):.6f}")
        
        save_plot(data.get('plot'), "waveform_specgram_difference.png")
        return True
    except Exception as e:
        print(f"✗ Difference test failed: {e}")
        return False

def test_error_handling(base_url, audio_url):
    """Test error handling for invalid requests."""
    print_header("Testing error handling")
    
    try:
        # Test missing audio_url
        print("\n1. Testing missing audio_url parameter...")
        response = requests.post(f"{base_url}/watermark", json={}, timeout=30)
        if response.status_code == 400:
            print("✓ Correctly returned 400 for missing audio_url")
        else:
            print(f"✗ Expected 400, got {response.status_code}")
        
        # Test invalid message length
        print("\n2. Testing invalid message length...")
        payload = {"audio_url": audio_url, "message": [1, 0, 1]}
        response = requests.post(f"{base_url}/watermark", json=payload, timeout=30)
        if response.status_code == 400:
            print("✓ Correctly returned 400 for invalid message length")
        else:
            print(f"✗ Expected 400, got {response.status_code}")
        
        return True
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="AudioSeal API Test Suite")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL of the Flask server")
    parser.add_argument("--audio-url", default=DEFAULT_AUDIO_URL, help="URL of the audio file to test")
    parser.add_argument("--no-interactive", action="store_true", help="Skip the 'Press Enter' prompt")
    args = parser.parse_args()

    print_header("AudioSeal Flask API Test Suite")
    print(f"Server URL: {args.base_url}")
    print(f"Test Audio: {args.audio_url}")
    
    setup_results_dir()
    
    if not args.no_interactive:
        input("\nPress Enter to start testing... (or Ctrl+C to cancel)")
    
    results = {}
    test_data = {}  # Store additional return values like watermarked_file
    
    def run_test(name, func, *args, **kwargs):
        """Helper to run a test, time it, and record results."""
        t0 = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - t0
        
        passed = False
        extra = None
        
        if isinstance(result, tuple):
            passed = result[0]
            extra = result[1]
        else:
            passed = result
            
        results[name] = {
            'passed': passed,
            'duration': duration
        }
        return passed, extra

    total_start_time = time.time()
    
    # Run tests
    passed, _ = run_test('health', test_health, args.base_url)
    
    if not passed:
        print("\n✗ Server is not responding. Aborting.")
        sys.exit(1)
        
    passed, watermarked_file = run_test('watermark', test_watermark, args.base_url, args.audio_url)
    
    # Run remaining tests
    run_test('detect', test_detect, args.base_url, args.audio_url, watermarked_file)
    run_test('pink_noise', test_pink_noise, args.base_url, args.audio_url, watermarked_file)
    run_test('filters', test_filters, args.base_url, args.audio_url, watermarked_file)
    run_test('waveform', test_waveform_and_specgram, args.base_url, args.audio_url)
    run_test('diff', test_waveform_and_specgram_difference, args.base_url, args.audio_url, watermarked_file)
    run_test('errors', test_error_handling, args.base_url, args.audio_url)
    
    # Summary
    total_duration = time.time() - total_start_time
    print_header("Test Summary")
    
    passed_count = sum(1 for r in results.values() if r['passed'])
    total_count = len(results)
    
    print(f"{'Test Name':<20} {'Status':<10} {'Duration':<10}")
    print("-" * 42)
    
    for name, data in results.items():
        status = "✓ PASSED" if data['passed'] else "✗ FAILED"
        print(f"{name:<20} {status:<10} {data['duration']:.2f}s")
        
    print("-" * 42)
    print(f"Total: {passed_count}/{total_count} passed in {total_duration:.2f}s")
    
    # Save summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_duration": total_duration,
        "results": results,
        "config": vars(args)
    }
    summary_file = CURRENT_RESULTS_DIR / "test_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Summary saved to: {summary_file}")

    if passed_count != total_count:
        sys.exit(1)

if __name__ == "__main__":
    main()
