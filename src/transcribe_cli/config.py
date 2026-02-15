DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"
DEFAULT_FORMAT = "txt"
DEFAULT_WORKERS = 1

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm"}
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

TRACKER_DIR = ".transcribe-cli"
TRACKER_DB = "jobs.db"
VOCABULARY_FILE = "vocabulary.json"
