'''
Simple map to illustrate kerning topography.
HTML canvas is interactive, and allows “exploring” a kern map.
pixel and svg output images may serve as a kerning “fingerprint”.

'''


import argparse
import colorsys

from defcon import Font
from pathlib import Path
from string import Template
from PIL import Image, ImageDraw

import getKerningPairsFromUFO


def get_args():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        'input_ufo',
        help='input UFO',
        action='store',
    )
    parser.add_argument(
        '-f', '--format',
        help='output format',
        choices=['canvas', 'pixel', 'svg'],
        default='canvas',
        action='store',
    )
    parser.add_argument(
        '-c', '--cell_size',
        help='cell size',
        default=5,
        action='store',
        type=int,
    )
    return parser.parse_args()


def float_to_hex(rgb_tuple):
    '''
    convert a RGB tuple into a hex string
    '''
    hex_string = '#'

    for value in rgb_tuple:
        hex_value = hex(int(round(value * 255)))
        hex_string += hex_value[2:].zfill(2)

    return hex_string


def kern_color(k_value, min_value, max_value, hex_values=False):
    '''
    assign a color based on kerning intensity
    '''
    # saturation is at least 50%, otherwise hard to see
    sat = 0.5
    val = 1
    if k_value == 0:
        hue = 0
        sat = 0
    elif k_value < 0:
        hue = (1 / 360) * 0
        # increase saturation by up to 50%
        sat += k_value / min_value / 2
    else:
        hue = (1 / 360) * 180
        sat += k_value / max_value / 2

    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)

    if hex_values:
        return float_to_hex((r, g, b))
    else:
        return r, g, b


def make_kern_map(ufo, cell_size=5, format=None):
    f = Font(ufo)
    g_order = f.glyphOrder
    basename = Path(ufo).stem
    ukr = getKerningPairsFromUFO.UFOkernReader(f, includeZero=True)
    all_kerned_pairs = ukr.allKerningPairs
    kern_values = list(all_kerned_pairs.values())
    k_min = min(kern_values)
    k_max = max(kern_values)

    if format == 'pixel':

        size_in_px = len(g_order) * cell_size
        img = Image.new('RGB', (size_in_px, size_in_px), '#fff')

        for row_index, g_name_a in enumerate(g_order):
            for col_index, g_name_b in enumerate(g_order):
                kv = all_kerned_pairs.get((g_name_a, g_name_b), None)
                x = row_index * cell_size
                y = col_index * cell_size
                rect = [(x, y), (x + cell_size, y + cell_size)]
                if kv is not None:
                    kc = kern_color(kv, k_min, k_max, hex_values=True)
                    img_dummy = ImageDraw.Draw(img)
                    img_dummy.rectangle(rect, fill=kc)

        output_path = Path(f'~/Desktop/{basename}_kernmap.png').expanduser()
        print(output_path)
        img.save(output_path)

    elif format == 'canvas':

        # A canvas can have a maxium area of 268 435 456 pixels.
        # Since we are dealing with hidpi canvas, the actual useable pixels
        # are 268 435 456 / 4 = 67 108 864
        canvas_area = (len(g_order) * cell_size) ** 2 * 4
        if canvas_area > 128 ** 4:
            print(
                'The canvas is too large and may not render.\n'
                'Try decreasing the cell size (option -c).'
            )

        with open('kernMap templates/canvas_prologue.html', 'r') as html_pro:
            canvas_prologue = Template(html_pro.read())
        with open('kernMap templates/canvas_epilogue.html', 'r') as html_epi:
            canvas_epilogue = html_epi.read()
        canvas = []

        sorted_pairs = sorted(
            all_kerned_pairs.keys(),
            key=lambda x: (g_order.index(x[0]), g_order.index(x[1])))
        neg_kerned_pairs = [
            p for p in sorted_pairs if all_kerned_pairs.get(p) <= 0]
        pos_kerned_pairs = [
            p for p in sorted_pairs if all_kerned_pairs.get(p) > 0]

        canvas.append(
            '                context.fillStyle = "#f00";')
        for left, right in neg_kerned_pairs:
            pair_index_l = g_order.index(left)
            pair_index_r = g_order.index(right)
            canvas.append(
                '                context.fillRect('
                f'{pair_index_l} * STEP, '
                f'{pair_index_r} * STEP, STEP, STEP)')

        canvas.append(
            '                context.fillStyle = "#0f0";')
        for left, right in pos_kerned_pairs:
            pair_index_l = g_order.index(left)
            pair_index_r = g_order.index(right)
            canvas.append(
                '                context.fillRect('
                f'{pair_index_l} * STEP, '
                f'{pair_index_r} * STEP, STEP, STEP)')

        # XXX this is a bit janky (and writes a lot of data into the html) --
        # but it works for now.
        flat_kern_items = [
            f'"{" ".join(p)}": {v},' for (p, v) in all_kerned_pairs.items()]

        header_content = {
            'base_name': basename,
            'glyph_order': ' '.join(g_order),
            'cell_size': cell_size,
            'kerning_data': ' '.join(flat_kern_items),
        }

        full_html = (
            canvas_prologue.safe_substitute(header_content) +
            '\n'.join(canvas) +
            canvas_epilogue
        )
        output_path = Path(f'~/Desktop/{basename}_kernmap.html').expanduser()
        print(output_path)
        with open(output_path, 'w') as o:
            o.write(full_html)

    elif format == 'svg':
        rect_size = cell_size

        svg_prologue = (
            '<svg version="1.1" width="{0}" height="{0}" '
            'xmlns="http://www.w3.org/2000/svg">\n'.format(
                len(g_order) * rect_size)
        )
        svg_epilogue = (
            '</svg>\n'
        )
        svg_path = (
            '<path style="fill:{}" d="M{} {} H{} V{} H{} z"/>'
        )

        svg = []
        for row_index, g_name_a in enumerate(g_order):
            for col_index, g_name_b in enumerate(g_order):
                x, y = row_index * rect_size, col_index * rect_size
                # pair = f'{g_name_a} {g_name_b}'
                kv = all_kerned_pairs.get((g_name_a, g_name_b), None)
                if kv is not None:
                    fill = kern_color(kv, k_min, k_max, hex_values=True)
                    svg.append(svg_path.format(
                        fill, x, y, x + rect_size, y + rect_size, x))

        full_svg = svg_prologue + '\n'.join(svg) + svg_epilogue
        output_path = Path(f'~/Desktop/{basename}_kernmap.svg').expanduser()
        print(output_path)
        with open(output_path, 'w') as o:
            o.write(full_svg)


if __name__ == '__main__':
    args = get_args()
    make_kern_map(args.input_ufo, args.cell_size, args.format)
