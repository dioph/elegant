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
    Vold = np.copy(V0)
    V = np.copy(V0)
    delta = np.inf
    if eps is None:
        eps = np.inf
    count = 0
    while delta > eps or count < Niter:
        for i in range(N):
            I = np.dot(Y[i], V)
            P, Q = S[i]
            if np.isnan(P):
                continue
            if np.isnan(Q):
                Q = -np.imag(np.conjugate(V[i]) * I)
                V[i] = ((P - 1j * Q) / np.conjugate(V[i]) - (I - Y[i, i] * V[i])) / Y[i, i]
                V[i] = V[i] * np.abs(Vold[i]) / np.abs(V[i])
            else:
                V[i] = ((P - 1j * Q) / np.conjugate(V[i]) - (I - Y[i, i] * V[i])) / Y[i, i]
        delta = max(np.abs(V - Vold))
        Vold = np.copy(V)
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
    JT = np.append(J11(N, V0, Y), J12(N, V0, Y), axis=1)
    JB = np.append(J21(N, V0, Y), J22(N, V0, Y), axis=1)
    J = np.append(JT, JB, axis=0)
    return J


def delta_Vdelta(delta_PQ, N, V0, Y):
    """
    Parameters
    ----------
    delta_PQ: mismatches arrays (1, N)
    N: size of V0
    V0: array with initial estimates (1, N)
    Y: admittance matrix

    Returns
    -------
    remove_from_j_adj: array with positions of to be removed from J
    delta_Vdelta: array with the increase values to update V0
    """
    n = np.size(delta_PQ)
    delta_PQ_adj = np.empty([0, 0])
    remove_from_j_adj = np.empty([0, 0])
    j_adj = jacobian(N, V0, Y)
    for i in range(n):
        if delta_PQ[i] != 0.:
            delta_PQ_adj = np.append(delta_PQ_adj, delta_PQ[i])
        else:
            remove_from_j_adj = np.append(remove_from_j_adj, i)
    remove_from_j_adj = remove_from_j_adj[-1::-1]
    for lincol in remove_from_j_adj:
        j_adj = np.delete(j_adj, int(lincol), 0)
        j_adj = np.delete(j_adj, int(lincol), 1)
    remove_from_j_adj = set(remove_from_j_adj)
    delta_Vdelta = np.linalg.solve(j_adj, delta_PQ_adj)
    return delta_Vdelta, remove_from_j_adj


def update_V(delta_PQ, N, V0, Y):
    """
    Parameters
    ----------
    delta_PQ:
    N: size of V0
    V0: array with initial estimates (1, N)
    Y: admittance matrix

    Returns
    -------
    V0: updated array with new estimates to the node tensions
    """
    Delta_Vdelta, Remove_from_j_adj = delta_Vdelta(delta_PQ, N, V0, Y)
    v_adj = np.empty([0, 0])
    v_adj_item = 0
    for v in V0:
        v_adj = np.append(v_adj, np.angle(v))
    for v in V0:
        v_adj = np.append(v_adj, np.abs(v))
    for i in range(np.size(v_adj)):
        if i in Remove_from_j_adj:
            pass
        else:
            v_adj[i] += Delta_Vdelta[v_adj_item]
            v_adj_item += 1
    v_adj_item = int(np.size(v_adj)/2)
    for i in range(N):
        V0[i] = complex(v_adj[v_adj_item] * np.cos(v_adj[v_adj_item - N]), v_adj[v_adj_item] * np.sin(v_adj[v_adj_item - N]))
        v_adj_item += 1
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
        delta_PQ = np.zeros([2 * N, 1])
        for i in range(N):
            P, Q = S[i]
            I = np.dot(V0, Y[i])
            if not (np.isnan(P)):
                Pcalc = np.dot(V[i], I.conjugate()).real
                delta_PQ[i] = P - Pcalc
                if np.isnan(Q):
                    pass
                else:
                    Qcalc = np.dot(V[i], I.conjugate()).imag
                    delta_PQ[i + N] = Q - Qcalc
            else:
                continue
        V0 = update_V(delta_PQ, N, V0, Y)
        delta = max(np.abs(V - V0))
        V = np.copy(V0)
        count += 1
    print('TOTAL: {} ITERACOES'.format(count))
    return V0
