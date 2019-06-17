import datetime
import tempfile

import numpy as np
from pylatex import Document, Section, Command, Tabular, Table, NoEscape, \
    Subsection, MultiColumn, MultiRow, UnsafeCommand, NewPage

from pylatex.base_classes import CommandBase
from pylatex.package import Package
from .SchemeInput import getSessionsDir


class Wye(CommandBase):
    _latex_name = 'wye'


def test_inf(x):
    if np.isfinite(x):
        return NoEscape('{:.2f}\\angle{:.2f}'.format(np.abs(x), np.angle(x) * 180 / np.pi))
    else:
        return NoEscape('$\\infty$')


def get_scheme(tr):
    code = {0: '\\why', 1: '\\wye', 2: '\\Delta'}
    return NoEscape('{} {}'.format(code[tr.primary], code[tr.secondary]))


def create_report(barras, linhas, trafos, grid):
    geometry_options = {"tmargin": "2cm", "lmargin": "2cm", "rmargin": "2cm", "bmargin": "2cm"}
    doc = Document(geometry_options=geometry_options)
    doc.preamble.append(Command('usepackage', 'cmbright'))
    doc.preamble.append(Command('usepackage', 'tikz'))
    # doc.preamble.append(Command('usepackage', 'xcolor', options='table'))
    # doc.preamble.append(Command('usepackage', 'pgfplots'))
    now = datetime.datetime.now()
    doc.append('Relatório gerado automaticamente em '
               '{:02d}/{:02d}/{:02d} {:02d}:{:02d}:{:02d} usando ASPy'.format(
        now.day, now.month, now.year, now.hour, now.minute, now.second))
    wye_comm = UnsafeCommand('newcommand', '\\wye', options=0,
                             extra_arguments=r'\text{\begin{tikzpicture}[x=1pt, y=1pt, scale=2]'
                                             r'\draw '
                                             r'(-0.9, 0) -- (0.9, 0) '
                                             r'(-0.6, -0.5) -- (0.6, -0.5) '
                                             r'(-0.3, -1) -- (0.3, -1) '
                                             r'(0, 0) -- ++(0, 1.5) -- ++(1.2, 0) coordinate (tmp)'
                                             r'-- +(0, -2) '
                                             r'(tmp) +(45:2) -- (tmp) -- +(135:2) ;'
                                             r'\end{tikzpicture}}')
    why_comm = UnsafeCommand('newcommand', '\\why', options=0,
                             extra_arguments=r'\text{\begin{tikzpicture}[x=1pt, y=1pt, scale=2]'
                                             r'\draw '
                                             r'(1.2, 1.5) coordinate (tmp)'
                                             r'-- +(0, -2) '
                                             r'(tmp) +(45:2) -- (tmp) -- +(135:2) ;'
                                             r'\end{tikzpicture}}')
    doc.append(wye_comm)
    doc.append(why_comm)
    doc.add_color(name="lightgray", model="gray", description="0.80")
    with doc.create(Section('Barras')):
        with doc.create(Subsection('Estudo de Fluxo de Carga')):
            with doc.create(Table(position='h')) as table:
                doc.append(NoEscape('\\centering'))
                with doc.create(Tabular('c|ccccccc')) as tbl:
                    tbl.add_hline()
                    tbl.add_row(('Barra', NoEscape('$|V|$ (pu)'), NoEscape('$\\delta$ (deg)'),
                                 NoEscape('$P_G$ (MW)'), NoEscape('$Q_G$ (Mvar)'),
                                 NoEscape('$P_L$ (MW)'), NoEscape('$Q_L$ (Mvar)'),
                                 NoEscape('$Z_L$ (pu)')))
                    tbl.add_hline()
                    for i, b in enumerate(barras):
                        if i % 2 == 0:
                            color = 'lightgray'
                        else:
                            color = None
                        tbl.add_row((b.barra_id,
                                     NoEscape('{:.04f}'.format(b.v)),
                                     NoEscape('${:.02f}$'.format(b.delta * 180 / np.pi)),
                                     NoEscape('{:.02f}'.format(b.pg * 100)),
                                     NoEscape('{:.02f}'.format(b.qg * 100)),
                                     NoEscape('{:.02f}'.format(b.pl * 100)),
                                     NoEscape('{:.02f}'.format(b.ql * 100)),
                                     test_inf(b.Z)),
                                    color=color)
                    tbl.add_hline()
        with doc.create(Subsection('Estudo de Curto-Circuito')):
            with doc.create(Table(position='h')) as table:
                doc.append(NoEscape('\\centering'))
                with doc.create(Tabular('c|cccccccc')) as tbl:
                    tbl.add_hline()
                    tbl.add_row((MultiRow(2, data='Barra'),
                                 MultiColumn(2, align='c', data=NoEscape('TPG')),
                                 MultiColumn(2, align='c', data=NoEscape('SLG')),
                                 MultiColumn(2, align='c', data=NoEscape('DLG')),
                                 MultiColumn(2, align='c', data=NoEscape('LL'))))
                    tbl.add_hline(2, 9)
                    tbl.add_row(('', NoEscape('$I_A$ (pu)'), NoEscape('$\\delta_A$ (deg)'),
                                 NoEscape('$I_A$ (pu)'), NoEscape('$\\delta_A$ (deg)'),
                                 NoEscape('$I_B$ (pu)'), NoEscape('$\\delta_B$ (deg)'),
                                 NoEscape('$I_B$ (pu)'), NoEscape('$\\delta_B$ (deg)')))
                    tbl.add_hline()
                    for i, b in enumerate(barras):
                        if i % 2 == 0:
                            color = 'lightgray'
                        else:
                            color = None
                        tbl.add_row((b.barra_id,
                                     NoEscape('{:.04f}'.format(np.abs(b.iTPG))),
                                     NoEscape('${:.02f}$'.format(np.angle(b.iTPG) * 180 / np.pi)),
                                     NoEscape('{:.04f}'.format(np.abs(b.iSLG))),
                                     NoEscape('${:.02f}$'.format(np.angle(b.iSLG) * 180 / np.pi)),
                                     NoEscape('{:.04f}'.format(np.abs(b.iDLG))),
                                     NoEscape('${:.02f}$'.format(np.angle(b.iDLG) * 180 / np.pi)),
                                     NoEscape('{:.04f}'.format(np.abs(b.iLL))),
                                     NoEscape('${:.02f}$'.format(np.angle(b.iLL) * 180 / np.pi))),
                                    color=color)
                    tbl.add_hline()
    with doc.create(Section('Linhas')):
        with doc.create(Table(position='h')) as table:
            doc.append(NoEscape('\\centering'))
            with doc.create(Tabular('c|cccccccc')) as tbl:
                tbl.add_hline()
                tbl.add_row((MultiRow(2, data='Linha'),
                             MultiColumn(3, align='c', data='Parametrização'),
                             MultiColumn(2, align='c', data='Perdas'),
                             MultiColumn(3, align='c', data='Fluxo')))
                tbl.add_hline(2, 9)
                tbl.add_row(('', NoEscape('$R$ (\\%pu)'), NoEscape('$X_L$ (\\%pu)'), NoEscape('$Y$ (\\%pu)'),
                             NoEscape('$P_{per}$ (MW)'), NoEscape('$Q_{per}$ (Mvar)'),
                             NoEscape('$P$ (MW)'), NoEscape('$Q$ (Mvar)'), NoEscape('$I/I_{max}$ (\\%)')))
                tbl.add_hline()
                for i, lt in enumerate(linhas):
                    if i % 2 == 0:
                        color = 'lightgray'
                    else:
                        color = None
                    tbl.add_row((NoEscape('{} -- {}'.format(grid[lt.origin].barra_id, grid[lt.destiny].barra_id)),
                                 NoEscape('{:.04f}'.format(lt.Zpu.real * 100)),
                                 NoEscape('{:.04f}'.format(lt.Zpu.imag * 100)),
                                 NoEscape('{:.04f}'.format(lt.Ypu.imag * 100)), 1, 2, 3, 4, 5),
                                color=color)
                tbl.add_hline()
    doc.append(NewPage())
    with doc.create(Section('Trafos')):
        with doc.create(Table(position='h')) as table:
            doc.append(NoEscape('\\centering'))
            with doc.create(Tabular('c|cccccccc')) as tbl:
                tbl.add_hline()
                tbl.add_row((MultiRow(2, data='Trafo'),
                             MultiColumn(3, align='c', data='Parametrização'),
                             MultiColumn(2, align='c', data='Perdas'),
                             MultiColumn(3, align='c', data='Fluxo')))
                tbl.add_hline(2, 9)
                tbl.add_row(('', NoEscape('$x^+$ (\\%pu)'), NoEscape('$x^0$ (\\%pu)'), 'Esquema',
                             NoEscape('$P_{per}$ (MW)'), NoEscape('$Q_{per}$ (Mvar)'),
                             NoEscape('$P$ (MW)'), NoEscape('$Q$ (Mvar)'), NoEscape('$S/S_N$ (\\%)')))
                tbl.add_hline()
                for i, tr in enumerate(trafos):
                    if i % 2 == 0:
                        color = 'lightgray'
                    else:
                        color = None
                    tbl.add_row((NoEscape('{} -- {}'.format(grid[tr.origin].barra_id, grid[tr.destiny].barra_id)),
                                 NoEscape('{:.02f}'.format(tr.Z1.imag * 100)),
                                 NoEscape('{:.02f}'.format(tr.Z0.imag * 100)),
                                 get_scheme(tr), 1, 2, 3, 4, 5),
                                color=color)
                tbl.add_hline()
    filename = next(tempfile._get_candidate_names())
    sessions_dir = getSessionsDir()
    doc.generate_pdf(sessions_dir + '/' + filename, clean_tex=False)


if __name__ == '__main__':
    geometry_options = {"tmargin": "1cm", "lmargin": "10cm"}
    doc = Document(geometry_options=geometry_options)
    doc.preamble.append(Command('usepackage', 'cmbright'))
    with doc.create(Section('Testing')):
        doc.append('Teeest')

    doc.generate_pdf('report_tests/test', clean_tex=False)
