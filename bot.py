# telegram_bot_fixed.py - БЕЗ JobQueue
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters, 
    ContextTypes,
    ConversationHandler
)
from telegram.constants import ParseMode

# Настройки
THINGSPEAK_CHANNEL_ID = "3194658"
THINGSPEAK_READ_API_KEY = None
TELEGRAM_BOT_TOKEN = "8555217863:AAFObnn77yJlpmOV0uYom7IZXw8mMk3nGyM"

# Настройки аварийных пределов (можно менять через бота)
ALERT_SETTINGS = {
    'temperature': {
        'min': 15,
        'max': 30,
        'enabled': True,
        'notify_every_minutes': 15  # Интервал повторных оповещений
    },
    'humidity': {
        'min': 30,
        'max': 70,
        'enabled': True,
        'notify_every_minutes': 15
    }
}

# Хранилище пользователей и настроек
USER_SETTINGS = {}  # {user_id: {alerts_enabled: True, notify_via: ['telegram'], ...}}
ALERT_HISTORY = {}  # Для отслеживания повторных оповещений

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
SETTING_TEMP_MIN, SETTING_TEMP_MAX, SETTING_HUM_MIN, SETTING_HUM_MAX = range(4)

class ThingSpeakMonitor:
    @staticmethod
    def get_latest_data():
        """Получение последних данных из ThingSpeak"""
        url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/feeds/last.json"
        
        params = {}
        if THINGSPEAK_READ_API_KEY:
            params['api_key'] = THINGSPEAK_READ_API_KEY
        
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # Проверяем наличие данных
                temp_str = data.get('field1')
                hum_str = data.get('field2')
                
                return {
                    'success': True,
                    'data': {
                        'temperature': float(temp_str) if temp_str and temp_str.strip() else None,
                        'humidity': float(hum_str) if hum_str and hum_str.strip() else None,
                        'timestamp': data.get('created_at', 'N/A'),
                        'entry_id': data.get('entry_id', 'N/A')
                    }
                }
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_historical_data(hours=24, limit=100):
        """Получение исторических данных"""
        url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/feeds.json"
        
        params = {'results': limit}
        if THINGSPEAK_READ_API_KEY:
            params['api_key'] = THINGSPEAK_READ_API_KEY
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                feeds = data.get('feeds', [])
                
                formatted_data = []
                for feed in feeds[-hours*3:]:  # Последние N часов (примерно 3 точки в час)
                    try:
                        temp = float(feed['field1']) if feed.get('field1') and feed['field1'].strip() else None
                        hum = float(feed['field2']) if feed.get('field2') and feed['field2'].strip() else None
                        
                        if temp is not None and hum is not None:
                            timestamp = datetime.strptime(
                                feed['created_at'], 
                                "%Y-%m-%dT%H:%M:%SZ"
                            )
                            formatted_data.append({
                                'time': timestamp.strftime("%H:%M"),
                                'full_time': timestamp,
                                'temperature': temp,
                                'humidity': hum
                            })
                    except:
                        continue
                
                return {'success': True, 'data': formatted_data}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def check_alerts(data):
        """Проверка данных на выход за пределы"""
        alerts = []
        
        if not data['success'] or not data['data']:
            return alerts
        
        sensor_data = data['data']
        
        # Проверка температуры
        if (ALERT_SETTINGS['temperature']['enabled'] and 
            sensor_data['temperature'] is not None):
            
            temp = sensor_data['temperature']
            temp_min = ALERT_SETTINGS['temperature']['min']
            temp_max = ALERT_SETTINGS['temperature']['max']
            
            if temp < temp_min:
                alerts.append({
                    'type': 'temperature',
                    'level': 'LOW',
                    'value': temp,
                    'limit': temp_min,
                    'message': f'🌡️ ТЕМПЕРАТУРА НИЖЕ НОРМЫ: {temp}°C (минимум: {temp_min}°C)',
                    'emoji': '❄️',
                    'severity': 'warning' if temp > temp_min - 5 else 'critical'
                })
            elif temp > temp_max:
                alerts.append({
                    'type': 'temperature',
                    'level': 'HIGH',
                    'value': temp,
                    'limit': temp_max,
                    'message': f'🌡️ ТЕМПЕРАТУРА ВЫШЕ НОРМЫ: {temp}°C (максимум: {temp_max}°C)',
                    'emoji': '🔥',
                    'severity': 'warning' if temp < temp_max + 5 else 'critical'
                })
        
        # Проверка влажности
        if (ALERT_SETTINGS['humidity']['enabled'] and 
            sensor_data['humidity'] is not None):
            
            hum = sensor_data['humidity']
            hum_min = ALERT_SETTINGS['humidity']['min']
            hum_max = ALERT_SETTINGS['humidity']['max']
            
            if hum < hum_min:
                alerts.append({
                    'type': 'humidity',
                    'level': 'LOW',
                    'value': hum,
                    'limit': hum_min,
                    'message': f'💧 ВЛАЖНОСТЬ НИЖЕ НОРМЫ: {hum}% (минимум: {hum_min}%)',
                    'emoji': '🏜️',
                    'severity': 'warning'
                })
            elif hum > hum_max:
                alerts.append({
                    'type': 'humidity',
                    'level': 'HIGH',
                    'value': hum,
                    'limit': hum_max,
                    'message': f'💧 ВЛАЖНОСТЬ ВЫШЕ НОРМЫ: {hum}% (максимум: {hum_max}%)',
                    'emoji': '💦',
                    'severity': 'warning'
                })
        
        return alerts
    
    @staticmethod
    def should_notify_alert(user_id, alert, now):
        """Проверка, нужно ли отправлять оповещение (избегаем спама)"""
        alert_key = f"{user_id}_{alert['type']}_{alert['level']}"
        
        if alert_key not in ALERT_HISTORY:
            ALERT_HISTORY[alert_key] = now
            return True
        
        last_notify = ALERT_HISTORY[alert_key]
        interval = ALERT_SETTINGS[alert['type']]['notify_every_minutes']
        
        if now - last_notify > timedelta(minutes=interval):
            ALERT_HISTORY[alert_key] = now
            return True
        
        return False

class TelegramBotManager:
    def __init__(self):
        self.monitor = ThingSpeakMonitor()
    
    # ======================= КОМАНДЫ БОТА =======================
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start - приветствие"""
        user = update.effective_user
        user_id = user.id
        
        # Инициализация настроек пользователя
        if user_id not in USER_SETTINGS:
            USER_SETTINGS[user_id] = {
                'alerts_enabled': True,
                'notify_via': ['telegram'],
                'language': 'ru',
                'notify_critical': True,
                'notify_warnings': True
            }
        
        welcome_text = f"""
🚀 *Добро пожаловать в IoT Monitoring Bot!* 🚀

Привет, {user.first_name}! Я ваш персональный помощник для мониторинга датчиков.

*📊 Канал мониторинга:* #{THINGSPEAK_CHANNEL_ID}
*🌡️ Мониторим:* Температура и Влажность

*🔔 Текущие настройки оповещений:*
• Температура: {ALERT_SETTINGS['temperature']['min']}°C - {ALERT_SETTINGS['temperature']['max']}°C
• Влажность: {ALERT_SETTINGS['humidity']['min']}% - {ALERT_SETTINGS['humidity']['max']}%

*📋 Доступные команды:*
/status - Текущие показания
/alerts - Настройки оповещений
/history - История данных
/stats - Статистика
/settings - Настройки бота
/help - Помощь

Нажмите кнопку ниже для быстрого доступа к функциям!
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Текущие показания", callback_data="status_now")],
            [InlineKeyboardButton("⚠️ Настройка оповещений", callback_data="alerts_menu")],
            [InlineKeyboardButton("📈 История данных", callback_data="history_menu")],
            [InlineKeyboardButton("⚙️ Настройки бота", callback_data="bot_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status - текущие показания"""
        await self.send_current_status(update, context)
    
    async def alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /alerts - настройки оповещений"""
        await self.show_alerts_menu(update, context)
    
    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /history - история данных"""
        await self.show_history_menu(update, context)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - статистика"""
        await self.show_statistics(update, context)
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /settings - настройки бота"""
        await self.show_bot_settings(update, context)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help - помощь"""
        help_text = """
*🤖 IoT Monitoring Bot - Помощь*

*📊 Основные команды:*
/start - Запустить бота
/status - Текущие показания датчиков
/alerts - Управление оповещениями
/history - Просмотр истории данных
/stats - Статистика за 24 часа
/settings - Настройки бота

*🔔 Оповещения:*
Бот автоматически уведомит вас, если:
• Температура выйдет за пределы {min_temp}°C - {max_temp}°C
• Влажность выйдет за пределы {min_hum}% - {max_hum}%

*⚡ Быстрые действия:*
• Нажмите кнопку "📊 Текущие показания" для мгновенного обновления
• Используйте "⚠️ Настройка оповещений" для изменения пределов
• "📈 История данных" покажет графики за выбранный период

*🛠️ Техническая информация:*
• Канал ThingSpeak: #{channel_id}
• Обновление данных: каждые 20 секунд

Для связи с разработчиком: @your_support
        """.format(
            min_temp=ALERT_SETTINGS['temperature']['min'],
            max_temp=ALERT_SETTINGS['temperature']['max'],
            min_hum=ALERT_SETTINGS['humidity']['min'],
            max_hum=ALERT_SETTINGS['humidity']['max'],
            channel_id=THINGSPEAK_CHANNEL_ID
        )
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    # ======================= ОБРАБОТЧИКИ КНОПОК =======================
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий кнопок"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "status_now":
            await self.send_current_status_callback(query, context)
        elif data == "alerts_menu":
            await self.show_alerts_menu_callback(query, context)
        elif data == "history_menu":
            await self.show_history_menu_callback(query, context)
        elif data == "bot_settings":
            await self.show_bot_settings_callback(query, context)
        elif data.startswith("alert_"):
            await self.handle_alert_settings(query, context)
        elif data.startswith("history_"):
            await self.handle_history_selection(query, context)
        elif data.startswith("setting_"):
            await self.handle_bot_settings(query, context)
        elif data == "refresh":
            await self.send_current_status_callback(query, context)
        elif data == "enable_alerts":
            await self.toggle_alerts(query, context, True)
        elif data == "disable_alerts":
            await self.toggle_alerts(query, context, False)
    
    # ======================= ФУНКЦИИ ОТПРАВКИ ДАННЫХ =======================
    
    async def send_current_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка текущих показаний"""
        data = self.monitor.get_latest_data()
        
        if not data['success']:
            await update.message.reply_text(
                "❌ *Ошибка получения данных*\nНе удалось подключиться к ThingSpeak",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        sensor_data = data['data']
        await self._send_status_message(update.effective_chat.id, sensor_data, context)
    
    async def send_current_status_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Отправка текущих показаний (callback версия)"""
        data = self.monitor.get_latest_data()
        
        if not data['success']:
            await query.edit_message_text(
                "❌ *Ошибка получения данных*\nНе удалось подключиться к ThingSpeak",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        sensor_data = data['data']
        await self._send_status_message(query.message.chat_id, sensor_data, context, query.message.message_id)
    
    async def _send_status_message(self, chat_id, sensor_data, context, message_id=None):
        """Внутренняя функция отправки статуса"""
        temp = sensor_data['temperature']
        hum = sensor_data['humidity']
        timestamp = sensor_data['timestamp']
        
        # Форматируем время
        try:
            dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
            time_str = dt.strftime("%H:%M:%S")
            date_str = dt.strftime("%d.%m.%Y")
        except:
            time_str = timestamp
            date_str = ""
        
        # Проверяем оповещения
        alerts = self.monitor.check_alerts({'success': True, 'data': sensor_data})
        
        # Определяем статусы
        temp_status = self._get_temperature_status(temp)
        hum_status = self._get_humidity_status(hum)
        
        # Формируем сообщение
        message = f"""
📊 *ТЕКУЩИЕ ПОКАЗАНИЯ ДАТЧИКОВ*

*🌡️ Температура:* `{temp if temp is not None else 'N/A'}°C`
{temp_status['emoji']} *Статус:* {temp_status['text']}

*💧 Влажность:* `{hum if hum is not None else 'N/A'}%`
{hum_status['emoji']} *Статус:* {hum_status['text']}

*⏰ Последнее обновление:* {time_str}
*📅 Дата:* {date_str}
*🆔 ID записи:* {sensor_data['entry_id']}
        """
        
        # Добавляем оповещения, если они есть
        if alerts:
            message += "\n\n🚨 *ОПОВЕЩЕНИЯ:*\n"
            for alert in alerts:
                message += f"{alert['emoji']} {alert['message']}\n"
            
            # Отправляем отдельное уведомление для оповещений
            user_id = chat_id
            user_settings = USER_SETTINGS.get(user_id, {})
            
            if user_settings.get('alerts_enabled', True):
                await self._send_alert_notification(context, user_id, alerts, sensor_data)
        
        message += f"\n*🔔 Границы оповещений:*"
        message += f"\n• Температура: {ALERT_SETTINGS['temperature']['min']}°C - {ALERT_SETTINGS['temperature']['max']}°C"
        message += f"\n• Влажность: {ALERT_SETTINGS['humidity']['min']}% - {ALERT_SETTINGS['humidity']['max']}%"
        
        # Клавиатура с действиями
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh")],
            [InlineKeyboardButton("⚠️ Настройка оповещений", callback_data="alerts_menu")],
            [InlineKeyboardButton("📈 История данных", callback_data="history_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if message_id:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    # ======================= МЕНЮ ОПОВЕЩЕНИЙ =======================
    
    async def show_alerts_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ меню настроек оповещений"""
        await self._send_alerts_menu(update.effective_chat.id, context)
    
    async def show_alerts_menu_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показ меню настроек оповещений (callback)"""
        await self._send_alerts_menu(query.message.chat_id, context, query.message.message_id)
    
    async def _send_alerts_menu(self, chat_id, context, message_id=None):
        """Внутренняя функция отправки меню оповещений"""
        user_id = chat_id
        alerts_enabled = USER_SETTINGS.get(user_id, {}).get('alerts_enabled', True)
        
        message = f"""
⚠️ *НАСТРОЙКА ОПОВЕЩЕНИЙ*

*Текущие настройки:*
• 🔔 Оповещения: {"✅ ВКЛЮЧЕНЫ" if alerts_enabled else "❌ ВЫКЛЮЧЕНЫ"}
• 🌡️ Температура: {ALERT_SETTINGS['temperature']['min']}°C - {ALERT_SETTINGS['temperature']['max']}°C
• 💧 Влажность: {ALERT_SETTINGS['humidity']['min']}% - {ALERT_SETTINGS['humidity']['max']}%

Выберите параметр для настройки:
        """
        
        keyboard = [
            [InlineKeyboardButton("🌡️ Настроить температуру", callback_data="alert_temp")],
            [InlineKeyboardButton("💧 Настроить влажность", callback_data="alert_hum")],
            [
                InlineKeyboardButton("✅ Включить оповещения", callback_data="enable_alerts") 
                if not alerts_enabled else 
                InlineKeyboardButton("❌ Выключить оповещения", callback_data="disable_alerts")
            ],
            [InlineKeyboardButton("📊 Текущие показания", callback_data="status_now")],
            [InlineKeyboardButton("🔙 Назад", callback_data="bot_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if message_id:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    async def handle_alert_settings(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработка настроек оповещений"""
        data = query.data
        
        if data == "alert_temp":
            await self._configure_temperature(query, context)
        elif data == "alert_hum":
            await self._configure_humidity(query, context)
    
    async def _configure_temperature(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Настройка температуры"""
        message = f"""
🌡️ *НАСТРОЙКА ТЕМПЕРАТУРЫ*

Текущие пределы: {ALERT_SETTINGS['temperature']['min']}°C - {ALERT_SETTINGS['temperature']['max']}°C

*Рекомендации:*
• Комфортная температура: 18-25°C
• Критический минимум: 10°C
• Критический максимум: 40°C

Введите минимальную температуру (целое число):
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="alerts_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        # Сохраняем состояние для обработки ввода
        context.user_data['awaiting_input'] = 'temp_min'
        await query.message.delete()
    
    async def _configure_humidity(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Настройка влажности"""
        message = f"""
💧 *НАСТРОЙКА ВЛАЖНОСТИ*

Текущие пределы: {ALERT_SETTINGS['humidity']['min']}% - {ALERT_SETTINGS['humidity']['max']}%

*Рекомендации:*
• Комфортная влажность: 40-60%
• Критический минимум: 20%
• Критический максимум: 80%

Введите минимальную влажность (целое число):
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="alerts_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        # Сохраняем состояние для обработки ввода
        context.user_data['awaiting_input'] = 'hum_min'
        await query.message.delete()
    
    async def toggle_alerts(self, query, context: ContextTypes.DEFAULT_TYPE, enable: bool):
        """Включение/выключение оповещений"""
        user_id = query.from_user.id
        
        if user_id not in USER_SETTINGS:
            USER_SETTINGS[user_id] = {}
        
        USER_SETTINGS[user_id]['alerts_enabled'] = enable
        
        status = "включены" if enable else "выключены"
        await query.edit_message_text(
            f"✅ Оповещения {status}!",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Показываем меню через 2 секунды
        await asyncio.sleep(2)
        await self._send_alerts_menu(query.message.chat_id, context, query.message.message_id)
    
    # ======================= МЕНЮ ИСТОРИИ =======================
    
    async def show_history_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ меню истории"""
        await self._send_history_menu(update.effective_chat.id, context)
    
    async def show_history_menu_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показ меню истории (callback)"""
        await self._send_history_menu(query.message.chat_id, context, query.message.message_id)
    
    async def _send_history_menu(self, chat_id, context, message_id=None):
        """Внутренняя функция отправки меню истории"""
        message = """
📈 *ИСТОРИЯ ДАННЫХ*

Выберите период для просмотра истории:
        """
        
        keyboard = [
            [InlineKeyboardButton("⏰ Последний час", callback_data="history_1")],
            [InlineKeyboardButton("⏳ Последние 6 часов", callback_data="history_6")],
            [InlineKeyboardButton("📅 Последние 24 часа", callback_data="history_24")],
            [InlineKeyboardButton("📊 Текущие показания", callback_data="status_now")],
            [InlineKeyboardButton("🔙 Назад", callback_data="bot_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if message_id:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    async def handle_history_selection(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора периода истории"""
        data = query.data
        hours = int(data.split("_")[1])
        
        await self.send_history_data(query, context, hours)
    
    async def send_history_data(self, query, context: ContextTypes.DEFAULT_TYPE, hours: int):
        """Отправка исторических данных"""
        await query.edit_message_text(
            f"📥 Загружаю данные за {hours} час(ов)...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        data = self.monitor.get_historical_data(hours)
        
        if not data['success'] or not data['data']:
            await query.edit_message_text(
                "❌ Не удалось загрузить исторические данные",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        history = data['data']
        
        # Вычисляем статистику
        temps = [h['temperature'] for h in history if h['temperature'] is not None]
        hums = [h['humidity'] for h in history if h['humidity'] is not None]
        
        if not temps or not hums:
            await query.edit_message_text(
                "❌ Нет данных за выбранный период",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Формируем текстовый отчет
        message = f"""
📊 *ИСТОРИЯ ДАННЫХ за {hours} час(ов)*

*🌡️ Температура:*
• Текущая: {temps[-1]:.1f}°C
• Средняя: {sum(temps)/len(temps):.1f}°C
• Минимум: {min(temps):.1f}°C
• Максимум: {max(temps):.1f}°C

*💧 Влажность:*
• Текущая: {hums[-1]:.1f}%
• Средняя: {sum(hums)/len(hums):.1f}%
• Минимум: {min(hums):.1f}%
• Максимум: {max(hums):.1f}%

*📈 Всего записей:* {len(history)}
*⏰ Период:* {hours} час(ов)

*Последние 5 записей:*
"""
        
        # Добавляем последние записи
        for i, record in enumerate(history[-5:][::-1], 1):
            message += f"\n{i}. {record['time']} - {record['temperature']:.1f}°C, {record['humidity']:.1f}%"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data=f"history_{hours}")],
            [InlineKeyboardButton("📈 Другой период", callback_data="history_menu")],
            [InlineKeyboardButton("📊 Текущие показания", callback_data="status_now")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    # ======================= НАСТРОЙКИ БОТА =======================
    
    async def show_bot_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ настроек бота"""
        await self._send_bot_settings(update.effective_chat.id, context)
    
    async def show_bot_settings_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показ настроек бота (callback)"""
        await self._send_bot_settings(query.message.chat_id, context, query.message.message_id)
    
    async def _send_bot_settings(self, chat_id, context, message_id=None):
        """Внутренняя функция отправки настроек бота"""
        user_id = chat_id
        user_settings = USER_SETTINGS.get(user_id, {})
        
        message = f"""
⚙️ *НАСТРОЙКИ БОТА*

*Текущие настройки:*
• 🔔 Оповещения: {"✅ ВКЛ" if user_settings.get('alerts_enabled', True) else "❌ ВЫКЛ"}
• 📢 Уведомления: {', '.join(user_settings.get('notify_via', ['telegram']))}
• 🚨 Критические: {"✅ ВКЛ" if user_settings.get('notify_critical', True) else "❌ ВЫКЛ"}
• ⚠️ Предупреждения: {"✅ ВКЛ" if user_settings.get('notify_warnings', True) else "❌ ВЫКЛ"}

Выберите настройку для изменения:
        """
        
        keyboard = [
            [InlineKeyboardButton("🔔 Управление оповещениями", callback_data="alerts_menu")],
            [InlineKeyboardButton("📊 Текущие показания", callback_data="status_now")],
            [InlineKeyboardButton("📈 История данных", callback_data="history_menu")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if message_id:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    async def handle_bot_settings(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработка настроек бота"""
        data = query.data
        
        if data == "setting_notify":
            await self._configure_notifications(query, context)
    
    async def _configure_notifications(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Настройка уведомлений"""
        user_id = query.from_user.id
        user_settings = USER_SETTINGS.get(user_id, {})
        
        message = """
📢 *НАСТРОЙКА УВЕДОМЛЕНИЙ*

Выберите способы получения уведомлений:
        """
        
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Telegram" if 'telegram' in user_settings.get('notify_via', ['telegram']) else "Telegram",
                    callback_data="toggle_telegram"
                )
            ],
            [InlineKeyboardButton("🔙 Назад", callback_data="bot_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    # ======================= СТАТИСТИКА =======================
    
    async def show_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ статистики"""
        data = self.monitor.get_historical_data(24, 100)
        
        if not data['success'] or not data['data']:
            await update.message.reply_text(
                "❌ Не удалось загрузить статистику",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        history = data['data']
        
        # Вычисляем статистику
        temps = [h['temperature'] for h in history if h['temperature'] is not None]
        hums = [h['humidity'] for h in history if h['humidity'] is not None]
        
        if not temps or not hums:
            await update.message.reply_text(
                "❌ Нет данных для статистики",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Находим аномалии
        temp_alerts = []
        hum_alerts = []
        
        for record in history:
            temp = record['temperature']
            hum = record['humidity']
            
            if temp and (temp < ALERT_SETTINGS['temperature']['min'] or 
                        temp > ALERT_SETTINGS['temperature']['max']):
                temp_alerts.append(record)
            
            if hum and (hum < ALERT_SETTINGS['humidity']['min'] or 
                       hum > ALERT_SETTINGS['humidity']['max']):
                hum_alerts.append(record)
        
        message = f"""
📈 *СТАТИСТИКА ЗА 24 ЧАСА*

*🌡️ Температура:*
• Записей: {len(temps)}
• Средняя: {sum(temps)/len(temps):.1f}°C
• Минимум: {min(temps):.1f}°C
• Максимум: {max(temps):.1f}°C
• Аномалий: {len(temp_alerts)}

*💧 Влажность:*
• Записей: {len(hums)}
• Средняя: {sum(hums)/len(hums):.1f}%
• Минимум: {min(hums):.1f}%
• Максимум: {max(hums):.1f}%
• Аномалий: {len(hum_alerts)}

*🔔 Границы оповещений:*
• Температура: {ALERT_SETTINGS['temperature']['min']}°C - {ALERT_SETTINGS['temperature']['max']}°C
• Влажность: {ALERT_SETTINGS['humidity']['min']}% - {ALERT_SETTINGS['humidity']['max']}%

*📊 Общая статистика:*
• Всего записей: {len(history)}
• Процент аномалий: {(len(temp_alerts) + len(hum_alerts)) / len(history) * 100:.1f}%
• Последняя запись: {history[-1]['time']}
        """
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    # ======================= ОБРАБОТКА ВВОДА =======================
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user_input = update.message.text.strip()
        user_id = update.effective_user.id
        
        if 'awaiting_input' in context.user_data:
            input_type = context.user_data['awaiting_input']
            
            try:
                value = int(user_input)
                
                if input_type == 'temp_min':
                    # Проверяем, что минимум меньше максимума
                    if value < ALERT_SETTINGS['temperature']['max']:
                        ALERT_SETTINGS['temperature']['min'] = value
                        await update.message.reply_text(
                            f"✅ Минимальная температура установлена: {value}°C\n\nТеперь введите максимальную температуру:",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        context.user_data['awaiting_input'] = 'temp_max'
                    else:
                        await update.message.reply_text(
                            f"❌ Минимальная температура должна быть меньше максимальной ({ALERT_SETTINGS['temperature']['max']}°C)\nПопробуйте снова:",
                            parse_mode=ParseMode.MARKDOWN
                        )
                
                elif input_type == 'temp_max':
                    # Проверяем, что максимум больше минимума
                    if value > ALERT_SETTINGS['temperature']['min']:
                        ALERT_SETTINGS['temperature']['max'] = value
                        await update.message.reply_text(
                            f"✅ Настройки температуры обновлены!\nНовые пределы: {ALERT_SETTINGS['temperature']['min']}°C - {value}°C",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        del context.user_data['awaiting_input']
                        
                        # Возвращаем в меню
                        await asyncio.sleep(2)
                        await self._send_alerts_menu(update.effective_chat.id, context)
                    else:
                        await update.message.reply_text(
                            f"❌ Максимальная температура должна быть больше минимальной ({ALERT_SETTINGS['temperature']['min']}°C)\nПопробуйте снова:",
                            parse_mode=ParseMode.MARKDOWN
                        )
                
                elif input_type == 'hum_min':
                    if value < ALERT_SETTINGS['humidity']['max']:
                        ALERT_SETTINGS['humidity']['min'] = value
                        await update.message.reply_text(
                            f"✅ Минимальная влажность установлена: {value}%\n\nТеперь введите максимальную влажность:",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        context.user_data['awaiting_input'] = 'hum_max'
                    else:
                        await update.message.reply_text(
                            f"❌ Минимальная влажность должна быть меньше максимальной ({ALERT_SETTINGS['humidity']['max']}%)\nПопробуйте снова:",
                            parse_mode=ParseMode.MARKDOWN
                        )
                
                elif input_type == 'hum_max':
                    if value > ALERT_SETTINGS['humidity']['min']:
                        ALERT_SETTINGS['humidity']['max'] = value
                        await update.message.reply_text(
                            f"✅ Настройки влажности обновлены!\nНовые пределы: {ALERT_SETTINGS['humidity']['min']}% - {value}%",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        del context.user_data['awaiting_input']
                        
                        # Возвращаем в меню
                        await asyncio.sleep(2)
                        await self._send_alerts_menu(update.effective_chat.id, context)
                    else:
                        await update.message.reply_text(
                            f"❌ Максимальная влажность должна быть больше минимальной ({ALERT_SETTINGS['humidity']['min']}%)\nПопробуйте снова:",
                            parse_mode=ParseMode.MARKDOWN
                        )
            
            except ValueError:
                await update.message.reply_text(
                    "❌ Пожалуйста, введите целое число:",
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await update.message.reply_text(
                "ℹ️ Используйте команды или кнопки для управления ботом.\n"
                "Нажмите /start для отображения меню.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    # ======================= ОТПРАВКА ОПОВЕЩЕНИЙ =======================
    
    async def _send_alert_notification(self, context, user_id, alerts, sensor_data):
        """Отправка уведомления об аварии"""
        # Проверяем, нужно ли отправлять оповещение (избегаем спама)
        now = datetime.now()
        alert = alerts[0]  # Берем первое оповещение
        
        alert_key = f"{user_id}_{alert['type']}_{alert['level']}"
        
        if alert_key in ALERT_HISTORY:
            last_notify = ALERT_HISTORY[alert_key]
            interval = ALERT_SETTINGS[alert['type']]['notify_every_minutes']
            
            if now - last_notify < timedelta(minutes=interval):
                return  # Не отправляем, если не прошло достаточно времени
        
        ALERT_HISTORY[alert_key] = now
        
        # Формируем сообщение
        alert_messages = []
        for alert in alerts:
            alert_messages.append(f"{alert['emoji']} *{alert['message']}*")
        
        message = "\n\n".join(alert_messages)
        
        # Добавляем текущие показания
        message += f"\n\n📊 *Текущие показания:*"
        message += f"\n🌡️ Температура: {sensor_data['temperature'] if sensor_data['temperature'] is not None else 'N/A'}°C"
        message += f"\n💧 Влажность: {sensor_data['humidity'] if sensor_data['humidity'] is not None else 'N/A'}%"
        
        # Добавляем время
        try:
            dt = datetime.strptime(sensor_data['timestamp'], "%Y-%m-%dT%H:%M:%SZ")
            time_str = dt.strftime("%H:%M:%S")
        except:
            time_str = sensor_data['timestamp']
        
        message += f"\n⏰ Время: {time_str}"
        
        # Добавляем действия
        message += "\n\n*Действия:*"
        message += "\n/status - Проверить текущие показания"
        message += "\n/alerts - Изменить настройки оповещений"
        
        # Клавиатура для быстрых действий
        keyboard = [
            [InlineKeyboardButton("📊 Проверить сейчас", callback_data="status_now")],
            [InlineKeyboardButton("⚙️ Изменить настройки", callback_data="alerts_menu")],
            [InlineKeyboardButton("🔕 Выключить оповещения", callback_data="disable_alerts")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            logger.info(f"Alert sent to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send alert to user {user_id}: {e}")
    
    # ======================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =======================
    
    def _get_temperature_status(self, temp):
        """Получить статус температуры"""
        if temp is None:
            return {'emoji': '❓', 'text': 'Нет данных'}
        
        if temp < ALERT_SETTINGS['temperature']['min']:
            return {'emoji': '❄️', 'text': 'НИЖЕ НОРМЫ'}
        elif temp > ALERT_SETTINGS['temperature']['max']:
            return {'emoji': '🔥', 'text': 'ВЫШЕ НОРМЫ'}
        elif temp < 18:
            return {'emoji': '⛄', 'text': 'Прохладно'}
        elif temp < 25:
            return {'emoji': '😊', 'text': 'Нормально'}
        else:
            return {'emoji': '😅', 'text': 'Тепло'}
    
    def _get_humidity_status(self, hum):
        """Получить статус влажности"""
        if hum is None:
            return {'emoji': '❓', 'text': 'Нет данных'}
        
        if hum < ALERT_SETTINGS['humidity']['min']:
            return {'emoji': '🏜️', 'text': 'НИЖЕ НОРМЫ'}
        elif hum > ALERT_SETTINGS['humidity']['max']:
            return {'emoji': '💦', 'text': 'ВЫШЕ НОРМЫ'}
        elif hum < 40:
            return {'emoji': '🌵', 'text': 'Сухо'}
        elif hum < 60:
            return {'emoji': '😊', 'text': 'Нормально'}
        else:
            return {'emoji': '🌧️', 'text': 'Влажно'}
    
    # ======================= ЗАПУСК БОТА =======================
    
    def setup_handlers(self, application):
        """Настройка обработчиков команд"""
        
        # Команды
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("alerts", self.alerts_command))
        application.add_handler(CommandHandler("history", self.history_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("settings", self.settings_command))
        application.add_handler(CommandHandler("help", self.help_command))
        
        # Обработчики кнопок
        application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Обработчики сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # УБРАЛИ JobQueue - теперь оповещения только при запросе данных
    
    async def post_init(self, application):
        """Действия после инициализации"""
        # Установка команд меню
        commands = [
            BotCommand("start", "Запустить бота"),
            BotCommand("status", "Текущие показания"),
            BotCommand("alerts", "Настройка оповещений"),
            BotCommand("history", "История данных"),
            BotCommand("stats", "Статистика"),
            BotCommand("settings", "Настройки бота"),
            BotCommand("help", "Помощь")
        ]
        
        await application.bot.set_my_commands(commands)
        
        logger.info("Бот успешно инициализирован")

def main():
    """Основная функция запуска бота"""
    print("="*60)
    print("🔥 ЗАПУСК ТЕЛЕГРАМ-БОТА ДЛЯ IoT МОНИТОРИНГА")
    print("="*60)
    print(f"Канал ThingSpeak: {THINGSPEAK_CHANNEL_ID}")
    print(f"Токен бота: {TELEGRAM_BOT_TOKEN[:10]}...")
    print("="*60)
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Создаем менеджер бота
    bot_manager = TelegramBotManager()
    
    # Настраиваем обработчики
    bot_manager.setup_handlers(application)
    
    # Запускаем бота
    print("🤖 Бот запущен! Ожидаем сообщений...")
    print("="*60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()