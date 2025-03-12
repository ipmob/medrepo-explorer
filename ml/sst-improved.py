#!/usr/bin/env python3
# ml/stt-improved.py

# work in progress, needs to fix chunking to tensor and merging

import os
import sys
import glob
import librosa
import numpy as np
import torch
from typing import List, Tuple, Dict, Optional, Any
from pydub import AudioSegment
import whisper
from tqdm import tqdm
import soundfile as sf
import tempfile
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import multiprocessing


def load_audio(file_path: str) -> Tuple[np.ndarray, int]:
    """
    Load an audio file using librosa.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Tuple containing the audio data and sample rate
    """
    print(f"Loading audio file: {file_path}")
    try:
        audio, sample_rate = librosa.load(file_path, sr=16000)  # Fixed sample rate for better Whisper compatibility
        print(f"Audio duration: {len(audio)/sample_rate:.2f} seconds")
        return audio, sample_rate
    except Exception as e:
        print(f"Error loading audio file: {e}")
        sys.exit(1)


def chunk_audio(audio: np.ndarray, sample_rate: int, 
                chunk_size_seconds: int = 60, 
                overlap_seconds: int = 10) -> List[Dict[str, Any]]:
    """
    Split audio into fixed-size chunks with specified overlap.
    
    Args:
        audio: Audio data as numpy array
        sample_rate: Sample rate of the audio
        chunk_size_seconds: Size of each chunk in seconds
        overlap_seconds: Overlap between chunks in seconds
        
    Returns:
        List of dictionaries with chunk data and metadata
    """
    # Calculate total duration in seconds
    total_duration = len(audio) / sample_rate
    
    # Calculate size and overlap in samples
    chunk_size_samples = chunk_size_seconds * sample_rate
    overlap_samples = overlap_seconds * sample_rate
    
    # Calculate step size (chunk size minus overlap)
    step_samples = chunk_size_samples - overlap_samples
    
    # Calculate number of chunks
    num_chunks = max(1, int(np.ceil((len(audio) - overlap_samples) / step_samples)))
    
    print(f"Splitting audio ({total_duration:.2f}s) into {num_chunks} chunks "
          f"of {chunk_size_seconds}s with {overlap_seconds}s overlap")
    
    chunks = []
    for i in range(num_chunks):
        # Calculate start and end positions for this chunk
        start_sample = int(i * step_samples)
        end_sample = min(int(start_sample + chunk_size_samples), len(audio))
        
        # Ensure minimum chunk size (at least 1 second)
        if (end_sample - start_sample) < sample_rate:
            if i > 0:  # Skip very short final chunks
                continue
        
        # Extract chunk
        chunk_audio = audio[start_sample:end_sample]
        
        # Calculate time range
        start_time = start_sample / sample_rate
        end_time = end_sample / sample_rate
        
        chunk_info = {
            "audio": chunk_audio,
            "start_time": start_time,
            "end_time": end_time,
            "index": i,
            "duration": (end_sample - start_sample) / sample_rate
        }
        
        chunks.append(chunk_info)
        
        print(f"Chunk {i+1}/{len(chunks)}: {start_time:.2f}s to {end_time:.2f}s "
              f"(duration: {chunk_info['duration']:.2f}s)")
    
    return chunks


def save_chunk_to_temp_file(chunk_audio: np.ndarray, sample_rate: int) -> str:
    """
    Save an audio chunk to a temporary WAV file.
    
    Args:
        chunk_audio: Audio chunk data
        sample_rate: Sample rate of the audio
        
    Returns:
        Path to the temporary file
    """
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file_path = temp_file.name
    temp_file.close()
    
    # Save the chunk to the temporary file
    sf.write(temp_file_path, chunk_audio, sample_rate)
    
    return temp_file_path


def transcribe_chunk(chunk_info: Dict[str, Any], sample_rate: int, model: Any) -> Dict[str, Any]:
    """
    Transcribe a single audio chunk using Whisper.
    
    Args:
        chunk_info: Dictionary with chunk audio and metadata
        sample_rate: Sample rate of the audio
        model: Loaded Whisper model
        
    Returns:
        Dictionary with chunk info and transcription
    """
    # Save chunk to temporary file
    temp_file_path = save_chunk_to_temp_file(chunk_info["audio"], sample_rate)
    
    try:
        # Transcribe the chunk with safe settings
        result = model.transcribe(
            temp_file_path,
            fp16=False,  # Disable FP16 to avoid GPU-specific errors
            word_timestamps=False,  # Disable word timestamps for better stability
            verbose=False
        )
        
        # Add transcription to chunk info
        chunk_info["transcription"] = result["text"]
        chunk_info["segments"] = result.get("segments", [])
        
        # Print a preview of the transcription
        preview = chunk_info["transcription"][:50] + "..." if len(chunk_info["transcription"]) > 50 else chunk_info["transcription"]
        print(f"Chunk {chunk_info['index']+1} transcription: {preview}")
        
    except Exception as e:
        # If transcription fails, use a fallback approach
        print(f"Warning: Error transcribing chunk {chunk_info['index']+1}: {e}")
        print(f"Using fallback empty transcription for this chunk")
        chunk_info["transcription"] = ""
        chunk_info["segments"] = []
    finally:
        # Clean up temporary file
        try:
            os.remove(temp_file_path)
        except Exception as e:
            print(f"Failed to remove temporary file {temp_file_path}: {e}")
    
    return chunk_info


def get_num_default_workers() -> int:
    """
    Get default number of workers based on CPU cores.
    
    Returns:
        Number of workers (at least 1, at most 4)
    """
    try:
        # Use half of available CPU cores, minimum 1, maximum 4
        return max(1, min(4, multiprocessing.cpu_count() // 2))
    except:
        # Fallback to 2 if can't determine CPU count
        return 2


def transcribe_chunks_parallel(chunks: List[Dict[str, Any]], sample_rate: int, 
                              model_name: str = "base", max_workers: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Transcribe audio chunks in parallel using Whisper.
    
    Args:
        chunks: List of chunk dictionaries
        sample_rate: Sample rate of the audio
        model_name: Whisper model to use
        max_workers: Maximum number of parallel transcription workers (None for auto)
        
    Returns:
        List of chunks with transcriptions
    """
    if max_workers is None:
        max_workers = get_num_default_workers()
        
    print(f"Loading Whisper model: {model_name}")
    try:
        model = whisper.load_model(model_name)
    except Exception as e:
        print(f"Error loading Whisper model '{model_name}': {e}")
        print("Available models: tiny, base, small, medium, large")
        sys.exit(1)
    
    print(f"Transcribing {len(chunks)} chunks with {max_workers} parallel workers...")
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all transcription tasks
        futures = {
            executor.submit(transcribe_chunk, chunk, sample_rate, model): i 
            for i, chunk in enumerate(chunks)
        }
        
        # Process results as they complete
        transcribed_chunks = [None] * len(chunks)
        for future in tqdm(as_completed(futures), total=len(futures)):
            chunk_index = futures[future]
            try:
                result = future.result()
                transcribed_chunks[chunk_index] = result
            except Exception as e:
                print(f"Error processing future for chunk {chunk_index}: {e}")
                # Create a minimal valid chunk result for failed chunks
                transcribed_chunks[chunk_index] = {
                    "index": chunk_index,
                    "transcription": "",
                    "segments": [],
                    "start_time": chunks[chunk_index]["start_time"],
                    "end_time": chunks[chunk_index]["end_time"]
                }
    
    return transcribed_chunks


def find_overlap_segments(chunk1: Dict[str, Any], chunk2: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """
    Find the overlapping time range between two chunks.
    
    Args:
        chunk1: First chunk
        chunk2: Second chunk
        
    Returns:
        Tuple of (overlap_start, overlap_end) times or None if no overlap
    """
    # The end of chunk1 and start of chunk2 should overlap
    overlap_start = chunk2["start_time"]
    overlap_end = chunk1["end_time"]
    
    # If there's no actual overlap, return None
    if overlap_end <= overlap_start:
        return None
    
    return (overlap_start, overlap_end)


def smart_merge_transcriptions(transcribed_chunks: List[Dict[str, Any]]) -> str:
    """
    Merge chunk transcriptions with smart handling of overlaps.
    
    Args:
        transcribed_chunks: List of chunks with transcriptions
        
    Returns:
        Merged transcription
    """
    if not transcribed_chunks:
        return ""
    
    # Remove empty chunks
    non_empty_chunks = [chunk for chunk in transcribed_chunks if chunk.get("transcription", "").strip()]
    
    if not non_empty_chunks:
        return ""
    
    # Sort chunks by start time to ensure correct order
    sorted_chunks = sorted(non_empty_chunks, key=lambda x: x["start_time"])
    
    # Initialize with the first chunk's transcription
    merged_text = sorted_chunks[0]["transcription"]
    
    for i in range(1, len(sorted_chunks)):
        current_chunk = sorted_chunks[i]
        prev_chunk = sorted_chunks[i-1]
        
        # Skip empty chunks
        if not current_chunk.get("transcription", "").strip():
            continue
        
        # Simple approach: just append with a space
        # This is more reliable than trying to detect overlap points
        merged_text += " " + current_chunk["transcription"]
    
    # Clean up any double spaces from the merging
    merged_text = re.sub(r'\s+', ' ', merged_text).strip()
    
    return merged_text


def process_audio_file(file_path: str, output_path: Optional[str] = None, 
                       chunk_size_seconds: int = 60, overlap_seconds: int = 10,
                       model_name: str = "base", max_workers: Optional[int] = None) -> str:
    """
    Process an audio file: chunk it, transcribe chunks, and merge transcriptions.
    
    Args:
        file_path: Path to the audio file
        output_path: Path to save the transcription (if None, derives from input)
        chunk_size_seconds: Size of each chunk in seconds
        overlap_seconds: Overlap between chunks in seconds
        model_name: Whisper model to use
        max_workers: Maximum number of parallel transcription workers
        
    Returns:
        Path to the saved transcription file
    """
    # Make sure the file exists
    if not os.path.isfile(file_path):
        print(f"Error: Audio file not found at {file_path}")
        sys.exit(1)
        
    # Set default output path if not provided
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        # Place output file in the project root directory
        output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                   f"{base_name}-transcription.txt")
    
    # Load the audio file
    audio, sample_rate = load_audio(file_path)
    
    # Split into chunks with overlap
    chunks = chunk_audio(audio, sample_rate, chunk_size_seconds, overlap_seconds)
    
    # Transcribe each chunk
    transcribed_chunks = transcribe_chunks_parallel(chunks, sample_rate, model_name, max_workers)
    
    # Merge transcriptions with smart handling of overlaps
    full_transcription = smart_merge_transcriptions(transcribed_chunks)
    
    # Save the transcription to a text file
    with open(output_path, "w") as f:
        f.write(full_transcription)
    
    print(f"\nTranscription saved to: {output_path}")
    return output_path


def find_audio_files(directory: str) -> List[str]:
    """
    Find all audio files in a directory.
    
    Args:
        directory: Directory to search in
        
    Returns:
        List of paths to audio files
    """
    audio_extensions = ['.wav', '.mp3', '.flac', '.ogg', '.m4a']
    audio_files = []
    
    for ext in audio_extensions:
        audio_files.extend(glob.glob(os.path.join(directory, f"*{ext}")))
    
    return audio_files


def main():
    """Parse command line arguments and process the audio file."""
    parser = argparse.ArgumentParser(description="Transcribe audio files using Whisper with chunking")
    parser.add_argument("audio_file", nargs='?', default=None,
                       help="Path to the audio file to transcribe (optional if --auto is used)")
    parser.add_argument("--auto", action="store_true", 
                       help="Automatically find and process audio files in the root directory")
    parser.add_argument("--output", "-o", help="Path to save the transcription")
    parser.add_argument("--chunk-size", type=int, default=30, 
                        help="Size of each chunk in seconds (default: 30)")
    parser.add_argument("--overlap", type=int, default=2, 
                        help="Overlap between chunks in seconds (default: 2)")
    parser.add_argument("--model", default="base", 
                        help="Whisper model to use (tiny, base, small, medium, large)")
    parser.add_argument("--workers", type=int, default=None, 
                        help="Maximum number of parallel workers (default: auto)")
    
    args = parser.parse_args()
    
    # Get the root directory of the project
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # If auto mode is enabled, find audio files in the root directory
    if args.auto:
        audio_files = find_audio_files(root_dir)
        if not audio_files:
            print(f"No audio files found in {root_dir}")
            sys.exit(1)
        
        print(f"Found {len(audio_files)} audio file(s): {[os.path.basename(f) for f in audio_files]}")
        
        # Process each audio file
        for audio_file in audio_files:
            print(f"\nProcessing audio file: {os.path.basename(audio_file)}")
            process_audio_file(
                audio_file,
                args.output,
                args.chunk_size,
                args.overlap,
                args.model,
                args.workers
            )
    else:
        # If no audio file specified, look for call-record.wav in both ml directory and root directory
        if args.audio_file is None:
            default_files = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "call-record.wav"),
                os.path.join(root_dir, "call-record.wav")
            ]
            
            for file_path in default_files:
                if os.path.isfile(file_path):
                    args.audio_file = file_path
                    print(f"Using default audio file: {file_path}")
                    break
            
            if args.audio_file is None:
                print("Error: No audio file specified and could not find call-record.wav")
                print(f"Please provide an audio file path or use --auto to search for audio files")
                sys.exit(1)
                
        # Process the single audio file
        process_audio_file(
            args.audio_file,
            args.output,
            args.chunk_size,
            args.overlap,
            args.model,
            args.workers
        )


if __name__ == "__main__":
    main() 