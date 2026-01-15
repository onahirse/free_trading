import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ta  # Technical Analysis Library

df = pd.read_csv('data.csv', encoding='utf-8')

# Рассчитываем индикаторы с помощью библиотеки ta
df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=18).rsi()  # RSI
stoch = ta.momentum.StochasticOscillator(df['High'], df['Low'], df['Close'], window=14, smooth_window=3)
df['%K'] = stoch.stoch()  # Stochastic Oscillator %K
df['%D'] = stoch.stoch_signal()  # Stochastic Oscillator %D
df['EMA'] = ta.trend.EMAIndicator(df['Close'], window=20).ema_indicator()  # EMA
bollinger = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
df['BB_upper'] = bollinger.bollinger_hband()  # Bollinger Bands Upper
df['BB_middle'] = bollinger.bollinger_mavg()  # Bollinger Bands Middle
df['BB_lower'] = bollinger.bollinger_lband()  # Bollinger Bands Lower

# Создаем свечной график
fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.6, 0.2, 0.2]
)

# Добавляем свечной график
fig.add_trace(go.Candlestick(
    x=df['Date'],
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close'],
    name='Цены'
), row=1, col=1)

# Добавляем EMA
fig.add_trace(go.Scatter(
    x=df['Date'],
    y=df['EMA'],
    mode='lines',
    name='EMA (20)',
    line=dict(color='orange', width=1.5)
), row=1, col=1)

# Добавляем Bollinger Bands
fig.add_trace(go.Scatter(
    x=df['Date'],
    y=df['BB_upper'],
    mode='lines',
    name='Bollinger Upper',
    line=dict(color='blue', width=1, dash='dot')
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=df['Date'],
    y=df['BB_middle'],
    mode='lines',
    name='Bollinger Middle',
    line=dict(color='blue', width=1)
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=df['Date'],
    y=df['BB_lower'],
    mode='lines',
    name='Bollinger Lower',
    line=dict(color='blue', width=1, dash='dot')
), row=1, col=1)

# Добавляем RSI как подграфик
fig.add_trace(go.Scatter(
    x=df['Date'],
    y=df['RSI'],
    mode='lines',
    name='RSI (14)',
    line=dict(color='green', width=1)
), row=2, col=1)

# Добавляем горизонтальные линии для RSI (70 и 30)
fig.add_trace(go.Scatter(
    x=[df['Date'].min(), df['Date'].max()],
    y=[70, 70],
    mode='lines',
    name='RSI Overbought (70)',
    line=dict(color='red', width=1, dash='dash')
), row=2, col=1)

fig.add_trace(go.Scatter(
    x=[df['Date'].min(), df['Date'].max()],
    y=[30, 30],
    mode='lines',
    name='RSI Oversold (30)',
    line=dict(color='green', width=1, dash='dash')
), row=2, col=1)

# Добавляем Stochastic Oscillator как подграфик
fig.add_trace(go.Scatter(
    x=df['Date'],
    y=df['%K'],
    mode='lines',
    name='%K (Stochastic)',
    line=dict(color='red', width=1)
), row=3, col=1)

fig.add_trace(go.Scatter(
    x=df['Date'],
    y=df['%D'],
    mode='lines',
    name='%D (Stochastic)',
    line=dict(color='purple', width=1)
), row=3, col=1)

# Настройка осей
fig.update_yaxes(title_text="Цена", row=1, col=1)
fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
fig.update_yaxes(title_text="Stochastic", row=3, col=1, range=[0, 100])

# Общие настройки графика
fig.update_layout(
    title='Свечной график с индикаторами',
    xaxis_title='Дата',
    xaxis_rangeslider_visible=False,
    height=800
)

# Показать график
fig.show()