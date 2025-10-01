from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

# ==================== ENUM LAR ====================
# PostgreSQL ENUM lariga mos keladigan Python Enumlari
# Bu enumlar ma'lumotlar bazasidagi ENUM tiplariga mos keladi

class ConnectionOrderStatus(Enum):
    """
    Ulanish arizalari (connection_orders) uchun statuslar
    Eslatma: NEW statusi bazada CHECK constraintda yo'q, shuning uchun olib tashlandi
    """
    IN_MANAGER = "in_manager"                    # Managerga tayinlangan
    IN_JUNIOR_MANAGER = "in_junior_manager"      # Kichik managerga tayinlangan
    IN_CONTROLLER = "in_controller"              # Kontrollerga tayinlangan
    IN_TECHNICIAN = "in_technician"              # Texnikaga tayinlangan
    IN_REPAIRS = "in_repairs"                    # Ta'mirlashda
    IN_WAREHOUSE = "in_warehouse"                # Omborga tayinlangan
    IN_TECHNICIAN_WORK = "in_technician_work"    # Texnik ish bajarayapti
    COMPLETED = "completed"                      # Yakunlangan
    BETWEEN_CONTROLLER_TECHNICIAN = "between_controller_technician"  # Kontroller va texnik o'rtasida

class SmartServiceCategory(Enum):
    """
    Smart Service buyurtmalarining kategoriyalari
    Har bir kategoriya turli xil texnologik yechimlarni ifodalaydi
    """
    AQLLI_AVTOMATLASHTIRILGAN_XIZMATLAR = "aqlli_avtomatlashtirilgan_xizmatlar"  # Aqlli uy, aqlli ofis
    XAVFSIZLIK_KUZATUV_TIZIMLARI = "xavfsizlik_kuzatuv_tizimlari"                # Kamera, signalizatsiya
    INTERNET_TARMOQ_XIZMATLARI = "internet_tarmoq_xizmatlari"                   # Wi-Fi, LAN, repeater
    ENERGIYA_YASHIL_TEXNOLOGIYALAR = "energiya_yashil_texnologiyalar"            # Quyosh panel, energiya tejovchi
    MULTIMEDIYA_ALOQA_TIZIMLARI = "multimediya_aloqa_tizimlari"                 # TV, audio, video konferensiya
    MAXSUS_QOSHIMCHA_XIZMATLAR = "maxsus_qoshimcha_xizmatlar"                   # IoT, AI, maxsus yechimlar

class TechnicianOrderStatus(Enum):
    """
    Texnik buyurtmalari (technician_orders) uchun statuslar
    Texnik xizmat ko'rsatish jarayonining bosqichlarini ifodalaydi
    """
    IN_CONTROLLER = "in_controller"              # Kontrollerga tayinlangan
    IN_TECHNICIAN = "in_technician"              # Texnikaga tayinlangan
    IN_DIAGNOSTICS = "in_diagnostics"            # Diagnostikada
    IN_REPAIRS = "in_repairs"                    # Ta'mirlashda
    IN_WAREHOUSE = "in_warehouse"                # Omborga tayinlangan
    IN_TECHNICIAN_WORK = "in_technician_work"    # Texnik ish bajarayapti
    COMPLETED = "completed"                      # Yakunlangan
    BETWEEN_CONTROLLER_TECHNICIAN = "between_controller_technician"  # Kontroller va texnik o'rtasida
    IN_CALL_CENTER_SUPERVISOR = "in_call_center_supervisor"         # Call center nazoratchisiga tayinlangan
    IN_CALL_CENTER_OPERATOR = "in_call_center_operator"             # Call center operatoriga tayinlangan

class SaffOrderStatus(Enum):
    """
    SAFF buyurtmalari uchun statuslar
    Turli foydalanuvchilar tomonidan yaratilgan va ko'rib chiqiladigan buyurtmalar
    """
    # Yaratish bosqichlari
    IN_CALL_CENTER_OPERATOR = "in_call_center_operator"      # Call center operatoriga tayinlangan
    IN_CALL_CENTER_SUPERVISOR = "in_call_center_supervisor"  # Call center nazoratchisiga tayinlangan
    
    # Ko'rib chiqish va tasdiqlash bosqichlari
    IN_MANAGER = "in_manager"                    # Managerga tayinlangan
    IN_JUNIOR_MANAGER = "in_junior_manager"      # Kichik managerga tayinlangan
    IN_CONTROLLER = "in_controller"              # Kontrollerga tayinlangan
    
    # Bajarish bosqichlari
    IN_TECHNICIAN = "in_technician"              # Texnikaga tayinlangan
    IN_DIAGNOSTICS = "in_diagnostics"            # Diagnostikada
    IN_REPAIRS = "in_repairs"                    # Ta'mirlashda
    IN_WAREHOUSE = "in_warehouse"                # Omborga tayinlangan
    IN_TECHNICIAN_WORK = "in_technician_work"    # Texnik ish bajarayapti
    
    # Yakunlash
    COMPLETED = "completed"                      # Yakunlangan
    BETWEEN_CONTROLLER_TECHNICIAN = "between_controller_technician"  # Kontroller va texnik o'rtasida

class SaffOrderTypeOfZayavka(Enum):
    """
    SAFF buyurtmalarining ariza turlari
    Call center orqali kelgan so'rovlarning turini aniqlaydi
    """
    CONNECTION = "connection"    # Internet ulanish arizasi
    TECHNICIAN = "technician"    # Texnik xizmat arizasi


class UserRole(Enum):
    """
    Foydalanuvchi rollari - tizimdagi foydalanuvchilarning vazifalarini aniqlaydi
    Har bir rol tizimda ma'lum huquqlar va mas'uliyatlarga ega
    """
    ADMIN = "admin"                          # Administrator - barcha huquqlar
    CLIENT = "client"                        # Mijoz - xizmat sotib oluvchi
    MANAGER = "manager"                      # Manager - buyurtmalarni boshqaruvchi
    JUNIOR_MANAGER = "junior_manager"        # Kichik manager - yordamchi manager
    CONTROLLER = "controller"                # Kontroller - buyurtmalarni tekshiruvchi
    TECHNICIAN = "technician"                # Texnik - amaliy ishlarni bajaruvchi
    WAREHOUSE = "warehouse"                  # Omborchi - materiallar bilan ishlaydi
    CALLCENTER_SUPERVISOR = "callcenter_supervisor"  # Call center nazoratchisi
    CALLCENTER_OPERATOR = "callcenter_operator"      # Call center operatori

# ==================== DOMAIN VALIDATSIYA ====================
# Smart Service Type DOMAIN uchun to'liq 42 ta validatsiya
# Bu ro'yxat PostgreSQL bazasidagi smart_service_type DOMAIN qiymatlari bilan mos keladi
SMART_SERVICE_TYPES = [
    'aqlli_uy_tizimlarini_ornatish_sozlash',                                    # Aqlli uy tizimlari o'rnatish
    'aqlli_yoritish_smart_lighting_tizimlari',                                  # Aqlli yoritish tizimlari
    'aqlli_termostat_iqlim_nazarati_tizimlari',                                 # Aqlli termostat tizimlari
    'smart_lock_internet_orqali_boshqariladigan_eshik_qulfi_tizimlari',         # Smart lock tizimlari
    'aqlli_rozetalar_energiya_monitoring_tizimlari',                            # Aqlli rozetka tizimlari
    'uyni_masofadan_boshqarish_qurilmalari_yagona_uzim_orqali_boshqarish',      # Masofaviy boshqarish
    'aqlli_pardalari_jaluz_tizimlari',                                          # Aqlli parda/jaluz tizimlari
    'aqlli_malahiy_texnika_integratsiyasi',                                     # Aqlli maishiy texnika
    'videokuzatuv_kameralarini_ornatish_ip_va_analog',                          # Video kuzatuv kameralari
    'kamera_arxiv_tizimlari_bulutli_saqlash_xizmatlari',                        # Kamera arxiv tizimlari
    'domofon_tizimlari_ornatish',                                               # Domofon tizimlari
    'xavfsizlik_signalizatsiyasi_harakat_sensorlarini_ornatish',                # Xavfsizlik signalizatsiyasi
    'yong_signalizatsiyasi_tizimlari',                                          # Yong'in signalizatsiyasi
    'gaz_sizish_sav_toshqinliqqa_qarshi_tizimlar',                              # Gaz/o't o'tkazmaydigan tizimlar
    'yuzni_tanish_face_recognition_tizimlari',                                  # Yuzni tanish tizimlari
    'avtomatik_eshik_darvoza_boshqaruv_tizimlari',                              # Avtomatik eshik tizimlari
    'wi_fi_tarmoqlarini_ornatish_sozlash',                                      # Wi-Fi tarmoq o'rnatish
    'wi_fi_qamrov_zonasini_kengaytirish_access_point',                          # Wi-Fi qamrov kengaytirish
    'mobil_aloqa_signalini_kuchaytirish_repeater',                              # Signal kuchaytirish
    'ofis_va_uy_uchun_lokal_tarmoq_lan_qurish',                                 # LAN tarmoq qurish
    'internet_provayder_xizmatlarini_ulash',                                    # Internet provayder xizmatlari
    'server_va_nas_qurilmalarini_ornatish',                                     # Server/NAS qurilmalari
    'bulutli_fayl_almashish_zaxira_tizimlari',                                  # Bulutli fayl almashish
    'vpn_va_xavfsiz_internet_ulanishlarini_tashkil_qilish',                     # VPN tashkil qilish
    'quyosh_panellarini_ornatish_ulash',                                        # Quyosh panel o'rnatish
    'quyosh_batareyalari_orqali_energiya_saqlash_tizimlari',                    # Quyosh batareya tizimlari
    'shamol_generatorlarini_ornatish',                                          # Shamol generatorlari
    'elektr_energiyasini_tejovchi_yoritish_tizimlari',                          # Energiya tejovchi yoritish
    'avtomatik_suv_orish_tizimlari_smart_irrigation',                           # Smart sug'orish tizimlari
    'smart_tv_ornatish_ulash',                                                  # Smart TV o'rnatish
    'uy_kinoteatri_tizimlari_ornatish',                                         # Uy kinoteatri tizimlari
    'audio_tizimlar_multiroom',                                                 # Multiroom audio tizimlari
    'ip_telefoniya_mini_ats_tizimlarini_tashkil_qilish',                        # IP telefoniya tizimlari
    'video_konferensiya_tizimlari',                                             # Video konferensiya tizimlari
    'interaktiv_taqdimot_tizimlari_proyektor_led_ekran',                        # Interaktiv taqdimot tizimlari
    'aqlli_ofis_tizimlarini_ornatish',                                          # Aqlli ofis tizimlari
    'data_markaz_server_room_loyihalash_montaj_qilish',                         # Data markaz loyihalash
    'qurilma_tizimlar_uchun_texnik_xizmat_korsatish',                           # Qurilma texnik xizmati
    'dasturiy_taminotni_ornatish_yangilash',                                    # Dasturiy ta'minot o'rnatish
    'iot_internet_of_things_qurilmalarini_integratsiya_qilish',                 # IoT qurilmalarni integratsiya
    'qurilmalarni_masofadan_boshqarish_tizimlarini_sozlash',                    # Masofaviy boshqarish tizimlari
    'suniy_intellekt_asosidagi_uy_ofis_boshqaruv_tizimlari'                     # AI boshqaruv tizimlari
]

def validate_smart_service_type(value: str) -> bool:
    """
    Smart service type qiymatini validatsiya qilish
    Qiymat ro'yxatda mavjudligini tekshiradi
    
    Args:
        value (str): Tekshiriladigan service type qiymati
        
    Returns:
        bool: Qiymat ro'yxatda mavjud bo'lsa True, aks holda False
    """
    return value in SMART_SERVICE_TYPES

# ==================== ASOSIY MODELLAR ====================
@dataclass
class BaseModel:
    """
    Barcha ma'lumotlar bazasi modellarining asosiy klassi
    Umumiy maydonlarni o'z ichiga oladi
    """
    id: Optional[int] = None                    # Jadval yozuvi IDsi (PRIMARY KEY)
    created_at: Optional[datetime] = None       # Yozuv yaratilgan vaqt
    updated_at: Optional[datetime] = None       # Yozuv oxirgi marta yangilangan vaqt

@dataclass
class Users(BaseModel):
    """
    Foydalanuvchilar jadvali modeli
    Tizim foydalanuvchilari haqida ma'lumot saqlaydi
    """
    telegram_id: Optional[int] = None           # Telegram foydalanuvchi IDsi (UNIQUE)
    full_name: Optional[str] = None             # Foydalanuvchi to'liq ismi
    username: Optional[str] = None              # Telegram username
    phone: Optional[str] = None                 # Telefon raqami
    language: str = "uz"                        # Til sozlamasi (default: uz)
    region: Optional[int] = None                # Hudud IDsi
    address: Optional[str] = None               # Manzil
    role: Optional[UserRole] = None             # Foydalanuvchi roli (ENUM)
    abonent_id: Optional[str] = None            # Abonent identifikatori
    is_blocked: bool = False                    # Foydalanuvchi bloklanganmi?

@dataclass
class Tarif(BaseModel):
    """
    Internet tariflari jadvali modeli
    Mavjud tarif rejalari haqida ma'lumot saqlaydi
    """
    name: Optional[str] = None                  # Tarif nomi
    picture: Optional[str] = None               # Tarif rasmi (fayl yo'li)

@dataclass
class ConnectionOrders(BaseModel):
    """
    Internet ulanish arizalari jadvali modeli
    Yangi ulanish so'rovlari haqida ma'lumot saqlaydi
    """
    user_id: Optional[int] = None               # Foydalanuvchi IDsi (FK users.id)
    region: Optional[str] = None                # Hudud nomi
    address: Optional[str] = None               # To'liq manzil
    tarif_id: Optional[int] = None              # Tanlangan tarif IDsi (FK tarif.id)
    longitude: Optional[float] = None           # Uzunlik (GPS koordinata)
    latitude: Optional[float] = None            # Kenglik (GPS koordinata)
    jm_notes: Optional[str] = None              # Junior manager izohlari
    is_active: bool = True                      # Ariza faolmi?
    status: ConnectionOrderStatus = ConnectionOrderStatus.IN_MANAGER  # Ariza statusi

@dataclass
class TechnicianOrders(BaseModel):
    """
    Texnik xizmat buyurtmalari jadvali modeli
    Texnik xizmat so'rovlari haqida ma'lumot saqlaydi
    """
    user_id: Optional[int] = None               # Foydalanuvchi IDsi (FK users.id)
    region: Optional[str] = None                # Hudud IDsi
    abonent_id: Optional[str] = None            # Abonent identifikatori
    address: Optional[str] = None               # Manzil
    media: Optional[str] = None                 # Media fayllar (rasm/video yo'li)
    longitude: Optional[float] = None           # Uzunlik (GPS koordinata)
    latitude: Optional[float] = None            # Kenglik (GPS koordinata)
    description: Optional[str] = None           # mijoz tavsifi
    description_ish: Optional[str] = None       # Bajarilgan ish tavsifi
    description_operator: Optional[str] = None  # Operator izohlari
    status: TechnicianOrderStatus = TechnicianOrderStatus.IN_CONTROLLER  # Buyurtma statusi
    is_active: bool = True                      # Buyurtma faolmi?

@dataclass
class SaffOrders(BaseModel):
    """
    SAFF (Call Center) buyurtmalari jadvali modeli
    Turli foydalanuvchilar tomonidan yaratilgan so'rovlarni saqlaydi
    """
    user_id: Optional[int] = None               # Foydalanuvchi IDsi (FK users.id) - Yaratuvchi
    phone: Optional[str] = None                 # Telefon raqami
    region: Optional[int] = None                # Hudud IDsi
    abonent_id: Optional[str] = None            # Abonent identifikatori
    tarif_id: Optional[int] = None              # Tarif IDsi (FK tarif.id)
    address: Optional[str] = None               # Manzil
    description: Optional[str] = None           # Tavsif
    status: SaffOrderStatus = SaffOrderStatus.NEW  # Boshlang'ich status - NEW
    type_of_zayavka: SaffOrderTypeOfZayavka = SaffOrderTypeOfZayavka.CONNECTION  # Ariza turi
    is_active: bool = True                      # Ariza faolmi?
    created_by_role: Optional[UserRole] = None  # Kim tomonidan yaratilgani (qo'shimcha)

@dataclass
class SmartServiceOrders(BaseModel):
    """
    Smart Service buyurtmalari jadvali modeli
    Aqlli texnologiyalar bo'yicha so'rovlarni saqlaydi
    """
    user_id: Optional[int] = None               # Foydalanuvchi IDsi (FK users.id)
    category: SmartServiceCategory = None       # Xizmat kategoriyasi (ENUM)
    service_type: str = None                    # Xizmat turi (DOMAIN qiymat)
    address: str = ""                           # Manzil
    longitude: Optional[float] = None           # Uzunlik (GPS koordinata)
    latitude: Optional[float] = None            # Kenglik (GPS koordinata)
    is_active: bool = True                      # Buyurtma faolmi?

    def __post_init__(self):
        """
        Smart service type qiymatini validatsiya qilish
        Qiymat ro'yxatda mavjudligini tekshiradi
        """
        if self.service_type and not validate_smart_service_type(self.service_type):
            raise ValueError(f"Invalid smart service type: {self.service_type}")

@dataclass
class Connections(BaseModel):
    """
    Buyurtmalarni bog'lash jadvali modeli
    Har xil turdagi buyurtmalarni foydalanuvchilar bilan bog'laydi
    """
    sender_id: Optional[int] = None             # Yuboruvchi foydalanuvchi IDsi (FK users.id)
    recipient_id: Optional[int] = None          # Qabul qiluvchi foydalanuvchi IDsi (FK users.id)
    connecion_id: Optional[int] = None          # Ulanish buyurtmasi IDsi (FK connection_orders.id)
    technician_id: Optional[int] = None         # Texnik buyurtmasi IDsi (FK technician_orders.id)
    saff_id: Optional[int] = None               # SAFF buyurtmasi IDsi (FK saff_orders.id)
    sender_status: Optional[str] = None         # Yuboruvchi statusi
    recipient_status: Optional[str] = None      # Qabul qiluvchi statusi

@dataclass
class Materials(BaseModel):
    """
    Materiallar jadvali modeli
    Omborda mavjud materiallar haqida ma'lumot saqlaydi
    """
    name: Optional[str] = None                  # Material nomi
    price: Optional[float] = None               # Narxi (so'mda)
    description: Optional[str] = None           # Tavsif
    quantity: int = 0                           # Miqdori
    serial_number: Optional[str] = None         # Seriya raqami (UNIQUE)

@dataclass
class MaterialRequests(BaseModel):
    """
    Material so'rovlari jadvali modeli
    Texniklar tomonidan material so'rovlari haqida ma'lumot saqlaydi
    """
    description: Optional[str] = None           # Tavsif
    user_id: Optional[int] = None               # Foydalanuvchi IDsi (FK users.id)
    applications_id: Optional[int] = None       # Ariza IDsi
    material_id: Optional[int] = None           # Material IDsi (FK materials.id)
    connection_order_id: Optional[int] = None   # Ulanish buyurtmasi IDsi (FK)
    technician_order_id: Optional[int] = None   # Texnik buyurtmasi IDsi (FK)
    saff_order_id: Optional[int] = None         # SAFF buyurtmasi IDsi (FK)
    quantity: int = 1                           # So'ralgan miqdor
    price: float = 0.0                          # Birlik narxi
    total_price: float = 0.0                    # Umumiy narx

@dataclass
class MaterialAndTechnician(BaseModel):
    """
    Texnik va materiallar bog'lanishi jadvali modeli
    Har bir texnik qaysi materiallardan foydalanganini kuzatib boradi
    """
    user_id: Optional[int] = None               # Texnik foydalanuvchi IDsi (FK users.id)
    material_id: Optional[int] = None           # Material IDsi (FK materials.id)
    quantity: Optional[int] = None              # Foydalangan miqdor

@dataclass
class Reports(BaseModel):
    """
    Hisobotlar jadvali modeli
    Managerlar tomonidan yaratilgan hisobotlarni saqlaydi
    """
    title: str = ""                             # Hisobot sarlavhasi
    description: Optional[str] = None           # Hisobot tavsifi
    created_by: Optional[int] = None            # Yaratuvchi foydalanuvchi IDsi (FK users.id)

@dataclass
class AktDocuments(BaseModel):
    """
    AKT hujjatlari jadvali modeli
    Bajarilgan ishlarning rasmiy hujjatlarini saqlaydi
    """
    request_id: Optional[int] = None            # So'rov IDsi
    request_type: Optional[str] = None          # So'rov turi ('connection', 'technician', 'saff')
    akt_number: str = ""                        # AKT raqami (AKT-{request_id}-{YYYYMMDD})
    file_path: str = ""                         # Fayl yo'li
    file_hash: str = ""                         # Fayl SHA256 hash
    sent_to_client_at: Optional[datetime] = None  # Mijozga yuborilgan vaqt

    def __post_init__(self):
        """
        So'rov turi qiymatini validatsiya qilish
        Qiymat ruxsat etilganlar ro'yxatida bo'lishi kerak
        """
        if self.request_type and self.request_type not in ['connection', 'technician', 'saff']:
            raise ValueError("Invalid request type")

@dataclass
class AktRatings(BaseModel):
    """
    AKT reytinglari jadvali modeli
    Mijozlarning bajarilgan ishlarga bergan reytinglarini saqlaydi
    """
    request_id: Optional[int] = None            # So'rov IDsi
    request_type: Optional[str] = None          # So'rov turi ('connection', 'technician', 'saff')
    rating: int = 0                             # Reyting (0-5)
    comment: Optional[str] = None               # Mijoz izohlari

    def __post_init__(self):
        """
        So'rov turi va reyting qiymatlarini validatsiya qilish
        """
        if self.request_type and self.request_type not in ['connection', 'technician', 'saff']:
            raise ValueError("Invalid request type")
        if not (0 <= self.rating <= 5):
            raise ValueError("Rating must be between 0 and 5")
        
def validate_request_type(value: str) -> bool:
    """
    So'rov turi qiymatini validatsiya qilish
    
    Args:
        value (str): Tekshiriladigan so'rov turi
        
    Returns:
        bool: Qiymat ruxsat etilganlar ro'yxatida bo'lsa True, aks holda False
    """
    return value in ['connection', 'technician', 'saff']

@dataclass
class MediaFiles(BaseModel):
    """
    Media fayllar uchun markazlashtirilgan model
    Barcha turdagi fayllarni saqlash uchun ishlatiladi
    """
    file_path: str = ""                          # "media/2024/01/orders/attachments/file.jpg"
    file_type: Optional[str] = None              # 'image', 'video', 'document', 'archive'
    file_size: Optional[int] = None              # bytes
    original_name: Optional[str] = None          # foydalanuvchi ko'radi
    mime_type: Optional[str] = None              # 'image/jpeg', 'application/pdf'
    category: Optional[str] = None               # 'order_attachment', 'akt', 'report', 'export'
    related_table: Optional[str] = None          # 'connection_orders', 'technician_orders'
    related_id: Optional[int] = None             # bog'langan yozuv ID
    uploaded_by: Optional[int] = None            # foydalanuvchi ID (FK users.id)
    is_active: bool = True                       # fayl faolmi?

# ==================== DATABASE KONFIGURATSIYA ====================
# Database konfiguratsiyasi - jadvallar va enumlar ro'yxati
DATABASE_CONFIG = {
    "tables": [
        "users", "tarif", "connection_orders", "technician_orders", 
        "saff_orders", "smart_service_orders", "connections", 
        "materials", "material_requests", "material_and_technician",
        "reports", "akt_documents", "akt_ratings", "media_files"  # Qo'shilgan
    ],
    "enums": {
    "connection_order_status": [status.value for status in ConnectionOrderStatus],
    "smart_service_category": [category.value for category in SmartServiceCategory],
    "technician_order_status": [status.value for status in TechnicianOrderStatus],
    "saff_order_status": [status.value for status in SaffOrderStatus],
    "saff_order_type_of_zayavka": [zayavka.value for zayavka in SaffOrderTypeOfZayavka],
    "type_of_zayavka": [zayavka.value for zayavka in SaffOrderTypeOfZayavka],
    "user_role": [role.value for role in UserRole]
}
}


# ==================== HELPER FUNKSIYALAR ====================
def get_table_name(model_class) -> str:
    """
    Model klass nomidan jadval nomini olish
    Klass nomini kichik harflarga o'girib qaytaradi
    
    Args:
        model_class: Model klassi
        
    Returns:
        str: Jadval nomi (masalan: Users -> users, Tarif -> tarif)
    """
    class_name = model_class.__name__
    if class_name.endswith('s'):
        return class_name.lower()
    return f"{class_name.lower()}s"

def validate_rating(value: int) -> bool:
    """
    Reyting qiymatini validatsiya qilish (0-5 oralig'i)
    
    Args:
        value (int): Tekshiriladigan reyting qiymati
        
    Returns:
        bool: Qiymat 0-5 oralig'ida bo'lsa True, aks holda False
    """
    return 0 <= value <= 5

def validate_request_type(value: str) -> bool:
    """
    So'rov turi qiymatini validatsiya qilish
    
    Args:
        value (str): Tekshiriladigan so'rov turi
        
    Returns:
        bool: Qiymat ruxsat etilganlar ro'yxatida bo'lsa True, aks holda False
    """
    return value in ['connection', 'technician', 'saff']