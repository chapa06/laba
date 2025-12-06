// static/js/dashboard.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔥 IoT Dashboard запущен!');
    
    // Глобальные переменные
    let charts = {};
    let latestData = null;
    let historyData = [];
    let updateInterval;
    let isUpdating = false;
    
    // Инициализация всех графиков
    function initAllCharts() {
        console.log('Инициализация графиков...');
        
        // 1. ГЛАВНЫЙ ГРАФИК (Температура и влажность)
        const mainCtx = document.getElementById('mainChart').getContext('2d');
        charts.mainChart = new Chart(mainCtx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: '🔥 Температура',
                        data: [],
                        borderColor: '#FF512F',
                        backgroundColor: 'rgba(255, 81, 47, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointHoverRadius: 8,
                        pointBackgroundColor: '#FF512F',
                        yAxisID: 'y'
                    },
                    {
                        label: '💧 Влажность',
                        data: [],
                        borderColor: '#1e90ff',
                        backgroundColor: 'rgba(30, 144, 255, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointHoverRadius: 8,
                        pointBackgroundColor: '#1e90ff',
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        labels: {
                            color: 'white',
                            font: {
                                family: 'Orbitron',
                                size: 14
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#FF512F',
                        bodyColor: 'white',
                        borderColor: '#FF512F',
                        borderWidth: 1,
                        cornerRadius: 10,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += context.dataset.label.includes('Температура') 
                                        ? context.parsed.y.toFixed(1) + '°C'
                                        : context.parsed.y.toFixed(1) + '%';
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'minute',
                            displayFormats: {
                                minute: 'HH:mm'
                            }
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#a0aec0',
                            font: {
                                family: 'Exo 2'
                            }
                        },
                        title: {
                            display: true,
                            text: 'Время',
                            color: '#a0aec0',
                            font: {
                                family: 'Orbitron',
                                size: 14
                            }
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#FF512F',
                            font: {
                                family: 'Orbitron'
                            },
                            callback: function(value) {
                                return value + '°C';
                            }
                        },
                        title: {
                            display: true,
                            text: 'Температура (°C)',
                            color: '#FF512F',
                            font: {
                                family: 'Orbitron',
                                size: 14
                            }
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            color: '#1e90ff',
                            font: {
                                family: 'Orbitron'
                            },
                            callback: function(value) {
                                return value + '%';
                            }
                        },
                        title: {
                            display: true,
                            text: 'Влажность (%)',
                            color: '#1e90ff',
                            font: {
                                family: 'Orbitron',
                                size: 14
                            }
                        }
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });
        
        // 2. ГРАФИК ТЕМПЕРАТУРЫ (отдельный)
        const tempCtx = document.getElementById('tempChart').getContext('2d');
        charts.tempChart = new Chart(tempCtx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Температура',
                    data: [],
                    borderColor: '#FF512F',
                    backgroundColor: 'rgba(255, 81, 47, 0.2)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        display: false
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#FF512F',
                            callback: function(value) {
                                return value + '°C';
                            }
                        }
                    }
                }
            }
        });
        
        // 3. ГРАФИК ВЛАЖНОСТИ (отдельный)
        const humCtx = document.getElementById('humChart').getContext('2d');
        charts.humChart = new Chart(humCtx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Влажность',
                    data: [],
                    borderColor: '#1e90ff',
                    backgroundColor: 'rgba(30, 144, 255, 0.2)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        display: false
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#1e90ff',
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
        
        // 4. СПИДОМЕТР ТЕМПЕРАТУРЫ
        const gaugeTempCtx = document.getElementById('gaugeTemp').getContext('2d');
        charts.gaugeTemp = new Chart(gaugeTempCtx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [0, 100],
                    backgroundColor: ['#FF512F', 'rgba(255, 255, 255, 0.1)'],
                    borderWidth: 0,
                    circumference: 270,
                    rotation: 225
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '80%',
                plugins: {
                    tooltip: { enabled: false },
                    legend: { display: false }
                }
            }
        });
        
        // 5. СПИДОМЕТР ВЛАЖНОСТИ
        const gaugeHumCtx = document.getElementById('gaugeHum').getContext('2d');
        charts.gaugeHum = new Chart(gaugeHumCtx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [0, 100],
                    backgroundColor: ['#1e90ff', 'rgba(255, 255, 255, 0.1)'],
                    borderWidth: 0,
                    circumference: 270,
                    rotation: 225
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '80%',
                plugins: {
                    tooltip: { enabled: false },
                    legend: { display: false }
                }
            }
        });
        
        console.log('✅ Все графики инициализированы!');
    }
    
    // Получение данных с сервера
    async function fetchData(endpoint) {
        try {
            const response = await fetch(endpoint);
            if (!response.ok) throw new Error('Network response was not ok');
            return await response.json();
        } catch (error) {
            console.error('Ошибка при получении данных:', error);
            throw error;
        }
    }
    
    // Обновление последних данных
    async function updateLatestData(showNotification = false) {
        if (isUpdating) return;
        
        isUpdating = true;
        const refreshBtn = document.getElementById('refreshBtn');
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Обновление...';
        
        try {
            const data = await fetchData('/api/latest');
            
            if (data.success) {
                latestData = data.data;
                updateUI(latestData);
                updateStatus(true);
                
                if (showNotification) {
                    showNotificationMessage('✅ Данные успешно обновлены!');
                }
            } else {
                updateStatus(false, data.error || 'Ошибка данных');
                if (showNotification) {
                    showNotificationMessage('❌ Ошибка при получении данных', 'error');
                }
            }
        } catch (error) {
            updateStatus(false, 'Ошибка сети');
            if (showNotification) {
                showNotificationMessage('❌ Ошибка подключения к серверу', 'error');
            }
        } finally {
            isUpdating = false;
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Обновить сейчас';
        }
    }
    
    // Загрузка исторических данных
    async function loadHistory(hours = 24) {
        const historyBtn = document.getElementById('historyBtn');
        const originalText = historyBtn.innerHTML;
        historyBtn.disabled = true;
        historyBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Загрузка...';
        
        try {
            const data = await fetchData(`/api/history?hours=${hours}`);
            
            if (data.success) {
                historyData = data.data;
                updateCharts(historyData);
                updateDataTable();
                
                // Обновляем активную кнопку временного диапазона
                document.querySelectorAll('.time-btn').forEach(btn => {
                    btn.classList.remove('active');
                    if (parseInt(btn.dataset.hours) === hours) {
                        btn.classList.add('active');
                    }
                });
                
                showNotificationMessage(`📊 Загружено ${historyData.length} записей за ${hours} ${getHoursWord(hours)}`);
            } else {
                showNotificationMessage('❌ Ошибка загрузки истории', 'error');
            }
        } catch (error) {
            showNotificationMessage('❌ Ошибка сети при загрузке истории', 'error');
        } finally {
            historyBtn.disabled = false;
            historyBtn.innerHTML = originalText;
        }
    }
    
    // Обновление интерфейса
    function updateUI(data) {
        if (!data) return;
        
        // Обновляем значения
        updateValueDisplay('temperature', data.temperature, '°C');
        updateValueDisplay('humidity', data.humidity, '%');
        
        // Обновляем время
        const timeElement = document.getElementById('lastUpdateTime');
        const footerTimeElement = document.getElementById('footerUpdateTime');
        const updateTime = formatDateTime(data.timestamp);
        
        timeElement.textContent = updateTime.time;
        timeElement.title = updateTime.full;
        footerTimeElement.textContent = updateTime.time;
        
        // Обновляем статусные карточки
        updateStatusCard('tempStatus', data.temperature, 'temperature');
        updateStatusCard('humStatus', data.humidity, 'humidity');
        
        // Обновляем спидометры
        updateGauge('gaugeTemp', data.temperature, 15, 35);
        updateGauge('gaugeHum', data.humidity, 0, 100);
    }
    
    // Обновление отображения значения
    function updateValueDisplay(elementId, value, unit) {
        const element = document.getElementById(elementId);
        if (!element || value === 'N/A') {
            element.textContent = '--';
            return;
        }
        
        const numValue = parseFloat(value);
        element.textContent = numValue.toFixed(1);
        
        // Добавляем анимацию
        element.classList.add('value-pulse');
        setTimeout(() => {
            element.classList.remove('value-pulse');
        }, 500);
    }
    
    // Обновление статусной карточки
    function updateStatusCard(elementId, value, type) {
        const element = document.getElementById(elementId);
        if (!element || value === 'N/A') return;
        
        const numValue = parseFloat(value);
        let status, colorClass;
        
        if (type === 'temperature') {
            if (numValue >= 30) {
                status = 'ЖАРКО 🔥';
                colorClass = 'status-hot';
            } else if (numValue >= 25) {
                status = 'Тепло';
                colorClass = 'status-warm';
            } else if (numValue >= 18) {
                status = 'Нормально';
                colorClass = 'status-normal';
            } else {
                status = 'Прохладно';
                colorClass = 'status-cool';
            }
        } else {
            if (numValue >= 70) {
                status = 'Высокая';
                colorClass = 'status-high';
            } else if (numValue >= 40) {
                status = 'Нормальная';
                colorClass = 'status-normal';
            } else {
                status = 'Низкая';
                colorClass = 'status-low';
            }
        }
        
        element.textContent = status;
        element.className = `status-badge ${colorClass}`;
    }
    
    // Обновление спидометра
    function updateGauge(chartName, value, min, max) {
        const chart = charts[chartName];
        if (!chart || value === 'N/A') return;
        
        const numValue = parseFloat(value);
        const percentage = ((numValue - min) / (max - min)) * 100;
        const clampedPercentage = Math.max(0, Math.min(100, percentage));
        
        chart.data.datasets[0].data = [clampedPercentage, 100 - clampedPercentage];
        chart.update();
        
        // Обновляем значение в центре спидометра
        const gaugeValueElement = document.getElementById(`${chartName}Value`);
        if (gaugeValueElement) {
            gaugeValueElement.textContent = numValue.toFixed(1);
        }
    }
    
    // Обновление графиков
    function updateCharts(data) {
        if (!data || data.length === 0) return;
        
        // Форматируем данные для графиков
        const formattedData = data.map(item => ({
            x: new Date(item.full_time || item.time),
            y: item.temperature,
            h: item.humidity
        })).filter(item => item.y !== null && item.h !== null);
        
        // Обновляем главный график
        if (charts.mainChart) {
            charts.mainChart.data.datasets[0].data = formattedData.map(d => ({ x: d.x, y: d.y }));
            charts.mainChart.data.datasets[1].data = formattedData.map(d => ({ x: d.x, y: d.h }));
            charts.mainChart.update();
        }
        
        // Обновляем график температуры
        if (charts.tempChart) {
            const recentTemp = formattedData.slice(-20);
            charts.tempChart.data.datasets[0].data = recentTemp.map(d => d.y);
            charts.tempChart.update();
        }
        
        // Обновляем график влажности
        if (charts.humChart) {
            const recentHum = formattedData.slice(-20);
            charts.humChart.data.datasets[0].data = recentHum.map(d => d.h);
            charts.humChart.update();
        }
    }
    
    // Обновление таблицы данных
    function updateDataTable() {
        const tableBody = document.getElementById('dataTableBody');
        if (!tableBody || !historyData.length) return;
        
        const recentData = historyData.slice(-10).reverse();
        tableBody.innerHTML = '';
        
        recentData.forEach(item => {
            const row = document.createElement('tr');
            
            const tempClass = getTemperatureClass(item.temperature);
            const humClass = getHumidityClass(item.humidity);
            
            row.innerHTML = `
                <td><i class="far fa-clock"></i> ${formatDateTime(item.full_time || item.time).time}</td>
                <td class="${tempClass}"><i class="fas fa-thermometer-half"></i> ${item.temperature !== null ? item.temperature.toFixed(1) : '--'}°C</td>
                <td class="${humClass}"><i class="fas fa-tint"></i> ${item.humidity !== null ? item.humidity.toFixed(1) : '--'}%</td>
                <td><span class="trend-indicator" data-temp="${item.temperature}" data-hum="${item.humidity}"></span></td>
            `;
            
            tableBody.appendChild(row);
        });
        
        // Обновляем индикаторы тренда
        updateTrendIndicators();
    }
    
    // Обновление индикаторов тренда
    function updateTrendIndicators() {
        document.querySelectorAll('.trend-indicator').forEach((indicator, index) => {
            if (historyData.length < 2) return;
            
            const currentIndex = historyData.length - 1 - index;
            if (currentIndex <= 0) return;
            
            const currentTemp = historyData[currentIndex]?.temperature;
            const prevTemp = historyData[currentIndex - 1]?.temperature;
            const currentHum = historyData[currentIndex]?.humidity;
            const prevHum = historyData[currentIndex - 1]?.humidity;
            
            if (currentTemp !== null && prevTemp !== null) {
                const tempDiff = currentTemp - prevTemp;
                if (Math.abs(tempDiff) > 0.1) {
                    indicator.innerHTML += `<i class="fas fa-arrow-${tempDiff > 0 ? 'up' : 'down'} ${tempDiff > 0 ? 'trend-up' : 'trend-down'}"></i> `;
                }
            }
            
            if (currentHum !== null && prevHum !== null) {
                const humDiff = currentHum - prevHum;
                if (Math.abs(humDiff) > 0.5) {
                    indicator.innerHTML += `<i class="fas fa-tint ${humDiff > 0 ? 'trend-up' : 'trend-down'}"></i>`;
                }
            }
            
            if (!indicator.innerHTML) {
                indicator.innerHTML = '<i class="fas fa-minus trend-stable"></i>';
            }
        });
    }
    
    // Обновление статуса подключения
    function updateStatus(connected, error = '') {
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        
        if (connected) {
            statusDot.className = 'status-dot online';
            statusDot.style.animation = 'pulse 2s infinite';
            statusText.textContent = 'Подключено к ThingSpeak';
            statusText.className = 'status-connected';
        } else {
            statusDot.className = 'status-dot offline';
            statusDot.style.animation = 'none';
            statusText.textContent = error || 'Нет подключения';
            statusText.className = 'status-disconnected';
        }
    }
    
    // Показать уведомление
    function showNotificationMessage(message, type = 'success') {
        const notification = document.getElementById('notification');
        if (!notification) return;
        
        notification.textContent = message;
        notification.className = `notification ${type}`;
        notification.style.display = 'block';
        
        // Автоматически скрыть через 5 секунд
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                notification.style.display = 'none';
                notification.style.opacity = '1';
            }, 500);
        }, 5000);
    }
    
    // Вспомогательные функции
    function formatDateTime(timestamp) {
        if (!timestamp || timestamp === 'N/A') {
            return { time: '--:--:--', full: 'Неизвестно' };
        }
        
        try {
            const date = new Date(timestamp);
            return {
                time: date.toLocaleTimeString('ru-RU'),
                full: date.toLocaleString('ru-RU')
            };
        } catch (e) {
            return { time: timestamp, full: timestamp };
        }
    }
    
    function getHoursWord(hours) {
        if (hours === 1) return 'час';
        if (hours >= 2 && hours <= 4) return 'часа';
        return 'часов';
    }
    
    function getTemperatureClass(temp) {
        if (temp === null) return '';
        if (temp >= 30) return 'temp-hot';
        if (temp >= 25) return 'temp-warm';
        if (temp >= 18) return 'temp-normal';
        return 'temp-cool';
    }
    
    function getHumidityClass(hum) {
        if (hum === null) return '';
        if (hum >= 70) return 'hum-high';
        if (hum >= 40) return 'hum-normal';
        return 'hum-low';
    }
    
    // Инициализация кнопок
    function initButtons() {
        console.log('Инициализация кнопок...');
        
        // Кнопка обновления
        document.getElementById('refreshBtn').addEventListener('click', () => {
            updateLatestData(true);
        });
        
        // Кнопка загрузки истории
        document.getElementById('historyBtn').addEventListener('click', () => {
            const activeBtn = document.querySelector('.time-btn.active');
            const hours = activeBtn ? parseInt(activeBtn.dataset.hours) : 24;
            loadHistory(hours);
        });
        
        // Кнопки временных диапазонов
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const hours = parseInt(this.dataset.hours);
                
                // Обновляем активную кнопку
                document.querySelectorAll('.time-btn').forEach(b => {
                    b.classList.remove('active');
                });
                this.classList.add('active');
                
                // Загружаем данные
                loadHistory(hours);
            });
        });
        
        // Кнопка автообновления
        const autoRefreshToggle = document.getElementById('autoRefreshToggle');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', function() {
                if (this.checked) {
                    startAutoRefresh();
                    showNotificationMessage('🔄 Автообновление включено');
                } else {
                    stopAutoRefresh();
                    showNotificationMessage('⏸️ Автообновление выключено');
                }
            });
        }
        
        // Кнопка экспорта
        document.getElementById('exportBtn').addEventListener('click', async () => {
            try {
                const response = await fetch('/api/export');
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `iot_data_${new Date().toISOString().slice(0,10)}.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                showNotificationMessage('📥 Данные экспортированы в CSV');
            } catch (error) {
                showNotificationMessage('❌ Ошибка экспорта', 'error');
            }
        });
        
        console.log('✅ Кнопки инициализированы!');
    }
    
    // Автоматическое обновление
    function startAutoRefresh() {
        if (updateInterval) clearInterval(updateInterval);
        
        updateInterval = setInterval(() => {
            updateLatestData();
        }, 10000); // Каждые 10 секунд
        
        console.log('Автообновление запущено');
    }
    
    function stopAutoRefresh() {
        if (updateInterval) {
            clearInterval(updateInterval);
            updateInterval = null;
            console.log('Автообновление остановлено');
        }
    }
    
    // Инициализация всего приложения
    async function initApp() {
        console.log('🚀 Запуск IoT Dashboard...');
        
        // Показываем загрузку
        showNotificationMessage('🔍 Подключение к ThingSpeak...', 'info');
        
        // Инициализация
        initAllCharts();
        initButtons();
        
        // Загрузка начальных данных
        try {
            await Promise.all([
                updateLatestData(),
                loadHistory(24)
            ]);
            
            // Запускаем автообновление
            startAutoRefresh();
            
            showNotificationMessage('✅ Система мониторинга запущена!');
        } catch (error) {
            showNotificationMessage('❌ Ошибка инициализации приложения', 'error');
        }
    }
    
    // Запускаем приложение
    initApp();
    
    // Глобальные функции для кнопок
    window.refreshData = () => updateLatestData(true);
    window.loadHistoryData = (hours) => loadHistory(hours);
    window.exportData = () => {
        document.getElementById('exportBtn').click();
    };
    
    // Анимация для значений
    const style = document.createElement('style');
    style.textContent = `
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        
        @keyframes valuePulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        .value-pulse {
            animation: valuePulse 0.5s ease;
        }
        
        .status-dot.online {
            background: #00ff00;
            box-shadow: 0 0 10px #00ff00, 0 0 20px #00ff00;
        }
        
        .status-dot.offline {
            background: #ff0000;
            box-shadow: 0 0 10px #ff0000;
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 10px;
            background: rgba(20, 25, 40, 0.95);
            border-left: 5px solid;
            z-index: 1000;
            transition: opacity 0.5s;
            backdrop-filter: blur(10px);
        }
        
        .notification.success {
            border-color: #00ff00;
            color: #00ff00;
        }
        
        .notification.error {
            border-color: #ff0000;
            color: #ff0000;
        }
        
        .notification.info {
            border-color: #1e90ff;
            color: #1e90ff;
        }
        
        .btn {
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255, 81, 47, 0.3);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .time-btn.active {
            background: var(--primary-gradient) !important;
            color: white !important;
            box-shadow: 0 0 15px rgba(255, 81, 47, 0.5);
        }
        
        .temp-hot { color: #FF512F; }
        .temp-warm { color: #FFA502; }
        .temp-normal { color: #2ED573; }
        .temp-cool { color: #1E90FF; }
        
        .hum-high { color: #1E90FF; }
        .hum-normal { color: #2ED573; }
        .hum-low { color: #FFA502; }
        
        .trend-up { color: #FF512F; }
        .trend-down { color: #1E90FF; }
        .trend-stable { color: #2ED573; }
        
        .status-hot { background: rgba(255, 81, 47, 0.2); color: #FF512F; }
        .status-warm { background: rgba(255, 165, 2, 0.2); color: #FFA502; }
        .status-normal { background: rgba(46, 213, 115, 0.2); color: #2ED573; }
        .status-cool { background: rgba(30, 144, 255, 0.2); color: #1E90FF; }
        .status-high { background: rgba(30, 144, 255, 0.2); color: #1E90FF; }
        .status-low { background: rgba(255, 165, 2, 0.2); color: #FFA502; }
    `;
    document.head.appendChild(style);
});