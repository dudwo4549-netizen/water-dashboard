let currentSlide = 0;
const slidesWrapper = document.getElementById('slidesWrapper');
const totalSlides = document.querySelectorAll('.slide').length;
const progressBar = document.getElementById('progressBar');
const indicator = document.getElementById('indicator');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');

function updateUI() {
    // Update Slider Position
    slidesWrapper.style.transform = `translateX(-${currentSlide * 100}%)`;
    
    // Update Progress Bar
    const progress = ((currentSlide + 1) / totalSlides) * 100;
    progressBar.style.width = `${progress}%`;
    
    // Update Indicator
    indicator.innerText = `${currentSlide + 1} / ${totalSlides}`;
    
    // Show/Hide buttons
    prevBtn.style.visibility = currentSlide === 0 ? 'hidden' : 'visible';
    nextBtn.innerText = currentSlide === totalSlides - 1 ? '처음으로' : '다음';
}

function goToSlide(index) {
    if (index >= 0 && index < totalSlides) {
        currentSlide = index;
    } else if (index >= totalSlides) {
        currentSlide = 0;
    }
    updateUI();
}

nextBtn.addEventListener('click', () => {
    goToSlide(currentSlide + 1);
});

prevBtn.addEventListener('click', () => {
    goToSlide(currentSlide - 1);
});

// Touch Events for Mobile
let touchStartX = 0;
let touchEndX = 0;

document.addEventListener('touchstart', e => {
    touchStartX = e.changedTouches[0].screenX;
});

document.addEventListener('touchend', e => {
    touchEndX = e.changedTouches[0].screenX;
    if (touchStartX - touchEndX > 50) {
        goToSlide(currentSlide + 1);
    } else if (touchEndX - touchStartX > 50) {
        goToSlide(currentSlide - 1);
    }
});

// Image Download Feature
const downloadBtn = document.getElementById('downloadBtn');
downloadBtn.addEventListener('click', async () => {
    downloadBtn.innerText = '저장 중... ⏳';
    downloadBtn.disabled = true;
    const slides = document.querySelectorAll('.slide');
    
    for (let i = 0; i < slides.length; i++) {
        // Temporarily scroll to the slide to capture it properly
        slidesWrapper.style.transform = `translateX(-${i * 100}%)`;
        await new Promise(r => setTimeout(r, 300)); // wait for transition
        
        const canvas = await html2canvas(slides[i], {
            scale: 2, // High resolution
            useCORS: true,
            backgroundColor: '#0a0a0c'
        });
        
        const link = document.createElement('a');
        link.download = `seoyong_cardnews_${i + 1}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    }
    
    // Restore back to current slide
    updateUI();
    downloadBtn.innerText = '이미지 저장 📸';
    downloadBtn.disabled = false;
    alert("모든 슬라이드가 이미지로 저장되었습니다!");
});

// Init
updateUI();
