import numpy as np

def Gij(i, j, Y):
    return np.abs(Y[i][j])*np.cos(np.angle(Y[i][j]))

def Bij(i, j, Y):
    return np.abs(Y[i][j])*np.sin(np.angle(Y[i][j]))

def Pi(i, N, V, Y):
    _ = 0
    for n in range(N):
        if n != N:
            _ += np.abs(V[i]*V[n]*Y[i][n])*np.cos(np.angle(Y[i][n])+np.angle(V[n])-np.angle(V[i]))
    return np.abs(V[i])**2*Gij(i, i, Y)+_

def Qi(i, N, V, Y):
    _ = 0
    for n in range(N):
        if n != N:
            _ += np.abs(V[i]*V[n]*Y[i][n])*np.sin(np.angle(Y[i][n])+np.angle(V[n])-np.angle(V[i]))
    j = i
    return -np.abs(V[i])**2*Bij(i, j, Y)-_

def Mii(i, V, N, Y):
    return -Qi(i, N, V, Y)-np.abs(V[i])**2*Bij(i, i, Y)

def Nii(i, V, N, Y):
    return Pi(i, N, V, Y)-np.abs(V[i])**2*Gij(i, i, Y)

def Mij(i, j, V, Y):
    return np.abs(V[j])*np.abs(V[i]*Y[i][j])*np.sin(np.angle(Y[i][j]) + np.angle(V[j]) - np.angle(V[i]))

def Nij(i, j, V, Y):
    return -np.abs(V[i]*V[j]*Y[i][j]*np.cos(np.angle(Y[i][j]) + np.angle(V[j]) - np.angle(V[i])))