// Web Portal Client Scripts

let isPolling = false;

// Haber kartını aç / kapat
function toggleCardExpansion(card) {
    if (event.target.closest('a') || event.target.closest('.badge')) {
        return;
    }

    const details = card.querySelector('.card-details');
    const inner = card.querySelector('.card-details-inner');

    if (card.classList.contains('expanded')) {
        card.classList.remove('expanded');
        details.style.maxHeight = '0px';
        return;
    }

    card.classList.add('expanded');
    details.style.maxHeight = (inner.scrollHeight + 32) + 'px';
}

function setLanguage(lang) {
    const url = new URL(window.location.href);
    url.searchParams.set("lang", lang);
    window.location.href = url.toString();
}

function setFilter(mode) {
    const url = new URL(window.location.href);
    url.searchParams.set("filter", mode);
    window.location.href = url.toString();
}

function changeDate(selectedDate) {
    const url = new URL(window.location.href);
    url.searchParams.set("date", selectedDate);
    window.location.href = url.toString();
}

// Global active source filters & search query tracking
let activeSourceFilter = 'all';
let activeViewTab = 'all'; // 'all' or 'az'
let activeAzSubcategory = 'all';
let currentSearchQuery = '';
let displayLimit = 25;

function switchViewTab(tab) {
    activeViewTab = tab;
    activeAzSubcategory = 'all';
    displayLimit = 25;

    const tabAll = document.getElementById('tabAllMedia');
    const tabAz = document.getElementById('tabAzAgenda');
    const azSubfiltersBar = document.getElementById('azSubfiltersBar');

    if (tab === 'az') {
        if (tabAll) tabAll.classList.remove('active');
        if (tabAz) tabAz.classList.add('active');
        if (azSubfiltersBar) azSubfiltersBar.style.display = 'flex';
        const pills = document.querySelectorAll('.az-filter-pill');
        pills.forEach((p, idx) => {
            if (idx === 0) p.classList.add('active');
            else p.classList.remove('active');
        });
    } else {
        if (tabAll) tabAll.classList.add('active');
        if (tabAz) tabAz.classList.remove('active');
        if (azSubfiltersBar) azSubfiltersBar.style.display = 'none';
    }

    applyFiltersAndPagination();
}

function filterAzCategory(category, clickedElement) {
    activeAzSubcategory = category;
    displayLimit = 25;

    const pills = document.querySelectorAll('.az-filter-pill');
    pills.forEach(p => p.classList.remove('active'));
    if (clickedElement) {
        clickedElement.classList.add('active');
    }

    applyFiltersAndPagination();
}

function handleSearchInput(value) {
    currentSearchQuery = value.trim().toLowerCase();
    const clearBtn = document.getElementById('clearSearchBtn');
    if (clearBtn) {
        clearBtn.style.display = currentSearchQuery ? 'block' : 'none';
    }
    displayLimit = 25; // Reset limit on search
    applyFiltersAndPagination();
}

function clearSearch() {
    const searchInput = document.getElementById('newsSearchInput');
    if (searchInput) {
        searchInput.value = '';
    }
    handleSearchInput('');
}

function applySearch() {
    const searchInput = document.getElementById('newsSearchInput');
    if (searchInput) {
        handleSearchInput(searchInput.value);
    }
}

function filterBySource(sourceName, clickedElement) {
    activeSourceFilter = sourceName;
    displayLimit = 25; // Reset limit when switching source
    
    // Toggle active classes in sidebar menu
    const menuItems = document.querySelectorAll('.source-menu-item');
    menuItems.forEach(item => item.classList.remove('active'));
    if (clickedElement) {
        clickedElement.classList.add('active');
    }

    applyFiltersAndPagination();
}

function filterByOtherSources(clickedElement) {
    activeSourceFilter = 'other';
    displayLimit = 25; // Reset limit
    
    // Toggle active classes
    const menuItems = document.querySelectorAll('.source-menu-item');
    menuItems.forEach(item => item.classList.remove('active'));
    if (clickedElement) {
        clickedElement.classList.add('active');
    }

    applyFiltersAndPagination();
}

let currentTimeSort = 'desc'; // 'desc' = newest first, 'asc' = oldest first

function toggleTimeSort(order) {
    currentTimeSort = order;
    const btnDesc = document.getElementById('sortDescBtn');
    const btnAsc = document.getElementById('sortAscBtn');
    if (btnDesc) btnDesc.classList.toggle('active', order === 'desc');
    if (btnAsc) btnAsc.classList.toggle('active', order === 'asc');
    
    sortCardsInDOM();
    applyFiltersAndPagination();
}

function sortCardsInDOM() {
    const cardsStream = document.querySelector('.cards-stream');
    if (!cardsStream) return;

    const cards = Array.from(cardsStream.querySelectorAll('.news-card'));
    if (cards.length === 0) return;

    cards.sort((a, b) => {
        const dateA = a.getAttribute('data-date') || '';
        const dateB = b.getAttribute('data-date') || '';
        if (currentTimeSort === 'desc') {
            return dateB.localeCompare(dateA);
        } else {
            return dateA.localeCompare(dateB);
        }
    });

    cards.forEach(card => {
        cardsStream.appendChild(card);
    });
}

function applyFiltersAndPagination() {
    const cardsStream = document.querySelector('.cards-stream');
    if (!cardsStream) return;

    const cards = cardsStream.querySelectorAll('.news-card');
    let matchingCount = 0;

    cards.forEach(card => {
        const cardSource = card.getAttribute('data-source') || '';
        const cardCategory = card.getAttribute('data-category') || '';
        const isIlgili = card.getAttribute('data-ilgili') === 'true';
        const ilgiKategorisi = card.getAttribute('data-ilgi-kategorisi') || '';
        const titleEl = card.querySelector('.card-title');
        const cardTitle = titleEl ? titleEl.innerText.toLowerCase() : '';

        let matchesTab = true;
        if (activeViewTab === 'az') {
            if (!isIlgili) {
                matchesTab = false;
            } else if (activeAzSubcategory !== 'all') {
                if (ilgiKategorisi.toLowerCase() !== activeAzSubcategory.toLowerCase() &&
                    !ilgiKategorisi.toLowerCase().includes(activeAzSubcategory.toLowerCase())) {
                    matchesTab = false;
                }
            }
        }

        let matchesSource = false;
        if (activeSourceFilter === 'all') {
            matchesSource = true;
        } else if (activeSourceFilter === 'other') {
            matchesSource = (card.getAttribute('data-is-other') === 'true') ||
                (cardCategory === 'Diğer / Sınıflandırılmamış');
        } else {
            matchesSource = (cardSource === activeSourceFilter);
        }

        let matchesFilter = matchesTab && matchesSource;
        if (matchesFilter && currentSearchQuery) {
            const ok = cardTitle.includes(currentSearchQuery) ||
                cardSource.toLowerCase().includes(currentSearchQuery) ||
                ilgiKategorisi.toLowerCase().includes(currentSearchQuery);
            if (!ok) matchesFilter = false;
        }

        if (matchesFilter) {
            matchingCount++;
            const showCard = (matchingCount <= displayLimit);

            if (showCard) {
                card.style.display = 'flex';
            } else {
                card.style.display = 'none';
            }
        } else {
            card.style.display = 'none';
        }
    });

    const visibleTotal = document.getElementById('visible-total');
    if (visibleTotal) visibleTotal.innerText = matchingCount;

    const hasMore = (matchingCount > displayLimit);
    const container = document.querySelector('.news-feed-column');
    let loadMoreBtn = container.querySelector('.load-more-btn');

    if (hasMore) {
        if (!loadMoreBtn) {
            loadMoreBtn = document.createElement('button');
            loadMoreBtn.className = 'load-more-btn';
            const isAz = document.documentElement.lang === 'az';
            loadMoreBtn.innerText = isAz ? 'Daha Çox Göstər' : 'Daha Fazla Göster';
            loadMoreBtn.onclick = () => {
                displayLimit += 25;
                applyFiltersAndPagination();
            };
            container.appendChild(loadMoreBtn);
        }
        loadMoreBtn.style.display = 'block';
    } else if (loadMoreBtn) {
        loadMoreBtn.style.display = 'none';
    }
}

async function triggerRefresh() {
    const btn = document.getElementById("refreshBtn");
    const btnText = document.getElementById("refreshBtnText");
    const statusBanner = document.getElementById("statusBanner");

    try {
        btn.disabled = true;
        btnText.innerText = "Taranıyor...";

        const response = await fetch("/api/refresh", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        });

        const data = await response.json();
        
        if (data.status === "started" || data.status === "already_running") {
            statusBanner.classList.add("active");
            startStatusPolling();
        } else {
            alert(data.message || "Hata oluştu.");
            btn.disabled = false;
            btnText.innerText = "Yeniden Tara";
        }
    } catch (err) {
        console.error("Refresh error:", err);
        alert("Bağlantı hatası oluştu.");
        btn.disabled = false;
    }
}

function startStatusPolling() {
    if (isPolling) return;
    isPolling = true;

    const interval = setInterval(async () => {
        try {
            const res = await fetch("/api/status");
            const status = await res.json();

            if (!status.is_running) {
                clearInterval(interval);
                isPolling = false;
                
                const btn = document.getElementById("refreshBtn");
                const statusBanner = document.getElementById("statusBanner");

                if (btn) btn.disabled = false;
                if (statusBanner) statusBanner.classList.remove("active");

                window.location.reload();
            }
        } catch (e) {
            console.error("Polling status error:", e);
        }
    }, 2500);
}

document.addEventListener("DOMContentLoaded", () => {
    const statusBanner = document.getElementById("statusBanner");
    if (statusBanner && statusBanner.classList.contains("active")) {
        const btn = document.getElementById("refreshBtn");
        if (btn) btn.disabled = true;
        startStatusPolling();
    }

    // Initialize pagination limits and time sorting
    sortCardsInDOM();
    applyFiltersAndPagination();
});
