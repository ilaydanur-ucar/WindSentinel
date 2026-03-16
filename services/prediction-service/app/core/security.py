import hashlib
import logging

logger = logging.getLogger(__name__)

def verify_file_checksum(file_path: str, expected_hash: str) -> bool:
    """
    Dosyanın SHA256 hash bütünlüğünü doğrular. 
    Bir güvenlik önlemi olarak (OWASP), dışarıdan yüklenen modellerin 
    bozulmadığından veya değiştirilmediğinden emin olur.
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        actual_hash = sha256_hash.hexdigest()
        if actual_hash == expected_hash:
            return True
            
        logger.warning(f"BÜTÜNLÜK HATASI: {file_path} için beklenen {expected_hash}, ama bulunan {actual_hash}")
        return False
    except FileNotFoundError:
        logger.error(f"Dosya bulunamadı: {file_path}")
        return False
    except Exception as e:
        logger.error(f"Checksum hesaplama sırasında beklenmedik hata: {e}")
        return False
