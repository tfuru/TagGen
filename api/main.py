from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_
from lib.database import SessionLocal, engine, Base
from lib.models import Song
from typing import List, Optional
from pydantic import BaseModel
from lib.ai_client import AIClient

# Create tables (if not exists, though watching service likely created them)
Base.metadata.create_all(bind=engine)

# Pydantic model for response
class SongResponse(BaseModel):
    id: int
    filename: str
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[str] = None
    comment: Optional[str] = None
    playback_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class SearchResponse(BaseModel):
    results: List[SongResponse]

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="TagGen API")

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/music", StaticFiles(directory="/music"), name="music")

ai_client = AIClient()

@app.get("/")
def read_root():
    return {"message": "TagGen API is running"}

@app.get("/search", response_model=SearchResponse)
def search_songs(
    request: Request,
    q: str = Query(..., description="Natural language search query"),
    db: Session = Depends(get_db)
):
    # 1. Expand query using Gemini
    keywords = ai_client.expand_query(q)
    print(f"Expanded keywords for '{q}': {keywords}")

    # 2. Build OR query
    filters = []
    for keyword in keywords:
        kw = f"%{keyword}%"
        filters.append(Song.title.ilike(kw))
        filters.append(Song.artist.ilike(kw))
        filters.append(Song.album.ilike(kw))
        filters.append(Song.genre.ilike(kw))
        filters.append(Song.comment.ilike(kw))
        filters.append(Song.filename.ilike(kw))

    songs = db.query(Song).filter(or_(*filters)).all()
    
    # Remove duplicates (since a song might match multiple keywords)
    unique_songs = {song.id: song for song in songs}.values()
    
    # Add playback_url
    results = []
    base_url = str(request.base_url).rstrip("/")
    for song in unique_songs:
        # Convert to Pydantic model and add URL
        song_resp = SongResponse.model_validate(song)
        song_resp.playback_url = f"{base_url}/music/{song.filename}" 
        results.append(song_resp)

    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
