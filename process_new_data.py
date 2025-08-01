#!/usr/bin/env python3
"""
Quick script to process new historical data files
Usage: python process_new_data.py <file_or_directory> [--replace]
"""

import sys
import os
from batch_data_processor import process_single_file, process_folder

def main():
    if len(sys.argv) < 2:
        print("Usage: python process_new_data.py <file_or_directory> [--replace]")
        print("\nExamples:")
        print("  python process_new_data.py backtest_Mar16_Mar31.xml")
        print("  python process_new_data.py ./historical_data/")
        print("  python process_new_data.py data.csv --replace")
        sys.exit(1)
    
    path = sys.argv[1]
    mode = 'replace' if '--replace' in sys.argv else 'append'
    
    print(f"Processing: {path}")
    print(f"Mode: {mode}")
    
    if os.path.isfile(path):
        # Process single file
        output = process_single_file(path, output_mode=mode)
        if output:
            print(f"\n✓ Success! Output saved to: {output}")
            
            # Quick stats
            import pandas as pd
            df = pd.read_csv(output)
            print(f"\nQuick Stats:")
            print(f"- Total picks: {len(df)}")
            print(f"- Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"- Win rate: {(df['hit'].sum() / len(df) * 100):.2f}%")
    
    elif os.path.isdir(path):
        # Process directory
        pattern = input("File pattern (e.g., *.xml, *.csv, backtest_*.xml): ") or "*.xml"
        output = process_folder(path, file_pattern=pattern, output_mode=mode)
        if output:
            print(f"\n✓ Success! Output saved to: {output}")
    
    else:
        print(f"Error: '{path}' is not a valid file or directory")
        sys.exit(1)

if __name__ == "__main__":
    main()