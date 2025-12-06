# thingspeak_sender.py
import time
import random
import urllib.request
import urllib.parse
from datetime import datetime

# Конфигурация ThingSpeak
CHANNEL_ID = "3194658"
WRITE_API_KEY = "W5LKIPSCLZV8ATA8"
BASE_URL = "https://api.thingspeak.com/update"

def generate_sensor_data():
    """Генерация реалистичных тестовых данных"""
    # Более реалистичные диапазоны
    base_temp = 22.0  # Базовая температура
    base_humidity = 45.0  # Базовая влажность
    
    # Добавляем суточные колебания
    hour = datetime.now().hour
    day_factor = 0.5 * (1 - abs(hour - 12) / 12)  # Пик в полдень
    
    return {
        'field1': round(base_temp + day_factor * 5 + random.uniform(-1, 1), 2),  # temperatura
        'field2': round(base_humidity + random.uniform(-5, 5), 2)  # vlahgnost
    }

def send_to_thingspeak(data):
    """Отправка данных в ThingSpeak"""
    params = urllib.parse.urlencode({
        'api_key': WRITE_API_KEY,
        'field1': data['field1'],  # temperatura
        'field2': data['field2']   # vlahgnost
    })
    
    try:
        response = urllib.request.urlopen(f"{BASE_URL}?{params}")
        result = response.read().decode()
        
        # Проверяем успешность отправки
        if result != '0':
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"[{current_time}] Данные отправлены успешно!")
            print(f"  Температура: {data['field1']}°C")
            print(f"  Влажность: {data['field2']}%")
            print(f"  ID записи: {result}")
            print("-" * 40)
            return True
        else:
            print("Ошибка: ThingSpeak вернул 0 (проверьте API ключ)")
            return False
            
    except urllib.error.HTTPError as e:
        print(f"HTTP ошибка {e.code}: {e.reason}")
        return False
    except Exception as e:
        print(f"Ошибка соединения: {e}")
        return False

def display_status(counter, start_time):
    """Отображение статуса работы"""
    elapsed = time.time() - start_time
    avg_interval = elapsed / max(counter, 1)
    
    print("\n" + "="*50)
    print("СТАТУС IoT-МОНИТОРИНГА")
    print("="*50)
    print(f"Канал ThingSpeak: {CHANNEL_ID}")
    print(f"Отправлено сообщений: {counter}")
    print(f"Время работы: {elapsed:.0f} секунд")
    print(f"Средний интервал: {avg_interval:.1f} сек/сообщение")
    print(f"Следующая отправка через: 20 секунд")
    print("="*50 + "\n")

def main():
    """Основной цикл отправки данных"""
    print("="*60)
    print("ЗАПУСК IoT-СИСТЕМЫ МОНИТОРИНГА НА THINGSPEAK")
    print("="*60)
    print(f"Канал ID: {CHANNEL_ID}")
    print(f"Поле 1: temperatura (°C)")
    print(f"Поле 2: vlahgnost (%)")
    print("="*60)
    
    counter = 0
    start_time = time.time()
    
    try:
        while True:
            try:
                # Генерируем данные
                sensor_data = generate_sensor_data()
                
                # Отправляем в ThingSpeak
                if send_to_thingspeak(sensor_data):
                    counter += 1
                
                # Отображаем статус каждые 5 сообщений
                if counter % 5 == 0:
                    display_status(counter, start_time)
                
                # ThingSpeak ограничивает отправку до 1 сообщения в 15 секунд
                # на бесплатном аккаунте. Используем 20 секунд для надежности
                print(f"Ожидание 20 секунд...")
                time.sleep(20)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"Неожиданная ошибка: {e}")
                time.sleep(30)  # Ждем дольше при ошибках
                
    except KeyboardInterrupt:
        print("\n" + "="*60)
        print("МОНИТОРИНГ ОСТАНОВЛЕН ПОЛЬЗОВАТЕЛЕМ")
        print("="*60)
        display_status(counter, start_time)
        print("Спасибо за использование системы!")

def test_connection():
    """Тестирование подключения к ThingSpeak"""
    print("Тестирование подключения к ThingSpeak...")
    
    test_data = {
        'field1': 21.5,
        'field2': 45.3
    }
    
    print(f"Тестовые данные: {test_data}")
    
    if send_to_thingspeak(test_data):
        print("✓ Подключение к ThingSpeak успешно!")
        return True
    else:
        print("✗ Не удалось подключиться к ThingSpeak")
        print("Проверьте:")
        print("1. Интернет-подключение")
        print("2. Правильность CHANNEL_ID и WRITE_API_KEY")
        print("3. Существует ли канал в ThingSpeak")
        return False

if __name__ == "__main__":
    # Сначала тестируем подключение
    if test_connection():
        # Если тест успешен, запускаем основной цикл
        time.sleep(2)
        print("\nЗапуск основного цикла мониторинга...\n")
        main()
    else:
        print("Запуск основной программы отменен.")
        print("Пожалуйста, исправьте ошибки и попробуйте снова.")