let dashboardData = [];
let monthlyData = {};
let weeklyData = {};
let selectedWeek = "";
let currentType = "전체";
let currentTableTab = "전체";
let monthlyChart = null;
let selectedMonthlyType = "전체";
let map = null;
let mapMarkers = [];
let gaugeChart = null;
let barChart = null;
let guidelinesCache = null;
let avgCurrentGlobal = 0;

document.addEventListener('DOMContentLoaded', () => {
    // API Key input load
    const savedKey = sessionStorage.getItem('gemini_api_key') || localStorage.getItem('gemini_api_key') || '';
    const apiKeyInput = document.getElementById('geminiApiKey');
    if (apiKeyInput && savedKey) {
        apiKeyInput.value = savedKey;
    }

    initMap();
    fetchData();
});

function initMap() {
    // 대한민국 중심 좌표 설정
    map = L.map('map').setView([36.3, 127.8], 7);
    
    // VWorld Base 지도 타일 로드 (라이트 스타일)
    L.tileLayer('https://api.vworld.kr/req/wmts/1.0.0/CEB52025-E065-364C-9DBA-44880E3B02B8/Base/{z}/{y}/{x}.png', {
        attribution: '&copy; <a href="http://map.vworld.kr" target="_blank">Vworld Map</a>',
        maxZoom: 19
    }).addTo(map);
}

// 데이터 수집 API 연동 (유수율 모니터링 - 정적 JSON 파일 로드)
// window.__DASHBOARD_DATA__ 가 존재하면 저장된 스냅샷 HTML에서 실행 중인 것으로 판단하여 내장 데이터를 우선 사용
async function fetchData() {
    try {
        let resJson;
        if (window.__DASHBOARD_DATA__) {
            // 스탠드얼론 저장 HTML: 내장 데이터 직접 사용
            resJson = window.__DASHBOARD_DATA__;
            console.log("📦 내장 스냅샷 데이터로 대시보드를 로드합니다.");
        } else {
            const response = await fetch('data.json');
            resJson = await response.json();
        }
        
        if (resJson.error) {
            console.error(resJson.error);
            return;
        }

        weeklyData = resJson.weekly || {};
        monthlyData = resJson.monthly || {};
        selectedWeek = resJson.latest_week || "";
        
        if (!selectedWeek && Object.keys(weeklyData).length > 0) {
            const keys = Object.keys(weeklyData);
            selectedWeek = keys[keys.length - 1];
        }
        
        dashboardData = weeklyData[selectedWeek] ? weeklyData[selectedWeek].sites : [];

        // 주차 선택 드롭다운 구축
        initWeekSelector();

        // 초기 화면은 '전체' 데이터로 렌더링
        updateKPIs(dashboardData);
        initGaugeChart(avgCurrentGlobal);
        initBarChart('전체');
        populateMap(dashboardData);
        populateRiskList(dashboardData);
        populateTable(dashboardData);

    } catch (error) {
        console.error("데이터 연동 실패:", error);
    }
}

// 용역별 탭 전환 및 동적 필터링 처리
function switchTypeTab(type, tabElement) {
    currentType = type;
    currentTableTab = "전체";
    
    // Reset table subtabs
    const tableSubtabs = document.querySelectorAll('.table-subtabs .table-subtab-btn');
    tableSubtabs.forEach(btn => {
        if (btn.textContent.includes('전체')) btn.classList.add('active');
        else btn.classList.remove('active');
    });
    
    // 1. 활성 탭 스타일 제어
    const tabButtons = document.querySelectorAll('.tabs-container .tab-btn');
    tabButtons.forEach(btn => {
        btn.classList.remove('active');
    });
    tabElement.classList.add('active');

    // 2. 탭 컨텐츠 보이기/숨기기
    document.getElementById('kpi-tab').classList.add('active');
    document.getElementById('monthly-tab').classList.remove('active');

    // 3. 데이터 필터링
    let filteredData = [];
    if (type === '전체') {
        filteredData = dashboardData;
    } else {
        filteredData = dashboardData.filter(site => site.type === type);
    }

    // 4. UI 컴포넌트 갱신
    updateKPIs(filteredData);
    initGaugeChart(avgCurrentGlobal);
    initBarChart(type);
    populateMap(filteredData);
    populateRiskList(filteredData);
    populateTable(filteredData);
    
    // 상세 보기 패널 닫기 (새로운 필터이므로)
    document.getElementById('site-detail-panel').style.display = 'none';

    // 5. 지도 크기 갱신 (지도가 깨지는 현상 방지)
    if (map) {
        setTimeout(() => {
            map.invalidateSize();
        }, 100);
    }
}

// 상세 테이블 서브 탭 필터링 전환 함수
function switchTableTab(tabType, tabElement) {
    currentTableTab = tabType;
    
    const buttons = document.querySelectorAll('.table-subtabs .table-subtab-btn');
    buttons.forEach(btn => btn.classList.remove('active'));
    tabElement.classList.add('active');
    
    let filteredData = [];
    if (currentType === '전체') {
        filteredData = dashboardData;
    } else {
        filteredData = dashboardData.filter(site => site.type === currentType);
    }
    populateTable(filteredData);
}

function updateKPIs(data) {
    let sumCurrent = 0;
    let sumAchieve = 0;
    let validSites = data.length;
    let atRiskCount = 0;

    data.forEach(d => {
        if (currentType === '블록관리') {
            sumCurrent += (d.blockProgress || 0);
            sumAchieve += (d.blockAchieveRate || 0);
            if (d.status === 'danger' || d.status === 'warning') atRiskCount++;
        } else {
            sumCurrent += d.current;
            if (d.status === 'danger') atRiskCount++;
        }
    });

    avgCurrentGlobal = validSites > 0 ? (sumCurrent / validSites).toFixed(1) : 0;
    let avgAchieveGlobal = validSites > 0 ? (sumAchieve / validSites).toFixed(1) : 0;
    
    document.getElementById('kpi-sites').innerHTML = `${validSites}<span class="unit">개소</span>`;
    
    const avgNrwCard = document.getElementById('avg-nrw').parentNode;
    const avgNrwTitle = avgNrwCard.querySelector('h3');
    const riskCard = document.getElementById('kpi-risks').parentNode;
    const riskDesc = riskCard.querySelector('.alert-desc');
    
    if (currentType === '블록관리') {
        if (avgNrwTitle) avgNrwTitle.textContent = '평균 블록 구축률 (달성률)';
        document.getElementById('avg-nrw').innerHTML = `${avgCurrentGlobal}<span class="unit">%</span> <span style="font-size: 1.1rem; color: #10b981; font-weight: 600;">(${avgAchieveGlobal}%)</span>`;
        if (riskDesc) riskDesc.textContent = '미달성 소블록 / 기간 촉박 현장';
    } else {
        if (avgNrwTitle) avgNrwTitle.textContent = '전체 평균 누적 유수율';
        document.getElementById('avg-nrw').innerHTML = `${avgCurrentGlobal}<span class="unit">%</span>`;
        if (riskDesc) riskDesc.textContent = '목표대비 3% 이상 미달';
    }
    
    document.getElementById('kpi-risks').innerHTML = `${atRiskCount}<span class="unit">개소</span>`;
}

function populateMap(data) {
    if (!map) return;

    // 기존 지도 마커 일괄 제거
    mapMarkers.forEach(marker => {
        map.removeLayer(marker);
    });
    mapMarkers = [];

    data.forEach(site => {
        let color = '#10b981'; // green
        if (site.status === 'danger') color = '#ef4444'; // red
        else if (site.status === 'warning') color = '#f59e0b'; // yellow
        
        const circle = L.circleMarker(site.coords, {
            color: color,
            fillColor: color,
            fillOpacity: 0.7,
            radius: 9,
            weight: 2
        }).addTo(map);

        let popupContent = "";
        if (site.type === '블록관리') {
            let remDaysText = site.remDays >= 0 ? `${site.remDays}일` : "정보 없음";
            popupContent = `
                <div style="font-family: 'Outfit', sans-serif; padding: 5px;">
                    <h4 style="margin: 0 0 5px 0; color: #2563eb; font-size: 1.1rem;">${site.name}</h4>
                    <p style="margin: 3px 0; font-size: 0.85rem; color:#475569"><b>사업구분:</b> ${site.type}</p>
                    <p style="margin: 3px 0; font-size: 0.85rem; color:#475569"><b>목표 소블록 수:</b> ${site.blockTotal}개</p>
                    <p style="margin: 3px 0; font-size: 0.85rem; color:#475569"><b>구축 완료 수:</b> <span style="color: #3b82f6; font-weight: bold;">${site.blockDone}개 (${site.blockProgress || 0}%)</span></p>
                    <p style="margin: 3px 0; font-size: 0.85rem; color:#475569"><b>유수율 달성 수:</b> <span style="color: #10b981; font-weight: bold;">${site.blockAchieved}개 (${site.blockAchieveRate || 0}%)</span></p>
                    <p style="margin: 3px 0; font-size: 0.85rem; color:#475569"><b>성과판정 잔여일:</b> <span style="color: #f59e0b; font-weight: bold;">${remDaysText}</span></p>
                    <p style="margin: 3px 0; font-size: 0.85rem; color:#475569"><b>미달 수량:</b> ${site.gap > 0 ? '<span style="color: #ef4444; font-weight: bold;">▼ ' + site.gap + '개 미달</span>' : '<span style="color: #10b981; font-weight: bold;">정상 달성</span>'}</p>
                </div>
            `;
        } else {
            popupContent = `
                <div style="font-family: 'Outfit', sans-serif; padding: 5px;">
                    <h4 style="margin: 0 0 5px 0; color: #2563eb; font-size: 1.1rem;">${site.name}</h4>
                    <p style="margin: 3px 0; font-size: 0.85rem; color:#475569"><b>사업구분:</b> ${site.type}</p>
                    <p style="margin: 3px 0; font-size: 0.85rem; color:#475569"><b>목표 유수율:</b> ${site.target}%</p>
                    <p style="margin: 3px 0; font-size: 0.85rem; color:#475569"><b>현재 유수율:</b> <span style="color: ${color}; font-weight: bold;">${site.current}%</span></p>
                    <p style="margin: 3px 0; font-size: 0.85rem; color:#475569"><b>미달 정도:</b> ${site.gap > 0 ? '▼ ' + site.gap.toFixed(1) + '%p 미달' : '▲ ' + Math.abs(site.gap).toFixed(1) + '%p 초과달성'}</p>
                </div>
            `;
        }

        circle.bindPopup(popupContent);
        mapMarkers.push(circle);
    });
}

function initGaugeChart(achieveVal) {
    const ctx = document.getElementById('gaugeChart').getContext('2d');
    achieveVal = parseFloat(achieveVal);
    let gapVal = 100 - achieveVal; if (gapVal < 0) gapVal = 0;

    if (gaugeChart) {
        gaugeChart.destroy();
    }

    gaugeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['달성', '미달'],
            datasets: [{
                data: [achieveVal, gapVal],
                backgroundColor: ['#3b82f6', 'rgba(59, 130, 246, 0.08)'],
                borderWidth: 0,
                cutout: '80%', 
                rotation: -90, 
                circumference: 180,
            }]
        },
        options: {
            responsive: true, 
            maintainAspectRatio: false,
            plugins: { 
                legend: { display: false }, 
                tooltip: { enabled: false } 
            }
        },
        plugins: [{
            id: 'textCenter',
            beforeDraw: function(chart) {
                var width = chart.width, height = chart.height, ctx = chart.ctx;
                ctx.restore();
                var fontSize = (height / 100).toFixed(2);
                ctx.font = "bold " + fontSize + "em Outfit";
                ctx.textBaseline = "middle"; 
                ctx.fillStyle = "#1e293b";
                var text = achieveVal + "%",
                    textX = Math.round((width - ctx.measureText(text).width) / 2),
                    textY = height / 1.35;
                ctx.fillText(text, textX, textY);
                ctx.save();
            }
        }]
    });
}

function initBarChart(type) {
    const ctx = document.getElementById('barChart').getContext('2d');
    
    if (barChart) {
        barChart.destroy();
    }

    const mData = monthlyData[type] || { labels: [], avg_nrw: [], avg_target: [], avg_achieve: [] };

    let targetLabel = '목표 유수율 (%)';
    let currentLabel = '실적 유수율 (%)';
    if (type === '블록관리') {
        targetLabel = '목표 구축률 (%)';
        currentLabel = '실적 구축률 (%)';
    }

    const datasets = [
        {
            label: targetLabel,
            data: mData.avg_target,
            borderColor: '#93c5fd', // Light pastel blue
            borderWidth: 2,
            borderDash: [5, 5], // Dashed line for target
            fill: false,
            tension: 0.4,
            pointBackgroundColor: '#93c5fd',
            pointBorderColor: '#fff',
            pointRadius: 4
        },
        {
            label: currentLabel,
            data: mData.avg_nrw,
            borderColor: '#3b82f6', // Medium blue
            backgroundColor: 'rgba(59, 130, 246, 0.05)',
            borderWidth: 2.5,
            fill: true,
            tension: 0.4,
            pointBackgroundColor: '#2563eb',
            pointBorderColor: '#fff',
            pointRadius: 4
        }
    ];

    if (type === '블록관리' && mData.avg_achieve) {
        datasets.push({
            label: '실적 달성률 (%)',
            data: mData.avg_achieve,
            borderColor: '#10b981', // Green
            backgroundColor: 'rgba(16, 185, 129, 0.05)',
            borderWidth: 2.5,
            fill: true,
            tension: 0.4,
            pointBackgroundColor: '#059669',
            pointBorderColor: '#fff',
            pointRadius: 4
        });
    }

    barChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: mData.labels,
            datasets: datasets
        },
        options: {
            responsive: true, 
            maintainAspectRatio: false,
            plugins: { 
                legend: { 
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#475569',
                        font: {
                            family: 'Outfit',
                            size: 11
                        }
                    }
                } 
            },
            scales: {
                y: { 
                    min: type === '블록관리' ? 0 : 60, 
                    max: 100,
                    grid: { color: 'rgba(59, 130, 246, 0.05)' },
                    ticks: { color: '#475569' }
                },
                x: {
                    grid: { color: 'rgba(59, 130, 246, 0.05)' },
                    ticks: { color: '#475569' }
                }
            }
        }
    });
}

function populateRiskList(data) {
    const riskList = document.getElementById('risk-list');
    riskList.innerHTML = '';
    
    // Filter danger & warning
    const atRisk = data.filter(d => d.status === 'danger' || d.status === 'warning').sort((a,b) => {
        // Sort by severity (danger first, then warning)
        if (a.status === 'danger' && b.status !== 'danger') return -1;
        if (a.status !== 'danger' && b.status === 'danger') return 1;
        // Then sort by gap descending
        return b.gap - a.gap;
    });
    
    if (atRisk.length === 0) {
        riskList.innerHTML = '<li class="risk-item" style="border-left-color: #10b981"><span class="risk-name">🚨 집중 위험 현장이 없습니다.</span></li>';
        return;
    }
    atRisk.forEach(site => {
        const li = document.createElement('li');
        li.className = 'risk-item';
        
        // Apply border color based on status
        if (site.status === 'danger') {
            li.style.borderLeft = '4px solid #ef4444'; // Red for danger
        } else {
            li.style.borderLeft = '4px solid #f59e0b'; // Yellow for warning
        }
        
        const statusLabel = site.status === 'danger' ? ' [경고]' : ' [집중관리]';
        
        if (site.type === '블록관리') {
            li.innerHTML = `<span class="risk-name">${site.name}${statusLabel}</span><span class="risk-value">▼ ${site.gap}개 미달</span>`;
        } else {
            li.innerHTML = `<span class="risk-name">${site.name}${statusLabel}</span><span class="risk-value">▼ ${site.gap.toFixed(1)}%p 미달</span>`;
        }
        riskList.appendChild(li);
    });
}

function populateTable(data) {
    const tbody = document.querySelector('#dataTable tbody');
    tbody.innerHTML = '';
    
    // Dynamically update table headers based on currentType
    const tableHeaderTarget = document.querySelector('#dataTable thead th:nth-child(5)');
    const tableHeaderCurrent = document.querySelector('#dataTable thead th:nth-child(6)');
    const tableHeaderGap = document.querySelector('#dataTable thead th:nth-child(7)');
    
    if (currentType === '블록관리') {
        if (tableHeaderTarget) tableHeaderTarget.textContent = '목표 소블록 수';
        if (tableHeaderCurrent) tableHeaderCurrent.textContent = '구축 완료(달성) 수';
        if (tableHeaderGap) tableHeaderGap.textContent = '잔여일 / 미달량';
    } else {
        if (tableHeaderTarget) tableHeaderTarget.textContent = '목표 유수율';
        if (tableHeaderCurrent) tableHeaderCurrent.textContent = '누적 유수율';
        if (tableHeaderGap) tableHeaderGap.textContent = '미달률';
    }
    
    // 서브 탭 필터링 적용 (전체 / 대상 / 외)
    let filtered = data;
    if (currentTableTab === '대상') {
        filtered = data.filter(site => site.judgment === '대상' || site.judgment === '전체');
    } else if (currentTableTab === '외') {
        filtered = data.filter(site => site.judgment === '외');
    }
    
    filtered.forEach(site => {
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.setAttribute('data-site-name', site.name);
        tr.addEventListener('click', () => showSiteDetail(site.name, tr));

        let badgeClass = 'status-success';
        let statusText = '정상';
        if (site.status === 'danger') { badgeClass = 'status-danger'; statusText = '경고'; }
        else if (site.status === 'warning') { badgeClass = 'status-warning'; statusText = '집중관리'; }

        // 성과판정 대상/외에 따른 기간 및 성과판정일 분기 처리
        let dateRange = '-';
        let targetDate = '-';
        
        if (site.judgment === '외') {
            dateRange = (site.startDate && site.endDate && site.startDate !== '-' && site.endDate !== '-') 
                ? `${site.startDate} ~ ${site.endDate}` 
                : '-';
            targetDate = '-';
        } else {
            dateRange = (site.pStartDate && site.pEndDate && site.pStartDate !== '-' && site.pEndDate !== '-') 
                ? `${site.pStartDate} ~ ${site.pEndDate}` 
                : '-';
            targetDate = (site.pEndDate && site.pEndDate !== '-') ? site.pEndDate : '-';
        }

        let targetText = `${site.target}%`;
        let currentText = `${site.current}%`;
        let gapHtml = `<span style="color: ${site.gap > 0 ? '#ef4444' : '#10b981'}; font-weight: bold;">
            ${site.gap > 0 ? '▼ ' + site.gap.toFixed(1) + '%p' : '▲ ' + Math.abs(site.gap).toFixed(1) + '%p'}
        </span>`;

        if (site.type === '블록관리') {
            targetText = `${site.blockTotal}개`;
            currentText = `${site.blockDone}개 <span style="color: #10b981; font-weight: 600;">(${site.blockAchieved}개)</span>`;
            
            let remDaysText = site.remDays >= 0 ? `${site.remDays}일` : "정보없음";
            let gapValText = site.gap > 0 ? `▼ ${site.gap}개` : "정상 달성";
            gapHtml = `<span style="font-size: 0.85rem; color: #475569;">${remDaysText}</span> / <span style="color: ${site.gap > 0 ? '#ef4444' : '#10b981'}; font-weight: bold;">${gapValText}</span>`;
        }

        tr.innerHTML = `
            <td><strong>${site.name}</strong></td>
            <td>${site.type}</td>
            <td style="font-size: 0.85rem; color: #475569;">${dateRange}</td>
            <td style="font-size: 0.85rem; color: #475569; font-weight: 500;">${targetDate}</td>
            <td>${targetText}</td>
            <td><strong>${currentText}</strong></td>
            <td>${gapHtml}</td>
            <td><span class="status-badge ${badgeClass}">${statusText}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

function showSiteDetail(siteName, trElement) {
    // 1. 테이블 행들의 selected 스타일 초기화 및 현재 행 선택
    const rows = document.querySelectorAll('#dataTable tbody tr');
    rows.forEach(r => r.style.backgroundColor = '');
    if (trElement) {
        trElement.style.backgroundColor = 'rgba(59, 130, 246, 0.08)'; // 파스텔 블루 선택 하이라이팅
    }

    // 2. 데이터 매칭
    const site = dashboardData.find(d => d.name === siteName);
    if (!site) return;

    // 성과판정 대상/외에 따른 기간 및 성과판정일 분기 처리
    let dateRange = '-';
    let targetDate = '-';
    
    if (site.judgment === '외') {
        dateRange = (site.startDate && site.endDate && site.startDate !== '-' && site.endDate !== '-') 
            ? `${site.startDate} ~ ${site.endDate}` 
            : '-';
        targetDate = '-';
    } else {
        dateRange = (site.pStartDate && site.pEndDate && site.pStartDate !== '-' && site.pEndDate !== '-') 
            ? `${site.pStartDate} ~ ${site.pEndDate}` 
            : '-';
        targetDate = (site.pEndDate && site.pEndDate !== '-') ? site.pEndDate : '-';
    }

    // 3. 패널 값 갱신
    document.getElementById('detail-site-name').textContent = site.name;
    document.getElementById('detail-duration').textContent = dateRange;
    document.getElementById('detail-target-date').textContent = targetDate;
    document.getElementById('detail-type').textContent = site.type;
    
    document.getElementById('detail-remarks').textContent = site.remarks || '특이사항이 없습니다.';
    document.getElementById('detail-direction').textContent = site.direction || '개선 조치 사항이 없습니다.';

    // WBS 정보 바인딩
    const wbsCard = document.getElementById('detail-wbs-card');
    if (wbsCard) {
        if (site.wbsPhase || site.progress !== undefined) {
            wbsCard.style.display = 'block';
            document.getElementById('detail-wbs-phase').textContent = site.wbsPhase || '1.1 착수 및 자료수집';
            
            const progressVal = site.progress !== undefined ? site.progress : 10;
            document.getElementById('detail-wbs-progress-text').textContent = `${progressVal}%`;
            document.getElementById('detail-wbs-progress-bar').style.width = `${progressVal}%`;
            
            const specificContainer = document.getElementById('detail-wbs-specific-container');
            if (specificContainer) {
                if (site.type === '블록관리') {
                    specificContainer.style.display = 'block';
                    specificContainer.innerHTML = `
                        <div style="margin-bottom: 0.8rem;">
                            <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:0.4rem;">
                                <span style="font-weight:600; color:#475569;">📦 소블록 구축률 (${site.blockDone || 0}/${site.blockTotal || 0}개)</span>
                                <span style="font-weight:700; color:#3b82f6;">${site.blockProgress || 0}%</span>
                            </div>
                            <div class="progress-bar-bg" style="height: 8px; background: rgba(59,130,246,0.1); border-radius: 4px; overflow: hidden;">
                                <div class="progress-bar-fill blue" style="width: ${site.blockProgress || 0}%; height: 100%; background: #3b82f6;"></div>
                            </div>
                        </div>
                        <div>
                            <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:0.4rem;">
                                <span style="font-weight:600; color:#475569;">🏆 유수율 달성률 (${site.blockAchieved || 0}/${site.blockTotal || 0}개)</span>
                                <span style="font-weight:700; color:#10b981;">${site.blockAchieveRate || 0}%</span>
                            </div>
                            <div class="progress-bar-bg" style="height: 8px; background: rgba(16,185,129,0.1); border-radius: 4px; overflow: hidden;">
                                <div class="progress-bar-fill green" style="width: ${site.blockAchieveRate || 0}%; height: 100%; background: #10b981;"></div>
                            </div>
                        </div>
                        <div style="margin-top: 0.8rem; font-size: 0.85rem; color: #475569;">
                            <strong>📅 성과판정 잔여일:</strong> ${site.remDays >= 0 ? site.remDays + '일 남음' : '정보 없음'}
                        </div>
                    `;
                } else if (site.type === '누수탐사') {
                    specificContainer.style.display = 'block';
                    specificContainer.innerHTML = `
                        <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:0.4rem;">
                            <span style="font-weight:600; color:#475569;">🔍 누수탐사 진행률 (${site.leakDone || 0}/${site.leakTarget || 0}km)</span>
                            <span style="font-weight:700; color:#8b5cf6;">${site.leakProgress || 0}%</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill purple" style="width: ${site.leakProgress || 0}%"></div>
                        </div>
                    `;
                } else {
                    if (site.blockTotal && site.blockTotal > 1) {
                        specificContainer.style.display = 'block';
                        specificContainer.innerHTML = `
                            <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:0.4rem;">
                                <span style="font-weight:600; color:#475569;">📦 소블록 구축률 (${site.blockDone || 0}/${site.blockTotal || 0}개)</span>
                                <span style="font-weight:700; color:#10b981;">${site.blockProgress || 0}%</span>
                            </div>
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill green" style="width: ${site.blockProgress || 0}%"></div>
                            </div>
                        `;
                    } else if (site.leakTarget && site.leakTarget > 0) {
                        specificContainer.style.display = 'block';
                        specificContainer.innerHTML = `
                            <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:0.4rem;">
                                <span style="font-weight:600; color:#475569;">🔍 누수탐사 진행률 (${site.leakDone || 0}/${site.leakTarget || 0}km)</span>
                                <span style="font-weight:700; color:#8b5cf6;">${site.leakProgress || 0}%</span>
                            </div>
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill purple" style="width: ${site.leakProgress || 0}%"></div>
                            </div>
                        `;
                    } else {
                        specificContainer.style.display = 'block';
                        specificContainer.innerHTML = `
                            <div style="font-size:0.85rem; color:#64748b; font-style:italic; padding-top: 1rem;">
                                해당 사업 유형은 별도의 세부 공정 지표가 지정되지 않았습니다.
                            </div>
                        `;
                    }
                }
            }
        } else {
            wbsCard.style.display = 'none';
        }
    }

    // 4. 패널 표시
    const panel = document.getElementById('site-detail-panel');
    panel.style.display = 'block';
    
    // 5. 패널 위치로 부드럽게 스크롤
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// 챗 사이드바 여닫기
function toggleChatSidebar(forceOpen = false) {
    const sidebar = document.getElementById('chatSidebar');
    if (forceOpen) {
        sidebar.classList.add('open');
    } else {
        sidebar.classList.toggle('open');
    }
}

// 챗 키프레스
function handleChatKeypress(event) {
    if (event.key === 'Enter') {
        sendChatMessage();
    }
}

// guidelines_cache.json 비동기 로드 함수
async function loadGuidelines() {
    if (guidelinesCache) return guidelinesCache;
    try {
        const response = await fetch('guidelines_cache.json');
        if (!response.ok) {
            throw new Error(`HTTP status ${response.status}`);
        }
        guidelinesCache = await response.json();
        console.log("RAG 지침서 문서 캐시 로드 성공:", guidelinesCache.chunks.length, "Chunks");
        return guidelinesCache;
    } catch (e) {
        console.error("지침서 캐시 로드 실패:", e);
        return null;
    }
}

// 로컬 키워드 검색기 (JS 포팅 버전)
function searchGuidelinesLocal(query, chunks, topK = 4) {
    const keywords = query.toLowerCase().match(/[가-힣a-zA-Z0-9]+/g) || [];
    if (keywords.length === 0) return [];
    
    const scored = [];
    chunks.forEach(chunk => {
        let score = 0;
        const textLower = chunk.text.toLowerCase();
        
        keywords.forEach(kw => {
            if (textLower.includes(kw)) {
                // 키워드 출현 횟수만큼 점수 부여
                const count = (textLower.split(kw).length - 1);
                score += count * 5;
                
                // 완전 단어 경계 매칭 시 가산점
                const idx = textLower.indexOf(kw);
                if (idx !== -1) {
                    const isStart = idx === 0 || !/[가-힣a-zA-Z0-9]/.test(textLower[idx - 1]);
                    const isEnd = (idx + kw.length === textLower.length) || !/[가-힣a-zA-Z0-9]/.test(textLower[idx + kw.length]);
                    if (isStart && isEnd) {
                        score += 10;
                    }
                }
            }
        });
        
        if (score > 0) {
            scored.push({ score, chunk });
        }
    });
    
    // 점수 높은 순 정렬 후 상위 topK개 반환
    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, topK).map(s => s.chunk);
}

// 브라우저 직접 Gemini API 호출
async function callGeminiAPI(promptText, apiKey) {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`;
    const maxRetries = 3;
    let delay = 1000; // 1초 대기부터 시작

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    contents: [
                        {
                            parts: [
                                {
                                    text: promptText
                                }
                            ]
                        }
                    ]
                })
            });
            
            // 503 (Overloaded) 또는 429 (Rate Limit)의 경우 백오프 후 재시도
            if (response.status === 503 || response.status === 429) {
                if (attempt < maxRetries) {
                    console.warn(`Gemini API returned ${response.status}. Retrying in ${delay}ms... (Attempt ${attempt}/${maxRetries})`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                    delay *= 2; // 지수 백오프
                    continue;
                }
            }

            if (!response.ok) {
                const errText = await response.text();
                if (response.status === 503) {
                    throw new Error(`Gemini API 서버가 현재 일시적인 과부하 상태(503)입니다. 잠시 후 다시 시도해 주십시오.`);
                }
                throw new Error(`Gemini API Error (Status ${response.status}): ${errText}`);
            }
            
            const data = await response.json();
            if (data.candidates && data.candidates[0] && data.candidates[0].content && data.candidates[0].content.parts[0]) {
                return data.candidates[0].content.parts[0].text;
            } else {
                throw new Error("Gemini API 응답에서 텍스트를 찾을 수 없습니다.");
            }
        } catch (error) {
            if (attempt === maxRetries) {
                throw error;
            }
            console.warn(`Fetch error: ${error.message}. Retrying in ${delay}ms...`);
            await new Promise(resolve => setTimeout(resolve, delay));
            delay *= 2;
        }
    }
}

// 대시보드 데이터 요약 컨텍스트 생성 함수
function getDashboardDataContext() {
    let context = `[현재 대시보드 데이터 실시간 현황 (기준 주차: ${selectedWeek})]\n`;
    context += `- 총 관리 대상 현장 수: ${dashboardData.length}개소\n`;
    context += `- 전체 평균 실적(유수율/구축률): ${avgCurrentGlobal}%\n`;
    
    // 경고(Danger) 및 집중관리(Warning) 현장 집계
    const dangers = dashboardData.filter(d => d.status === 'danger');
    const warnings = dashboardData.filter(d => d.status === 'warning');
    context += `- 경고 현장: ${dangers.length}개소, 집중관리 현장: ${warnings.length}개소\n\n`;
    
    context += `[현장별 상세 실적 목록]\n`;
    dashboardData.forEach(site => {
        if (site.type === '블록관리') {
            const remText = site.remDays >= 0 ? `${site.remDays}일 남음` : '정보 없음';
            const gapText = site.gap > 0 ? `${site.gap}개 미달` : '정상 달성';
            context += `- ${site.name} (유형: ${site.type}): 목표 소블록 ${site.blockTotal}개, 구축 완료 ${site.blockDone}개, 유수율 달성 ${site.blockAchieved}개 (구축률 ${site.blockProgress}%, 달성률 ${site.blockAchieveRate}%), 성과판정 잔여일: ${remText}, 상태: ${site.status === 'danger' ? '경고' : site.status === 'warning' ? '집중관리' : '정상'} (미달량: ${gapText})\n`;
        } else {
            const gapText = site.gap > 0 ? `▼ ${site.gap.toFixed(1)}%p 미달` : `▲ ${Math.abs(site.gap).toFixed(1)}%p 초과`;
            context += `- ${site.name} (유형: ${site.type}): 목표 유수율 ${site.target}%, 현재 누적 유수율 ${site.current}%, 미달량: ${gapText}, 상태: ${site.status === 'danger' ? '경고' : site.status === 'warning' ? '집중관리' : '정상'}\n`;
        }
    });
    return context;
}

// 챗 메시지 전송 로직 (완전 클라이언트 RAG + Gemini 연동)
async function sendChatMessage() {
    const chatInput = document.getElementById('chatInput');
    const query = chatInput.value.trim();
    if (!query) return;

    chatInput.value = '';

    // 1. 유저 메시지 렌더링
    appendMessage(query, 'user');

    // 2. API Key 확인
    const apiKey = sessionStorage.getItem('gemini_api_key') || localStorage.getItem('gemini_api_key') || '';
    if (!apiKey) {
        appendMessage("⚠️ **Gemini API Key가 설정되지 않았습니다.** 대시보드 화면 우측 상단의 ⚙️ 설정 아이콘을 클릭하여 API Key를 등록해 주십시오. (입력한 API Key는 외부 서버로 유출되지 않으며 브라우저에만 안전하게 보관됩니다.)", "system-error");
        return;
    }

    // 3. 타이핑/로딩 인디케이터 표시
    const loadingId = showChatLoading();

    try {
        // 4. 로컬 지침서 데이터 로드 (최초 1회)
        const cache = await loadGuidelines();
        
        // 5. 유사 구절 검색
        let retrieved = [];
        if (cache && cache.chunks) {
            retrieved = searchGuidelinesLocal(query, cache.chunks, 4);
        }
        
        // 6. 콘텍스트 조립
        let contextStr = "";
        const sources = [];
        retrieved.forEach(c => {
            contextStr += `\n[${c.file} - ${c.page}페이지]:\n${c.text}\n`;
            const sourceInfo = `${c.file} (p.${c.page})`;
            if (!sources.includes(sourceInfo)) {
                sources.push(sourceInfo);
            }
        });
        
        // 7. 시스템 프롬프트 작성
        const prompt = `
당신은 상하수도 지침 및 설계 법규, 기술 자문을 담당하고 대시보드 데이터를 분석하는 **AI 챗봇**입니다. 
제공되는 [실시간 대시보드 현황 데이터] 및 [기술지침서 및 매뉴얼 발췌본] 자료를 통합적으로 참고하여 질문에 논리적이고 친절하게 조언하십시오.

[실시간 대시보드 현황 데이터]:
${getDashboardDataContext()}

[답변 가이드라인]:
1. 전문 기술 자문관답게 논리적이고 차분한 신뢰감을 주도록 기술 기준 및 대시보드 통계 수치에 기반해 답변합니다.
2. 사용자가 대시보드 현황에 대해 묻는 경우 [실시간 대시보드 현황 데이터]의 수치(목표, 실적, 미달량, 상태 등)를 인용하여 명확히 요약해주십시오.
3. 질문에 구체적인 설계 기준, 절차, 노하우(예: 차단 순서, MNF 분석법, 밸브 세팅 등)가 있다면 본문 근거를 최대한 보강해서 설명하십시오.
4. 답변 마지막에는 반드시 참고한 파일들과 페이지 정보(출처)를 명확히 나열하십시오. (단, 대시보드 데이터만으로 답변한 경우 "대시보드 실시간 현황 자료 참고"로 표기)
5. 만약 아래 제공된 지침서 발췌본에 직접적인 언급이 없다면, 억지로 답변을 꾸며내지 말고 "자료실 문서에 해당 구절이 없으나 상하수도 일반설계기준(KDS) 및 현장 노하우를 바탕으로 자문하자면..." 형태로 솔직하면서도 깊이 있게 조언하십시오.

[기술지침서 및 매뉴얼 발췌본]:
${contextStr ? contextStr : "(일치하는 로컬 지침서 데이터가 검색되지 않았습니다. 일반 지식을 토대로 자문해 드립니다.)"}

[질문]:
${query}
`;

        // 8. Gemini API 호출
        const responseText = await callGeminiAPI(prompt, apiKey);
        
        removeChatLoading(loadingId);

        // 9. 출처 정보 조립 후 출력
        let sourceSuffix = "";
        if (sources.length > 0) {
            sourceSuffix = "\n\n---\n**📚 참고 지침 문서 출처:**\n" + sources.map(s => `- ${s}`).join("\n");
        }
        
        appendMessage(responseText + sourceSuffix, 'assistant');

    } catch (error) {
        removeChatLoading(loadingId);
        appendMessage(`❌ 오류가 발생했습니다: ${error.message}`, "system-error");
    }
}

// 챗 메시지 추가
function appendMessage(text, sender) {
    const chatMessages = document.getElementById('chatMessages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    
    if (sender === 'assistant') {
        msgDiv.innerHTML = parseMarkdown(text);
    } else {
        msgDiv.textContent = text;
    }
    
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 간단한 자체 Markdown 파서
function parseMarkdown(text) {
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Bold: **text**
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Headings
    html = html.replace(/^### (.*?)$/gm, "<h3>$1</h3>");
    html = html.replace(/^## (.*?)$/gm, "<h2>$1</h2>");
    html = html.replace(/^# (.*?)$/gm, "<h1>$1</h1>");

    // Bullet List
    html = html.replace(/^- (.*?)$/gm, "<li>$1</li>");
    
    // Code blocks
    html = html.replace(/```([\s\S]*?)```/g, "<pre style='background: rgba(0,0,0,0.05); border: 1px solid rgba(59,130,246,0.15); padding: 0.8rem; border-radius: 6px; overflow-x:auto; margin: 0.5rem 0; font-family: monospace; font-size: 0.85rem; color:#1e293b;'><code>$1</code></pre>");

    // Newlines
    html = html.replace(/\n/g, "<br>");

    return html;
}

// 로딩 애니메이션 표시
function showChatLoading() {
    const chatMessages = document.getElementById('chatMessages');
    const loadingDiv = document.createElement('div');
    const id = 'loading_' + Date.now();
    loadingDiv.id = id;
    loadingDiv.className = 'chat-loading';
    loadingDiv.innerHTML = `
        <span>AI 챗봇 분석 중</span>
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
    `;
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return id;
}

// 로딩 애니메이션 제거
function removeChatLoading(id) {
    const loadingDiv = document.getElementById(id);
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

// 설정 모달 켜고 끄기
function toggleSettingsModal() {
    const modal = document.getElementById('settingsModal');
    modal.classList.toggle('open');
}

// 설정 저장
function saveSettings() {
    const apiKey = document.getElementById('geminiApiKey').value.trim();
    if (!apiKey) {
        alert("⚠️ API Key를 바르게 입력해 주십시오.");
        return;
    }

    sessionStorage.setItem('gemini_api_key', apiKey);
    localStorage.setItem('gemini_api_key', apiKey); // 세션이 닫혀도 유지될 수 있도록 복수 저장

    alert("💾 Gemini API Key가 성공적으로 브라우저에 임시 저장되었습니다.");
    toggleSettingsModal();
}

// ─────────────────────────────────────────────────────────────────────────────
// 대시보드 저장: 현재 대시보드 전체를 독립 실행형 HTML 파일로 저장
// 저장된 HTML은 별도 서버 없이 브라우저에서 바로 열람 가능하며, 현장 데이터가 내장됨
// ─────────────────────────────────────────────────────────────────────────────
async function saveDashboardAsHTML() {
    const btn = document.querySelector('.export-btn');
    const originalText = btn ? btn.textContent : '';
    if (btn) { btn.textContent = '저장 중... ⏳'; btn.disabled = true; }

    try {
        // 1. CSS 및 JS 파일 내용을 비동기로 가져오기
        const [cssRes, jsRes] = await Promise.all([
            fetch('style.css'),
            fetch('app.js')
        ]);
        const cssText = await cssRes.text();
        const jsText = await jsRes.text();

        // 2. 현재 대시보드 데이터를 JSON으로 직렬화
        const embeddedPayload = JSON.stringify({
            weekly: weeklyData,
            monthly: monthlyData,
            latest_week: selectedWeek
        });

        // 3. 현재 페이지 HTML 전체 가져오기
        let html = '<!DOCTYPE html>\n' + document.documentElement.outerHTML;

        // 4. style.css 링크를 인라인 <style> 태그로 교체
        html = html.replace(
            '<link rel="stylesheet" href="style.css">',
            `<style>\n${cssText}\n</style>`
        );

        // 5. app.js를 인라인 <script>로 교체 (데이터 내장 선언 먼저)
        const inlineJS = `// ── 내장 스냅샷 데이터 (저장 시각: ${new Date().toLocaleString('ko-KR')}) ──\nwindow.__DASHBOARD_DATA__ = ${embeddedPayload};\n\n${jsText}`;
        html = html.replace(
            '<script src="app.js"></script>',
            `<script>\n${inlineJS}\n</script>`
        );

        // 6. 스냅샷 생성 시각 배너를 <body> 시작 직후에 삽입
        const saveDateBanner = `<div style="position:fixed; top:0; left:0; right:0; z-index:99999; background:linear-gradient(90deg,#1e3a5f,#2563eb); color:#fff; font-family:'Outfit',sans-serif; font-size:0.85rem; padding:0.4rem 1.2rem; display:flex; justify-content:space-between; align-items:center;"><span>📋 저장된 대시보드 스냅샷 &nbsp;|&nbsp; 저장 일시: ${new Date().toLocaleString('ko-KR')}</span><span style="opacity:0.7; font-size:0.78rem;">이 파일은 저장 시점의 데이터를 포함한 독립 실행형 HTML입니다.</span></div>`;
        html = html.replace('<body>', `<body>${saveDateBanner}`);

        // 7. Blob URL 생성 후 다운로드 트리거
        const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
        link.download = `상수도_통합_대시보드_${selectedWeek}_${dateStr}.html`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => URL.revokeObjectURL(url), 3000);

    } catch (e) {
        console.error('대시보드 저장 실패:', e);
        alert('❌ 저장 실패: ' + e.message);
    } finally {
        if (btn) { btn.textContent = originalText; btn.disabled = false; }
    }
}

function exportData() {
    const activeTab = document.querySelector('.tabs-container .tab-btn.active');
    const activeText = activeTab ? activeTab.textContent.trim().replace(/🌍 |🏗️ |🔧 |📦 |🔍 |📊 /g, '') : '전체';
    
    // 만약 월별 실적 통계 탭이 활성화되어 있다면 월별 데이터를 추출하여 CSV로 내보내기
    if (activeText.includes('월별') || activeText.includes('통계')) {
        let csvContent = "data:text/csv;charset=utf-8,\ufeff"; // BOM for Korean Excel
        csvContent += "구분,월구분,목표(%),실적(%),실적 달성률(%, 블록관리 전용),갭(구축),갭(달성, 블록관리 전용)\n";
        
        const typeKeys = Object.keys(monthlyData);
        typeKeys.forEach(typeKey => {
            const mData = monthlyData[typeKey];
            if (mData && mData.labels) {
                mData.labels.forEach((label, idx) => {
                    const target = mData.avg_target[idx];
                    const current = mData.avg_nrw[idx];
                    const achieve = mData.avg_achieve ? mData.avg_achieve[idx] : 0;
                    
                    const diffBuild = target - current;
                    const diffAchieve = target - achieve;
                    
                    let diffBuildStr = "";
                    let diffAchieveStr = "";
                    let achieveValStr = "-";
                    
                    if (typeKey === '블록관리') {
                        diffBuildStr = diffBuild > 0 ? `-${diffBuild.toFixed(1)}%` : `+${Math.abs(diffBuild).toFixed(1)}%`;
                        diffAchieveStr = diffAchieve > 0 ? `-${diffAchieve.toFixed(1)}%` : `+${Math.abs(diffAchieve).toFixed(1)}%`;
                        achieveValStr = `${achieve.toFixed(1)}%`;
                    } else {
                        diffBuildStr = diffBuild > 0 ? `-${diffBuild.toFixed(1)}%p` : `+${Math.abs(diffBuild).toFixed(1)}%p`;
                        diffAchieveStr = "-";
                    }
                    
                    csvContent += `"${typeKey}","${label}",${target.toFixed(1)},${current.toFixed(1)},"${achieveValStr}","${diffBuildStr}","${diffAchieveStr}"\n`;
                });
            }
        });
        
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `상수도_월별_실적_통계_보고.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        return;
    }
    
    let filteredData = [];
    if (currentType === '전체') {
        filteredData = [...dashboardData];
    } else {
        filteredData = dashboardData.filter(site => site.type === currentType);
    }

    // 상세 테이블 서브 탭 필터링 적용 (전체 / 대상 / 외)
    if (currentTableTab === '대상') {
        filteredData = filteredData.filter(site => site.judgment === '대상' || site.judgment === '전체');
    } else if (currentTableTab === '외') {
        filteredData = filteredData.filter(site => site.judgment === '외');
    }

    let csvContent = "data:text/csv;charset=utf-8,\ufeff"; // BOM for Korean Excel
    if (currentType === '블록관리') {
        csvContent += "현장명,사업구분,용역기간,성과판정일,목표 소블록 수(개),구축 완료 수(개),유수율 달성 수(개),잔여기간(일),미달 수량(개),성과판정여부,상태\n";
    } else {
        csvContent += "현장명,사업구분,용역기간,성과판정일,목표(%),실적(%),미달량,성과판정여부,상태\n";
    }

    filteredData.forEach(site => {
        let targetVal = site.target;
        let currentVal = site.current;
        let gapStr = "";
        
        if (site.type === '블록관리') {
            targetVal = site.blockTotal;
            currentVal = site.blockDone;
            gapStr = site.gap > 0 ? `-${site.gap}개` : `+${Math.abs(site.gap)}개`;
        } else {
            gapStr = site.gap > 0 ? `-${site.gap.toFixed(1)}%p` : `+${Math.abs(site.gap).toFixed(1)}%p`;
        }
        
        // 성과판정 대상/외에 따른 기간 및 성과판정일 분기 처리
        let dateRange = '-';
        let targetDate = '-';
        
        if (site.judgment === '외') {
            dateRange = (site.startDate && site.endDate && site.startDate !== '-' && site.endDate !== '-') 
                ? `${site.startDate} ~ ${site.endDate}` 
                : '-';
            targetDate = '-';
        } else {
            dateRange = (site.pStartDate && site.pEndDate && site.pStartDate !== '-' && site.pEndDate !== '-') 
                ? `${site.pStartDate} ~ ${site.pEndDate}` 
                : '-';
            targetDate = (site.pEndDate && site.pEndDate !== '-') ? site.pEndDate : '-';
        }

        let statusText = '정상';
        if (site.status === 'danger') statusText = '경고';
        else if (site.status === 'warning') statusText = '집중관리';
        
        if (site.type === '블록관리') {
            let remDaysText = site.remDays >= 0 ? `${site.remDays}` : "-";
            csvContent += `"${site.name}","${site.type}","${dateRange}","${targetDate}",${targetVal},${currentVal},${site.blockAchieved || 0},"${remDaysText}","${gapStr}","${site.judgment || '-'}","${statusText}"\n`;
        } else {
            csvContent += `"${site.name}","${site.type}","${dateRange}","${targetDate}",${targetVal},${currentVal},"${gapStr}","${site.judgment || '-'}","${statusText}"\n`;
        }
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `상수도_통합성과_보고_${activeText.replace(/\s+/g, '_')}_[성과판정_${currentTableTab}].csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function initWeekSelector() {
    const select = document.getElementById('weekSelect');
    if (!select) return;
    select.innerHTML = '';
    
    const weeks = Object.keys(weeklyData);
    weeks.forEach(wk => {
        const opt = document.createElement('option');
        opt.value = wk;
        opt.textContent = wk;
        select.appendChild(opt);
    });
    
    if (selectedWeek) {
        select.value = selectedWeek;
        const dateSpan = document.getElementById('selected-week-date');
        if (dateSpan && weeklyData[selectedWeek]) {
            dateSpan.textContent = `(기준일자: ${weeklyData[selectedWeek].date})`;
        }
    }
}

function changeWeek(week) {
    selectedWeek = week;
    if (!weeklyData[week]) return;
    
    dashboardData = weeklyData[week].sites;
    currentTableTab = "전체";
    
    // Reset table subtabs
    const tableSubtabs = document.querySelectorAll('.table-subtabs .table-subtab-btn');
    tableSubtabs.forEach(btn => {
        if (btn.textContent.includes('전체')) btn.classList.add('active');
        else btn.classList.remove('active');
    });
    
    const dateSpan = document.getElementById('selected-week-date');
    if (dateSpan) {
        dateSpan.textContent = `(기준일자: ${weeklyData[week].date})`;
    }
    
    let filteredData = [];
    if (currentType === '전체') {
        filteredData = dashboardData;
    } else {
        filteredData = dashboardData.filter(site => site.type === currentType);
    }
    
    updateKPIs(filteredData);
    initGaugeChart(avgCurrentGlobal);
    initBarChart(currentType);
    populateMap(filteredData);
    populateRiskList(filteredData);
    populateTable(filteredData);
    
    document.getElementById('site-detail-panel').style.display = 'none';
    
    if (map) {
        setTimeout(() => {
            map.invalidateSize();
        }, 100);
    }
}

function switchMonthlyTab(tabElement) {
    const tabButtons = document.querySelectorAll('.tabs-container .tab-btn');
    tabButtons.forEach(btn => {
        btn.classList.remove('active');
    });
    tabElement.classList.add('active');

    document.getElementById('kpi-tab').classList.remove('active');
    document.getElementById('monthly-tab').classList.add('active');

    initMonthlyTab();
}

function switchMonthlyType(type, element) {
    const subtabs = document.querySelectorAll('.monthly-subtabs .subtab-btn');
    subtabs.forEach(btn => btn.classList.remove('active'));
    element.classList.add('active');
    
    selectedMonthlyType = type;
    initMonthlyTab();
}

function initMonthlyTab() {
    const mData = monthlyData[selectedMonthlyType] || { labels: [], avg_nrw: [], avg_target: [], avg_achieve: [] };
    
    const lastTarget = mData.avg_target.length > 0 ? mData.avg_target[mData.avg_target.length - 1] : 0;
    const lastCurrent = mData.avg_nrw.length > 0 ? mData.avg_nrw[mData.avg_nrw.length - 1] : 0;
    const lastAchieve = (selectedMonthlyType === '블록관리' && mData.avg_achieve && mData.avg_achieve.length > 0)
        ? mData.avg_achieve[mData.avg_achieve.length - 1]
        : 0;
    
    const targetCard = document.getElementById('monthly-avg-target').parentNode;
    const targetTitle = targetCard.querySelector('h3');
    const currentCard = document.getElementById('monthly-avg-current').parentNode;
    const currentTitle = currentCard.querySelector('h3');
    const gapCard = document.getElementById('monthly-avg-gap').parentNode;
    const gapTitle = gapCard.querySelector('h3');
    
    if (selectedMonthlyType === '블록관리') {
        if (targetTitle) targetTitle.textContent = '목표 구축(달성)률';
        if (currentTitle) currentTitle.textContent = '실제 평균 구축(달성)률';
        if (gapTitle) gapTitle.textContent = '평균 갭 (구축/달성)';
        
        document.getElementById('monthly-avg-target').innerHTML = `${lastTarget.toFixed(1)}<span class="unit">%</span>`;
        document.getElementById('monthly-avg-current').innerHTML = `${lastCurrent.toFixed(1)}% <span style="font-size: 1.1rem; color: #10b981; font-weight: 600;">(${lastAchieve.toFixed(1)}%)</span>`;
        
        const gapValueEl = document.getElementById('monthly-avg-gap');
        const gapDescEl = document.getElementById('monthly-gap-desc');
        
        let diffBuild = lastTarget - lastCurrent;
        let diffAchieve = lastTarget - lastAchieve;
        
        let buildGapText = diffBuild > 0 ? `▼ ${diffBuild.toFixed(1)}%` : `▲ ${Math.abs(diffBuild).toFixed(1)}%`;
        let achieveGapText = diffAchieve > 0 ? `▼ ${diffAchieve.toFixed(1)}%` : `▲ ${Math.abs(diffAchieve).toFixed(1)}%`;
        
        gapValueEl.innerHTML = `${buildGapText} <span style="font-size: 1.1rem; color: ${diffAchieve > 0 ? '#ef4444' : '#10b981'}; font-weight: 600;">(${achieveGapText})</span>`;
        gapValueEl.className = (diffBuild > 0 || diffAchieve > 0) ? "kpi-value alert-text" : "kpi-value success-text";
        gapDescEl.textContent = "최종 월 기준 목표 대비 미달 상태입니다. (괄호안은 유수율 달성률 기준)";
        if (gapCard) {
            if (diffBuild > 0 || diffAchieve > 0) gapCard.classList.add('alert-card');
            else gapCard.classList.remove('alert-card');
        }
    } else {
        if (targetTitle) targetTitle.textContent = '월별 평균 목표 유수율';
        if (currentTitle) currentTitle.textContent = '월별 실제 평균 유수율';
        if (gapTitle) gapTitle.textContent = '평균 유수율 갭 (Gap)';
        
        document.getElementById('monthly-avg-target').innerHTML = `${lastTarget.toFixed(1)}<span class="unit">%</span>`;
        document.getElementById('monthly-avg-current').innerHTML = `${lastCurrent.toFixed(1)}<span class="unit">%</span>`;
        
        const gapVal = lastTarget - lastCurrent;
        const gapValueEl = document.getElementById('monthly-avg-gap');
        const gapDescEl = document.getElementById('monthly-gap-desc');
        
        if (gapVal > 0) {
            gapValueEl.className = "kpi-value alert-text";
            gapValueEl.innerHTML = `▼ ${gapVal.toFixed(1)}<span class="unit">%p 미달</span>`;
            gapDescEl.textContent = "최종 월 기준 목표 대비 미달 상태입니다.";
            if (gapCard) gapCard.classList.add('alert-card');
        } else {
            gapValueEl.className = "kpi-value success-text";
            gapValueEl.innerHTML = `▲ ${Math.abs(gapVal).toFixed(1)}<span class="unit">%p 초과</span>`;
            gapDescEl.textContent = "최종 월 기준 목표를 달성하였습니다.";
            if (gapCard) gapCard.classList.remove('alert-card');
        }
    }
    
    const tbody = document.querySelector('#monthlySummaryTable tbody');
    if (tbody) {
        tbody.innerHTML = '';
        
        const monthlyHeaderTarget = document.querySelector('#monthlySummaryTable thead th:nth-child(2)');
        const monthlyHeaderCurrent = document.querySelector('#monthlySummaryTable thead th:nth-child(3)');
        const monthlyHeaderGap = document.querySelector('#monthlySummaryTable thead th:nth-child(4)');
        if (selectedMonthlyType === '블록관리') {
            if (monthlyHeaderTarget) monthlyHeaderTarget.textContent = '목표 구축(달성)률';
            if (monthlyHeaderCurrent) monthlyHeaderCurrent.textContent = '실제 구축(달성)률';
            if (monthlyHeaderGap) monthlyHeaderGap.textContent = '갭 (구축/달성)';
        } else {
            if (monthlyHeaderTarget) monthlyHeaderTarget.textContent = '목표 유수율';
            if (monthlyHeaderCurrent) monthlyHeaderCurrent.textContent = '실제 유수율';
            if (monthlyHeaderGap) monthlyHeaderGap.textContent = '갭 (Gap)';
        }

        mData.labels.forEach((label, idx) => {
            const tr = document.createElement('tr');
            const target = mData.avg_target[idx];
            const current = mData.avg_nrw[idx];
            const achieve = (selectedMonthlyType === '블록관리' && mData.avg_achieve) ? mData.avg_achieve[idx] : 0;
            
            let targetText = `${target.toFixed(1)}%`;
            let currentText = `${current.toFixed(1)}%`;
            let diffText = "";
            let isAlert = false;
            
            if (selectedMonthlyType === '블록관리') {
                currentText = `${current.toFixed(1)}% (${achieve.toFixed(1)}%)`;
                const diffBuild = target - current;
                const diffAchieve = target - achieve;
                
                const buildText = diffBuild > 0 ? `▼${diffBuild.toFixed(1)}%` : `▲${Math.abs(diffBuild).toFixed(1)}%`;
                const achieveText = diffAchieve > 0 ? `▼${diffAchieve.toFixed(1)}%` : `▲${Math.abs(diffAchieve).toFixed(1)}%`;
                
                diffText = `${buildText} (${achieveText})`;
                isAlert = (diffBuild > 0 || diffAchieve > 0);
            } else {
                const diff = target - current;
                diffText = diff > 0 ? '▼ ' + diff.toFixed(1) + '%p' : '▲ ' + Math.abs(diff).toFixed(1) + '%p';
                isAlert = diff > 0;
            }
            
            tr.innerHTML = `
                <td><strong>${label}</strong></td>
                <td>${targetText}</td>
                <td><strong>${currentText}</strong></td>
                <td style="color: ${isAlert ? '#ef4444' : '#10b981'}; font-weight: bold;">
                    ${diffText}
                </td>
            `;
            tbody.appendChild(tr);
        });
        if (mData.labels.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#64748b;">데이터가 없습니다.</td></tr>';
        }
    }
    
    const ctx = document.getElementById('monthlyTrendChart').getContext('2d');
    if (monthlyChart) {
        monthlyChart.destroy();
    }
    
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.3)');
    gradient.addColorStop(1, 'rgba(59, 130, 246, 0.01)');
    
    let targetLabel = '목표 평균 유수율 (%)';
    let currentLabel = '실제 평균 유수율 (%)';
    if (selectedMonthlyType === '블록관리') {
        targetLabel = '목표 구축률 (%)';
        currentLabel = '실제 평균 구축률 (%)';
    }

    let datasets = [
        {
            label: targetLabel,
            data: mData.avg_target,
            borderColor: 'rgba(147, 197, 253, 0.8)',
            borderWidth: 2,
            borderDash: [6, 6],
            fill: false,
            tension: 0.35,
            pointBackgroundColor: '#93c5fd',
            pointBorderColor: '#fff',
            pointRadius: 5,
            pointHoverRadius: 7
        },
        {
            label: currentLabel,
            data: mData.avg_nrw,
            borderColor: '#2563eb',
            backgroundColor: gradient,
            borderWidth: 3,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: '#1d4ed8',
            pointBorderColor: '#fff',
            pointRadius: 5,
            pointHoverRadius: 7
        }
    ];

    if (selectedMonthlyType === '블록관리' && mData.avg_achieve) {
        const gradAchieve = ctx.createLinearGradient(0, 0, 0, 300);
        gradAchieve.addColorStop(0, 'rgba(16, 185, 129, 0.25)');
        gradAchieve.addColorStop(1, 'rgba(16, 185, 129, 0.01)');
        
        datasets.push({
            label: '실제 평균 달성률 (%)',
            data: mData.avg_achieve,
            borderColor: '#10b981',
            backgroundColor: gradAchieve,
            borderWidth: 3,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: '#059669',
            pointBorderColor: '#fff',
            pointRadius: 5,
            pointHoverRadius: 7
        });
    }

    monthlyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: mData.labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#334155',
                        font: {
                            family: 'Outfit',
                            size: 12,
                            weight: 'bold'
                        }
                    }
                },
                tooltip: {
                    padding: 12,
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleFont: { size: 14, weight: 'bold' },
                    bodyFont: { size: 13 },
                    cornerRadius: 8
                }
            },
            scales: {
                y: {
                    min: selectedMonthlyType === '블록관리' ? 0 : 50,
                    max: 100,
                    grid: { color: 'rgba(59, 130, 246, 0.05)' },
                    ticks: {
                        color: '#475569',
                        font: { size: 11 }
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: {
                        color: '#475569',
                        font: { size: 11, weight: 'bold' }
                    }
                }
            }
        }
    });
}


