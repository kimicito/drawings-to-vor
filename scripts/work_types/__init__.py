from abc import ABC, abstractmethod
from typing import List, Dict, Tuple


class WorkTypeExtractor(ABC):
    """Базовый класс для извлечения объёмов работ из OCR-результатов.
    
    Каждый подкласс реализует:
    - detect(): определяет, есть ли на чертеже этот тип работ
    - extract(): извлекает спецификации и рассчитывает объёмы
    - generate_vor(): формирует строки ВОР
    """
    
    TYPE_NAME: str = ""
    KEYWORDS: List[str] = []
    
    @classmethod
    def detect(cls, ocr_text: str) -> bool:
        """Проверяет, содержит ли текст ключевые слова этого типа работ."""
        text_lower = ocr_text.lower()
        return any(kw.lower() in text_lower for kw in cls.KEYWORDS)
    
    @abstractmethod
    def extract(self, data: list) -> List[Dict]:
        """Извлекает спецификации из OCR данных."""
        pass
    
    @abstractmethod
    def generate_vor(self, specs: List[Dict]) -> Tuple[List[Dict], Dict]:
        """Генерирует строки ВОР. Возвращает (rows, totals)."""
        pass
    
    def get_resource_code(self, work_name: str) -> str:
        """Возвращает код ресурса по названию работы."""
        # Переопределяется в подклассах
        return ""


class VolumeCalculator:
    """Общие формулы расчёта объёмов."""
    
    @staticmethod
    def pile_volume(diameter_mm: float, length_m: float) -> float:
        """Объём цилиндра сваи."""
        r = (diameter_mm / 1000) / 2
        return 3.14159 * (r ** 2) * length_m
    
    @staticmethod
    def rectangular_volume(length_m: float, width_m: float, height_m: float) -> float:
        """Объём прямоугольной конструкции."""
        return length_m * width_m * height_m
    
    @staticmethod
    def soil_with_loosening(volume_m3: float, factor: float = 1.15) -> float:
        """Объём выбурки с учётом разрыхления."""
        return volume_m3 * factor
    
    @staticmethod
    def rebar_weight(concrete_m3: float, kg_per_m3: float = 120) -> float:
        """Вес арматуры."""
        return concrete_m3 * kg_per_m3
    
    @staticmethod
    def excavation_volume(length_m: float, width_m: float, depth_m: float) -> float:
        """Объём земляной выемки."""
        return length_m * width_m * depth_m
    
    @staticmethod
    def wall_area(length_m: float, height_m: float) -> float:
        """Площадь стены."""
        return length_m * height_m
    
    @staticmethod
    def floor_area(length_m: float, width_m: float) -> float:
        """Площадь перекрытия."""
        return length_m * width_m
