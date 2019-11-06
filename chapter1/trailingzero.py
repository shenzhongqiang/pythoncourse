num = 0
n = 100

while True:
    n = int(n / 5)
    if n == 0:
	break
    num = num + n

print(num)
