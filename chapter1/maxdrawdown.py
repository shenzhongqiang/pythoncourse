
def get_max_drawdown(array):
    drawdowns = []
    for i in range(len(array)):
        max_array = max(array[:i+1])
        drawdown = max_array - array[i]
        drawdowns.append(drawdown)
    return max(drawdowns)

values = [1, 2, 3, 5, 8, 13, 5, 6, 1, 29, 2, 1, 11, 17]
result = get_max_drawdown(values)
print(result)
