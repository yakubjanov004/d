from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_call_center_supervisor_main_menu(lang: str = 'uz') -> ReplyKeyboardMarkup:
    if lang == 'ru':
        keyboard = [
            [KeyboardButton(text="📥 Входящие"),KeyboardButton(text="👥 Активность сотрудников")],
            [KeyboardButton(text="🔌 Создать заявку на подключение"), KeyboardButton(text="🔧 Создать техническую заявку")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📤 Экспорт")],
            [KeyboardButton(text="🌐 Изменить язык")],
        ]
    else:
        keyboard = [
            [KeyboardButton(text="📥 Inbox"),KeyboardButton(text="👥 Xodimlar faoliyati")],
            [KeyboardButton(text="🔌 Ulanish arizasi yaratish"), KeyboardButton(text="🔧 Texnik xizmat yaratish")],
            [KeyboardButton(text="📊 Statistikalar"), KeyboardButton(text="📤 Export")],
            [KeyboardButton(text="🌐 Tilni o'zgartirish")],
        ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)



def zayavka_type_keyboard(lang="uz"):
    """Zayavka turini tanlash klaviaturasi - 2 tilda"""
    person_physical_text = "👤 Jismoniy shaxs" if lang == "uz" else "👤 Физическое лицо"
    person_legal_text = "🏢 Yuridik shaxs" if lang == "uz" else "🏢 Юридическое лицо"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=person_physical_text, callback_data="zayavka_type_b2c")],
            [InlineKeyboardButton(text=person_legal_text, callback_data="zayavka_type_b2b")]
        ]
    )
    return keyboard

def get_operator_tariff_selection_keyboard() -> InlineKeyboardMarkup:
    """Tariff selection keyboard for CALL-CENTER OPERATOR (UZ only)."""
    keyboard = [
        [
            InlineKeyboardButton(text="Oddiy-20", callback_data="op_tariff_b2c_plan_0"),
            InlineKeyboardButton(text="Oddiy-50", callback_data="op_tariff_b2c_plan_1"),
        ],
        [
            InlineKeyboardButton(text="Oddiy-100", callback_data="op_tariff_b2c_plan_2"),
            InlineKeyboardButton(text="XIT-200", callback_data="op_tariff_b2c_plan_3"),
        ],
        [
            InlineKeyboardButton(text="VIP-500", callback_data="op_tariff_b2c_plan_4"),
            InlineKeyboardButton(text="PREMIUM", callback_data="op_tariff_b2c_plan_5"),
        ],
        [
            InlineKeyboardButton(text="BizNET-Pro-1", callback_data="op_tariff_biznet_plan_0"),
            InlineKeyboardButton(text="BizNET-Pro-2", callback_data="op_tariff_biznet_plan_1"),
        ],
        [
            InlineKeyboardButton(text="BizNET-Pro-3", callback_data="op_tariff_biznet_plan_2"),
            InlineKeyboardButton(text="BizNET-Pro-4", callback_data="op_tariff_biznet_plan_3"),
        ],
        [
            InlineKeyboardButton(text="BizNET-Pro-5", callback_data="op_tariff_biznet_plan_4"),
            InlineKeyboardButton(text="BizNET-Pro-6", callback_data="op_tariff_biznet_plan_5"),
        ],
        [
            InlineKeyboardButton(text="BizNET-Pro-7+", callback_data="op_tariff_biznet_plan_6"),
            InlineKeyboardButton(text="Tijorat-1", callback_data="op_tariff_tijorat_plan_0"),
        ],
        [
            InlineKeyboardButton(text="Tijorat-2", callback_data="op_tariff_tijorat_plan_1"),
            InlineKeyboardButton(text="Tijorat-3", callback_data="op_tariff_tijorat_plan_2"),
        ],
        [
            InlineKeyboardButton(text="Tijorat-4", callback_data="op_tariff_tijorat_plan_3"),
            InlineKeyboardButton(text="Tijorat-5", callback_data="op_tariff_tijorat_plan_4"),
        ],
        [
            InlineKeyboardButton(text="Tijorat-100", callback_data="op_tariff_tijorat_plan_5"),
            InlineKeyboardButton(text="Tijorat-300", callback_data="op_tariff_tijorat_plan_6"),
        ],
        [
            InlineKeyboardButton(text="Tijorat-500", callback_data="op_tariff_tijorat_plan_7"),
            InlineKeyboardButton(text="Tijorat-1000", callback_data="op_tariff_tijorat_plan_8"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def confirmation_keyboard(lang="uz"):
    """Tasdiqlash klaviaturasi - 2 tilda"""
    confirm_text = "✅ Tasdiqlash" if lang == "uz" else "✅ Подтвердить"
    resend_text = "🔄 Qayta yuborish" if lang == "uz" else "🔄 Отправить заново"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=confirm_text, callback_data="confirm_zayavka_call_center"),
            InlineKeyboardButton(text=resend_text, callback_data="resend_zayavka_call_center")
        ]
    ])
    return keyboard

def confirmation_keyboard_tech_service(lang="uz"):
    """Tasdiqlash klaviaturasi - 2 tilda"""
    confirm_text = "✅ Tasdiqlash" if lang == "uz" else "✅ Подтвердить"
    resend_text = "🔄 Qayta yuborish" if lang == "uz" else "🔄 Отправить заново"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=confirm_text, callback_data="confirm_zayavka_call_center_tech_service"),
            InlineKeyboardButton(text=resend_text, callback_data="resend_zayavka_call_center_tech_service")
        ]
    ])
    return keyboard

def get_client_regions_keyboard(lang: str = 'uz') -> InlineKeyboardMarkup:
    """Regions selection keyboard for client"""
    keyboard = [
        [
            InlineKeyboardButton(text="Toshkent shahri", callback_data="region_toshkent_city"),
            InlineKeyboardButton(text="Toshkent viloyati", callback_data="region_toshkent_region")
        ],
        [
            InlineKeyboardButton(text="Andijon", callback_data="region_andijon"),
            InlineKeyboardButton(text="Farg'ona", callback_data="region_fergana")
        ],
        [
            InlineKeyboardButton(text="Namangan", callback_data="region_namangan"),
            InlineKeyboardButton(text="Sirdaryo", callback_data="region_sirdaryo")
        ],
        [
            InlineKeyboardButton(text="Jizzax", callback_data="region_jizzax"),
            InlineKeyboardButton(text="Samarqand", callback_data="region_samarkand")
        ],
        [
            InlineKeyboardButton(text="Buxoro", callback_data="region_bukhara"),
            InlineKeyboardButton(text="Navoiy", callback_data="region_navoi")
        ],
        [
            InlineKeyboardButton(text="Qashqadaryo", callback_data="region_kashkadarya"),
            InlineKeyboardButton(text="Surxondaryo", callback_data="region_surkhandarya")
        ],
        [
            InlineKeyboardButton(text="Xorazm", callback_data="region_khorezm"),
            InlineKeyboardButton(text="Qoraqalpog'iston", callback_data="region_karakalpakstan")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_ccs_export_types_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Call Center Supervisor export types keyboard with language support"""
    if lang == "uz":
        keyboard = [
            [
                InlineKeyboardButton(text="📋 Operatorlar ochgan arizalar", callback_data="ccs_export_operator_orders"),
                InlineKeyboardButton(text="👥 Call Center operatorlari", callback_data="ccs_export_operators"),
            ],
            [
                InlineKeyboardButton(text="📊 Statistika", callback_data="ccs_export_statistics"),
            ],
            [InlineKeyboardButton(text="🚫 Yopish", callback_data="ccs_export_end")],
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton(text="📋 Заявки операторов", callback_data="ccs_export_operator_orders"),
                InlineKeyboardButton(text="👥 Операторы Call Center", callback_data="ccs_export_operators"),
            ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="ccs_export_statistics"),
            ],
            [InlineKeyboardButton(text="🚫 Закрыть", callback_data="ccs_export_end")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_ccs_export_formats_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Call Center Supervisor export formats keyboard with language support"""
    if lang == "uz":
        keyboard = [
            [InlineKeyboardButton(text="CSV", callback_data="ccs_format_csv")],
            [InlineKeyboardButton(text="Excel", callback_data="ccs_format_xlsx")],
            [InlineKeyboardButton(text="Word", callback_data="ccs_format_docx")],
            [InlineKeyboardButton(text="PDF", callback_data="ccs_format_pdf")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="ccs_export_back_types")],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(text="CSV", callback_data="ccs_format_csv")],
            [InlineKeyboardButton(text="Excel", callback_data="ccs_format_xlsx")],
            [InlineKeyboardButton(text="Word", callback_data="ccs_format_docx")],
            [InlineKeyboardButton(text="PDF", callback_data="ccs_format_pdf")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="ccs_export_back_types")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)