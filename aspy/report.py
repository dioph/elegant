import datetime
import os
import tempfile

import matplotlib.pyplot as plt
import numpy as np
from pylatex import Document, Section, Command, Tabular, Table, NoEscape, \
    Subsection, MultiColumn, MultiRow, UnsafeCommand, Figure

from aspy.utils import debug

_S_FACTOR_ = 3
_DIST_H = 0.2
_DIST_V = 0.25


def test_inf(x):
    if np.isfinite(x):
        return NoEscape('{:.2f}\\angle{:.2f}'.format(np.abs(x), np.angle(x) * 180 / np.pi))
    else:
        return NoEscape('$\\infty$')


def get_scheme(tr):
    code = {0: '$\\why{}$', 1: '$\\wye{}$', 2: '$\\Delta$'}
    return NoEscape('{} {}'.format(code[tr.primary], code[tr.secondary]))


def matplotlib_coordpairs(entity, sfactor=_S_FACTOR_):
    coords = np.array(entity[2])
    x, y = list(coords[:, i] for i in range(np.shape(coords)[1] - 1, -1, -1))
    return sfactor * x, sfactor * -y


def draw_rep_buses(ax, buses, size=250, sfactor=_S_FACTOR_):
    for bus in buses:
        x, y = bus.__getattribute__('posicao')[::-1]
        plt.scatter(sfactor * x, sfactor * -y, s=size, c='k', zorder=3)
        ax.annotate(bus.barra_id,
                    xy=(sfactor * x, sfactor * -y),
                    color='w',
                    fontfamily='monospace',
                    horizontalalignment='center',
                    verticalalignment='center')


def collect_line_data(ax, line):
    x, y = line.get_data()
    p1x, p2x, p1y, p2y = x[0], x[1], y[0], y[1]
    pblx, plx, pbly, ply = x[-2], x[-1], y[-2], y[-1]
    r_p1 = ax.transData.transform_point([p1x, p1y])
    r_p2 = ax.transData.transform_point([p2x, p2y])
    r_pbl = ax.transData.transform_point([pblx, pbly])
    r_pl = ax.transData.transform_point([plx, ply])
    return r_p1, r_p2, r_pbl, r_pl


def get_line_slopes(line_data):
    r_p1, r_p2, r_pbl, r_pl = line_data
    start_slope = np.arctan2(np.abs(r_p2[1] - r_p1[1]), np.abs(r_p2[0] - r_p1[0]))
    end_slope = np.arctan2(np.abs(r_pl[1] - r_pbl[1]), np.abs(r_pl[0] - r_pbl[0]))
    return np.rad2deg(start_slope), np.rad2deg(end_slope)


def draw_rep_lines(ax, lines, linewidth=1):
    glines = []
    for line in lines:
        coords = matplotlib_coordpairs(line)
        gline = ax.plot(*coords, linewidth=linewidth, color='b')
        glines.append(gline)
    return glines


def draw_rep_trafos(ax, trafos, linewidth=1):
    gtrafos = []
    for trafo in trafos:
        coords = matplotlib_coordpairs(trafo)
        gtrafo = ax.plot(*coords, linewidth=linewidth, color='r')
        gtrafos.append(gtrafo)
    return gtrafos


def draw_rep_scheme(data):
    buses, lines, trafos = data
    ax = plt.gca()
    ax.clear()
    glines = draw_rep_lines(ax, lines)
    gtrafos = draw_rep_trafos(ax, trafos)
    draw_rep_buses(ax, buses)
    ax.set_axis_off()
    return glines, gtrafos


def get_entity_extremities(entity):
    core_obj = entity[0]
    oy, ox = core_obj.origin
    post_oy, post_ox = entity[2][1]
    dy, dx = core_obj.destiny
    pre_dy, pre_dx = entity[2][-2]
    return ox, -oy, post_ox, -post_oy, dx, -dy, pre_dx, -pre_dy


def corr_origin(ox, post_ox, oy, post_oy):
    if post_ox >= ox:
        corr_ox = 1
    else:
        corr_ox = -1
    if post_oy <= oy:
        corr_oy = -1
    else:
        corr_oy = 1
    return corr_ox, corr_oy


def corr_destiny(pre_dx, dx, pre_dy, dy):
    if pre_dx >= dx:
        corr_dx = 1
    else:
        corr_dx = -1
    if pre_dy <= dy:
        corr_dy = -1
    else:
        corr_dy = 1
    return corr_dx, corr_dy


def corr_slopes(ox, oy, post_ox, post_oy, dx, dy, pre_dx, pre_dy):
    if post_ox >= ox:
        if post_oy <= oy:
            corr_sslope = -1
        else:
            corr_sslope = 1
    else:
        if post_oy <= oy:
            corr_sslope = 1
        else:
            corr_sslope = -1
    if pre_dx >= dx:
        if pre_dy <= dy:
            corr_eslope = -1
        else:
            corr_eslope = 1
    else:
        if pre_dy <= dy:
            corr_eslope = 1
        else:
            corr_eslope = -1
    return corr_sslope, corr_eslope


def direction_based_correction(extremities):
    ox, oy, post_ox, post_oy, dx, dy, pre_dx, pre_dy = extremities
    corr_ox, corr_oy = corr_origin(ox, post_ox, oy, post_oy)
    corr_dx, corr_dy = corr_destiny(pre_dx, dx, pre_dy, dy)
    corr_sslope, corr_eslope = corr_slopes(*extremities)
    return {0: [corr_ox, corr_oy], 1: [corr_dx, corr_dy], 2: [corr_sslope, corr_eslope]}


def annotate_lines_flux_data(ax, glines, lines, sfactor=_S_FACTOR_, disth=_DIST_H, distv=_DIST_V):
    for gentty, lentty in zip(glines, lines):
        gline, line = gentty[0], lentty[0]
        real_gline_data = collect_line_data(ax, gline)
        sslope, eslope = get_line_slopes(real_gline_data)
        extremities = get_entity_extremities(lentty)
        corr = direction_based_correction(extremities)
        ox, oy, dx, dy = extremities[0], extremities[1], extremities[4], extremities[5]
        sx = sfactor * (ox + disth * np.cos(np.deg2rad(sslope)) * corr[0][0])
        sy = sfactor * (oy + distv * np.sin(np.deg2rad(sslope)) * corr[0][1])
        ex = sfactor * (dx + disth * np.cos(np.deg2rad(eslope)) * corr[1][0])
        ey = sfactor * (dy + distv * np.sin(np.deg2rad(eslope)) * corr[1][1])
        common_config = {'fontfamily': 'monospace', 'rotation_mode': 'anchor', 'fontsize': 6,
                         'verticalalignment': 'bottom'}
        hmask = {1: 'left', -1: 'right'}
        ax.annotate('{:.1f}'.format(line.S1 * 100),
                    xy=(sx, sy),
                    horizontalalignment=hmask[corr[0][0]],
                    rotation=sslope * corr[2][0],
                    color='b',
                    **common_config)
        ax.annotate("{:.1f}".format(line.S2 * 100),
                    xy=(ex, ey),
                    horizontalalignment=hmask[corr[1][0]],
                    rotation=eslope * corr[2][1],
                    color='r',
                    **common_config)


def annotate_trafos_flux_data(ax, gtrafos, trafos, sfactor=_S_FACTOR_, disth=_DIST_H, distv=_DIST_V):
    for gentty, tentty in zip(gtrafos, trafos):
        gtrafo, trafo = gentty[0], tentty[0]
        real_gtrafo_data = collect_line_data(ax, gtrafo)
        sslope, eslope = get_line_slopes(real_gtrafo_data)
        extremities = get_entity_extremities(tentty)
        corr = direction_based_correction(extremities)
        ox, oy, dx, dy = extremities[0], extremities[1], extremities[4], extremities[5]
        sx = sfactor * (ox + disth * np.cos(np.deg2rad(sslope)) * corr[0][0])
        sy = sfactor * (oy + distv * np.sin(np.deg2rad(sslope)) * corr[0][1])
        ex = sfactor * (dx + disth * np.cos(np.deg2rad(eslope)) * corr[1][0])
        ey = sfactor * (dy + distv * np.sin(np.deg2rad(eslope)) * corr[1][1])
        common_config = {'fontfamily': 'monospace', 'rotation_mode': 'anchor', 'fontsize': 6,
                         'verticalalignment': 'bottom'}
        hmask = {1: 'left', -1: 'right'}
        ax.annotate('{:.1f}'.format(trafo.Spu * 100),
                    xy=(sx, sy),
                    horizontalalignment=hmask[corr[0][0]],
                    rotation=sslope * corr[2][0],
                    color='b',
                    **common_config)
        ax.annotate("{:.1f}".format((trafo.Spu - trafo.Sper) * 100),
                    xy=(ex, ey),
                    horizontalalignment=hmask[corr[1][0]],
                    rotation=eslope * corr[2][1],
                    color='r',
                    **common_config)


def make_system_schematic(data, sessions_dir, filename, ext='pdf'):
    ax = plt.gca()
    buses, lines, trafos = data
    glines, gtrafos = draw_rep_scheme(data)
    annotate_lines_flux_data(ax, glines, lines)
    annotate_trafos_flux_data(ax, gtrafos, trafos)
    img = os.path.join(sessions_dir, filename) + '_i.' + ext
    plt.savefig(img)
    return img.split(os.sep)[-1]

@debug
def create_report(BUSES, LINES, TRANSFORMERS, GRID_BUSES):
    if len(LINES) > 0:
        linhas = np.array(LINES)[:, 0]
    else:
        linhas = np.array([])
    if len(TRANSFORMERS) > 0:
        trafos = np.array(TRANSFORMERS)[:, 0]
    else:
        trafos = np.array([])
    grid = GRID_BUSES
    barras = BUSES
    from aspy.utils import getSessionsDir
    sessions_dir = getSessionsDir()
    filename = next(tempfile._get_candidate_names())
    geometry_options = {"tmargin": "2cm", "lmargin": "2cm", "rmargin": "2cm", "bmargin": "2cm"}
    doc = Document(geometry_options=geometry_options)
    doc.preamble.append(Command('usepackage', 'cmbright'))
    doc.preamble.append(Command('usepackage', 'tikz'))
    doc.preamble.append(Command('usepackage', 'amsmath'))
    doc.preamble.append(Command('usepackage', 'graphicx'))
    now = datetime.datetime.now()
    doc.append('Relatório gerado automaticamente em '
               '{:02d}/{:02d}/{:02d} {:02d}:{:02d}:{:02d} usando ASPy'.format(
        now.day, now.month, now.year, now.hour, now.minute, now.second))
    wye_comm = UnsafeCommand('newcommand', '\\wye',
                             extra_arguments=r'\mathbin{\text{\begin{tikzpicture}[x=1pt, y=1pt, scale=2]'
                                             r'\draw '
                                             r'(-0.9, 0) -- (0.9, 0) '
                                             r'(-0.6, -0.5) -- (0.6, -0.5) '
                                             r'(-0.3, -1) -- (0.3, -1) '
                                             r'(0, 0) -- ++(0, 1.5) -- ++(1.2, 0) coordinate (tmp)'
                                             r'-- +(0, -2) '
                                             r'(tmp) +(45:2) -- (tmp) -- +(135:2) ;'
                                             r'\end{tikzpicture}}}')
    why_comm = UnsafeCommand('newcommand', '\\why',
                             extra_arguments=r'\mathbin{\text{\begin{tikzpicture}[x=1pt, y=1pt, scale=2]'
                                             r'\draw '
                                             r'(1.2, 1.5) coordinate (tmp)'
                                             r'-- +(0, -2) '
                                             r'(tmp) +(45:2) -- (tmp) -- +(135:2) ;'
                                             r'\end{tikzpicture}}}')
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
                with doc.create(Tabular('c|cccccccccc')) as tbl:
                    tbl.add_hline()
                    tbl.add_row((MultiRow(2, data='Barra'),
                                 MultiColumn(2, align='c', data=NoEscape('TPG')),
                                 MultiColumn(2, align='c', data=NoEscape('SLG')),
                                 MultiColumn(4, align='c', data=NoEscape('DLG')),
                                 MultiColumn(2, align='c', data=NoEscape('LL'))))
                    tbl.add_hline(2, 11)
                    tbl.add_row(('', NoEscape('$I_A$ (pu)'), NoEscape('$\\delta_A$ (deg)'),
                                 NoEscape('$I_A$ (pu)'), NoEscape('$\\delta_A$ (deg)'),
                                 NoEscape('$I_B$ (pu)'), NoEscape('$\\delta_B$ (deg)'),
                                 NoEscape('$I_C$ (pu)'), NoEscape('$\\delta_C$ (deg)'),
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
                                     NoEscape('{:.04f}'.format(np.abs(b.iDLGb))),
                                     NoEscape('${:.02f}$'.format(np.angle(b.iDLGb) * 180 / np.pi)),
                                     NoEscape('{:.04f}'.format(np.abs(b.iDLGc))),
                                     NoEscape('${:.02f}$'.format(np.angle(b.iDLGc) * 180 / np.pi)),
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
                                 NoEscape('{:.04f}'.format(lt.Ypu.imag * 100)),
                                 NoEscape('{:.02f}'.format(lt.Sper.real * 100)),
                                 NoEscape('{:.02f}'.format(lt.Sper.imag * 100)),
                                 NoEscape('{:.02f}'.format(lt.S2.real * 100)),
                                 NoEscape('{:.02f}'.format(lt.S2.imag * 100)),
                                 NoEscape('{:.02f}'.format(np.abs(lt.I) / lt.imax * 100))),
                                color=color)
                tbl.add_hline()
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
                                 get_scheme(tr),
                                 NoEscape('{:.02f}'.format(tr.Sper.real * 100)),
                                 NoEscape('{:.02f}'.format(tr.Sper.imag * 100)),
                                 NoEscape('{:.02f}'.format(tr.Spu.real * 100)),
                                 NoEscape('{:.02f}'.format(tr.Spu.imag * 100)),
                                 NoEscape('{:.02f}'.format(np.abs(tr.Spu) * 1e8 / tr.snom * 100))),
                                color=color)
                tbl.add_hline()
    data = BUSES, LINES, TRANSFORMERS
    img = make_system_schematic(data, sessions_dir, filename)
    with doc.create(Section('Sistema')):
        doc.append(NoEscape('\\centering'))
        with doc.create(Figure(position='h!')) as system_pic:
            system_pic.add_image(img)
    doc.generate_pdf(sessions_dir + '/' + filename, clean_tex=True)
