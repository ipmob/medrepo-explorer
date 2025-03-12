# Speech-to-Text with Audio Chunking

## Overview

This project provides a solution for transcribing long audio recordings by using a chunking approach with overlaps. The implementation splits a large audio file into multiple segments, transcribes each segment independently, and then combines the results into a complete transcription.

## Problem

Speech-to-Text (STT) models like Whisper often have limitations when processing very long audio files:

1. **Memory Constraints**: Long audio files require significant RAM for processing
2. **Context Window Limitations**: Models may have maximum sequence length constraints
3. **Processing Time**: Transcribing large files in one go is time-consuming and resource-intensive

## Solution

Our approach addresses these issues by:

1. **Chunking**: Splitting the audio into manageable segments (6 chunks in this implementation)
2. **Overlap Strategy**: Including 10-second overlaps between chunks to maintain context at boundaries
3. **Parallel Processing**: Each chunk can be processed independently (though the current implementation is sequential)
4. **Result Merging**: Combining individual transcriptions into a complete result

## Technical Implementation

The solution uses the following components:

- **librosa**: For loading and processing audio files
- **OpenAI Whisper**: For high-quality speech recognition
- **soundfile**: For saving temporary audio chunks
- **numpy**: For efficient audio data manipulation
- **tqdm**: For progress visualization during transcription

### Key Functions

1. `load_audio()`: Loads the audio file using librosa
2. `split_into_chunks()`: Divides the audio into chunks with specified overlap
3. `transcribe_chunks()`: Processes each chunk with Whisper
4. `combine_transcriptions()`: Merges individual transcriptions

## Usage

1. Place the audio file to be transcribed in the `ml` directory with the name `call-record.wav`
2. Install required dependencies: `pip install -r sst-requirements.txt`
3. Run the script: `python stt.py`
4. The complete transcription will be saved to `call-record-transcription.txt`

## Potential Improvements

- **Advanced Merging**: Implement more sophisticated techniques for merging overlapping sections
- **Parallel Processing**: Add multi-threading to process chunks simultaneously
- **Language Detection**: Auto-detect or allow specification of the audio language
- **Timestamp Retention**: Preserve timestamps from individual chunks in the final output
- **Diarization**: Add speaker identification for multi-speaker conversations

## References

- [OpenAI Whisper Documentation](https://github.com/openai/whisper)
- [Audio Chunking Techniques for ASR](https://blog.unrealspeech.com/making-automatic-speech-recognition-on-large-files-feasible-with-wav2vec2-and-chunking-techniques/) 