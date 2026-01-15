from typing import Callable, Dict, Any
import pandas as pd

Condition = Callable[[pd.DataFrame, Dict[str, Any]], bool]

__all__ = ['Condition']
