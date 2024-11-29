import os
import time
import uuid
import logging
import asyncio
import yt_dlp
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create download directory if it doesn't exist
download_dir = './downloads'
if not os.path.exists(download_dir):
    os.makedirs(download_dir)

# Store download progress and history
download_progress = {}
download_history = {}

@app.post("/download_video")
async def download_video(request: Request):
    data = await request.json()
    video_url = data['videoUrl']
    resolution = data['resolution']

    # Generate a unique video ID for this download
    video_id = str(uuid.uuid4())
    download_progress[video_id] = {'percent': 0, 'size': 0}  # Initialize download progress
    download_history[video_id] = "Downloading..."

    logging.debug(f"Download task started for video_id: {video_id} with URL: {video_url}")

    # Check available formats before downloading
    available_formats = await get_available_formats(video_url)

    if resolution not in available_formats:
        logging.warning(f"Requested format {resolution} not available. Selecting best available format.")
        resolution = 'bestvideo+bestaudio'  # Fallback to best quality

    # Start the download in the background
    asyncio.create_task(download_task(video_url, resolution, video_id))

    return JSONResponse({
        "video_id": video_id,
        "video_name": "Downloading..."
    })

async def get_available_formats(video_url):
    try:
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            formats = info_dict.get('formats', [])
            available_formats = [fmt['format_id'] for fmt in formats]
            logging.debug(f"Available formats for video: {available_formats}")
            return available_formats
    except Exception as e:
        logging.error(f"Error getting available formats: {e}")
        return []

async def download_task(video_url, resolution, video_id):
    try:
        ydl_opts = {
            'format': resolution,
            'outtmpl': f'./downloads/{video_id}.mp4',  # Save the video as .mp4
            'progress_hooks': [progress_hook(video_id)],
            'quiet': False,  # Show progress and logging
            'noprogress': False  # Make sure progress is shown
        }

        logging.debug(f"Starting download for {video_id} with options: {ydl_opts}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            video_name = info_dict.get('title', 'Unknown Video')

            # Set download progress to 100% once complete
            download_progress[video_id] = {'percent': 100, 'size': download_progress[video_id]['size']}
            download_history[video_id] = video_name

            logging.debug(f"Download completed for {video_id}. Video name: {video_name}")

    except Exception as e:
        download_progress[video_id] = {'percent': 0, 'size': 0}
        download_history[video_id] = f"Error: {str(e)}"
        logging.error(f"Error during download for {video_id}: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": f"Error occurred: {str(e)}"
        })

def progress_hook(video_id):
    def hook(d):
        if d['status'] == 'downloading':
            percent = d.get('progress', 0)
            downloaded_size = d.get('downloaded_bytes', 0) / (1024 * 1024)  # Convert to MB
            if percent:
                download_progress[video_id] = {'percent': int(percent), 'size': downloaded_size}
            logging.debug(f"Progress for {video_id}: {percent}% - Downloaded: {downloaded_size:.2f} MB")
        elif d['status'] == 'finished':
            download_progress[video_id] = {'percent': 100, 'size': download_progress[video_id]['size']}
            logging.debug(f"Download finished for {video_id}")
    return hook

@app.get("/progress/{video_id}")
async def get_progress(video_id: str):
    logging.debug(f"Request to get progress for video_id: {video_id}")

    if video_id not in download_progress:
        logging.error(f"Video ID {video_id} not found.")
        return JSONResponse(status_code=404, content={"error": "Video ID not found"})

    def event_stream():
        try:
            while download_progress[video_id]['percent'] != 100:
                percent = download_progress[video_id]['percent']
                size = download_progress[video_id]['size']
                logging.debug(f"Progress for {video_id}: {percent}% - Downloaded: {size:.2f} MB")
                yield f"data: {percent},{size:.2f}\n\n"
                time.sleep(1)
            logging.debug(f"Download complete for {video_id}")
            yield "data: complete\n\n"
        except Exception as e:
            logging.error(f"Error during stream for {video_id}: {str(e)}")
            yield f"data: Error occurred: {str(e)}\n\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/history")
async def get_history():
    logging.debug(f"Request to get download history")
    return JSONResponse({"history": download_history})