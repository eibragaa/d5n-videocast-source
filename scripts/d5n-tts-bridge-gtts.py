
import os
import sys
import argparse
from gtts import gTTS
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio-dir', required=True)
    parser.add_argument('--editorial-date', required=True)
    args = parser.parse_args()

    audio_dir = Path(args.audio_dir)
    
    # Get all text files in audio_dir
    txt_files = sorted(list(audio_dir.glob('*.txt')))
    
    if not txt_files:
        print("No text files found in audio_dir")
        sys.exit(1)

    print(f"D5N gTTS BRIDGE — {args.editorial_date}")
    print(f"Sintetizando {len(txt_files)} seções via Google TTS...")

    success_count = 0
    for txt_file in txt_files:
        try:
            text = txt_file.read_text(encoding='utf-8').strip()
            if not text:
                continue
            
            mp3_path = txt_file.with_suffix('.mp3')
            tts = gTTS(text=text, lang='pt')
            tts.save(str(mp3_path))
            
            print(f"  ✓ {txt_file.name} -> {mp3_path.name}")
            success_count += 1
        except Exception as e:
            print(f"  ✗ {txt_file.name} falhou: {e}")

    print(f"\nConcluído: {success_count} OK, {len(txt_files) - success_count} falhou(s)")

if __name__ == '__main__':
    main()
