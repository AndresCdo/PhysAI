import matplotlib.pyplot as plt

x = [0, 1]
y = [1, 0]
plt.plot(x, y)
plt.title('x + y = z')
plt.xlabel('x')
plt.ylabel('y')
plt.savefig('equation_images/plot.png')