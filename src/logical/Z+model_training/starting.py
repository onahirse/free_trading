import joblib

from src.logical.Z+model_training.education import education
from src.logical.model_training.predictions import make_prediction

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)


def starting(data):
    
    logger.info("Запускаем обучение моделей")
    # обучение моделей
    education(data)
    logger.info("Обучение завершено")
    
    logger.info("Получаем предсказания")
    clf = joblib.load("clf_model.pkl")
    reg = joblib.load("reg_model.pkl")
    
    proba_down, proba_up, y_pred_reg = make_prediction(data,clf, reg)
    logger.info(f"Вероятность роста: {round( proba_up, 2)}%")
    logger.info(f"Вероятность падения: {round(proba_down, 2)}%")

    logger.info(f"Ожидаемая доходность: {round(y_pred_reg, 2)}%")