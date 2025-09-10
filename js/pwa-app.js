// PWA Application with YouTube Downloader, FFmpeg.js, and Drawing Canvas
// Import the functions you need from the SDKs you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.15.0/firebase-app.js";
import { getAuth, GoogleAuthProvider, signInWithPopup, onAuthStateChanged, signOut } from "https://www.gstatic.com/firebasejs/9.15.0/firebase-auth.js";

// --- Firebase Configuration ---
const firebaseConfig = {
    apiKey: "YOUR_API_KEY",
    authDomain: "YOUR_AUTH_DOMAIN",
    projectId: "YOUR_PROJECT_ID",
    storageBucket: "YOUR_STORAGE_BUCKET",
    messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
    appId: "YOUR_APP_ID"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

// --- Global Elements & State ---
const pageContainer = document.getElementById('page-container');
const toastContainer = document.getElementById('toast-container');
let playerSwiper = null;
let isPlayerInitialized = false;
let navEffect;
let currentPageIndex = 0;
const pageIds = ['home', 'play', 'about'];

// --- FFmpeg.js Setup ---
let ffmpeg = null;
let ffmpegLoaded = false;

// --- LocalStorage Manager ---
class LocalStorageManager {
    static STORAGE_KEY = 'outa_dow_songs';
    
    static saveSong(songData) {
        const songs = this.getSongs();
        const song = {
            id: Date.now().toString(),
            title: songData.title,
            artist: songData.artist,
            thumbnail: songData.thumbnail,
            audioData: songData.audioData,
            duration: songData.duration,
            dateAdded: new Date().toISOString()
        };
        songs.push(song);
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(songs));
        return song;
    }
    
    static getSongs() {
        const songs = localStorage.getItem(this.STORAGE_KEY);
        return songs ? JSON.parse(songs) : [];
    }
    
    static deleteSong(songId) {
        const songs = this.getSongs();
        const filteredSongs = songs.filter(song => song.id !== songId);
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(filteredSongs));
    }
    
    static clearAllSongs() {
        localStorage.removeItem(this.STORAGE_KEY);
    }
}

// --- Toast Notification Logic ---
const showToast = (message, type = 'success') => {
    const toast = document.createElement('div');
    const bgColor = type === 'success' ? 'bg-green-500' : 'bg-red-500';
    toast.className = `toast ${bgColor} text-white font-semibold py-2 px-4 rounded-lg shadow-lg`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
};

// --- FFmpeg.js Initialization ---
async function initializeFFmpeg() {
    if (ffmpegLoaded) return;
    
    try {
        const { FFmpeg } = FFmpegWASM;
        const { fetchFile, toBlobURL } = FFmpegUtil;
        
        ffmpeg = new FFmpeg();
        
        const baseURL = 'https://unpkg.com/@ffmpeg/core@0.12.6/dist/umd';
        await ffmpeg.load({
            coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),
            wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),
        });
        
        ffmpegLoaded = true;
        console.log('FFmpeg.js loaded successfully');
    } catch (error) {
        console.error('Failed to load FFmpeg.js:', error);
        showToast('Failed to load audio converter', 'error');
    }
}

// --- YouTube Downloader with FFmpeg.js ---
class YouTubeDownloader {
    constructor() {
        this.apiUrl = 'http://localhost:5000/api';
    }
    
    async downloadVideo(url, customTitle = null) {
        try {
            showToast('Starting download...', 'success');
            
            // Get video info first
            const infoResponse = await fetch(`${this.apiUrl}/thumbnail?url=${encodeURIComponent(url)}`);
            const videoInfo = await infoResponse.json();
            
            if (!videoInfo.thumbnail) {
                throw new Error('Could not get video information');
            }
            
            // Start download
            const downloadResponse = await fetch(`${this.apiUrl}/download`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: url,
                    title: customTitle
                })
            });
            
            const { download_id } = await downloadResponse.json();
            
            // Poll for progress
            return await this.pollDownloadProgress(download_id, videoInfo);
            
        } catch (error) {
            console.error('Download error:', error);
            showToast(`Download failed: ${error.message}`, 'error');
            return null;
        }
    }
    
    async pollDownloadProgress(downloadId, videoInfo) {
        return new Promise((resolve, reject) => {
            const pollInterval = setInterval(async () => {
                try {
                    const response = await fetch(`${this.apiUrl}/progress/${downloadId}`);
                    const progress = await response.json();
                    
                    this.updateDownloadProgress(progress.progress);
                    
                    if (progress.status === 'completed') {
                        clearInterval(pollInterval);
                        
                        // Convert to audio using FFmpeg.js
                        const audioData = await this.convertToAudio(progress.result.file_path);
                        
                        // Save to localStorage
                        const song = LocalStorageManager.saveSong({
                            title: progress.result.title,
                            artist: progress.result.artist,
                            thumbnail: videoInfo.thumbnail,
                            audioData: audioData,
                            duration: progress.result.duration
                        });
                        
                        showToast('Download completed!', 'success');
                        this.updatePlaylist();
                        resolve(song);
                        
                    } else if (progress.status === 'error') {
                        clearInterval(pollInterval);
                        reject(new Error(progress.error));
                    }
                } catch (error) {
                    clearInterval(pollInterval);
                    reject(error);
                }
            }, 1000);
        });
    }
    
    async convertToAudio(videoPath) {
        if (!ffmpegLoaded) {
            await initializeFFmpeg();
        }
        
        try {
            // Read video file
            await ffmpeg.writeFile('input.mp4', await fetchFile(videoPath));
            
            // Convert to MP3
            await ffmpeg.exec(['-i', 'input.mp4', '-vn', '-acodec', 'mp3', '-ab', '192k', 'output.mp3']);
            
            // Read output
            const data = await ffmpeg.readFile('output.mp3');
            
            // Convert to base64 for localStorage
            const blob = new Blob([data.buffer], { type: 'audio/mp3' });
            return await this.blobToBase64(blob);
            
        } catch (error) {
            console.error('Audio conversion error:', error);
            throw error;
        }
    }
    
    async blobToBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }
    
    updateDownloadProgress(progress) {
        const progressBars = document.querySelectorAll('.progress-bar-fill');
        const progressTexts = document.querySelectorAll('[id$="-percent"]');
        
        progressBars.forEach(bar => {
            bar.style.width = `${progress}%`;
        });
        
        progressTexts.forEach(text => {
            text.textContent = `${progress}%`;
        });
    }
}

// --- Drawing Canvas ---
class DrawingCanvas {
    constructor() {
        this.canvas = document.getElementById('drawing-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.isDrawing = false;
        this.lastX = 0;
        this.lastY = 0;
        
        this.setupCanvas();
        this.setupEventListeners();
    }
    
    setupCanvas() {
        // Set canvas size
        const rect = this.canvas.getBoundingClientRect();
        this.canvas.width = rect.width * window.devicePixelRatio;
        this.canvas.height = rect.height * window.devicePixelRatio;
        this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        
        // Set default styles
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';
        this.ctx.strokeStyle = '#000000';
        this.ctx.lineWidth = 5;
    }
    
    setupEventListeners() {
        // Mouse events
        this.canvas.addEventListener('mousedown', this.startDrawing.bind(this));
        this.canvas.addEventListener('mousemove', this.draw.bind(this));
        this.canvas.addEventListener('mouseup', this.stopDrawing.bind(this));
        this.canvas.addEventListener('mouseout', this.stopDrawing.bind(this));
        
        // Touch events for mobile
        this.canvas.addEventListener('touchstart', this.handleTouch.bind(this));
        this.canvas.addEventListener('touchmove', this.handleTouch.bind(this));
        this.canvas.addEventListener('touchend', this.stopDrawing.bind(this));
        
        // Controls
        document.getElementById('color-picker').addEventListener('change', (e) => {
            this.ctx.strokeStyle = e.target.value;
        });
        
        document.getElementById('brush-size').addEventListener('input', (e) => {
            this.ctx.lineWidth = e.target.value;
            document.getElementById('brush-size-label').textContent = `${e.target.value}px`;
        });
        
        document.getElementById('clear-canvas').addEventListener('click', () => {
            this.clearCanvas();
        });
        
        document.getElementById('save-drawing').addEventListener('click', () => {
            this.saveDrawing();
        });
    }
    
    startDrawing(e) {
        this.isDrawing = true;
        const rect = this.canvas.getBoundingClientRect();
        this.lastX = e.clientX - rect.left;
        this.lastY = e.clientY - rect.top;
    }
    
    draw(e) {
        if (!this.isDrawing) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const currentX = e.clientX - rect.left;
        const currentY = e.clientY - rect.top;
        
        this.ctx.beginPath();
        this.ctx.moveTo(this.lastX, this.lastY);
        this.ctx.lineTo(currentX, currentY);
        this.ctx.stroke();
        
        this.lastX = currentX;
        this.lastY = currentY;
    }
    
    stopDrawing() {
        this.isDrawing = false;
    }
    
    handleTouch(e) {
        e.preventDefault();
        const touch = e.touches[0];
        const mouseEvent = new MouseEvent(e.type === 'touchstart' ? 'mousedown' : 
                                         e.type === 'touchmove' ? 'mousemove' : 'mouseup', {
            clientX: touch.clientX,
            clientY: touch.clientY
        });
        this.canvas.dispatchEvent(mouseEvent);
    }
    
    clearCanvas() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        showToast('Canvas cleared', 'success');
    }
    
    saveDrawing() {
        const dataURL = this.canvas.toDataURL('image/png');
        const link = document.createElement('a');
        link.download = `drawing-${Date.now()}.png`;
        link.href = dataURL;
        link.click();
        showToast('Drawing saved!', 'success');
    }
}

// --- Home Page Logic ---
function initializeHomePage() {
    const urlInput = document.getElementById('url-input');
    const saveButton = document.getElementById('save-button');
    const linksContainer = document.getElementById('links-container');
    const downloader = new YouTubeDownloader();

    const renderDownloads = () => {
        const songs = LocalStorageManager.getSongs();
        if (songs.length === 0) {
            linksContainer.innerHTML = `<div class="no-downloads-placeholder text-center text-gray-300 py-10 rounded-lg border border-dashed border-gray-600">
                <p class="text-lg font-semibold">No downloads yet.</p>
                <p class="mt-1 text-gray-400">Paste a URL above to get started!</p>
            </div>`;
        } else {
            linksContainer.innerHTML = songs.map(song => `
                <div class="download-item w-full rounded-lg p-4 border border-gray-700 shadow-lg">
                    <div class="flex items-center gap-3">
                        <img src="${song.thumbnail}" alt="${song.title}" class="w-12 h-12 rounded object-cover">
                        <div class="flex-grow">
                            <h3 class="font-bold text-gray-100">${song.title}</h3>
                            <p class="text-sm text-gray-400">${song.artist}</p>
                        </div>
                        <button onclick="playSong('${song.id}')" class="bg-blue-500 text-white px-3 py-1 rounded text-sm">Play</button>
                    </div>
                </div>
            `).join('');
        }
    };
    
    const addDownload = async () => {
        const url = urlInput.value.trim();
        if (!url) { 
            showToast('Please enter a URL.', 'error'); 
            return; 
        }
        
        try { 
            new URL(url); 
        } catch (_) { 
            showToast('Please enter a valid URL.', 'error'); 
            return; 
        }
        
        if(linksContainer.querySelector('.no-downloads-placeholder')) {
            linksContainer.innerHTML = '';
        }
        
        // Show progress bar
        const downloadId = `download-${Date.now()}`;
        const card = document.createElement('div');
        card.className = 'download-item w-full rounded-lg p-4 border border-gray-700 shadow-lg';
        card.id = downloadId;
        card.innerHTML = `<div class="flex justify-between items-center mb-2"><p class="font-bold text-gray-100 truncate text-sm">Downloading...</p><p id="${downloadId}-percent" class="text-sm font-semibold text-gray-300">0%</p></div><div class="w-full bg-black/30 rounded-full h-2.5"><div id="${downloadId}-fill" class="progress-bar-fill h-2.5 rounded-full bg-blue-500" style="width: 0%"></div></div>`;
        linksContainer.prepend(card);
        urlInput.value = '';
        
        try {
            await downloader.downloadVideo(url);
            card.remove();
            renderDownloads();
        } catch (error) {
            card.querySelector('p').textContent = 'Download failed';
            showToast('Download failed', 'error');
        }
    };
    
    saveButton.addEventListener('click', addDownload);
    urlInput.addEventListener('keypress', (e) => { 
        if (e.key === 'Enter') addDownload(); 
    });
    
    renderDownloads();
}

// --- Music Player Logic ---
function initializeMusicPlayer() {
    if (isPlayerInitialized) return;

    const playlistItems = document.querySelectorAll("#page-play .playlist-item");
    const likeBtns = document.querySelectorAll("#page-play .like-btn");
    const audioPlayer = document.getElementById("audioPlayer");
    const volumeRange = document.getElementById("volume-range");
    const progressBar = document.getElementById("progress-bar");
    const playPauseBtn = document.getElementById("playPauseBtn");
    const playPauseIcon = document.getElementById("playPauseIcon");
    const prevBtn = document.getElementById("prevBtn");
    const nextBtn = document.getElementById("nextBtn");
    const shuffleBtn = document.getElementById("shuffleBtn");

    let currentSongIndex = 0;
    let isSongLoaded = false;
    const songs = LocalStorageManager.getSongs();
    
    if (songs.length === 0) {
        // Show default songs if no downloads
        const defaultSongs = [
            "https://github.com/ecemgo/mini-samples-great-tricks/raw/main/song-list/SynCole-FeelGood.mp3",
            "https://github.com/ecemgo/mini-samples-great-tricks/raw/main/song-list/HarddopeClarx-Castle.mp3",
            "https://github.com/ecemgo/mini-samples-great-tricks/raw/main/song-list/PlayDead-NEFFEX.mp3"
        ];
        audioPlayer.src = defaultSongs[0];
    } else {
        // Use downloaded songs
        audioPlayer.src = songs[0].audioData;
    }
    
    playerSwiper = new Swiper("#page-play .swiper", { 
        effect: "cards", 
        cardsEffect: { perSlideOffset: 9, perSlideRotate: 3 }, 
        grabCursor: true, 
        speed: 700, 
        initialSlide: 0 
    });
    
    const updatePlaylistHighlight = (index) => { 
        playlistItems.forEach((item, i) => { 
            i === index ? item.classList.add("active-playlist-item") : item.classList.remove("active-playlist-item"); 
        }); 
    };
    
    const loadAndPlaySong = (index) => { 
        if (songs.length > 0) {
            audioPlayer.src = songs[index].audioData;
        }
        playSong(); 
        updatePlaylistHighlight(index); 
        isSongLoaded = true; 
    };
    
    const pauseSong = () => { 
        audioPlayer.pause(); 
        updatePlayPauseIcon(false); 
    };
    
    const playSong = () => { 
        const playPromise = audioPlayer.play(); 
        if (playPromise !== undefined) { 
            playPromise.then(_ => { 
                updatePlayPauseIcon(true); 
            }).catch(error => { 
                if (error.name !== 'AbortError') { 
                    console.error('Playback failed:', error); 
                    updatePlayPauseIcon(false); 
                } 
            }); 
        } 
    };
    
    const togglePlayPause = () => { 
        if (!isSongLoaded) { 
            loadAndPlaySong(currentSongIndex); 
        } else if (audioPlayer.paused) { 
            playSong(); 
        } else { 
            pauseSong(); 
        } 
    };
    
    const updatePlayPauseIcon = (isPlaying) => { 
        if (isPlaying) { 
            playPauseIcon.classList.add("fa-pause"); 
            playPauseIcon.classList.remove("fa-play"); 
        } else { 
            playPauseIcon.classList.add("fa-play"); 
            playPauseIcon.classList.remove("fa-pause"); 
        } 
    };
    
    const nextSong = () => { 
        currentSongIndex = (currentSongIndex + 1) % songs.length; 
        loadAndPlaySong(currentSongIndex); 
    };
    
    const prevSong = () => { 
        currentSongIndex = (currentSongIndex - 1 + songs.length) % songs.length; 
        loadAndPlaySong(currentSongIndex); 
    };
    
    playlistItems.forEach((item, index) => { 
        item.addEventListener("click", () => { 
            currentSongIndex = index; 
            loadAndPlaySong(index); 
        }); 
    });
    
    playPauseBtn.addEventListener("click", togglePlayPause);
    nextBtn.addEventListener("click", nextSong);
    prevBtn.addEventListener("click", prevSong);
    
    audioPlayer.addEventListener("loadedmetadata", () => { 
        progressBar.max = audioPlayer.duration; 
        progressBar.value = audioPlayer.currentTime; 
    });
    
    audioPlayer.addEventListener("timeupdate", () => { 
        if (!audioPlayer.paused) { 
            progressBar.value = audioPlayer.currentTime; 
        } 
    });
    
    progressBar.addEventListener("input", () => { 
        audioPlayer.currentTime = progressBar.value; 
    });
    
    progressBar.addEventListener("change", () => { 
        playSong(); 
    });
    
    volumeRange.addEventListener("input", () => { 
        audioPlayer.volume = volumeRange.value / 100; 
    });
    
    audioPlayer.addEventListener("ended", nextSong);
    
    shuffleBtn.addEventListener("click", () => { 
        const randomIndex = Math.floor(Math.random() * songs.length); 
        currentSongIndex = randomIndex !== currentSongIndex ? randomIndex : (randomIndex + 1) % songs.length; 
        loadAndPlaySong(currentSongIndex); 
    });
    
    likeBtns.forEach((likeBtn) => { 
        likeBtn.addEventListener("click", (e) => { 
            e.stopPropagation(); 
            likeBtn.classList.toggle("fa-regular"); 
            likeBtn.classList.toggle("fa-solid"); 
        }); 
    });
    
    updatePlaylistHighlight(currentSongIndex);
    isPlayerInitialized = true;
}

// --- Firebase Authentication Logic ---
const userProfileContainer = document.getElementById('user-profile-container');

const signInWithGoogle = () => { 
    signInWithPopup(auth, provider).then((result) => { 
        showToast(`Welcome, ${result.user.displayName}!`); 
    }).catch((error) => { 
        console.error("Authentication failed:", error); 
        showToast('Sign-in failed. Please try again.', 'error'); 
    }); 
};

const signOutUser = () => { 
    signOut(auth).then(() => { 
        showToast('You have been signed out.'); 
    }).catch((error) => { 
        console.error("Sign out failed:", error); 
    }); 
};

const updateProfileUI = (user) => {
    if (user) {
        userProfileContainer.innerHTML = `<div class="bg-transparent flex flex-col items-center"><img src="${user.photoURL}" alt="User Profile" class="w-24 h-24 rounded-full mb-4 border-4 border-[#f52cb9]"><h1 class="text-2xl font-bold">${user.displayName}</h1><p class="text-gray-400 mb-6">${user.email}</p><button id="sign-out-btn" class="bg-gray-600 hover:bg-gray-700 text-white font-semibold rounded-lg px-6 py-2 transition duration-200">Sign Out</button></div>`;
    } else {
        userProfileContainer.innerHTML = `<div class="bg-transparent"><h1 class="text-3xl font-bold mb-4">User Profile</h1><p class="text-gray-300 mb-6">Sign in to view your profile and sync your data.</p><button id="google-signin-btn" class="bg-[#f52cb9] hover:bg-[#d4249b] text-white font-semibold rounded-lg px-6 py-3 transition duration-200 shadow-[0_0_15px_rgba(245,44,185,0.5)] hover:shadow-[0_0_25px_rgba(245,44,185,0.8)] flex items-center justify-center mx-auto"><svg class="w-6 h-6 mr-3" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4C12.955 4 4 12.955 4 24s8.955 20 20 20s20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"></path><path fill="#FF3D00" d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4C16.318 4 9.656 8.337 6.306 14.691z"></path><path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"></path><path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303c-.792 2.237-2.231 4.166-4.087 5.571l6.19 5.238C42.021 35.596 44 30.138 44 24c0-1.341-.138-2.65-.389-3.917z"></path></svg>Sign In with Google</button></div>`;
    }
};

// --- Navigation and Page Switching Logic ---
const showPage = (pageId) => {
    const pageIndex = pageIds.indexOf(pageId);
    if (pageIndex !== -1) {
        const scrollX = pageIndex * window.innerWidth;
        pageContainer.scrollTo({ left: scrollX, behavior: 'smooth' });
        if (pageId === 'play') {
            initializeMusicPlayer();
        } else if (pageId === 'about') {
            // Initialize drawing canvas when about page is shown
            if (!window.drawingCanvas) {
                window.drawingCanvas = new DrawingCanvas();
            }
        }
        currentPageIndex = pageIndex;
    }
};

class NavigationEffect {
    constructor(navigation) { 
        this.navigation = navigation; 
        this.anchors = this.navigation.querySelectorAll("a"); 
        this.anchors.forEach((anchor) => { 
            anchor.addEventListener("click", (e) => { 
                e.preventDefault(); 
                const pageId = anchor.dataset.page; 
                if(pageId) showPage(pageId); 
                this.handlePrevious(); 
                this.handleCurrent(anchor); 
            }); 
        }); 
    }
    
    handleCurrent(current) { 
        this.current = current; 
        this.current.classList.add("active"); 
        const nodes = this.getNodes(this.current); 
        gsap.to(nodes[0], { 
            duration: 1.8, 
            ease: "elastic.out(1.4, 0.4)", 
            yPercent: "-100", 
            stagger: 0.008, 
            overwrite: true 
        }); 
        gsap.to(nodes[1], { 
            duration: 1.8, 
            ease: "elastic.out(1.4, 0.4)", 
            yPercent: "-100", 
            stagger: 0.008, 
            overwrite: true 
        }); 
    }
    
    handlePrevious() { 
        this.previous = this.navigation.querySelector(".active"); 
        if (this.previous) { 
            this.previous.classList.remove("active"); 
            const nodes = this.getNodes(this.previous); 
            gsap.to(nodes[0], { 
                duration: 0.2, 
                ease: "power1.out", 
                yPercent: "100", 
                overwrite: true, 
                stagger: 0.012 
            }); 
            gsap.to(nodes[1], { 
                duration: 0.2, 
                ease: "power1.out", 
                yPercent: "100", 
                overwrite: true, 
                delay: 0.02, 
                stagger: 0.012 
            }); 
        } 
    }
    
    getNodes(item) { 
        return [
            gsap.utils.shuffle(gsap.utils.selector(item)(".blue rect")), 
            gsap.utils.shuffle(gsap.utils.selector(item)(".pink rect"))
        ]; 
    }
}

// --- Swipe Navigation ---
let touchStartX = 0;
let touchEndX = 0;

function handleSwipeGesture() {
    const swipeThreshold = 150;
    if (touchEndX < touchStartX - swipeThreshold) {
        if (currentPageIndex < pageIds.length - 1) {
            currentPageIndex++;
            const nextPageId = pageIds[currentPageIndex];
            showPage(nextPageId);
            const navLink = document.querySelector(`nav a[data-page="${nextPageId}"]`);
            if(navLink) {
                navEffect.handlePrevious();
                navEffect.handleCurrent(navLink);
            }
        }
    }
    if (touchEndX > touchStartX + swipeThreshold) {
        if (currentPageIndex > 0) {
            currentPageIndex--;
            const prevPageId = pageIds[currentPageIndex];
            showPage(prevPageId);
            const navLink = document.querySelector(`nav a[data-page="${prevPageId}"]`);
             if(navLink) {
                navEffect.handlePrevious();
                navEffect.handleCurrent(navLink);
            }
        }
    }
}

pageContainer.addEventListener('touchstart', e => { 
    touchStartX = e.changedTouches[0].screenX; 
}, { passive: true });

pageContainer.addEventListener('touchend', e => { 
    touchEndX = e.changedTouches[0].screenX; 
    handleSwipeGesture(); 
});

// --- Initial Load ---
document.addEventListener('DOMContentLoaded', () => {
    gsap.registerPlugin(EasePack);
    navEffect = new NavigationEffect(document.querySelector("nav"));
    const homeLink = document.querySelector('a[data-page="home"]');
    if (homeLink) navEffect.handleCurrent(homeLink);
    
    initializeHomePage();
    initializeFFmpeg();

    onAuthStateChanged(auth, user => { 
        updateProfileUI(user); 
    });
    
    userProfileContainer.addEventListener('click', (e) => {
        if (e.target.closest('#google-signin-btn')) signInWithGoogle();
        if (e.target.closest('#sign-out-btn')) signOutUser();
    });
});

// Global function for playing songs from home page
window.playSong = function(songId) {
    const songs = LocalStorageManager.getSongs();
    const song = songs.find(s => s.id === songId);
    if (song) {
        const audioPlayer = document.getElementById("audioPlayer");
        audioPlayer.src = song.audioData;
        audioPlayer.play();
        showToast(`Playing: ${song.title}`, 'success');
    }
};
