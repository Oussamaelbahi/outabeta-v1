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

// --- Toast Notification Logic ---
const showToast = (message, type = 'success') => {
    const toast = document.createElement('div');
    const bgColor = type === 'success' ? 'bg-green-500' : 'bg-red-500';
    toast.className = `toast ${bgColor} text-white font-semibold py-2 px-4 rounded-lg shadow-lg`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
};

// --- Home Page Logic ---
function initializeHomePage() {
    const urlInput = document.getElementById('url-input');
    const saveButton = document.getElementById('save-button');
    const linksContainer = document.getElementById('links-container');

    const renderDownloads = () => {
        if (!linksContainer.hasChildNodes()) {
            linksContainer.innerHTML = `<div class="no-downloads-placeholder text-center text-gray-300 py-10 rounded-lg border border-dashed border-gray-600">
                <p class="text-lg font-semibold">No downloads yet.</p>
                <p class="mt-1 text-gray-400">Paste a URL above to get started!</p>
            </div>`;
        }
    };
    
    const addDownload = () => {
        const url = urlInput.value.trim();
        if (!url) { showToast('Please enter a URL.', 'error'); return; }
        try { new URL(url); } catch (_) { showToast('Please enter a valid URL.', 'error'); return; }
        if(linksContainer.querySelector('.no-downloads-placeholder')) {
            linksContainer.innerHTML = '';
        }
        const downloadId = `download-${Date.now()}`;
        const card = document.createElement('div');
        card.className = 'download-item w-full rounded-lg p-4 border border-gray-700 shadow-lg';
        card.id = downloadId;
        card.innerHTML = `<div class="flex justify-between items-center mb-2"><p class="font-bold text-gray-100 truncate text-sm">Preparing download...</p><p id="${downloadId}-percent" class="text-sm font-semibold text-gray-300">0%</p></div><div class="w-full bg-black/30 rounded-full h-2.5"><div id="${downloadId}-fill" class="progress-bar-fill h-2.5 rounded-full" style="width: 0%"></div></div>`;
        linksContainer.prepend(card);
        urlInput.value = '';
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.floor(Math.random() * 5) + 1;
            if (progress > 100) progress = 100;
            const fill = document.getElementById(`${downloadId}-fill`);
            const percentText = document.getElementById(`${downloadId}-percent`);
            if (fill && percentText) { fill.style.width = `${progress}%`; percentText.textContent = `${progress}%`; }
            if (progress === 100) { clearInterval(interval); if(percentText) percentText.textContent = 'Completed'; card.querySelector('p').textContent = 'Download Finished'; }
        }, 200);
    };
    
    saveButton.addEventListener('click', addDownload);
    urlInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') addDownload(); });
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

    let currentSongIndex = 2;
    let isSongLoaded = false;
    const songs = [ 
        "https://github.com/ecemgo/mini-samples-great-tricks/raw/main/song-list/SynCole-FeelGood.mp3", 
        "https://github.com/ecemgo/mini-samples-great-tricks/raw/main/song-list/HarddopeClarx-Castle.mp3", 
        "https://github.com/ecemgo/mini-samples-great-tricks/raw/main/song-list/PlayDead-NEFFEX.mp3", 
        "https://github.com/ecemgo/mini-samples-great-tricks/raw/main/song-list/KnowMyself-PatrickPatrikios.mp3", 
        "https://github.com/ecemgo/mini-samples-great-tricks/raw/main/song-list/BesomorphCoopex-Redemption.mp3", 
    ];
    
    playerSwiper = new Swiper("#page-play .swiper", { 
        effect: "cards", 
        cardsEffect: { perSlideOffset: 9, perSlideRotate: 3 }, 
        grabCursor: true, 
        speed: 700, 
        initialSlide: 2 
    });
    
    playerSwiper.on("slideChange", () => { 
        const newIndex = playerSwiper.realIndex; 
        if (newIndex !== currentSongIndex) { 
            currentSongIndex = newIndex; 
            loadAndPlaySong(currentSongIndex); 
        } 
    });
    
    const updateSwiperToMatchSong = (index) => { 
        if (playerSwiper && playerSwiper.activeIndex !== index) { 
            playerSwiper.slideTo(index); 
        } 
    };
    
    const updatePlaylistHighlight = (index) => { 
        playlistItems.forEach((item, i) => { 
            i === index ? item.classList.add("active-playlist-item") : item.classList.remove("active-playlist-item"); 
        }); 
    };
    
    const loadAndPlaySong = (index) => { 
        audioPlayer.src = songs[index]; 
        playSong(); 
        updatePlaylistHighlight(index); 
        updateSwiperToMatchSong(index); 
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
    const swipeThreshold = 150; // Increased swipe threshold
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

    onAuthStateChanged(auth, user => { 
        updateProfileUI(user); 
    });
    
    userProfileContainer.addEventListener('click', (e) => {
        if (e.target.closest('#google-signin-btn')) signInWithGoogle();
        if (e.target.closest('#sign-out-btn')) signOutUser();
    });
});
