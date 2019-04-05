import numpy as np


def gauss_seidel(Y, V0, S, eps=None, Niter=1):
    N = V0.size
    V = np.copy(V0)
    delta = np.inf
    if eps is None:
        eps = np.inf
    count = 0
    while delta > eps or count < Niter:
        for i in range(N):
            I = np.dot(Y[i], V0)
            P, Q = S[i]
            if np.isnan(P):
                continue
            if np.isnan(Q):
                Q = -np.imag(np.conjugate(V0[i]) * I)
                V0[i] = ((P - 1j * Q) / np.conjugate(V0[i]) - (I - Y[i,i] * V0[i])) / Y[i,i]
                V0[i] = V0[i] * np.abs(V[i]) / np.abs(V0[i])
            else:
                V0[i] = ((P - 1j * Q) / np.conjugate(V0[i]) - (I - Y[i, i] * V0[i])) / Y[i,i]
        delta = max(np.abs(V-V0))
        V = np.copy(V0)
        count += 1
    print('TOTAL: {} ITERACOES'.format(count))
    return V

