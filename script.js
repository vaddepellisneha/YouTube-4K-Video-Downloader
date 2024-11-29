function startDownload() {
    const videoUrl = document.getElementById('videoUrl').value;
    const resolution = document.getElementById('resolutionSelect').value;

    if (!videoUrl) {
        alert("Please enter a YouTube video URL");
        return;
    }

    // Display initial "Preparing" message
    document.getElementById('video-details').innerHTML = `
        Preparing to start download... Please wait a few seconds.
    `;

    // Start download request to backend
    fetch('http://localhost:8000/download_video', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ videoUrl: videoUrl, resolution: resolution })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to start download');
        }
        return response.json();
    })
    .then(data => {
        const videoId = data.video_id;

        // Display download start message
        document.getElementById('video-details').innerHTML = `
            Download started! Tracking progress...<br>
            Video ID: ${videoId}
        `;

        // Set up EventSource for progress updates
        const eventSource = new EventSource(`https://youtubevideodownloader-lovestoblog-com.vercel.app/progress/${videoId}`);
        let startTime = Date.now(); // Track when the download started

        eventSource.onmessage = function(event) {
            if (event.data === "complete") {
                const elapsedTime = ((Date.now() - startTime) / 1000).toFixed(2);
                document.getElementById('video-details').innerHTML += `
                    <br>Download complete! Total time: ${elapsedTime} seconds.
                `;
                alert("Download complete!");
                eventSource.close(); // Stop listening to events
            } else {
                const progressData = event.data.split(',');
                const progress = parseInt(progressData[0]);
                const size = parseFloat(progressData[1]);
                const speed = progressData[2];
                const eta = progressData[3];

                document.getElementById("progress").style.width = progress + "%";
                document.getElementById('video-details').innerHTML = `
                    Download Progress: ${progress}% <br>
                    Downloaded: ${size.toFixed(2)} MB <br>
                    Speed: ${speed} <br>
                    ETA: ${eta} seconds
                `;
            }
        };

        eventSource.onerror = function(error) {
            console.error("EventSource error:", error);
            alert("Error occurred during download.");
            eventSource.close();
        };
    })
    .catch(error => {
        console.error("Fetch error:", error);
        alert("Error starting download.");
    });
}
