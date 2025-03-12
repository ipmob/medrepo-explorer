#!/usr/bin/env python3
# ml/stt.py

import os
import librosa
import numpy as np
import torch
from typing import List, Tuple, Optional
from pydub import AudioSegment
import whisper
from tqdm import tqdm
import soundfile as sf
import tempfile

def load_audio(file_path: str) -> Tuple[np.ndarray, int]:
    """
    Load an audio file using librosa.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Tuple containing the audio data and sample rate
    """
    print(f"Loading audio file: {file_path}")
    audio, sample_rate = librosa.load(file_path, sr=None)
    return audio, sample_rate

def split_into_chunks(audio: np.ndarray, sample_rate: int, num_chunks: int = 6, 
                      overlap_seconds: int = 10) -> List[np.ndarray]:
    """
    Split audio into specified number of chunks with overlap.
    
    Args:
        audio: Audio data as numpy array
        sample_rate: Sample rate of the audio
        num_chunks: Number of chunks to split into
        overlap_seconds: Overlap duration in seconds
        
    Returns:
        List of audio chunks
    """
    # Calculate total duration in seconds
    duration = len(audio) / sample_rate
    
    # Calculate the size of each chunk (excluding overlap)
    chunk_size = duration / num_chunks
    
    # Calculate overlap in samples
    overlap_samples = overlap_seconds * sample_rate
    
    chunks = []
    for i in range(num_chunks):
        # Calculate start and end positions for this chunk
        start_sec = i * chunk_size
        end_sec = (i + 1) * chunk_size + (0 if i == num_chunks-1 else overlap_seconds)
        
        # Convert to samples
        start_sample = int(start_sec * sample_rate)
        end_sample = min(int(end_sec * sample_rate), len(audio))
        
        # Extract chunk
        chunk = audio[start_sample:end_sample]
        chunks.append(chunk)
        
        print(f"Chunk {i+1}/{num_chunks}: {start_sec:.2f}s to {end_sec:.2f}s (duration: {len(chunk)/sample_rate:.2f}s)")
    
    return chunks

def save_chunk_to_temp_file(chunk: np.ndarray, sample_rate: int) -> str:
    """
    Save an audio chunk to a temporary WAV file.
    
    Args:
        chunk: Audio chunk data
        sample_rate: Sample rate of the audio
        
    Returns:
        Path to the temporary file
    """
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file_path = temp_file.name
    temp_file.close()
    
    # Save the chunk to the temporary file
    sf.write(temp_file_path, chunk, sample_rate)
    
    return temp_file_path

def transcribe_chunks(chunks: List[np.ndarray], sample_rate: int, model_name: str = "base") -> List[str]:
    """
    Transcribe each audio chunk using Whisper.
    
    Args:
        chunks: List of audio chunks
        sample_rate: Sample rate of the audio
        model_name: Whisper model to use
        
    Returns:
        List of transcriptions for each chunk
    """
    print(f"Loading Whisper model: {model_name}")
    # Use OpenAI's Whisper library
    model = whisper.load_model(model_name)
    
    transcriptions = []
    temp_files = []
    
    try:
        print("Transcribing chunks...")
        for i, chunk in enumerate(tqdm(chunks)):
            # Save chunk to temporary file
            temp_file_path = save_chunk_to_temp_file(chunk, sample_rate)
            temp_files.append(temp_file_path)
            
            # Transcribe the chunk
            result = model.transcribe(temp_file_path)
            transcription = result["text"]
            
            print(f"Chunk {i+1} transcription: {transcription[:50]}...")
            transcriptions.append(transcription)
    
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except Exception as e:
                print(f"Failed to remove temporary file {temp_file}: {e}")
    
    return transcriptions

def combine_transcriptions(transcriptions: List[str]) -> str:
    """
    Combine chunk transcriptions into a single transcription.
    This is a simple concatenation, but could be improved with
    more sophisticated merging of overlapping sections.
    
    Args:
        transcriptions: List of transcriptions from each chunk
        
    Returns:
        Combined transcription
    """
    return " ".join(transcriptions)

def main():
    """Main function to process the audio file."""
    # Path to the audio file
    audio_file = os.path.join(os.path.dirname(__file__), "call-record.wav")
    
    # Load the audio file
    audio, sample_rate = load_audio(audio_file)
    
    # Split into chunks with overlap
    chunks = split_into_chunks(audio, sample_rate, num_chunks=6, overlap_seconds=10)
    
    # Transcribe each chunk
    chunk_transcriptions = transcribe_chunks(chunks, sample_rate, model_name="base")
    
    # Combine transcriptions
    full_transcription = combine_transcriptions(chunk_transcriptions)
    
    # Print the full transcription
    print("\nFull Transcription:")
    print(full_transcription)
    
    # Save the transcription to a text file
    output_file = os.path.join(os.path.dirname(__file__), "call-record-transcription.txt")
    with open(output_file, "w") as f:
        f.write(full_transcription)
    
    print(f"\nTranscription saved to: {output_file}")

if __name__ == "__main__":
    main()
