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
                V0[i] = ((P - 1j * Q) / np.conjugate(V0[i]) - (I - Y[i, i] * V0[i])) / Y[i, i]
                V0[i] = V0[i] * np.abs(V[i]) / np.abs(V0[i])
            else:
                V0[i] = ((P - 1j * Q) / np.conjugate(V0[i]) - (I - Y[i, i] * V0[i])) / Y[i, i]
        delta = max(np.abs(V - V0))
        V = np.copy(V0)
        count += 1
    print('TOTAL: {} ITERACOES'.format(count))
    return V


def Gij(i, j, Y):
    return np.abs(Y[i][j]) * np.cos(np.angle(Y[i][j]))


def Bij(i, j, Y):
    return np.abs(Y[i][j]) * np.sin(np.angle(Y[i][j]))


def Pi(i, N, V, Y):
    _ = 0
    for n in range(N):
        if n != i:
            _ += np.abs(V[i] * V[n] * Y[i][n]) * np.cos(np.angle(Y[i][n]) + np.angle(V[n]) - np.angle(V[i]))
    return np.abs(V[i]) ** 2 * Gij(i, i, Y) + _


def Qi(i, N, V, Y):
    _ = 0
    for n in range(N):
        if n != i:
            _ += np.abs(V[i] * V[n] * Y[i][n]) * np.sin(np.angle(Y[i][n]) + np.angle(V[n]) - np.angle(V[i]))
    return -np.abs(V[i]) ** 2 * Bij(i, i, Y) - _


def Mij(i, j, V, N, Y):
    if i == j:
        return -Qi(i, N, V, Y) - np.abs(V[i]) ** 2 * Bij(i, i, Y)
    else:
        return -np.abs(V[j]) * np.abs(V[i] * Y[i][j]) * np.sin(np.angle(Y[i][j]) + np.angle(V[j]) - np.angle(V[i]))


def Nij(i, j, V, N, Y):
    if i == j:
        return Pi(i, N, V, Y) - np.abs(V[i]) ** 2 * Gij(i, i, Y)
    else:
        return -np.abs(V[i] * V[j] * Y[i][j]) * np.cos(np.angle(Y[i][j]) + np.angle(V[j]) - np.angle(V[i]))


def J11(N, V, Y):
    j11 = np.zeros([N, N])
    for i in range(N):
        for j in range(N):
            j11[i][j] = Mij(i, j, V, N, Y)
    return j11


def J12(N, V, Y):
    j12 = np.zeros([N, N])
    for i in range(N):
        for j in range(N):
            j12[i][j] = Nij(i, j, V, N, Y) + 2 * np.abs(V[i]) ** 2 * Gij(i, j, Y) if i == j else -Nij(i, j, V, N, Y)
    return j12


def J21(N, V, Y):
    j21 = np.zeros([N, N])
    for i in range(N):
        for j in range(N):
            j21[i][j] = Nij(i, j, V, N, Y)
    return j21


def J22(N, V, Y):
    j22 = np.zeros([N, N])
    for i in range(N):
        for j in range(N):
            j22[i][j] = -Mij(i, j, V, N, Y) - 2 * np.abs(V[i]) ** 2 * Bij(i, j, Y) if i == j else Mij(i, j, V, N, Y)
    return j22


def jacobian(N, V0, Y):
    """
    Parameters
    ----------
    N: size of V0
    V0: array with initial estimates (1, N)
    Y: admittance matrix

    Returns
    -------
    J: Jacobian matrix (N, N)
    """
    j11_j12 = np.append(J11(N, V0, Y), J12(N, V0, Y), axis=1)
    j21_j22 = np.append(J21(N, V0, Y), J22(N, V0, Y), axis=1)
    J = np.append(j11_j12, j21_j22, axis=0)
    return J


def DeltaVdelta(deltaPQ, N, V0, Y):
    """
    Parameters
    ----------
    deltaPQ: mismatches arrays (1, N)
    N: size of V0
    V0: array with initial estimates (1, N)
    Y: admittance matrix

    Returns
    -------
    jacobiansDespises: array with positions to be removed from J
    deltaVdelta: array with the increase values to update V0
    """
    n = np.size(deltaPQ)
    deltaPQ_adj = np.empty([0, 0])
    jacobiansDespises = np.empty([0, 0])
    j_adj = jacobian(N, V0, Y)
    for i in range(n):
        if deltaPQ[i] != 0.:
            deltaPQ_adj = np.append(deltaPQ_adj, deltaPQ[i])
        else:
            jacobiansDespises = np.append(jacobiansDespises, i)
    jacobiansDespises = jacobiansDespises[-1::-1]
    for lincol in jacobiansDespises:
        j_adj = np.delete(j_adj, int(lincol), 0)
        j_adj = np.delete(j_adj, int(lincol), 1)
    jacobiansDespises = set(jacobiansDespises)
    deltaVdelta = np.linalg.solve(j_adj, deltaPQ_adj)
    return deltaVdelta, jacobiansDespises


def updateV(deltaPQ, N, V0, Y):
    """
    Parameters
    ----------
    deltaPQ:
    N: size of V0
    V0: array with initial estimates (1, N)
    Y: admittance matrix

    Returns
    -------
    V0: updated array with new estimates to the node tensions
    """
    deltaVdelta, jacobiansDespises = DeltaVdelta(deltaPQ, N, V0, Y)
    Vadj = np.empty([0, 0])
    VadjCounter = 0
    for v in V0:
        Vadj = np.append(Vadj, np.angle(v))
    for v in V0:
        Vadj = np.append(Vadj, np.abs(v))
    for i in range(np.size(Vadj)):
        if i in jacobiansDespises:
            pass
        else:
            Vadj[i] += deltaVdelta[VadjCounter]
            VadjCounter += 1
    VadjCounter = int(np.size(Vadj)/2)
    for i in range(N):
        V0[i] = complex(Vadj[VadjCounter] * np.cos(Vadj[VadjCounter - N]), Vadj[VadjCounter] * np.sin(Vadj[VadjCounter - N]))
        VadjCounter += 1
    return V0


def newton_raphson(Y, V0, S, eps=None, Niter=1):
    """
    Parameters
    ----------
    Y: admittance matrix
    V0: array with initial estimates (1, N)
    S: array with specified powers in each bar (N, 2)
    eps: defined tolerance, default = None
    Niter: max number of iterations, default = 1

    Returns
    -------
    V0: updated array with estimates to the node tensions (1, N)
    """
    N = V0.size
    V = np.copy(V0)
    delta = np.inf
    if eps is None:
        eps = np.inf
    count = 0
    while delta > eps or count < Niter:
        deltaPQ = np.zeros([2*N, 1])
        for i in range(N):
            P, Q = S[i]
            I = np.dot(V0, Y[i])
            if not (np.isnan(P)):
                Pcalc = np.dot(V[i], I.conjugate()).real
                deltaPQ[i] = P - Pcalc
                if np.isnan(Q):
                    pass
                else:
                    Qcalc = np.dot(V[i], I.conjugate()).imag
                    deltaPQ[i + N] = Q - Qcalc
            else:
                continue
        V0 = updateV(deltaPQ, N, V0, Y)
        delta = max(np.abs(V - V0))
        V = np.copy(V0)
        count += 1
    print('TOTAL: {} ITERACOES'.format(count))
    return V0


# Stevenson test example:

Y = np.array([
    [8.985190 - 44.835953 * 1j, -3.815629 + 19.078144 * 1j, -5.169561 + 25.847809 * 1j, 0],
    [-3.815629 + 19.078144 * 1j, 8.985190 - 44.835953 * 1j, 0, -5.169561 + 25.847809 * 1j],
    [-5.169561 + 25.847809 * 1j, 0, 8.193267 - 40.863838 * 1j, -3.023705 + 15.118528 * 1j],
    [0, -5.169561 + 25.847809 * 1j, -3.023705 + 15.118528 * 1j, 8.193267 - 40.863838 * 1j]
])

V0 = np.array([1+0*1j, 1+0*1j, 1+0*1j, 1.02+0*1j])
S = np.array([[np.nan, np.nan], [-1.7, -1.0535], [-2, -1.2394], [2.38, np.nan]])

V0 = newton_raphson(Y, V0, S, eps=1e-12)
