#include <Python.h>
#include <bits/stdc++.h>
using namespace std;

typedef struct {
    PyObject_HEAD
    PyObject *x_attr;        /* Attributes dictionary */
} CmplxObject;

//typedef complex<double> CmplxObject;

static PyTypeObject Cmplx_Type;
#define CmplxObject_Check(v) (Py_TYPE(v) == &Cmplx_Type)

static CmplxObject * newCmplxObject(PyObject *arg)
{
    CmplxObject *self;
    self = PyObject_New(CmplxObject, &Cmplx_Type);
    if (self == NULL)
        return NULL;
    self->x_attr = NULL;
    return self;
}

static PyObject * GaussSeidel(PyObject *self, PyObject *args)
{
    double eps;
    CmplxObject *V;

    if (!PyArg_ParseTuple(args, "l", &eps))
        return NULL;
    V = newCmplxObject(args);
    /*
    for (int i = 0; i < N; i++) V[i] = V0[i];
    do
    {
        for (int i = 0; i < N; i++)
        {
            I = cmplx(0.0, 0.0);
            for (int j = 0; j < N; j++) I += Y[i][j] * V[j];

            Q[i] = -imag(conj(V[i]) * I);
            V[i] = (cmplx(P[i], -Q[i])/conj(V[i]) - (I - Y[i][i]*V[i])) / Y[i][i];
        }
    } while (delta > eps);
    return;*/

    return (PyObject *)V;
}

static PyMethodDef Methods[] = {
    {"gauss_seidel",  GaussSeidel, METH_VARARGS,
     "Gauss-Seidel Method."},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef methods = {
    PyModuleDef_HEAD_INIT,
    "methods",   /* name of module */
    NULL, /* module documentation, may be NULL */
    -1,       /* size of per-interpreter state of the module,
                 or -1 if the module keeps state in global variables. */
    Methods
};

PyMODINIT_FUNC
PyInit_methods(void)
{
    return PyModule_Create(&methods);
}

int main ()
{
    return 0;
}
