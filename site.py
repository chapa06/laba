# web_app.py (обновленная версия)
from flask import Flask, render_template, jsonify, request, send_file
import requests
from datetime import datetime, timedelta
import json
import csv
import io

app = Flask(__name__)

# Конфигурация
THINGSPEAK_CHANNEL_ID = "3194658"
THINGSPEAK_READ_API_KEY = None
THINGSPEAK_BASE_URL = "https://api.thingspeak.com"

class ThingSpeakClient:
    @staticmethod
    def get_channel_status():
        """Проверка статуса канала"""
        try:
            url = f"{THINGSPEAK_BASE_URL}/channels/{THINGSPEAK_CHANNEL_ID}/status.json"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    @staticmethod
    def get_latest_data():
        """Получение последних данных"""
        url = f"{THINGSPEAK_BASE_URL}/channels/{THINGSPEAK_CHANNEL_ID}/feeds/last.json"
        
        params = {}
        if THINGSPEAK_READ_API_KEY:
            params['api_key'] = THINGSPEAK_READ_API_KEY
        
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # Рассчитываем тренды
                temp = float(data.get('field1', 0)) if data.get('field1') else None
                hum = float(data.get('field2', 0)) if data.get('field2') else None
                
                return {
                    'success': True,
                    'data': {
                        'temperature': temp,
                        'humidity': hum,
                        'timestamp': data.get('created_at', 'N/A'),
                        'entry_id': data.get('entry_id', 'N/A')
                    }
                }
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_historical_data(hours=24, max_points=8000):
        """Получение исторических данных"""
        # Рассчитываем количество точек
        points_per_hour = 180  # 1 точка каждые 20 секунд
        results = min(max_points, hours * points_per_hour)
        
        url = f"{THINGSPEAK_BASE_URL}/channels/{THINGSPEAK_CHANNEL_ID}/feeds.json"
        
        params = {'results': results}
        if THINGSPEAK_READ_API_KEY:
            params['api_key'] = THINGSPEAK_READ_API_KEY
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                feeds = data.get('feeds', [])
                
                formatted_data = []
                for feed in feeds:
                    try:
                        if feed.get('field1') and feed.get('field2'):
                            timestamp = datetime.strptime(
                                feed['created_at'], 
                                "%Y-%m-%dT%H:%M:%SZ"
                            )
                            formatted_data.append({
                                'time': timestamp.strftime("%H:%M"),
                                'full_time': timestamp.isoformat(),
                                'temperature': float(feed['field1']),
                                'humidity': float(feed['field2']),
                                'entry_id': feed.get('entry_id')
                            })
                    except:
                        continue
                
                return {'success': True, 'data': formatted_data, 'count': len(formatted_data)}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_channel_info():
        """Получение информации о канале"""
        url = f"{THINGSPEAK_BASE_URL}/channels/{THINGSPEAK_CHANNEL_ID}.json"
        
        params = {}
        if THINGSPEAK_READ_API_KEY:
            params['api_key'] = THINGSPEAK_READ_API_KEY
        
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'data': {
                        'name': data.get('name', 'IoT Мониторинг'),
                        'description': data.get('description', ''),
                        'created_at': data.get('created_at', ''),
                        'field1': data.get('field1', 'Температура'),
                        'field2': data.get('field2', 'Влажность')
                    }
                }
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Маршруты
@app.route('/')
def index():
    """Главная страница"""
    channel_info = ThingSpeakClient.get_channel_info()
    channel_status = ThingSpeakClient.get_channel_status()
    
    channel_data = {
        'id': THINGSPEAK_CHANNEL_ID,
        'name': 'IoT Дашборд',
        'status': 'online' if channel_status else 'offline'
    }
    
    if channel_info['success']:
        channel_data.update(channel_info['data'])
    
    return render_template('dashboard.html', **channel_data)

@app.route('/api/latest')
def api_latest():
    """API для последних данных"""
    data = ThingSpeakClient.get_latest_data()
    return jsonify(data)

@app.route('/api/history')
def api_history():
    """API для исторических данных"""
    hours = request.args.get('hours', default=24, type=int)
    data = ThingSpeakClient.get_historical_data(hours)
    return jsonify(data)

@app.route('/api/channel')
def api_channel():
    """API информации о канале"""
    data = ThingSpeakClient.get_channel_info()
    return jsonify(data)

@app.route('/api/status')
def api_status():
    """API статуса системы"""
    latest = ThingSpeakClient.get_latest_data()
    channel_status = ThingSpeakClient.get_channel_status()
    
    status = {
        'system': 'online',
        'thingspeak': 'online' if channel_status else 'offline',
        'timestamp': datetime.now().isoformat(),
        'channel_id': THINGSPEAK_CHANNEL_ID,
        'data_available': latest['success']
    }
    
    return jsonify(status)

@app.route('/api/export')
def api_export():
    """API экспорта данных в CSV"""
    data = ThingSpeakClient.get_historical_data(168, 5000)  # 1 неделя, максимум 5000 точек
    
    if not data['success']:
        return jsonify({'error': 'Не удалось получить данные'}), 500
    
    # Создаем CSV в памяти
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow(['Дата и время', 'Температура (°C)', 'Влажность (%)', 'ID записи'])
    
    # Данные
    for item in data['data']:
        writer.writerow([
            item['full_time'],
            item['temperature'],
            item['humidity'],
            item.get('entry_id', '')
        ])
    
    output.seek(0)
    
    filename = f"iot_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/stats')
def api_stats():
    """API статистики"""
    data = ThingSpeakClient.get_historical_data(24, 500)
    
    if not data['success'] or not data['data']:
        return jsonify({'error': 'Нет данных'}), 404
    
    temps = [d['temperature'] for d in data['data']]
    hums = [d['humidity'] for d in data['data']]
    
    stats = {
        'temperature': {
            'current': temps[-1] if temps else None,
            'avg': sum(temps) / len(temps) if temps else None,
            'min': min(temps) if temps else None,
            'max': max(temps) if temps else None,
            'trend': 'up' if len(temps) > 1 and temps[-1] > temps[-2] else 'down' if len(temps) > 1 and temps[-1] < temps[-2] else 'stable'
        },
        'humidity': {
            'current': hums[-1] if hums else None,
            'avg': sum(hums) / len(hums) if hums else None,
            'min': min(hums) if hums else None,
            'max': max(hums) if hums else None,
            'trend': 'up' if len(hums) > 1 and hums[-1] > hums[-2] else 'down' if len(hums) > 1 and hums[-1] < hums[-2] else 'stable'
        },
        'data_points': len(data['data'])
    }
    
    return jsonify({'success': True, 'stats': stats})

# Статические файлы
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    print("="*60)
    print("🔥 ЗАПУСК ОГНЕННОГО IoT ДАШБОРДА")
    print("="*60)
    print(f"Канал ThingSpeak: {THINGSPEAK_CHANNEL_ID}")
    print(f"API статус: {'✅ Онлайн' if ThingSpeakClient.get_channel_status() else '❌ Оффлайн'}")
    print("Сервер запущен: http://localhost:5000")
    print("="*60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)