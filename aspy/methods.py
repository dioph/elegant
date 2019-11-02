import numpy as np

__all__ = ['short', 'gauss_seidel', 'newton_raphson']


def short(Y1, Y0, V):
    """Calculates three-phase short circuit current levels for each bus

    Parameters
    ----------
    Y1: array, shape (N,N)
        Positive-sequence bus admittance matrix
    Y0: array, shape (N,N)
        Zero-sequence bus admittance matrix
    V: array, shape (N,)
        Pre-fault voltage levels for each bus

    Returns
    -------
    I: array, shape (N, 4, 3)
        Three-phase current levels for each of the N buses for each of the following fault types:
        
        * Three-phase to ground (TPG);
        * Single-line to ground (SLG);
        * Double-line to ground (DLG);
        * Line-to-line (LL)
    """
    N = len(V)
    if N > 0 and np.linalg.cond(Y1) < 1 / np.finfo(Y1.dtype).eps and \
            np.linalg.cond(Y0) < 1 / np.finfo(Y0.dtype).eps:
        Z1 = np.diag(np.linalg.inv(Y1))
        Z0 = np.diag(np.linalg.inv(Y0))
    else:
        return np.zeros((N, 4, 3))
    alpha = np.exp(2j * np.pi / 3)
    A = np.array([[1, 1, 1], [1, alpha ** 2, alpha], [1, alpha, alpha ** 2]])
    I = []
    for i in range(N):
        # TPG
        if1 = np.dot(A, np.array([0., V[i] / Z1[i], 0.]))
        # SLG
        if2a = 3 * V[i] / (2 * Z1[i] + Z0[i])
        if2 = np.array([if2a, 0., 0.])
        # DLG
        if3a = V[i] / (Z1[i] + Z1[i] * Z0[i] / (Z1[i] + Z0[i]))
        if3 = np.array([-if3a * Z1[i] / (Z1[i] + Z0[i]), if3a, -if3a * Z0[i] / (Z1[i] + Z0[i])])
        if3 = np.dot(A, if3)
        # LL
        if4 = V[i] / (2 * Z1[i])
        if4 = np.array([0., if4, -if4])
        if4 = np.dot(A, if4)
        I.append([if1, if2, if3, if4])
    return np.array(I)


def gauss_seidel(Y, V0, S, eps=None, Niter=1, Nmax=1000):
    """Gauss-Seidel Method

    Parameters
    ----------
    Y: array, shape (N,N)
        Ybus matrix
    V0: array, shape (N,)
        Complex initial guess
    S: array, shape (N,2)
        Specified apparent power
    eps: float, optional
        Tolerance
    Niter: int, optional
        Minimum number of iterations (default=1)

    Returns
    -------
    V: array, shape (N,)
        Bus voltage approximations 
    """
    N = V0.size
    if N < 1:
        return 0, np.inf, V0
    Vold = np.copy(V0)
    V = np.copy(V0)
    delta = np.inf
    if eps is None:
        eps = np.inf
    count = 0
    while (delta > eps or count < Niter) and count < Nmax:
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
    return count, delta, V


def newton_raphson(Y, V0, S, eps=None, Niter=1, Nmax=1000):
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
    if N < 1:
        return 0, np.inf, V0
    V = np.copy(V0)
    Vold = np.copy(V0)
    delta = np.inf
    if eps is None:
        eps = np.inf
    count = 0
    while (delta > eps or count < Niter) and count < Nmax:
        deltaPQ = np.zeros((2 * N, 1))
        for i in range(N):
            P, Q = S[i]
            I = np.dot(Y[i], V)
            if np.isfinite(P):
                Pcalc = np.real(V[i] * np.conjugate(I))
                deltaPQ[i] = P - Pcalc
                if np.isfinite(Q):
                    Qcalc = np.imag(V[i] * np.conjugate(I))
                    deltaPQ[i + N] = Q - Qcalc
        V = update_V(deltaPQ, N, V, Y)
        delta = max(np.abs(V - Vold))
        Vold = np.copy(V)
        count += 1
    return count, delta, V


def Gij(i, j, Y):
    return np.abs(Y[i][j]) * np.cos(np.angle(Y[i][j]))


def Bij(i, j, Y):
    return np.abs(Y[i][j]) * np.sin(np.angle(Y[i][j]))


def Pi(i, N, V, Y):
    s = 0
    for n in range(N):
        if n != i:
            s += np.abs(V[i] * V[n] * Y[i][n]) * np.cos(np.angle(Y[i][n]) + np.angle(V[n]) - np.angle(V[i]))
    return np.abs(V[i]) ** 2 * Gij(i, i, Y) + s


def Qi(i, N, V, Y):
    s = 0
    for n in range(N):
        if n != i:
            s += np.abs(V[i] * V[n] * Y[i][n]) * np.sin(np.angle(Y[i][n]) + np.angle(V[n]) - np.angle(V[i]))
    return -np.abs(V[i]) ** 2 * Bij(i, i, Y) - s


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
    jacobianDisregard: array with positions to be removed from J
    deltaVdelta: array with the increasing values to update V0
    """
    n = np.size(deltaPQ)
    deltaPQAdj = np.empty((0, 0))
    jacobianDisregard = np.empty((0, 0))
    jAdj = jacobian(N, V0, Y)
    for i in range(n):
        if deltaPQ[i] != 0.:
            deltaPQAdj = np.append(deltaPQAdj, deltaPQ[i])
        else:
            jacobianDisregard = np.append(jacobianDisregard, i)
    jacobianDisregard = jacobianDisregard[-1::-1]
    for lincol in jacobianDisregard:
        jAdj = np.delete(jAdj, int(lincol), 0)
        jAdj = np.delete(jAdj, int(lincol), 1)
    jacobianDisregard = set(jacobianDisregard)
    if np.size(jAdj) > 0 and np.linalg.cond(jAdj) < 1 / np.finfo(jAdj.dtype).eps:
        deltaVdelta = np.linalg.solve(jAdj, deltaPQAdj)
    else:
        print('### SINGULAR JACOBIAN! ###')
        return None, None
    return deltaVdelta, jacobianDisregard


def update_V(deltaPQ, N, V0, Y):
    """
    Parameters
    ----------
    deltaPQ:
    N: size of V0
    V0: array with initial estimates (1, N)
    Y: admittance matrix

    Returns
    -------
    V0: updated array with new estimates to the node voltages
    """
    deltaVdelta, RemoveFromJAdj = DeltaVdelta(deltaPQ, N, V0, Y)
    if deltaVdelta is None:
        return V0
    vAdj = np.empty((0, 0))
    for v in V0:  # First the angles of voltages
        vAdj = np.append(vAdj, np.angle(v))
    for v in V0:  # Lastly, the absolute values of voltages
        vAdj = np.append(vAdj, np.abs(v))
    vAdj_counter = 0
    for i in range(np.size(vAdj)):
        if i in RemoveFromJAdj:
            pass
        else:
            vAdj[i] += deltaVdelta[vAdj_counter]
            vAdj_counter += 1
    vAdj_counter = int(np.size(vAdj) / 2)
    for i in range(N):
        V0[i] = vAdj[vAdj_counter] * np.exp(1j * vAdj[vAdj_counter - N])
        vAdj_counter += 1
    return V0
