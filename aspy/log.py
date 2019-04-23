from pylatex import Document, Section, Subsection, Tabular, MultiColumn, Center, Math, MediumText
from pylatex.utils import bold
from collections import defaultdict, namedtuple
from time import strftime
import matplotlib.pyplot as plt
import numpy as np
import os
import ntpath
from kivy.uix.button import Button
from aspy.core import *
from scipy import misc

math_inline = lambda x: Math(escape=False, inline=True, data=x)

# TODO: put systemScheme in the latex document
# TODO: continue TRAFOCalcs
# TODO: Idea: let the user choose the name of the report doc
# TODO: Idea: let the user choose the report's language

def systemScheme(grid, dimensions):
    """Builds up the system scheme figure
    """
    # Mounting picture
    abs_path = './data/'
    i_max, j_max = dimensions  # rows, cols in interface.kv, line: 82
    picture = np.zeros((i_max, j_max), object)  # pic grid to receive ndarrays
    for i in range(i_max):
        for j in range(j_max):
            background = ntpath.split(grid[i, j].background_down)[1]
            picture[i, j] = misc.imread(abs_path+background)
    # Plotting
    positioning = 1
    picture = picture.flatten()
    for i, cell in enumerate(picture):
        plt.subplot(i_max, j_max, positioning)
        plt.imshow(cell)
        plt.axis('off')
        if positioning < np.shape(picture)[0]:
            positioning += 1
        else:
            positioning = 1
    # plt.show()
    # plt.savefig('.')
    # TODO: only calls this function inside report
    # TODO: save picture with the same name than the data file


def LTCalcs(LINHAS, GRID):
    """Proceeds with LTs calculations about power flux

    Parameters
    ----------
    LINHAS: _
    GRID: _

    Returns
    -------
    ltsDATA: lsSTRUCT with data about each transmission line in 'LINHAS'
    """
    ltSTRUCT = namedtuple('ltSTRUCT', 'source destiny power_flux losses I')
    ltsDATA = defaultdict(ltSTRUCT)
    for NUMBER, LINE in enumerate(LINHAS):
        line, [i, j] = LINE[0], LINE[1]  # line, coords
        Y, Z = line.Y, line.Z
        # Try catch source and destiny bar
        source_bar, receptor_bar = None, None
        for v_pos in range(j, 11):
            if isinstance(GRID[i, v_pos], Barra): receptor_bar = GRID[i, v_pos]; break
            else: continue
        for v_pos in range(j, -1, -1):
            print(j)
            if isinstance(GRID[i, v_pos], Barra): source_bar = GRID[i, v_pos]; break
            else: continue
        if source_bar is None or receptor_bar is None:  # In case of some bar non-identification
            raise Exception("Source or destiny bars could not been identified")
        # Bar voltages (real basis)
        source_voltage, receptor_voltage = source_bar.v, receptor_bar.v
        # Matrix calculations
        A, B = 1+0.5*Y*Z, Z
        # Power flux
        powerFlux_s2r = receptor_voltage * 1/B * (source_voltage - A * receptor_voltage).conjugate()  # unit: VA
        powerFlux_r2s = source_voltage * 1/B * (receptor_voltage - A * source_voltage).conjugate()  # unit: VA
        # Current per phase
        I = powerFlux_s2r/(np.sqrt(3)*source_voltage)  # unit: A
        # Z losses
        losses = 3 * np.abs(I)**2 * line.Z  # unit: VA
        l_data = ltSTRUCT(source_bar.barra_id, receptor_bar.barra_id, [powerFlux_s2r, powerFlux_r2s], losses, I)
        ltsDATA[NUMBER] = l_data
    return ltsDATA


def TRAFOCalcs(data):
    pass


def report(doc, data):
    """Add a section, a subsection and some text to the document.
    Parameters
    ----------
    S: vector
    """
    Y, BARRAS, LINHAS, TRAFOS, GRID = data
    doc.add_color(name="lightgray", model="gray", description="0.80")
    with doc.create(Section('Relatório de fluxo de carga')):
        doc.append('Criado em {0} usando Aspy'.format(strftime('%D')))  # TODO: change time to brazillian format
        # First table: V in normal basis and p.u. basis
        with doc.create(Subsection('Informações das Barras')):
            with doc.create(Center()):
                BarsTable = Tabular('|cccccccc|')
                BarsTable.add_hline()
                BarsTable.add_row((MultiColumn(8, align='|c|', data=MediumText(bold('Tensões nas barras'))),), color="lightgray")
                BarsTable.add_hline()
                BarsTable.add_hline()
                BarsTable.add_row((MultiColumn(8, align='|c|', data='Base reais'),), color="lightgray")
                BarsTable.add_hline()
                BarsTable.add_row(('Barra', 'Tipo',
                                   math_inline([r'P_G', r'\textrm{ (MW)}']),
                                   math_inline([r'Q_G', r'\textrm{ (MVar)}']),
                                   math_inline([r'P_L', r'\textrm{ (MW)}']),
                                   math_inline([r'Q_L', r'\textrm{ (MVar)}']),
                                   'V (kV)',
                                   math_inline(['\delta', r'\textrm{ (deg)}']),))
                BarsTable.add_hline()
                for i in range(np.size(BARRAS)):  # Real basis
                    BARRA = BARRAS[i]
                    v = BARRA.v/1e3  # kV
                    pl = BARRA.pl/1e6  # MW
                    pg = BARRA.pg/1e6  # MW
                    ql = BARRA.ql/1e6  # MVar
                    qg = BARRA.qg/1e6  # MVar
                    if isinstance(BARRA, BarraSL):
                        BarsTable.add_row((i+1, 'Slack', pg, qg, pl, ql, v, np.rad2deg(np.angle(v))))
                        BarsTable.add_hline()
                    elif isinstance(BARRA, BarraPV) == 'PV':
                        BarsTable.add_row((i+1, 'PV', pg, qg, pl, ql, v, np.rad2deg(np.angle(v))))
                        BarsTable.add_hline()
                    else:
                        BarsTable.add_row((i+1, 'PQ', pg, qg, pl, ql, v, np.rad2deg(np.angle(v))))
                        BarsTable.add_hline()
                BarsTable.add_hline()
                BarsTable.add_row((MultiColumn(8, align='|c|', data='Por unidade'),), color="lightgray")
                BarsTable.add_hline()
                BarsTable.add_row(('Barra', 'Tipo',
                                   math_inline([r'P_G']),
                                   math_inline([r'Q_G']),
                                   math_inline([r'P_L']),
                                   math_inline([r'Q_L']),
                                   'V',
                                   math_inline(['\delta', r'\textrm{ (deg)}']),))
                BarsTable.add_hline()
                for i in range(np.size(BARRAS)):  # P.u. basis
                    BARRA = BARRAS[i]
                    v = BARRA.v/BARRA.vbase
                    pl = BARRA.pl/1e6
                    pg = BARRA.pg/1e6
                    ql = BARRA.ql/1e6
                    qg = BARRA.qg/1e6
                    if isinstance(BARRA, BarraSL):
                        BarsTable.add_row((i+1, 'Slack', pg, qg, pl, ql, v, np.rad2deg(np.angle(v))))
                        BarsTable.add_hline()
                    elif isinstance(BARRA, BarraPV):
                        BarsTable.add_row((i+1, 'PV', pg, qg, pl, ql, v, np.rad2deg(np.angle(v))))
                        BarsTable.add_hline()
                    else:
                        BarsTable.add_row((i+1, 'PQ', pg, qg, pl, ql, v, np.rad2deg(np.angle(v))))
                        BarsTable.add_hline()
                doc.append(BarsTable)  # Append BarsTable in .tex file

        # Second table: power flux in the transmission lines (real and p.u. basis)
        with doc.create(Subsection('Fluxos de carga')):
            with doc.create(Center()):
                cols_lt_table = 6
                FluxTable = Tabular('|{0}|'.format('c'*cols_lt_table))
                FluxTable.add_hline()
                FluxTable.add_row((MultiColumn(cols_lt_table, align='|c|', data=MediumText(bold('Fluxo de carga'))),),
                                  color="lightgray")
                FluxTable.add_hline()
                FluxTable.add_hline()
                FluxTable.add_row((MultiColumn(cols_lt_table, align='|c|', data='Bases reais'),), color="lightgray")
                FluxTable.add_hline()
                FluxTable.add_row('Barra', 'Para', 'MV', 'MVar',)
                FluxTable.add_hline()
                doc.append(FluxTable)  # Append FluxTable in .tex file


if __name__ == '__main__':
    pass
    # btn1 = Button()
    # btn2 = Button()
    # btn3 = Button()
    # btn4 = Button()
    # btn1.background_down = './data/scipy/seta.jpg'
    # btn2.background_down = './data/scipy/seta.jpg'
    # btn3.background_down = './data/scipy/seta.jpg'
    # btn4.background_down = './data/scipy/seta.jpg'
    # grid = np.array([[btn1, btn2],
    #                  [btn3, btn4]])
    # systemScheme(grid, np.shape(grid))

    # BarraTeste = BarraSL(v=10e3)
    # BARRAS = np.array([BarraTeste])
    # LINHAS = None
    # TRAFOS = None
    # GRID = None
    # data = [BARRAS, LINHAS, TRAFOS, GRID]
    # default_config = {"tmargin": "2cm", "lmargin": "2cm", "rmargin": "2cm", "bmargin": "2cm"}
    # doc = Document('rep_test', geometry_options=default_config)
    # report(doc, data)
    # while True:
    #     try:
    #         doc.generate_pdf(clean_tex=False, compiler='pdflatex', filepath='./report_tests/')
    #         doc.generate_tex(filepath='./report_tests/')
    #     except FileNotFoundError as ferr:
    #         print(ferr)
    #         print('Creating folder...')
    #         os.mkdir('./report_tests')
    #         print('Folder created')
    #         continue
    #     else:
    #         break
    # lt = LT(l=32e3, r=2.5e-2, d12=4.5, d23=3.0, d31=7.5, d=0.4, m=2)
    # Y = np.array([[1 / .12j, 0, -1 / .12j], [0, 1 / lt.Z, -1 / lt.Z], [-1 / .12j, -1 / lt.Z, 1 / .12j + 1 / lt.Z]])
    # barra1 = Barra(v=1 + 1.01 * 1j, pg=140, qg=2450, pl=5370, ql=460)
    # barra2 = Barra(v=1 - 1.01 * 1j, pg=125, qg=215, pl=335, ql=545)
    # barra3 = Barra(v=1.01 + 1j, pg=2341, qg=351, pl=451, ql=513)
    # BARRAS = np.array([barra1, barra2, barra3])
    # data = [Y, BARRAS]
    # getMissingData(data)
