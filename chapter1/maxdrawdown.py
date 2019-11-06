import numpy as np

def get_max_drawdown(array):
    drawdowns = []
    for i in range(len(array)):
        max_array = max(array[:i+1])
        drawdown = max_array - array[i]
        drawdowns.append(drawdown)
    return max(drawdowns)

np.random.seed(1)
a = np.random.randn(1000)
values = np.cumsum(a)
result = get_max_drawdown(values)
print(result)
