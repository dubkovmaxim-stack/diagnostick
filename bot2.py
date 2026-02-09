#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
РЕМОНТ АУДИТ БОТ - ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ВЕРСИЯ 2.0
Исправления:
1. Работающие кнопки во всех состояниях
2. Логика ответвлений для разных стадий
3. Умные переходы между вопросами
4. Персонализированные расчёты и рекомендации
5. Все inline-кнопки работают
"""

import asyncio
import logging
import os
import sys
import random
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from ai_logic import ai_engine

# ============ НАСТРОЙКА ПУТЕЙ ============
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

print(f"📁 Текущая папка: {CURRENT_DIR}")

# ============ ЛОГИРОВАНИЕ ============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("repair_bot_fixed_v2.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# ============ КОНФИГ ============
env_path = os.path.join(CURRENT_DIR, ".env")
if not os.path.exists(env_path):
    logger.error(f"❌ Файл .env не найден: {env_path}")
    print(f"❌ Создайте файл .env в папке: {CURRENT_DIR}")
    sys.exit(1)

load_dotenv(dotenv_path=env_path)

REPAIR_TOKEN = os.getenv("REPAIR_BOT_TOKEN", "").strip()
REPAIR_ADMIN = os.getenv("REPAIR_ADMIN_ID", "0").strip()

if not REPAIR_TOKEN:
    logger.error("❌ REPAIR_BOT_TOKEN не установлен")
    print("❌ Установите REPAIR_BOT_TOKEN в файле .env")
    sys.exit(1)

try:
    REPAIR_ADMIN = int(REPAIR_ADMIN)
except ValueError:
    REPAIR_ADMIN = 0

# Контактные данные эксперта
EXPERT_PHONE = "+79615223190"
EXPERT_TELEGRAM = "@systemkontrolrem"
EXPERT_SHORT = "systemkontrolrem"

# Цены
PRICE_NORMAL = 9900
PRICE_DISCOUNT = 4900
PRICE_VIP = 29900

print(f"✅ Токен загружен")
print(f"✅ Эксперт: {EXPERT_PHONE} | {EXPERT_TELEGRAM}")
print(f"✅ Цены: {PRICE_DISCOUNT}₽ (со скидкой) | {PRICE_VIP}₽ (VIP)")

# ============ СОСТОЯНИЯ ============
class RepairStates(StatesGroup):
    repair_waiting_stage = State()
    repair_waiting_area = State()
    repair_waiting_control = State()
    repair_waiting_fixation = State()
    repair_calculating = State()
    repair_showing_results = State()
    repair_showing_offer = State()
    repair_choosing_offer = State()
    repair_waiting_phone = State()
    repair_waiting_question = State()
    repair_changing_answer = State()  # новое состояние для изменения ответов

# ============ ХРАНИЛИЩЕ ============
class RepairStorage:
    def __init__(self):
        self.user_data: Dict[int, Dict] = {}
    
    async def save(self, user_id: int, data: dict):
        if user_id not in self.user_data:
            self.user_data[user_id] = {"history": []}
        self.user_data[user_id].update(data)
        if "answer" in data:
            self.user_data[user_id]["history"].append({
                "state": data.get("state"),
                "answer": data.get("answer"),
                "timestamp": datetime.now().isoformat()
            })
    
    async def get(self, user_id: int) -> Optional[Dict]:
        return self.user_data.get(user_id)
    
    async def get_history(self, user_id: int) -> List:
        data = await self.get(user_id)
        return data.get("history", []) if data else []
    
    async def clear_last_answer(self, user_id: int):
        """Удалить последний ответ из истории"""
        if user_id in self.user_data and self.user_data[user_id]["history"]:
            self.user_data[user_id]["history"].pop()

repair_db = RepairStorage()

# ============ УМНЫЙ КАЛЬКУЛЯТОР С РЕАЛЬНЫМИ ЦИФРАМИ ============
class IntelligentLossCalculator:
    """Умный калькулятор потерь с логикой ответвлений"""
    
    # Базовые потери для разных стадий (в тыс руб)
    STAGE_BASE_LOSSES = {
        "not_started": {
            "name": "Ещё не начали",
            "base_range": (50, 300),  # в тыс ₽
            "risk_factors": [
                ("planning", 1.3, "Отсутствие детального плана"),
                ("contract", 1.4, "Неправильный договор"),
                ("specs", 1.2, "Нет технического задания"),
                ("budget", 1.3, "Неполный бюджет"),
            ],
            "skip_fixation": True,  # пропустить вопрос о фиксации
            "skip_control": False,  # НЕ пропускать вопрос о контроле
            "examples": [
                ("Переделки электрики", "80-150 тыс ₽", "После начала работ оказалось, что розетки не там"),
                ("Доплаты за изменения", "30-80 тыс ₽", "Постоянные правки в процессе"),
                ("Штрафы за просрочку", "20-50 тыс ₽", "Нет чётких сроков в договоре"),
            ],
            "emotional_hook": "💰 *Это деньги на новую кухню или диван*",
        },
        "demolition": {
            "name": "Демонтаж",
            "base_range": (30, 200),
            "risk_factors": [
                ("damage", 1.4, "Повреждение конструкций"),
                ("documentation", 1.3, "Нет фотофиксации ДО"),
                ("rubbish", 1.2, "Проблемы с вывозом мусора"),
                ("neighbors", 1.5, "Конфликты с соседями"),
            ],
            "skip_fixation": False,
            "skip_control": False,
            "examples": [
                ("Повреждён стояк", "100-200 тыс ₽", "Замена + компенсация соседям"),
                ("Не вывезли мусор", "20-50 тыс ₽", "Штрафы + срочный вывоз"),
                ("Сломали не то", "30-80 тыс ₽", "Восстановление + доплата"),
            ],
            "emotional_hook": "🏗️ *Эти деньги могли пойти на новые окна*",
        },
        "rough": {
            "name": "Черновые работы",
            "base_range": (80, 300),
            "risk_factors": [
                ("plaster", 1.5, "Кривая штукатурка"),
                ("electric", 1.4, "Ошибки в электрике"),
                ("plumbing", 1.6, "Проблемы с сантехникой"),
                ("levels", 1.3, "Неровные полы/потолки"),
            ],
            "skip_fixation": False,
            "skip_control": False,
            "examples": [
                ("Кривые стены", "80-250 тыс ₽", "Мебель не встаёт ровно"),
                ("Электрика не работает", "50-200 тыс ₽", "Вскрытие штроб + переделка"),
                ("Протечки сантехники", "60-180 тыс ₽", "Ремонт у соседей + свой ремонт"),
            ],
            "emotional_hook": "🔧 *Сумма, за которую можно сделать весь пол с подогревом*",
        },
        "finishing": {
            "name": "Чистовая отделка",
            "base_range": (60, 250),
            "risk_factors": [
                ("tiles", 1.4, "Плитка отваливается"),
                ("paint", 1.3, "Кривая покраска"),
                ("joints", 1.2, "Неровные стыки"),
                ("materials", 1.4, "Не те материалы"),
            ],
            "skip_fixation": False,
            "skip_control": False,
            "examples": [
                ("Отвалилась плитка", "50-200 тыс ₽", "Новый материал + работа"),
                ("Неровная покраска", "60-120 тыс ₽", "Шлифовка + перекраска"),
                ("Щели в стыках", "40-100 тыс ₽", "Демонтаж + переделка"),
            ],
            "emotional_hook": "🎨 *Этих денег хватило бы на дизайнерскую мебель*",
        },
        "living": {
            "name": "Уже живём",
            "base_range": (100, 500),
            "risk_factors": [
                ("hidden_defects", 1.6, "Скрытые дефекты"),
                ("warranty", 1.8, "Гарантия закончилась"),
                ("repairs", 1.4, "Дорогие переделки"),
                ("stress", 1.3, "Стресс и нервы"),
            ],
            "skip_fixation": False,  # всё равно спрашиваем о фиксации (ретроспективно)
            "skip_control": True,   # пропустить вопрос о контроле (уже поздно)
            "examples": [
                ("Протечка в ванной", "100-300 тыс ₽", "Ремонт соседей + свой ремонт"),
                ("Электрика не работает", "50-150 тыс ₽", "Вскрытие стен + поиск проблемы"),
                ("Отслоилась отделка", "80-200 тыс ₽", "Полный передел участка"),
            ],
            "emotional_hook": "🏠 *Сумма, которую ты мог вложить в следующую квартиру*",
        }
    }
    
    # Мультипликаторы для площади (база = 50-80 м²)
    AREA_MULTIPLIERS = {
        "small": 0.6,      # до 50 м²
        "medium": 1.0,     # 50-80 м²
        "large": 1.3,      # 80-120 м²
        "xlarge": 1.7,     # 120+ м²
        "unknown": 1.0,
    }
    
    # Мультипликаторы для контроля
    CONTROL_MULTIPLIERS = {
        "self": 1.4,       # сам/сама
        "foreman": 1.0,    # прораб
        "nobody": 1.8,     # никто
        "unknown": 1.5,    # не думал(а)
        "skip": 1.0,       # если вопрос пропущен
    }
    
    # Мультипликаторы для фиксации
    FIXATION_MULTIPLIERS = {
        "full": 0.9,           # полностью зафиксировано
        "partial": 1.0,        # частично
        "none": 1.3,           # никак
        "planned_full": 1.0,   # планирую фиксировать всё
        "planned_none": 1.4,   # не думал(а) об этом
        "skip": 1.0,           # если вопрос пропущен
    }
    
    @staticmethod
    def get_stage_code(text: str) -> str:
        mapping = {
            "Ещё не начали (только планирую)": "not_started",
            "Демонтаж (ломаем, убираем старое)": "demolition",
            "Черновые работы (штукатурка, электрика)": "rough",
            "Чистовая отделка (плитка, обои, покраска)": "finishing",
            "Уже живём после ремонта": "living"
        }
        return mapping.get(text, "not_started")
    
    @staticmethod
    def get_area_code(text: str) -> str:
        mapping = {
            "До 50 м² (студия/1-комнатная)": "small",
            "50-80 м² (2-комнатная)": "medium",
            "80-120 м² (3-комнатная)": "large",
            "120+ м² (4+ комнат/дом)": "xlarge",
            "Не знаю точно": "unknown"
        }
        return mapping.get(text, "unknown")
    
    @staticmethod
    def get_control_code(text: str) -> str:
        mapping = {
            "Я сам/сама (но не специалист)": "self",
            "Прораб/подрядчик (он отвечает за всё)": "foreman",
            "Никто толком не контролирует": "nobody",
            "Не думал(а) об этом": "unknown",
            "Уже поздно (ремонт закончен)": "skip"
        }
        return mapping.get(text, "unknown")
    
    @staticmethod
    def get_fixation_code(text: str, stage: str = "not_started") -> str:
        if stage == "not_started":
            mapping = {
                "Планирую фиксировать всё фото/видео": "planned_full",
                "Ещё не думал(а) об этом": "planned_none"
            }
        elif stage == "living":
            mapping = {
                "Были зафиксированы фото/видео": "full",
                "Фотографировали частично": "partial",
                "Ничего не фиксировали": "none",
                "Не помню/не знаю": "planned_none"
            }
        else:
            mapping = {
                "Зафиксированы фото/видео полностью": "full",
                "Фотографировал(а) частично": "partial",
                "Никак не фиксировались, надеюсь на мастеров": "none"
            }
        return mapping.get(text, "planned_none")
    
    @classmethod
    def should_skip_control(cls, stage: str) -> bool:
        """Нужно ли пропускать вопрос о контроле для этой стадии"""
        stage_data = cls.STAGE_BASE_LOSSES.get(stage)
        return stage_data.get("skip_control", False) if stage_data else False
    
    @classmethod
    def should_skip_fixation(cls, stage: str) -> bool:
        """Нужно ли пропускать вопрос о фиксации для этой стадии"""
        stage_data = cls.STAGE_BASE_LOSSES.get(stage)
        return stage_data.get("skip_fixation", False) if stage_data else False
    
    @classmethod
    def calculate_intelligent_loss(cls, stage: str, area: str, control: str, fixation: str) -> dict:
        """Умный расчёт потерь с учётом всех факторов"""
        stage_data = cls.STAGE_BASE_LOSSES.get(stage, cls.STAGE_BASE_LOSSES["not_started"])
        
        # Базовые значения
        base_min, base_max = stage_data["base_range"]
        base_avg = (base_min + base_max) / 2
        
        # Мультипликаторы
        area_mult = cls.AREA_MULTIPLIERS.get(area, 1.0)
        
        # Если контроль пропущен (для стадии "living")
        if control == "skip":
            control_mult = cls.CONTROL_MULTIPLIERS["skip"]
        else:
            control_mult = cls.CONTROL_MULTIPLIERS.get(control, 1.0)
        
        # Если фиксация пропущена (для стадии "not_started")
        if fixation == "skip":
            fixation_mult = cls.FIXATION_MULTIPLIERS["skip"]
        else:
            fixation_mult = cls.FIXATION_MULTIPLIERS.get(fixation, 1.0)
        
        # Комбинированный мультипликатор
        total_mult = area_mult * control_mult * fixation_mult
        
        # Итоговые потери (в тыс ₽)
        loss_min = base_min * total_mult
        loss_max = base_max * total_mult
        loss_avg = base_avg * total_mult
        
        # Округление до тысяч
        loss_min = round(loss_min) * 1000
        loss_max = round(loss_max) * 1000
        loss_avg = round(loss_avg) * 1000
        
        # Выбор персонализированных примеров
        examples = stage_data["examples"]
        if stage == "not_started" and control == "self":
            examples = [
                ("Самоконтроль без знаний", "80-200 тыс ₽", "Не заметил ошибок вовремя"),
                ("Нет технической экспертизы", "50-150 тыс ₽", "Принял некачественную работу"),
            ] + examples[:1]
        
        # Эмоциональный якорь
        emotional_hook = stage_data["emotional_hook"]
        
        # Ключевая контрольная точка
        checkpoints = {
            "not_started": "📝 Детальное ТЗ + прописанный договор с ответственностью",
            "demolition": "📸 Фотофиксация ДО/ПОСЛЕ + акт скрытых работ",
            "rough": "📐 Лазерный уровень + проверка СНИПов + фото всех узлов",
            "finishing": "🔍 Проверка стыков + тест на адгезию + поэтапная оплата",
            "living": "⚖️ Гарантийные акты + тесты под нагрузкой + видеофиксация состояния"
        }
        checkpoint = checkpoints.get(stage, "Регулярный контроль всех этапов")
        
        return {
            "min": loss_min,
            "max": loss_max,
            "avg": loss_avg,
            "stage_name": stage_data["name"],
            "examples": examples,
            "emotional_hook": emotional_hook,
            "checkpoint": checkpoint,
            "multipliers": {
                "area": area_mult,
                "control": control_mult,
                "fixation": fixation_mult,
                "total": round(total_mult, 2)
            }
        }
    
    @staticmethod
    def format_money(amount: float) -> str:
        """Форматирование суммы денег"""
        if amount >= 1000000:
            return f"{amount/1000000:.1f} млн ₽"
        elif amount >= 100000:
            return f"{int(amount/1000)} тыс ₽"
        elif amount >= 1000:
            return f"{int(amount/1000)} тыс ₽"
        else:
            return f"{int(amount)} ₽"

calculator = IntelligentLossCalculator()

# ============ УМНЫЕ ПАУЗЫ ============
async def smart_pause(seconds: float = 1.5):
    """Умная пауза с обработкой ошибок"""
    try:
        await asyncio.sleep(seconds)
    except (asyncio.CancelledError, Exception):
        pass

# ============ КЛАВИАТУРЫ ============
def get_repair_kb_start() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="👉 НАЧАТЬ ДИАГНОСТИКУ")]],
        resize_keyboard=True
    )

def get_repair_kb_stage(show_back: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="Ещё не начали (только планирую)")],
        [KeyboardButton(text="Демонтаж (ломаем, убираем старое)")],
        [KeyboardButton(text="Черновые работы (штукатурка, электрика)")],
        [KeyboardButton(text="Чистовая отделка (плитка, обои, покраска)")],
        [KeyboardButton(text="Уже живём после ремонта")]
    ]
    if show_back:
        buttons.append([KeyboardButton(text="◀️ Изменить предыдущий ответ")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

def get_repair_kb_area(show_back: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="До 50 м² (студия/1-комнатная)")],
        [KeyboardButton(text="50-80 м² (2-комнатная)")],
        [KeyboardButton(text="80-120 м² (3-комнатная)")],
        [KeyboardButton(text="120+ м² (4+ комнат/дом)")],
        [KeyboardButton(text="Не знаю точно")]
    ]
    if show_back:
        buttons.append([KeyboardButton(text="◀️ Изменить предыдущий ответ")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

def get_repair_kb_control(show_back: bool = False, for_living: bool = False) -> ReplyKeyboardMarkup:
    """Клавиатура для контроля (разные варианты для living)"""
    if for_living:
        buttons = [
            [KeyboardButton(text="Я сам/сама (но не специалист)")],
            [KeyboardButton(text="Прораб/подрядчик (он отвечает за всё)")],
            [KeyboardButton(text="Никто толком не контролирует")],
            [KeyboardButton(text="Уже поздно (ремонт закончен)")]
        ]
    else:
        buttons = [
            [KeyboardButton(text="Я сам/сама (но не специалист)")],
            [KeyboardButton(text="Прораб/подрядчик (он отвечает за всё)")],
            [KeyboardButton(text="Никто толком не контролирует")],
            [KeyboardButton(text="Не думал(а) об этом")]
        ]
    
    if show_back:
        buttons.append([KeyboardButton(text="◀️ Изменить предыдущий ответ")])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

def get_repair_kb_fixation(show_back: bool = False, stage: str = "not_started") -> ReplyKeyboardMarkup:
    """Клавиатура для фиксации с учётом стадии"""
    if stage == "not_started":
        buttons = [
            [KeyboardButton(text="Планирую фиксировать всё фото/видео")],
            [KeyboardButton(text="Ещё не думал(а) об этом")]
        ]
    elif stage == "living":
        buttons = [
            [KeyboardButton(text="Были зафиксированы фото/видео")],
            [KeyboardButton(text="Фотографировали частично")],
            [KeyboardButton(text="Ничего не фиксировали")],
            [KeyboardButton(text="Не помню/не знаю")]
        ]
    else:
        buttons = [
            [KeyboardButton(text="Зафиксированы фото/видео полностью")],
            [KeyboardButton(text="Фотографировал(а) частично")],
            [KeyboardButton(text="Никак не фиксировались, надеюсь на мастеров")]
        ]
    
    if show_back:
        buttons.append([KeyboardButton(text="◀️ Изменить предыдущий ответ")])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

def get_repair_kb_results() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="👉 ПОКАЖИ РЕШЕНИЕ")],
        
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_repair_kb_offer() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="💳 Купить систему")],
        [KeyboardButton(text="📱 Оставить номер для связи")],
        [KeyboardButton(text="🧮 Рассчитать точную смету")],
        [KeyboardButton(text="🤖 Получить AI-консультацию")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_repair_kb_phone() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📞 Отправить мой номер", request_contact=True)],
        [KeyboardButton(text="✏️ Ввести номер вручную")],
        [KeyboardButton(text="⏪ Назад к выбору")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

def get_inline_payment_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="💳 Купить систему за 4 900 ₽", url="https://t.me/systemkontrolrem")],
        [InlineKeyboardButton(text="👑 VIP за 29 900 ₽", url="https://t.me/systemkontrolrem")],
        [InlineKeyboardButton(text="💬 Задать вопрос в боте", callback_data="ask_question")],
        [InlineKeyboardButton(text="📞 Позвонить эксперту", callback_data="call_expert")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_inline_expert_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📞 Позвонить сейчас", url=f"tel:{EXPERT_PHONE}")],
        [InlineKeyboardButton(text="✉️ Написать в Telegram", url=f"https://t.me/{EXPERT_SHORT}")],
        [InlineKeyboardButton(text="💬 Задать вопрос в боте", callback_data="ask_question_bot")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ============ ТЕКСТЫ С ВЕТВЛЕНИЯМИ ============
REPAIR_TEXTS = {
    "start": """🏠 *ПРИВЕТ!*

Это быстрая диагностика твоей ситуации в ремонте.

Ответь на несколько вопросов — и узнаешь:
• На каком этапе уже теряешь деньги  
• Конкретно сколько можешь потерять
• Как это предотвратить

*Готов пройти диагностику за 2 минуты?*""",
    
    "stage_question": """🔍 *Вопрос 1 из 4*

На какой стадии сейчас твой ремонт?""",
    
    "area_question": """📏 *Вопрос 2 из 4*

Для точности расчёта: какая общая площадь ремонта?""",
    
    "control_question": """👷 *Вопрос 3 из 4*

Кто принимает работы у подрядчиков?""",
    
    "control_question_living": """👷 *Вопрос 3 из 4* *(ретроспективно)*

Кто принимал работы у подрядчиков, когда ремонт шёл?""",
    
    "fixation_question": """📸 *Вопрос 4 из 4*

Скрытые работы не забываешь фиксировать (примыкания узлов, сантехника,электрика в стенах, трассы кондиционирования, состояние стояка и труб отопления, состояние окон и подоконников) у тебя:""",
    
    "fixation_question_not_started": """📸 *Вопрос 4 из 4*

Планируешь ли ты фиксировать скрытые работы (примыкания узлов, сантехника,электрика в стенах, трассы кондиционирования, состояние стояка и труб отопления, состояние окон и подоконников) фото/видео?""",
    
    "fixation_question_living": """📸 *Вопрос 4 из 4* *(ретроспективно)*

Скрытые работы (примыкания узлов, сантехника,электрика в стенах, трассы кондиционирования, состояние стояка и труб отопления, состояние окон и подоконников) были зафиксированы фото/видео?""",
    
    "calculating": [
        "⏳ *Анализирую твои ответы...*",
        "📊 *Сравниваю с сотнями похожих кейсов...*",
        "🔍 *Ищу слабые места в твоей ситуации...*",
        "💰 *Рассчитываю потенциальные потери...*",
        "✅ *Готово! Смотри результаты.*"
    ],
    
    "results_pause": """
💭 *Пауза.*

Ты сейчас представил эти деньги?
Это не абстрактные цифры.

Это конкретно:
• *Новая кухня*
• *Диван в гостиную*  
• *Отпуск с семьёй*
• *Обучение детей*

Эти деньги могут *УЙТИ* на переделки.
Или *ОСТАТЬСЯ* у тебя.

*Вопрос:* что выбираешь?
""",
    
    "solution_intro": """
🎯 *ПРОБЛЕМА НЕ В МАСТЕРАХ.*
*Проблема — в ОТСУТСТВИИ СИСТЕМЫ КОНТРОЛЯ.*

Контроль — это *не конфликт*.
Контроль — это *понимание:* ЧТО, КОГДА и КАК проверять.

Я создал *«СИСТЕМУ КОНТРОЛЯ РЕМОНТА»* — это готовое решение для таких ситуаций, как твоя.
""",
    
    "system_details": """
📦 *ЧТО ВНУТРИ СИСТЕМЫ:*

1. 📋 *47 КОНТРОЛЬНЫХ ТОЧЕК*
   От демонтажа до уборки. Точно знаешь, что проверять.

2. 🎬 *ВИДЕО-ИНСТРУКЦИИ*
   Показ: "Вот так проверяй углы, вот так — уровни"

3. 📝 *ГОТОВЫЕ ДОКУМЕНТЫ*
   Акт скрытых работ, дефектная ведомость — бери и заполняй

4. 💬 *СКРИПТЫ РАЗГОВОРОВ*
   Как сказать прорабу о проблеме без скандала

🎯 *РЕЗУЛЬТАТ ДЛЯ ТЕБЯ:*

✔ Экономия *20-40% бюджета* (твои деньги остаются у тебя)
✔ Сокращение сроков на *15-30%* (не 6 месяцев, а 4)
✔ *0 спорных ситуаций* с подрядчиком (всё по документам)
✔ *Нервы и время* остаются при тебе
""",
    
    "price_info": """
💰 *СТОИМОСТЬ:*

• *Обычная цена:* {normal_price:,} ₽
• *СЕГОДНЯ со скидкой:* {discount_price:,} ₽
• *VIP пакет:* {vip_price:,} ₽ (с личной консультацией)

📊 *ТВОЯ ВЫГОДА:*
Система: {discount_price:,} ₽
Экономия: от 200 000 ₽
ROI: *4 000%* (в 40 раз больше)

⏰ *ОКУПАЕМОСТЬ:* 2-3 недели
(первая же предотвращённая ошибка окупает систему)
""",
    
    "contact_expert": f"""
📞 *Связь с экспертом:*

*Доступные способы связи:*

1. *Телефон:* {EXPERT_PHONE}
   • Пн-Пт: 10:00-19:00
   • Консультация 15 минут бесплатно
   • Можно обсудить срочные вопросы

2. *Telegram:* {EXPERT_TELEGRAM}
   • Ответ в течение 30 минут
   • Можно отправлять фото/видео
   • Консультации по этапам ремонта

3. *В этом боте*
   • Задай вопрос прямо здесь
   • Получи ответ от эксперта
   • Сохрани всю переписку

*Рекомендую:* напиши в Telegram с пометкой "Из диагностики" — отвечу быстрее!
""",
    
    "buy_options": f"""
🎯 *Отличный выбор!* Это решение сэкономит тебе сотни тысяч рублей.

*Доступны 2 варианта:*

1. *СТАНДАРТ* — {PRICE_DISCOUNT:,} ₽ (скидка 50%)
   • Полный доступ к системе контроля
   • Закрытый Telegram-канал
   • База знаний по этапам ремонта
   • 30 мин консультация

2. *VIP* — {PRICE_VIP:,} ₽
   • Всё из стандарта +
   • Личная консультация по твоему объекту
   • Индивидуальный подход
   • Помощь в приёмке работ
   • Проверка договора

💎 *ГАРАНТИЯ:* 14 дней на возврат.
Если система не подойдёт — верну деньги без вопросов.

*Выбери вариант:*
""",
    
    "calculate_estimate": """
🧮 *Расчёт точной сметы*

Для точного расчёта сметы ремонта у меня есть *отдельный бот-калькулятор*.

*Что он умеет:*
• Рассчитать стоимость по квадратным метрам
• Учесть все виды работ (черновые, чистовая, сантехника, электрика)
• Сформировать детализированную смету
• Учесть твой бюджет и пожелания

*Переходи в бота-калькулятора:*
👉 @repair_estimate_bot

*P.S.* Это отдельный бот, поэтому нужно будет начать с команды /start
""",
    
    "ai_consultation": """
🤖 *AI-консультант по ремонту*

У меня есть *умный AI-консультант*, который поможет:

• Ответить на вопросы по ремонту 24/7
• Проанализировать фото проблем
• Подсказать решения на основе базы знаний
• Помочь с выбором материалов

*AI использует:*
1. Мою базу знаний (15 лет опыта)
2. Технические нормативы (СНИПы, ГОСТы)
3. Практические кейсы
4. Актуальные цены на материалы

*Переходи к AI-консультанту:*
👉 @repair_ai_bot

*P.S.* Это отдельный бот, начни с команды /start
""",
}

# ============ ИНИЦИАЛИЗАЦИЯ БОТА ============
bot = Bot(token=REPAIR_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher(storage=MemoryStorage())

# ============ ОСНОВНЫЕ ОБРАБОТЧИКИ ============
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(REPAIR_TEXTS["start"], reply_markup=get_repair_kb_start())
    logger.info(f"Пользователь {message.from_user.id} начал работу")

@dp.message(F.text == "👉 НАЧАТЬ ДИАГНОСТИКУ")
async def start_diagnostic(message: Message, state: FSMContext):
    await state.clear()
    await repair_db.save(message.from_user.id, {"started_at": datetime.now().isoformat()})
    await state.set_state(RepairStates.repair_waiting_stage)
    await message.answer(REPAIR_TEXTS["stage_question"], reply_markup=get_repair_kb_stage(show_back=False))
    await smart_pause(0.5)

# ============ ВЕТВЛЯЩАЯСЯ ЛОГИКА ВОПРОСОВ ============
@dp.message(RepairStates.repair_waiting_stage)
async def process_stage(message: Message, state: FSMContext):
    """Обработка стадии ремонта с ветвлением"""
    user_text = message.text
    
    if user_text == "◀️ Изменить предыдущий ответ":
        await message.answer("Это первый вопрос, назад нельзя.")
        return
    
    stage_code = calculator.get_stage_code(user_text)
    if not stage_code:
        await message.answer("Пожалуйста, выберите вариант из списка", 
                           reply_markup=get_repair_kb_stage(show_back=False))
        return
    
    await repair_db.save(message.from_user.id, {
        "stage": stage_code,
        "stage_text": user_text,
        "answer": user_text,
        "state": "stage"
    })
    await state.update_data(stage=stage_code, stage_text=user_text)
    
    # Персонализированный комментарий для стадии
    stage_comments = {
        "not_started": "💡 *Отлично!* Значит, у тебя есть время всё сделать правильно с самого начала.",
        "demolition": "⚡ *Важный этап!* Ошибки на демонтаже потом очень дорого исправлять.",
        "rough": "🎯 *Самый критичный этап!* Именно здесь теряют больше всего денег.",
        "finishing": "🎨 *Время финальных штрихов.* Но именно сейчас многие расслабляются.",
        "living": "🏠 *Ремонт завершён.* Но это не значит, что риски прошли."
    }
    
    if stage_code in stage_comments:
        await message.answer(stage_comments[stage_code])
        await smart_pause(2.0)
    
    # Переход к следующему вопросу
    await state.set_state(RepairStates.repair_waiting_area)
    await smart_pause(1.0)
    await message.answer(REPAIR_TEXTS["area_question"], 
                        reply_markup=get_repair_kb_area(show_back=True))

@dp.message(RepairStates.repair_waiting_area)
async def process_area(message: Message, state: FSMContext):
    """Обработка площади с возможностью вернуться назад"""
    user_text = message.text
    
    if user_text == "◀️ Изменить предыдущий ответ":
        await state.set_state(RepairStates.repair_waiting_stage)
        await message.answer("Возвращаю к вопросу о стадии ремонта...")
        await smart_pause(1.0)
        await message.answer(REPAIR_TEXTS["stage_question"], 
                           reply_markup=get_repair_kb_stage(show_back=False))
        return
    
    area_code = calculator.get_area_code(user_text)
    if not area_code:
        await message.answer("Пожалуйста, выберите вариант из списка",
                           reply_markup=get_repair_kb_area(show_back=True))
        return
    
    await repair_db.save(message.from_user.id, {
        "area": area_code,
        "area_text": user_text,
        "answer": user_text,
        "state": "area"
    })
    await state.update_data(area=area_code, area_text=user_text)
    
    # Комментарий в зависимости от площади
    if area_code != "unknown":
        await message.answer(f"📊 *Запомнил.* Рассчитаю риски для {user_text}.")
    else:
        await message.answer("👌 *Без проблем.* Использую средние значения.")
    
    await smart_pause(1.5)
    
    # ВЕТВЛЕНИЕ: проверяем, нужно ли спрашивать о контроле
    user_data = await state.get_data()
    stage = user_data.get("stage", "not_started")
    
    if calculator.should_skip_control(stage):
        # Для "living" пропускаем вопрос о контроле
        await state.update_data(control="skip", control_text="Уже поздно (ремонт закончен)")
        await repair_db.save(message.from_user.id, {
            "control": "skip",
            "control_text": "Уже поздно (ремонт закончен)",
            "state": "control"
        })
        
        # Переходим к следующему вопросу (или пропускаем его)
        if calculator.should_skip_fixation(stage):
            # Пропускаем фиксацию
            await state.update_data(fixation="skip", fixation_text="Пропущено (стадия living)")
            await repair_db.save(message.from_user.id, {
                "fixation": "skip",
                "fixation_text": "Пропущено (стадия living)",
                "state": "fixation"
            })
            
            # Идём сразу к расчётам
            await state.set_state(RepairStates.repair_calculating)
            await show_calculations(message, state)
        else:
            # Задаём вопрос о фиксации (для living)
            await state.set_state(RepairStates.repair_waiting_fixation)
            await smart_pause(1.0)
            await message.answer(REPAIR_TEXTS["fixation_question_living"],
                               reply_markup=get_repair_kb_fixation(show_back=True, stage="living"))
    else:
        # Спрашиваем о контроле
        await state.set_state(RepairStates.repair_waiting_control)
        
        # Разный текст вопроса для living
        if stage == "living":
            question_text = REPAIR_TEXTS["control_question_living"]
            for_living = True
        else:
            question_text = REPAIR_TEXTS["control_question"]
            for_living = False
            
        await message.answer(question_text,
                           reply_markup=get_repair_kb_control(show_back=True, for_living=for_living))

@dp.message(RepairStates.repair_waiting_control)
async def process_control(message: Message, state: FSMContext):
    """Обработка контроля с ветвлением"""
    user_text = message.text
    
    if user_text == "◀️ Изменить предыдущий ответ":
        await state.set_state(RepairStates.repair_waiting_area)
        await message.answer("Возвращаю к вопросу о площади...")
        await smart_pause(1.0)
        await message.answer(REPAIR_TEXTS["area_question"],
                           reply_markup=get_repair_kb_area(show_back=True))
        return
    
    # Определяем код контроля
    user_data = await state.get_data()
    stage = user_data.get("stage", "not_started")
    
    if stage == "living" and "уже поздно" in user_text.lower():
        control_code = "skip"
    else:
        control_code = calculator.get_control_code(user_text)
    
    if not control_code:
        # Определяем правильную клавиатуру
        for_living = stage == "living"
        await message.answer("Пожалуйста, выберите вариант из списка",
                           reply_markup=get_repair_kb_control(show_back=True, for_living=for_living))
        return
    
    await repair_db.save(message.from_user.id, {
        "control": control_code,
        "control_text": user_text,
        "answer": user_text,
        "state": "control"
    })
    await state.update_data(control=control_code, control_text=user_text)
    
    # Персонализированный комментарий
    control_comments = {
        "self": "🤔 *Понимаю.* Многие контролируют сами. Но без технических знаний можно пропустить серьёзные ошибки.",
        "foreman": "⚠️ *Важный момент:* прораб отвечает за процесс, но не за твои деньги. Это разные задачи.",
        "nobody": "🚨 *Самый рискованный сценарий.* Когда нет контроля — нет и ответственности.",
        "unknown": "💭 *Именно об этом чаще всего не думают заранее.*",
        "skip": "📝 *Понятно.* Раз ремонт уже закончен, оценим риски по факту."
    }
    
    if control_code in control_comments:
        await message.answer(control_comments[control_code])
        await smart_pause(2.0)
    
    # ВЕТВЛЕНИЕ: проверяем, нужно ли спрашивать о фиксации
    if calculator.should_skip_fixation(stage):
        # Для "not_started" пропускаем вопрос о фиксации
        await state.update_data(fixation="skip", fixation_text="Пропущено (стадия not_started)")
        await repair_db.save(message.from_user.id, {
            "fixation": "skip",
            "fixation_text": "Пропущено (стадия not_started)",
            "state": "fixation"
        })
        
        # Идём сразу к расчётам
        await state.set_state(RepairStates.repair_calculating)
        await show_calculations(message, state)
    else:
        # Задаём вопрос о фиксации
        await state.set_state(RepairStates.repair_waiting_fixation)
        await smart_pause(1.0)
        
        # Разный текст в зависимости от стадии
        if stage == "not_started":
            question_text = REPAIR_TEXTS["fixation_question_not_started"]
            kb_stage = "not_started"
        elif stage == "living":
            question_text = REPAIR_TEXTS["fixation_question_living"]
            kb_stage = "living"
        else:
            question_text = REPAIR_TEXTS["fixation_question"]
            kb_stage = "other"
        
        await message.answer(question_text,
                           reply_markup=get_repair_kb_fixation(show_back=True, stage=kb_stage))

@dp.message(RepairStates.repair_waiting_fixation)
async def process_fixation(message: Message, state: FSMContext):
    """Обработка фиксации с учётом стадии"""
    user_text = message.text
    
    if user_text == "◀️ Изменить предыдущий ответ":
        await state.set_state(RepairStates.repair_waiting_control)
        await message.answer("Возвращаю к вопросу о контроле...")
        await smart_pause(1.0)
        
        user_data = await state.get_data()
        stage = user_data.get("stage", "not_started")
        if stage == "living":
            question_text = REPAIR_TEXTS["control_question_living"]
            for_living = True
        else:
            question_text = REPAIR_TEXTS["control_question"]
            for_living = False
            
        await message.answer(question_text,
                           reply_markup=get_repair_kb_control(show_back=True, for_living=for_living))
        return
    
    # Определяем код фиксации
    user_data = await state.get_data()
    stage = user_data.get("stage", "not_started")
    fixation_code = calculator.get_fixation_code(user_text, stage)
    
    if not fixation_code:
        # Определяем правильную клавиатуру
        await message.answer("Пожалуйста, выберите вариант из списка",
                           reply_markup=get_repair_kb_fixation(show_back=True, stage=stage))
        return
    
    await repair_db.save(message.from_user.id, {
        "fixation": fixation_code,
        "fixation_text": user_text,
        "answer": user_text,
        "state": "fixation"
    })
    await state.update_data(fixation=fixation_code, fixation_text=user_text)
    
    # Комментарий в зависимости от фиксации
    if fixation_code in ["full", "planned_full"]:
        await message.answer("📸 *Отлично!* Фотофиксация — твой главный инструмент защиты.")
    elif fixation_code in ["partial", "none"]:
        await message.answer("⚠️ *Внимание:* без фотофиксации сложно доказать, что было ДО ремонта.")
    else:
        await message.answer("🤔 *Понял.* Давай посчитаем риски.")
    
    await smart_pause(1.5)
    
    # Переходим к расчётам
    await state.set_state(RepairStates.repair_calculating)
    await show_calculations(message, state)

# ============ РАСЧЁТЫ И РЕЗУЛЬТАТЫ ============
async def show_calculations(message: Message, state: FSMContext):
    """Показ расчётов с анимацией"""
    steps = REPAIR_TEXTS["calculating"]
    
    for text in steps:
        await message.answer(text)
        await smart_pause(1.5)
    
    # Переходим в состояние показа результатов
    await state.set_state(RepairStates.repair_showing_results)
    await show_results(message, state)

async def show_results(message: Message, state: FSMContext):
    """Показ результатов диагностики с ИИ-персонализацией"""
    user_data = await state.get_data()
    
    stage = user_data.get("stage", "not_started")
    area = user_data.get("area", "unknown")
    control = user_data.get("control", "unknown")
    fixation = user_data.get("fixation", "planned_none")
    
    # Рассчитываем потери
    losses = calculator.calculate_intelligent_loss(stage, area, control, fixation)
    
    # ИИ: Персонализированная рекомендация
    ai_recommendation = ai_engine.get_personalized_recommendation(stage, control, area, fixation)
    
    # ИИ: Эмоциональный ответ
    emotional_response = ai_engine.get_emotional_response(losses['avg'])
    
    # ИИ: Персонализированные примеры
    ai_examples = ai_engine.generate_personalized_examples(stage, control, losses['avg'])
    
    # Форматирование денег с ИИ-контекстом
    money_min = ai_engine.smart_format_money(losses['min'], "emotional")
    money_avg = ai_engine.smart_format_money(losses['avg'], "emotional")
    money_max = ai_engine.smart_format_money(losses['max'], "emotional")
    
    # Формируем сообщение с результатами
    result_msg = f"""
🎯 *ТВОЙ ПЕРСОНАЛИЗИРОВАННЫЙ ДИАГНОЗ:*

🔹 *Стадия:* {user_data.get('stage_text', 'Не указано')}
🔹 *Площадь:* {user_data.get('area_text', 'Не указано')}
{f"🔹 *Контроль:* {user_data.get('control_text', 'Не указано')}" if control != "skip" else ""}
{f"🔹 *Фиксация:* {user_data.get('fixation_text', 'Не указано')}" if fixation != "skip" else ""}

{ai_recommendation['recommendation']}

💸 *ТВОИ ПОТЕНЦИАЛЬНЫЕ ПОТЕРИ:*

• Минимально: *{money_min}*
• Скорее всего: *{money_avg}*
• Максимально: *{money_max}*

{emotional_response}

⚡ *КОНКРЕТНЫЕ РИСКИ ДЛЯ ТВОЕГО СЦЕНАРИЯ:*
"""
    
    # Используем ИИ-примеры вместо стандартных
    for i, (error, loss, scenario) in enumerate(ai_examples[:2], 1):
        result_msg += f"""
{i}. *{error}*
   💸 Потеря: *{loss}*
   📖 {scenario}
"""
    
    result_msg += f"""

📌 *Ключевая точка контроля:* {losses['checkpoint']}

{ai_recommendation['emotional']}

💰 *ТВОЙ СРЕДНИЙ РИСК:* {ai_engine.smart_format_money(losses['avg'], 'result')}
"""
    
    await message.answer(result_msg)
    await smart_pause(5.0)
    
    # ИИ: Вовлекающий вопрос
    engagement_question = ai_engine.get_engagement_question(stage)
    if engagement_question:
        await message.answer(f"💭 *Вопрос для размышления:*\n\n{engagement_question}")
        await smart_pause(3.0)
    
    # Пауза для эмоционального вовлечения
    await message.answer(REPAIR_TEXTS["results_pause"])
    await smart_pause(3.0)
    
    # Предлагаем следующий шаг
    await message.answer("👉 *Хочешь узнать, как сохранить эти деньги?*", 
                        reply_markup=get_repair_kb_results())


# ============ ИСПРАВЛЕННЫЕ ОБРАБОТЧИКИ КНОПОК РЕЗУЛЬТАТОВ ============
@dp.message(RepairStates.repair_showing_results, F.text == "👉 ПОКАЖИ РЕШЕНИЕ")
async def show_solution(message: Message, state: FSMContext):
    """Показ решения (системы контроля)"""
    await message.answer(REPAIR_TEXTS["solution_intro"])
    await smart_pause(2.0)
    
    await message.answer(REPAIR_TEXTS["system_details"])
    await smart_pause(2.0)
    
    price_text = REPAIR_TEXTS["price_info"].format(
        normal_price=PRICE_NORMAL,
        discount_price=PRICE_DISCOUNT,
        vip_price=PRICE_VIP
    )
    
    await message.answer(price_text)
    await smart_pause(2.0)
    
    # Переходим в состояние выбора предложения
    await state.set_state(RepairStates.repair_choosing_offer)
    await message.answer("*Теперь выбор за тобой.*\n\nВыбери следующий шаг:", 
                        reply_markup=get_repair_kb_offer())

# ============ УНИВЕРСАЛЬНЫЕ ОБРАБОТЧИКИ КНОПОК ============
# Обработчик для кнопки "🤔 НУЖНА КОНСУЛЬТАЦИЯ" - работает ИЗ ЛЮБОГО СОСТОЯНИЯ
@dp.message(F.text == "🤔 НУЖНА КОНСУЛЬТАЦИЯ")
async def need_consultation_anywhere(message: Message, state: FSMContext):
    """Обработчик кнопки 'Нужна консультация' из любого состояния"""
    await handle_contact_expert(message, state)

# Обработчик для кнопки "📞 Связаться с экспертом" - работает ИЗ ЛЮБОГО СОСТОЯНИЯ  
@dp.message(F.text == "📞 Связаться с экспертом")
async def contact_expert_anywhere(message: Message, state: FSMContext):
    """Обработчик кнопки 'Связаться с экспертом' из любого состояния"""
    await handle_contact_expert(message, state)

# ============ ОБРАБОТКА 5 ВАРИАНТОВ ПРЕДЛОЖЕНИЙ ============
@dp.message(RepairStates.repair_choosing_offer)
async def process_offer_choice(message: Message, state: FSMContext):
    """Обработка выбора варианта из предложений"""
    choice = message.text
    
    if "Купить" in choice:
        await handle_buy_system(message, state)
    elif "Связаться" in choice or "экспертом" in choice.lower():
        await handle_contact_expert(message, state)
    elif "Оставить номер" in choice or "номер" in choice.lower():
        await handle_collect_phone(message, state)
    elif "Рассчитать" in choice or "смету" in choice.lower():
        await handle_calculate_estimate(message, state)
    elif "AI" in choice.upper() or "консультацию" in choice.lower():
        await handle_ai_consultation(message, state)
    else:
        await message.answer("Пожалуйста, выберите вариант из списка", 
                           reply_markup=get_repair_kb_offer())

async def handle_buy_system(message: Message, state: FSMContext):
    """Обработка покупки системы"""
    await message.answer(REPAIR_TEXTS["buy_options"], reply_markup=get_inline_payment_kb())
    logger.info(f"Пользователь {message.from_user.id} выбрал покупку системы")

async def handle_contact_expert(message: Message, state: FSMContext):
    """Обработка связи с экспертом - ТЕПЕРЬ РАБОТАЕТ ИЗ ЛЮБОГО СОСТОЯНИЯ!"""
    await message.answer(REPAIR_TEXTS["contact_expert"], reply_markup=get_inline_expert_kb())
    logger.info(f"Пользователь {message.from_user.id} запросил связь с экспертом")

async def handle_collect_phone(message: Message, state: FSMContext):
    """Сбор номера телефона"""
    await state.set_state(RepairStates.repair_waiting_phone)
    
    phone_text = """
📱 *Оставить номер для связи*

Отлично! Эксперт перезвонит тебе в удобное время.

*Как это работает:*
1. Ты оставляешь номер
2. Эксперт связывается в течение 24 часов
3. Бесплатная 15-минутная консультация
4. Ответы на твои вопросы по ремонту

*Выбери способ:*
"""
    
    await message.answer(phone_text, reply_markup=get_repair_kb_phone())

@dp.message(RepairStates.repair_waiting_phone)
async def process_phone_input(message: Message, state: FSMContext):
    """Обработка ввода номера телефона"""
    if message.text == "⏪ Назад к выбору":
        await state.set_state(RepairStates.repair_choosing_offer)
        await message.answer("Возвращаю к выбору вариантов...", 
                           reply_markup=get_repair_kb_offer())
        return
    
    phone_number = None
    
    if message.text == "✏️ Ввести номер вручную":
        await message.answer("Напиши свой номер телефона в формате:\n+7 XXX XXX XX XX\nили\n8 XXX XXX XX XX")
        return
    
    if message.contact:
        phone_number = message.contact.phone_number
        await message.answer(f"✅ *Спасибо!* Получил твой номер: {phone_number}")
    elif message.text and any(char.isdigit() for char in message.text):
        phone_number = message.text.strip()
        await message.answer(f"✅ *Спасибо!* Записал твой номер: {phone_number}")
    
    if phone_number:
        await repair_db.save(message.from_user.id, {"phone": phone_number})
        
        confirmation = f"""
✅ *Номер получен!*

Эксперт свяжется с тобой по номеру:
{phone_number}

*Что будет дальше:*
1. В течение 24 часов тебе перезвонят
2. 15-минутная бесплатная консультация  
3. Ответы на вопросы по твоему ремонту
4. Рекомендации по следующим шагам

Если есть срочный вопрос — напиши прямо сейчас в Telegram: {EXPERT_TELEGRAM}
"""
        
        await message.answer(confirmation)
        logger.info(f"Пользователь {message.from_user.id} оставил номер: {phone_number}")
    else:
        await message.answer("Пожалуйста, введи номер телефона или используй кнопку 'Отправить мой номер'",
                           reply_markup=get_repair_kb_phone())
        return
    
    await state.set_state(RepairStates.repair_choosing_offer)
    await message.answer("Выбери следующий шаг:", reply_markup=get_repair_kb_offer())

async def handle_calculate_estimate(message: Message, state: FSMContext):
    """Обработка запроса калькулятора сметы"""
    await message.answer(REPAIR_TEXTS["calculate_estimate"])
    logger.info(f"Пользователь {message.from_user.id} запросил калькулятор сметы")

async def handle_ai_consultation(message: Message, state: FSMContext):
    """Обработка запроса AI-консультации"""
    await message.answer(REPAIR_TEXTS["ai_consultation"])
    logger.info(f"Пользователь {message.from_user.id} запросил AI-консультацию")

# ============ INLINE ОБРАБОТЧИКИ ============
@dp.callback_query(F.data == "ask_question")
async def ask_question_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик inline-кнопки 'Задать вопрос'"""
    await state.set_state(RepairStates.repair_waiting_question)
    await callback.message.answer("""
💬 *Задай свой вопрос эксперту:*

Напиши его здесь, и я передам напрямую эксперту.

*Что можно спросить:*
• Консультацию по твоему этапу ремонта
• Помощь с выбором материалов
• Проверку сметы или договора
• Рекомендации по подрядчикам

Эксперт ответит в течение 24 часов.
Для срочных вопросов лучше написать в Telegram напрямую.
""")
    await callback.answer()

@dp.callback_query(F.data == "ask_question_bot")
async def ask_question_bot_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик inline-кнопки 'Задать вопрос в боте'"""
    await state.set_state(RepairStates.repair_waiting_question)
    await callback.message.answer("""
💬 *Задай свой вопрос эксперту:*

Напиши его здесь, и я передам напрямую эксперту.

*Что можно спросить:*
• Консультацию по твоему этапу ремонта
• Помощь с выбором материалов
• Проверку сметы или договора
• Рекомендации по подрядчикам

Эксперт ответит в течение 24 часов.
Для срочных вопросов лучше написать в Telegram напрямую.
""")
    await callback.answer()

@dp.message(RepairStates.repair_waiting_question)
async def process_expert_question(message: Message, state: FSMContext):
    """Обработка вопроса для эксперта"""
    question = message.text
    user_id = message.from_user.id
    
    await repair_db.save(user_id, {"expert_question": question, "question_time": datetime.now().isoformat()})
    
    await message.answer(f"""
✅ *Вопрос отправлен эксперту!*

Твой вопрос:
"{question}"

Эксперт ответит в течение 24 часов.
Если вопрос срочный — напиши напрямую в Telegram: {EXPERT_TELEGRAM}

*Тем временем можешь:*
• Ознакомиться с системой контроля
• Получить бесплатный чек-лист
• Рассчитать точную смету
""", reply_markup=get_repair_kb_offer())
    
    await state.set_state(RepairStates.repair_choosing_offer)
    logger.info(f"Пользователь {user_id} задал вопрос эксперту: {question[:50]}...")

@dp.callback_query(F.data == "call_expert")
async def call_expert_callback(callback: CallbackQuery):
    """Обработчик inline-кнопки 'Позвонить эксперту'"""
    await callback.message.answer(f"""
📞 *Позвонить эксперту:*

*Номер телефона:* {EXPERT_PHONE}

*Часы работы:*
• Пн-Пт: 10:00-19:00
• Сб: 11:00-16:00
• Вс: выходной

*Скажи, что ты из диагностики* — получишь приоритетный ответ.
""")
    await callback.answer()

# ============ КОМАНДЫ ============
@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Команда помощи"""
    help_text = f"""
*Помощь по ремонт-боту:*

🤖 *Это бот для диагностики рисков в ремонте.*
Он поможет определить, где ты теряешь деньги.

*Основные команды:*
/start - Начать диагностику
/help - Эта справка
/cancel - Отменить диагностику

*Контакты эксперта:*
📞 Телефон: {EXPERT_PHONE}
✉️ Telegram: {EXPERT_TELEGRAM}

*Как работает бот:*
1. 4 вопроса о твоём ремонте (с ветвлениями)
2. Анализ рисков и потерь
3. Реальные цифры из опыта
4. Решения для экономии
"""
    await message.answer(help_text)

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Команда отмены"""
    await state.clear()
    await message.answer("Диагностика отменена. Начни заново с /start",
                        reply_markup=get_repair_kb_start())

# ============ ОБРАБОТКА ЛЮБЫХ ДРУГИХ СООБЩЕНИЙ ============
@dp.message()
async def handle_unknown(message: Message, state: FSMContext):
    """Обработчик любых других сообщений"""
    current_state = await state.get_state()
    
    if not current_state:
        await message.answer("Начни диагностику с команды /start", 
                           reply_markup=get_repair_kb_start())
    elif current_state == RepairStates.repair_showing_results:
        await message.answer("Выбери вариант выше 👆", 
                           reply_markup=get_repair_kb_results())
    elif current_state == RepairStates.repair_choosing_offer:
        await message.answer("Выбери вариант из списка 👆", 
                           reply_markup=get_repair_kb_offer())
    else:
        await message.answer("Пожалуйста, используй кнопки для ответа. Или отправь /cancel для отмены.")

# ============ ЗАПУСК ============
async def main():
    try:
        bot_info = await bot.get_me()
        print("=" * 60)
        print("🔧 РЕМОНТ АУДИТ БОТ - ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ВЕРСИЯ 2.0")
        print("=" * 60)
        print(f"🤖 Бот: @{bot_info.username}")
        print(f"📞 Эксперт: {EXPERT_PHONE}")
        print(f"✉️ Telegram: {EXPERT_TELEGRAM}")
        print(f"💰 Цена: {PRICE_DISCOUNT}₽ (скидка) | {PRICE_VIP}₽ (VIP)")
        print("=" * 60)
        print("✅ Бот запущен с полными исправлениями:")
        print("   1. ✅ Все кнопки работают (включая 'Нужна консультация')")
        print("   2. ✅ Логика ответвлений для разных стадий:")
        print("       • 'Не начали' → пропускает фиксацию")
        print("       • 'Уже живём' → пропускает контроль")
        print("       • Разные тексты вопросов для каждой стадии")
        print("   3. ✅ Персонализированные расчёты потерь")
        print("   4. ✅ Умные переходы между состояниями")
        print("   5. ✅ Все inline-кнопки работают")
        print("   6. ✅ Обработка возврата к предыдущим вопросам")
        print("=" * 60)
        print(f"📊 Символов кода: {len(__doc__) + sum(len(line) for line in open(__file__, 'r', encoding='utf-8'))}")
        print("=" * 60)
        print("⏳ Ожидание сообщений...")
        print("=" * 60)
        
        logger.info(f"Бот @{bot_info.username} запущен")
        
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")
        print(f"💥 ОШИБКА: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Запуск полностью исправленной версии бота v2.0...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Бот остановлен")
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")
        logger.error(f"Неожиданная ошибка: {e}")