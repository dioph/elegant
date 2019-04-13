from pylatex import Document, Section, Subsection, Tabular, MultiColumn, Center, Math, MediumText
from pylatex.utils import bold
from time import strftime
import numpy as np

mathi = lambda x : Math(escape=False, inline=True, data=x)

def getBarsType(Sesp):
    """Returns array with bar types, based on specified power array
    Parameters
    ----------
    Sesp: array with specified powers (N, 2)

    Returns
    -------
    types: array with bar types (N)
    """
    types = np.empty((0, 0), str)
    for bar in Sesp:
        if all(np.isnan(bar)):
            types = np.append(types, 'SLACK')
        elif any(np.isnan(bar)):
            types = np.append(types, 'PV')
        else:
            types = np.append(types, 'PQ')
    return types


def getBarMissingData():
    pass

def log(doc, BARRAS):
    """Add a section, a subsection and some text to the document.
    Parameters
    ----------
    S: vector
    :param doc: the document
    :type doc: :class:`pylatex.document.Document` instance
    """
    types = getBarsType(S)
    print(types)
    doc.add_color(name="lightgray", model="gray", description="0.80")
    with doc.create(Section('Relatório de fluxo de carga')):
        doc.append('Criado em {0} usando Aspy'.format(strftime('%D')))

        with doc.create(Subsection('Tabela de fluxo de carga')):
            with doc.create(Center()):
                fluxTable = Tabular('|cccccccc|')
                fluxTable.add_hline()
                fluxTable.add_row((MultiColumn(8, align='|c|', data=MediumText(bold('Fluxo de carga'))),), color="lightgray")
                fluxTable.add_hline()
                fluxTable.add_hline()
                fluxTable.add_row((MultiColumn(8, align='|c|', data='Bases reais'),), color="lightgray")
                fluxTable.add_hline()
                fluxTable.add_row(('Barra', 'Tipo',
                                   mathi([r'P_G', r'\textrm{ (MW)}']),
                                   mathi([r'Q_G', r'\textrm{ (MVar)}']),
                                   mathi([r'P_L', r'\textrm{ (MW)}']),
                                   mathi([r'Q_L', r'\textrm{ (MVar)}']),
                                   'V (kV)',
                                   mathi(['\delta', r'\textrm{ (deg)}']),))
                fluxTable.add_hline()
                for i in range(int(np.size(S)/np.ndim(S))):
                    if types[i] == 'SLACK':
                        fluxTable.add_row((i+1, types[i], 'calc', 'calc', 'esp', 'esp', V[i], np.rad2deg(np.angle(V[i]))))
                        fluxTable.add_hline()
                    elif types[i] == 'PV':
                        fluxTable.add_row((i+1, types[i], 'esp', 'calc', 'esp', 'calc', V[i], np.rad2deg(np.angle(V[i]))))
                        fluxTable.add_hline()
                    else:
                        fluxTable.add_row((i + 1, types[i], 'esp', 'esp', 'esp', 'esp', V[i], np.rad2deg(np.angle(V[i]))))
                        fluxTable.add_hline()
                fluxTable.add_hline()
                fluxTable.add_row((MultiColumn(8, align='|c|', data='Por unidade'),), color="lightgray")
                fluxTable.add_hline()
                fluxTable.add_row(('Barra', 'Tipo',
                                   mathi([r'P_G']),
                                   mathi([r'Q_G']),
                                   mathi([r'P_L']),
                                   mathi([r'Q_L']),
                                   'V',
                                   mathi(['\delta', r'\textrm{ (deg)}']),))
                fluxTable.add_hline()
                for i in range(int(np.size(S)/np.ndim(S))):
                    if types[i] == 'SLACK':
                        fluxTable.add_row((i+1, types[i], 'calc', 'calc', 'esp', 'esp', V[i], np.rad2deg(np.angle(V[i]))))
                        fluxTable.add_hline()
                    elif types[i] == 'PV':
                        fluxTable.add_row((i+1, types[i], 'esp', 'calc', 'esp', 'calc', V[i], np.rad2deg(np.angle(V[i]))))
                        fluxTable.add_hline()
                    else:
                        fluxTable.add_row((i + 1, types[i], 'esp', 'esp', 'esp', 'esp', V[i], np.rad2deg(np.angle(V[i]))))
                        fluxTable.add_hline()
                doc.append(fluxTable)



if __name__ == '__main__':

    S = np.array([[np.nan, np.nan], [1, 2], [2, np.nan], [1, 3], [1, 3]])
    V = np.array([1, 1, 1.4, 4, 5])
    config = {"tmargin": "2cm", "lmargin": "2cm", "rmargin": "2cm", "bmargin": "2cm"}
    doc = Document('latex_tests', geometry_options=config)
    log(doc, S, V)
    # while True:
    #     try:
    doc.generate_pdf(clean_tex=False, compiler='pdflatex')
    doc.generate_tex()
