import numpy as np
import matplotlib.pyplot as plt

np.random.seed(0)

mu1 = [2, 2]
cov1 = [[2, 1],
        [1, 2]]

mu2 = [7, 5]
cov2 = [[2, -1],
        [-1, 2]]

X1 = np.random.multivariate_normal(mu1, cov1, 500)
X2 = np.random.multivariate_normal(mu2, cov2, 500)

plt.scatter(X1[:, 0], X1[:, 1], s=10)
plt.scatter(X2[:, 0], X2[:, 1], s=10)
plt.axis("equal")
plt.show()
