import datetime
import os

import matplotlib.pyplot as plt
import numpy as np
from pylatex import Document, Section, Command, NoEscape, Figure, \
    Subsection, MultiColumn, MultiRow, UnsafeCommand, LongTable, NewPage

from aspy.core import TL, Bus

_S_FACTOR_ = 3
_DIST_CORR = {  # todo no overlapping based corrections
    4: (0.2, 0.2),
    5: (0.2, 0.2),
    6: (0.2, 0.2),
    7: (0.2, 0.2),
    8: (0.2, 0.2),
}
_MINIMAL_FONTSIZE_ = 6


def matplotlib_coordpairs(curve, sfactor=_S_FACTOR_):
    coords = np.array(curve.coords)
    x = coords[:, 1]
    y = coords[:, 0]
    return sfactor * x, sfactor * -y


def draw_rep_buses(ax, grid, size=250, sfactor=_S_FACTOR_):
    N = grid.shape[0]
    for y in range(N):
        for x in range(N):
            if isinstance(grid[y, x], Bus):
                plt.scatter(sfactor * x, sfactor * -y, s=size, c='k', zorder=3)
                ax.annotate(grid[y, x].bus_id,
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


def draw_rep_curves(ax, curves, linewidth=1):
    gcurves = []
    for curve in curves:
        coords = matplotlib_coordpairs(curve)
        if isinstance(curve.obj, TL):
            color = 'b'
        else:
            color = 'r'
        gcurve, = ax.plot(*coords, linewidth=linewidth, color=color)
        gcurves.append(gcurve)
    return gcurves


def draw_rep_scheme(grid, curves):
    ax = plt.gca()
    ax.clear()
    gcurves = draw_rep_curves(ax, curves)
    draw_rep_buses(ax, grid)
    ax.set_axis_off()
    return gcurves


def get_curve_extremities(curve):
    oy, ox = curve.coords[0]
    post_oy, post_ox = curve.coords[1]
    dy, dx = curve.coords[-1]
    pre_dy, pre_dx = curve.coords[-2]
    return ox, -oy, post_ox, -post_oy, dx, -dy, pre_dx, -pre_dy


def corr_orig(ox, post_ox, oy, post_oy):
    if post_ox >= ox:
        corr_ox = 1
    else:
        corr_ox = -1
    if post_oy <= oy:
        corr_oy = -1
    else:
        corr_oy = 1
    return corr_ox, corr_oy


def corr_dest(pre_dx, dx, pre_dy, dy):
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
    corr_ox, corr_oy = corr_orig(ox, post_ox, oy, post_oy)
    corr_dx, corr_dy = corr_dest(pre_dx, dx, pre_dy, dy)
    corr_sslope, corr_eslope = corr_slopes(*extremities)
    return [[corr_ox, corr_oy], [corr_dx, corr_dy], [corr_sslope, corr_eslope]]


def annotate_overlapping_flow(ax, gcurves, curves, fontsize, sfactor=_S_FACTOR_):
    txts = []
    disth, distv = _DIST_CORR[fontsize]
    for gcurve, curve in zip(gcurves, curves):
        obj = curve.obj
        real_data = collect_line_data(ax, gcurve)
        sslope, eslope = get_line_slopes(real_data)
        extremities = get_curve_extremities(curve)
        corr = direction_based_correction(extremities)
        ox, oy, dx, dy = extremities[0], extremities[1], extremities[4], extremities[5]
        sx = sfactor * (ox + disth * np.cos(np.deg2rad(sslope)) * corr[0][0])
        sy = sfactor * (oy + distv * np.sin(np.deg2rad(sslope)) * corr[0][1])
        ex = sfactor * (dx + disth * np.cos(np.deg2rad(eslope)) * corr[1][0])
        ey = sfactor * (dy + distv * np.sin(np.deg2rad(eslope)) * corr[1][1])
        common_config = {'fontfamily': 'monospace',
                         'rotation_mode': 'anchor',
                         'fontsize': fontsize,
                         'verticalalignment': 'bottom'}
        hmask = {1: 'left', -1: 'right'}
        ltxt = ax.annotate('{:.1f}'.format(obj.S1 * 100),
                           xy=(sx, sy),
                           horizontalalignment=hmask[corr[0][0]],
                           rotation=sslope * corr[2][0],
                           color='b',
                           **common_config)
        ttxt = ax.annotate("{:.1f}".format(-obj.S2 * 100),
                           xy=(ex, ey),
                           horizontalalignment=hmask[corr[1][0]],
                           rotation=eslope * corr[2][1],
                           color='r',
                           **common_config)
        txts.append(ltxt)
        txts.append(ttxt)
    return txts


def overlaps(text, others):
    renderer = plt.get_current_fig_manager().canvas.get_renderer()
    text_bbox = text.get_window_extent(renderer=renderer)
    for other in others:
        other_bbox = other.get_window_extent(renderer=renderer)
        if text_bbox.overlaps(other_bbox) > 0:
            return True
    return False


def reannotate(txts):
    for i in range(len(txts) - 1):
        txt = txts.pop(i)
        if overlaps(txt, txts):
            txts.insert(i, txt)
            return True
        txts.insert(i, txt)
    return False


def annotate_flow(ax, gcurves, curves, initial_fontsize):
    current_fontsize = initial_fontsize
    txts = annotate_overlapping_flow(ax, gcurves, curves, current_fontsize)
    while reannotate(txts) and current_fontsize > _MINIMAL_FONTSIZE_:
        current_fontsize -= 1
        print('current_fontsize = ', current_fontsize)
        for txt in txts:
            txt.remove()
        txts = annotate_overlapping_flow(ax, gcurves, curves, current_fontsize)


def make_system_schematic(curves, grid, filepath, savefig, initial_fontsize, ext='pdf'):
    ax = plt.gca()
    gcurves = draw_rep_scheme(grid, curves)
    annotate_flow(ax, gcurves, curves, initial_fontsize)
    img = os.path.join(filepath) + '_i.' + ext
    if savefig:
        plt.savefig(img, bbox_inches='tight')


def check_inf(x):
    if np.isfinite(x) and np.abs(x) < 1e6:
        if isinstance(x, complex):
            return NoEscape('{:.02f}\\angle{:.02f}'.format(np.abs(x), np.angle(x, deg=True)))
        else:
            return NoEscape('{:.04f}'.format(x))
    else:
        return NoEscape('$\\infty$')


def get_scheme(tr):
    code = {0: '$\\why{}$', 1: '$\\wye{}$', 2: '$\\Delta$'}
    return NoEscape('{} {}'.format(code[tr.primary], code[tr.secondary]))


def create_report(system, curves, grid, filename, savefig=False):
    lines = system.lines
    xfmrs = system.xfmrs
    buses = system.buses

    geometry_options = {"tmargin": "1cm",
                        "lmargin": "1cm",
                        "rmargin": "1cm",
                        "bmargin": "1cm",
                        "includeheadfoot": True}
    doc = Document(page_numbers=True, geometry_options=geometry_options)
    doc.preamble.append(Command('usepackage', 'cmbright'))
    doc.preamble.append(Command('usepackage', 'tikz'))
    doc.preamble.append(Command('usepackage', 'amsmath'))
    doc.preamble.append(Command('usepackage', 'graphicx'))
    now = datetime.datetime.now()
    doc.append('Report auto-generated by ASPy at '
               '{:02d}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}'.format(
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
    with doc.create(Section('Buses')):
        with doc.create(Subsection('Power-Flow Solution')):
            with doc.create(LongTable('c|ccccccc')) as tbl:
                tbl.add_hline()
                tbl.add_row(('Bus', NoEscape('$|V|$ (pu)'), NoEscape('$\\delta$ (deg)'),
                             NoEscape('$P_G$ (MW)'), NoEscape('$Q_G$ (Mvar)'),
                             NoEscape('$P_L$ (MW)'), NoEscape('$Q_L$ (Mvar)'),
                             NoEscape('$Z_L$ (pu)')))
                tbl.add_hline()
                tbl.end_table_header()
                tbl.add_hline()
                tbl.add_row((MultiColumn(8, align='r', data='Continued on Next Page'),))
                tbl.add_hline()
                tbl.end_table_footer()
                tbl.add_hline()
                tbl.end_table_last_footer()

                for i, b in enumerate(buses):
                    if i % 2 == 0:
                        color = 'lightgray'
                    else:
                        color = None
                    tbl.add_row((b.bus_id,
                                 NoEscape('{:.04f}'.format(b.v)),
                                 NoEscape('${:.02f}$'.format(b.delta * 180 / np.pi)),
                                 NoEscape('{:.02f}'.format(b.pg * 100)),
                                 NoEscape('{:.02f}'.format(b.qg * 100)),
                                 NoEscape('{:.02f}'.format(b.pl * 100)),
                                 NoEscape('{:.02f}'.format(b.ql * 100)),
                                 check_inf(b.Z)),
                                color=color)
        with doc.create(Subsection('Fault Calculations')):
            with doc.create(LongTable('c|cccccccccc')) as tbl:
                tbl.add_hline()
                tbl.add_row((MultiRow(2, data='Bus'),
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
                tbl.end_table_header()
                tbl.add_hline()
                tbl.add_row((MultiColumn(11, align='r', data='Continued on Next Page'),))
                tbl.add_hline()
                tbl.end_table_footer()
                tbl.add_hline()
                tbl.end_table_last_footer()

                for i, b in enumerate(buses):
                    if i % 2 == 0:
                        color = 'lightgray'
                    else:
                        color = None
                    tbl.add_row((b.bus_id,
                                 check_inf(np.abs(b.iTPG)),
                                 NoEscape('${:.02f}$'.format(np.angle(b.iTPG) * 180 / np.pi)),
                                 check_inf(np.abs(b.iSLG)),
                                 NoEscape('${:.02f}$'.format(np.angle(b.iSLG) * 180 / np.pi)),
                                 check_inf(np.abs(b.iDLGb)),
                                 NoEscape('${:.02f}$'.format(np.angle(b.iDLGb) * 180 / np.pi)),
                                 check_inf(np.abs(b.iDLGc)),
                                 NoEscape('${:.02f}$'.format(np.angle(b.iDLGc) * 180 / np.pi)),
                                 check_inf(np.abs(b.iLL)),
                                 NoEscape('${:.02f}$'.format(np.angle(b.iLL) * 180 / np.pi))),
                                color=color)
    with doc.create(Section('Lines')):
        with doc.create(LongTable('c|cccccccc')) as tbl:
            tbl.add_hline()
            tbl.add_row((MultiRow(2, data='Line'),
                         MultiColumn(3, align='c', data='Parametrization'),
                         MultiColumn(2, align='c', data='Loss'),
                         MultiColumn(3, align='c', data='Flow')))
            tbl.add_hline(2, 9)
            tbl.add_row(('', NoEscape('$R$ (\\%pu)'), NoEscape('$X_L$ (\\%pu)'), NoEscape('$Y$ (\\%pu)'),
                         NoEscape('$P_{loss}$ (MW)'), NoEscape('$Q_{loss}$ (Mvar)'),
                         NoEscape('$P$ (MW)'), NoEscape('$Q$ (Mvar)'), NoEscape('$I/I_{max}$ (\\%)')))
            tbl.add_hline()
            tbl.end_table_header()
            tbl.add_hline()
            tbl.add_row((MultiColumn(9, align='r', data='Continued on Next Page'),))
            tbl.add_hline()
            tbl.end_table_footer()
            tbl.add_hline()
            tbl.end_table_last_footer()

            for i, lt in enumerate(lines):
                if i % 2 == 0:
                    color = 'lightgray'
                else:
                    color = None
                tbl.add_row((NoEscape('{} -- {}'.format(lt.orig.bus_id, lt.dest.bus_id)),
                             NoEscape('{:.04f}'.format(lt.Zpu.real * 100)),
                             NoEscape('{:.04f}'.format(lt.Zpu.imag * 100)),
                             NoEscape('{:.04f}'.format(lt.Ypu.imag * 100)),
                             NoEscape('{:.02f}'.format(lt.Sper.real * 100)),
                             NoEscape('{:.02f}'.format(lt.Sper.imag * 100)),
                             NoEscape('{:.02f}'.format(lt.S2.real * 100)),
                             NoEscape('{:.02f}'.format(lt.S2.imag * 100)),
                             NoEscape('{:.02f}'.format(np.abs(lt.I) / lt.imax * 100))),
                            color=color)
    with doc.create(Section('XFMRs')):
        with doc.create(LongTable('c|cccccccc')) as tbl:
            tbl.add_hline()
            tbl.add_row((MultiRow(2, data='XFMR'),
                         MultiColumn(3, align='c', data='Parametrization'),
                         MultiColumn(2, align='c', data='Loss'),
                         MultiColumn(3, align='c', data='Flow')))
            tbl.add_hline(2, 9)
            tbl.add_row(('', NoEscape('$x^+$ (\\%pu)'), NoEscape('$x^0$ (\\%pu)'), 'Configuration',
                         NoEscape('$P_{loss}$ (MW)'), NoEscape('$Q_{loss}$ (Mvar)'),
                         NoEscape('$P$ (MW)'), NoEscape('$Q$ (Mvar)'), NoEscape('$S/S_N$ (\\%)')))
            tbl.add_hline()
            tbl.end_table_header()
            tbl.add_hline()
            tbl.add_row((MultiColumn(9, align='r', data='Continued on Next Page'),))
            tbl.add_hline()
            tbl.end_table_footer()
            tbl.add_hline()
            tbl.end_table_last_footer()

            for i, tr in enumerate(xfmrs):
                if i % 2 == 0:
                    color = 'lightgray'
                else:
                    color = None
                tbl.add_row((NoEscape('{} -- {}'.format(tr.orig.bus_id, tr.dest.bus_id)),
                             NoEscape('{:.02f}'.format(tr.Z1.imag * 100)),
                             NoEscape('{:.02f}'.format(tr.Z0.imag * 100)),
                             get_scheme(tr),
                             NoEscape('{:.02f}'.format(tr.Sper.real * 100)),
                             NoEscape('{:.02f}'.format(tr.Sper.imag * 100)),
                             NoEscape('{:.02f}'.format(tr.S2.real * 100)),
                             NoEscape('{:.02f}'.format(tr.S2.imag * 100)),
                             NoEscape('{:.02f}'.format(np.abs(tr.S2) * 1e8 / tr.snom * 100))),
                            color=color)

    filepath = filename.strip('.pdf')
    make_system_schematic(curves, grid, filepath, savefig=savefig, initial_fontsize=8)
    doc.append(NewPage())
    with doc.create(Section('System')):
        with doc.create(Figure(position='h')) as system_pic:
            system_pic.add_plot(bbox_inches='tight', width=NoEscape('\\textwidth'))
    doc.generate_pdf(filepath, clean_tex=True, compiler='latexmk', compiler_args=['-pdf'])
