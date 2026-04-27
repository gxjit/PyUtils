# PyUtils

A collection of handy Python utility scripts for automating day-to-day tasks. This repository focuses heavily on file system management, batch processing, archiving, and media/audio manipulation.

## 🧰 Included Utilities

### 🎬 Media & Audio Processing
* **`audioBitrateCheck.py`** - Scan and check the bitrates of audio files.
* **`chapterSplitsM4a.py`** - Split `.m4a` audio files (like audiobooks or podcasts) into separate tracks based on their embedded chapter metadata.
* **`chapterizeAudio.py`** - Add or process chapter metadata for audio files.
* **`checkMedia.py`** - Verify the integrity or properties of media files in a directory.
* **`extractAudio.py`** - Extract audio tracks from video files automatically.

### 📁 File & Directory Management
* **`copyWithStruct.py`** - Copy specific files from one location to another while preserving their original directory tree structure.
* **`moveUpDir.py`** - Move all files within subdirectories up one directory level, flattening the folder structure.
* **`recursiveDirsCmd.py`** - Execute a specific terminal command recursively across all subdirectories.
* **`recursiveDirsList.py`** - Generate a clean list of files or directories recursively.
* **`renDirList.py`** - Bulk rename files or directories based on a list or specific logic.
* **`slugifyNames.py`** - Clean up file and folder names by "slugifying" them (removing spaces and special characters to make them web-safe and CLI-friendly).

### 📦 Archiving
* **`extractZips.py`** - Batch extract multiple ZIP archives in one go.
* **`zip-dirs.py`** - Compress multiple subdirectories into their own individual ZIP archives.
* **`zip-files.py`** - Compress specific lists or groups of files into ZIP archives.

## 🚀 Usage

Most of these scripts are designed to be run directly from the command line. You can typically run them by passing the target directory or file as an argument:

```bash
python slugifyNames.py /path/to/target/folder
