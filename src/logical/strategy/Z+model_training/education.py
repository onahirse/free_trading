
from src.logical.model_training.fe_v1 import make_features
from src.logical.model_training.fe_v2 import make_features_v2

import joblib

# процесс обучения моделей
# df - данные для обучения
def education(df):

    # X, y_reg, y_cls = make_features(df, horizon=5)
    X, y_reg, y_cls = make_features_v2(df, horizon=5)
    
    print("Статистика таргета (y_reg):")
    print(y_reg.describe())

     
    # обучаем классификатор
    from lightgbm import LGBMClassifier
    clf = LGBMClassifier()
    clf.fit(X, y_cls)

    # обучаем регрессию
    from lightgbm import LGBMRegressor
    reg = LGBMRegressor()
    reg.fit(X, y_reg)
    
    # сохраняем
    joblib.dump(clf, "clf_model.pkl")
    joblib.dump(reg, "reg_model.pkl")

    return clf, reg
    