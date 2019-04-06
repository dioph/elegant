import numpy as np


def gauss_seidel(Y, V0, S, eps=None, Niter=1):
    """Gauss-Seidel Method

    Parameters
    ----------
    Y: Matriz Ybarra (N,N)
    V0: Chute inicial complexo (N,)
    S: Potencias especificadas (N,2)
    eps: tolerancia (optional)
    Niter: Numero de iteracoes minimo (optional default=1)

    Returns
    -------
    V: aproximacao para tensoes nos nos
    """
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




def newton_raphson(Y, V0, S, eps=None, Niter=1):
    """Newthon-Raphson Method
    Parameters
    ----------
    Y: Matriz de admitâncias
    V0: Vetor de chutes iniciais (N,1)
    S0: Potencias aparantes especificadas (N,2)
    eps:
    Niter:

    Returns
    -------
    V: Aproximacao para tensao nos nós
    """
    def Gij(i, j):
        return np.abs(Y[i][j])*np.cos(np.angle(Y[i][j]))

    def Bij(i, j):
        return np.abs(Y[i][j])*np.sin(np.angle(Y[i][j]))

    def Pi(i):
        _ = 0
        for n in range(N):
            if n != N:
                _ += np.abs(V[i]*V[n]*Y[i][n])*np.cos(np.angle(Y[i][n])+np.angle(V[n])-np.angle(V[i]))
        return np.abs(V[i])^2*Gij(i, i)+_

    def Qi(i):
        _ = 0
        for n in range(N):
            if n != N:
                _ += np.abs(V[i]*V[n]*Y[i][n])*np.sin(np.angle(Y[i][n])+np.angle(V[n])-np.angle(V[i]))
        return -np.abs(V[i])^2*Bij(i, i)-_

    def Mii(i):
        return -Q[i]-np.abs(V[i])**2*Bij(i, i)

    def Nii(i):
        return Pi(i)-np.abs(V[i])**2*Gij(i, i)

    def Mij(i, j):
        return np.abs(V[j])*np.abs(V[i]*Y[i][j])*np.sin(np.angle(Y[i][j]) + np.angle(V[j]) - np.angle(V[i]))

    def Nij(i, j):
        return -np.abs(V[i]*V[j]*Y[i][j]*np.cos(np.angle(Y[i][j]) + np.angle(V[j]) - np.angle(V[i])))

    def J_inv(N):
        J11, J12, J21, J22 = np.zeros([N-1][N-1])
        for i in range(2, N):
            for j in range(2, N):
                J11[i][j] = Mii(i)
                J21[i][j] = Nii(i)
                if i == j:
                    J12[i][j] = Nii(i)+2*np.abs(V[i])**2*Gij(i, i)
                    J22[i][j] = -Mii(i)-2*np.abs(V[i])**2*Bij(i, i)
                else:
                    J12[i][j] = -Nij(i, j)
                    J22[i][j] = Mij(i, j)

        J_inv = np.linalg.inv(np.array([J11, J12], [J21, J22]))

        return J_inv

    N = V0.size
    V = V0.copy()
    delta = np.inf
    if eps is None:
        eps = np.inf
    count = 0
    while delta < eps or count < Niter:
        for i in range(N):
            pass