import time
import os
import logging
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from sqlalchemy.orm import Session
from lib.database import SessionLocal, engine, Base
from lib.models import Song
from lib.ai_client import AIClient

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

MUSIC_DIR = "/music"

class MusicHandler(FileSystemEventHandler):
    def __init__(self):
        self.ai_client = AIClient()

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".mp3"):
            logger.info(f"New MP3 detected: {event.src_path}")
            self.process_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".mp3"):
             # Simple debounce/check to avoid processing twice if needed, 
             # but for now we'll just process.
             # In docker volume mount, sometimes file events are tricky.
             pass

    def process_file(self, filepath):
        filename = os.path.basename(filepath)
        logger.info(f"Processing {filename}...")

        # 1. Extract existing tags
        existing_tags = {}
        try:
            audio = MP3(filepath, ID3=EasyID3)
            for key in audio.keys():
                existing_tags[key] = audio[key][0]
        except Exception as e:
            logger.warning(f"Could not read ID3 tags from {filename}: {e}")

        # 2. Get tags from Gemini
        try:
            logger.info(f"Starting Audio Analysis for {filename}...")
            generated_tags = self.ai_client.generate_tags(filename, filepath, existing_tags)
            logger.info(f"Generated tags for {filename}: {generated_tags}")
        except Exception as e:
            logger.error(f"Failed to generate tags for {filename}: {e}")
            generated_tags = {}

        # 3. Save to DB
        db = SessionLocal()
        try:
            # Check if exists
            song = db.query(Song).filter(Song.filepath == filepath).first()
            if not song:
                song = Song(filepath=filepath, filename=filename)
                db.add(song)
            
            # Update fields
            song.title = generated_tags.get("title") or existing_tags.get("title")
            song.artist = generated_tags.get("artist") or existing_tags.get("artist")
            song.album = generated_tags.get("album") or existing_tags.get("album")
            song.genre = generated_tags.get("genre") or existing_tags.get("genre")
            song.year = generated_tags.get("year") or existing_tags.get("date") # mutagen uses 'date'
            song.comment = generated_tags.get("comment")

            db.commit()
            logger.info(f"Saved {filename} to database.")

        except Exception as e:
            logger.error(f"Database error: {e}")
            db.rollback()
        finally:
            db.close()

    def scan_existing_files(self, directory):
        """Scan directory for existing MP3 files and process them."""
        logger.info(f"Scanning {directory} for existing files...")
        for filename in os.listdir(directory):
            if filename.endswith(".mp3"):
                filepath = os.path.join(directory, filename)
                self.process_file(filepath)
                time.sleep(10) # Avoid rate limits

if __name__ == "__main__":
    path = MUSIC_DIR
    event_handler = MusicHandler()
    
    # Scan existing files first
    event_handler.scan_existing_files(path)

    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()
    logger.info(f"Watching directory: {path}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
