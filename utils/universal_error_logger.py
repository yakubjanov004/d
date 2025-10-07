"""
Universal Error Logger - Centralized logging system

Bu modul barcha xatolarni markazlashtirilgan tarzda log qiladi.
"""

import logging
import traceback
from typing import Optional, Dict, Any
from datetime import datetime
import json
import os
from logging.handlers import RotatingFileHandler

log_dir = "media/logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            os.path.join(log_dir, "bot.log"), 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        ),
        RotatingFileHandler(
            os.path.join(log_dir, "errors.log"), 
            maxBytes=5*1024*1024,   # 5MB
            backupCount=3,
            encoding="utf-8"
        )
    ]
)

# Error logger alohida
error_logger = logging.getLogger("ErrorLogger")
error_handler = RotatingFileHandler(
    os.path.join(log_dir, "errors.log"), 
    maxBytes=5*1024*1024, 
    backupCount=3,
    encoding="utf-8"
)
error_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter(
    "%(asctime)s | ERROR | %(message)s"
)
error_handler.setFormatter(error_formatter)
error_logger.addHandler(error_handler)
error_logger.setLevel(logging.ERROR)

def get_universal_logger(name: str = "AlfaConnectBot") -> logging.Logger:
    """Universal logger olish"""
    return logging.getLogger(name)

def log_error(
    error: Exception,
    context: str = "",
    user_id: Optional[int] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """Xatolarni log qilish"""
    logger = get_universal_logger()
    
    error_data = {
        "timestamp": datetime.now().isoformat(),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context,
        "user_id": user_id,
        "traceback": traceback.format_exc()
    }
    
    if additional_data:
        error_data.update(additional_data)
    
    # Asosiy loggerga yozish
    logger.error(f"ERROR: {json.dumps(error_data, ensure_ascii=False)}")
    
    # Alohida error loggerga ham yozish
    error_logger.error(json.dumps(error_data, ensure_ascii=False, indent=2))

def log_info(message: str, context: str = "", user_id: Optional[int] = None) -> None:
    """Info log qilish"""
    logger = get_universal_logger()
    logger.info(f"INFO: {context} | {message} | User: {user_id}")

def log_warning(message: str, context: str = "", user_id: Optional[int] = None) -> None:
    """Warning log qilish"""
    logger = get_universal_logger()
    logger.warning(f"WARNING: {context} | {message} | User: {user_id}")

def log_debug(message: str, context: str = "", user_id: Optional[int] = None) -> None:
    """Debug log qilish"""
    logger = get_universal_logger()
    logger.debug(f"DEBUG: {context} | {message} | User: {user_id}")

def get_recent_errors(limit: int = 50) -> list:
    """So'nggi xatoliklarni olish"""
    error_file = os.path.join(log_dir, "errors.log")
    errors = []
    
    if os.path.exists(error_file):
        try:
            with open(error_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # So'nggi qatorlarni olish
                recent_lines = lines[-limit*3:]  # Har bir error bir necha qator bo'lishi mumkin
                
                current_error = ""
                for line in recent_lines:
                    if line.strip().startswith('{'):
                        if current_error:
                            try:
                                error_data = json.loads(current_error)
                                errors.append(error_data)
                            except:
                                pass
                        current_error = line.strip()
                    elif current_error and (line.startswith('  ') or line.startswith('\t')):
                        current_error += line
                
                # So'nggi errorni ham qo'shish
                if current_error:
                    try:
                        error_data = json.loads(current_error)
                        errors.append(error_data)
                    except:
                        pass
                        
        except Exception as e:
            log_error(e, "Error reading error log file")
    
    return errors[-limit:] if len(errors) > limit else errors

def search_errors_by_type(error_type: str, limit: int = 20) -> list:
    """Xatolik turi bo'yicha qidirish"""
    all_errors = get_recent_errors(200)  # Ko'proq error olish
    filtered_errors = []
    
    for error in all_errors:
        if error.get('error_type', '').lower() == error_type.lower():
            filtered_errors.append(error)
            if len(filtered_errors) >= limit:
                break
    
    return filtered_errors

def get_error_statistics() -> Dict[str, Any]:
    """Xatoliklar statistikasi"""
    errors = get_recent_errors(100)
    stats = {
        'total_errors': len(errors),
        'error_types': {},
        'users_with_errors': set(),
        'contexts': {}
    }
    
    for error in errors:
        # Error type statistikasi
        error_type = error.get('error_type', 'Unknown')
        stats['error_types'][error_type] = stats['error_types'].get(error_type, 0) + 1
        
        # User statistikasi
        user_id = error.get('user_id')
        if user_id:
            stats['users_with_errors'].add(user_id)
        
        # Context statistikasi
        context = error.get('context', 'Unknown')
        stats['contexts'][context] = stats['contexts'].get(context, 0) + 1
    
    stats['users_with_errors'] = len(stats['users_with_errors'])
    return stats

def clear_old_logs(days: int = 7) -> None:
    """Eski loglarni tozalash"""
    import time
    
    current_time = time.time()
    cutoff_time = current_time - (days * 24 * 60 * 60)
    
    for filename in os.listdir(log_dir):
        if filename.endswith('.log'):
            filepath = os.path.join(log_dir, filename)
            if os.path.getctime(filepath) < cutoff_time:
                try:
                    os.remove(filepath)
                    log_info(f"Old log file removed: {filename}", "Log Cleanup")
                except Exception as e:
                    log_error(e, f"Error removing old log file: {filename}")
