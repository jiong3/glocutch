"""
Use at your own risk!

This script was written to cut up glossika chinese pdf files into individual
sentence pngs at 300dpi.

Requirements: python2.x + numpy + opencv, imagemagick (convert command)

Usage: python cut.py X
X can be:
GLOSSIKA-EBK-ENZH-B1.pdf
GLOSSIKA-EBK-ENZH-B2.pdf
GLOSSIKA-EBK-ENZH-B3.pdf
GLOSSIKA-EBK-ENZH-DLY.pdf
GLOSSIKA-EBK-ENZH-BIZINTRO.pdf
GLOSSIKA-EBK-BIZ1-ENZH.pdf

Errors:
If imagemagick reports some memory problems (...alloc...) there might be a 1px 
horizontal line appearing (white or black) in one of the images causing
problems. Remove that line manually if necessary.

Also, if the file format changes in the future the whole program probably won't
work anymore.
"""

import numpy as np
import cv2
import os
import subprocess
import sys
import shutil

RENDER_PNG = True
BORDER = 10 # at top and bottom of result

#########################################################

# 0-255
THRESHOLD = 230

VERTICAL_OFFSET = -5 # offset cut position from markerposition

# Basic1:
ITEMS1 = ('english', 'literal', 'simplified',
    'traditional', 'pinyin', 'phonetic')
# Basic2-3:
ITEMS2 = ('english', 'simplified',
    'traditional', 'pinyin', 'phonetic')
# daily, business intro
ITEMS3 = ('english', 'traditional',  'simplified',
    'pinyin', 'phonetic')
# business1
ITEMS4 = ('english', 'traditional', 'simplified', 'pinyin')

all_default = {
        'cut_footer': 2333,
        'dpi': 300,
        'cut_thresh': 240, # thresholding during slicing
        }
basic_default = dict(all_default, **{
        'items': None,
        'mode': 'flexible_no',
        'dist_marker': 90, # from begining of number to beginning of marker
        'width_marker': 50,
        'dist_sents': 155, # same to beginning of sentences
        'min_dist_no': 100, # from left border
        'width_no': 70, # max width of number
        })
fixed_default = dict(all_default, **{
        'items': ITEMS3,
        'mode': 'fixed',
        'dist_marker': 300, # dists from left border
        'width_marker': 70,
        'dist_sents': 375,
        'min_dist_no': 100,
        'width_no': 100,
        })
flexible_ma = dict(all_default, **{
        'items': ITEMS3,
        'mode': 'flexible_ma',
        'dist_marker': 0, # is flexible
        'width_marker': 50,
        'dist_sents': 65, # from left border of marker
        'min_dist_no': 100, # from left border
        'width_no': 95, # max width of number
        'hori_ma_offset': 0,
        })

presets = {
    'GLOSSIKA-EBK-ENZH-B1': dict(basic_default, **{'items': ITEMS1}),
    'GLOSSIKA-EBK-ENZH-B2': dict(basic_default, **{'items': ITEMS2}),
    'GLOSSIKA-EBK-ENZH-B3':dict(basic_default, **{'items': ITEMS2}),
    'GLOSSIKA-EBK-ENZH-DLY': fixed_default,
    'GLOSSIKA-EBK-ENZH-BIZINTRO': flexible_ma,
    'GLOSSIKA-EBK-BIZ1-ENZH':dict(flexible_ma, **{
        'items': ITEMS4,
        'width_no': 150,
        'hori_ma_offset': -5,
        'dist_sents': 70,}),
    }

def get_slice_indeces(image, thresh):
    image[image <= thresh] = 0
    image[image > thresh] = 255
    image_min = np.min(image, axis=1)
    white_to_black = cv2.filter2D(image_min, -1, np.array([[0, 1, -1]]).T)
    result = list(np.where(white_to_black != 0)[0])
    result = [i + VERTICAL_OFFSET for i in result]
    result.append(None)
    return result

def slice_image(image, no_slice, marker_slice, sents_slice, items, thresh):
    items_no = len(items)
    image_orig = np.array(image)
    no_slices = get_slice_indeces(image[:, no_slice], thresh)
    blocks_on_page = len(no_slices) - 1
    ma_slices = get_slice_indeces(image[:, marker_slice], thresh)
    if len(ma_slices) != (items_no * blocks_on_page) + 1:
        #print len(ma_slices), (items_no * blocks_on_page) + 1, no_slice
        return False
    blocks = []
    for i_block in range(blocks_on_page):
        block = {}
        for i_item, item in enumerate(items):
            i_total = i_block * items_no + i_item
            block[item] = image_orig[ma_slices[i_total]:ma_slices[i_total + 1],
                    sents_slice]
        blocks.append(block)
    return blocks


def main():
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        sys.exit('Please provide .pdf file')

    foldername = filename[:-4]

    if foldername in presets:
        p = presets[foldername]
    else:
        sys.exit('Could not find pdf name in presets, please edit the code.')

    path_temp = foldername + '/temp/'
    if RENDER_PNG:
        try:
            os.makedirs(foldername)
        except OSError:
            sys.exit('Please delete existing folder ' + foldername)
        os.makedirs(path_temp)
        print 'Converting pdf to images, this can take a LONG time...'
        subprocess.call(['convert', '-density', str(p['dpi']), '-depth', '8',
            filename, path_temp + 'p.png'])

    temp_files = os.listdir(path_temp)
    temp_files.sort(key=lambda i: int(i[2:-4]))
    items = p['items']
    for item in items:
        try:
            os.makedirs(foldername + '/' + item)
        except OSError:
            pass
    total_no = 1
    for filename in temp_files:
        if not filename.endswith('.png'):
            continue
        print filename
        image = cv2.imread(
        path_temp + filename,
        cv2.CV_LOAD_IMAGE_GRAYSCALE)

        # Preprocessing
        # create thresholded image
        image_t = np.array(image)
        image_t[image >= p['cut_thresh']] = 255
        image_t[image < p['cut_thresh']] = 0
        image_t = image_t[:p['cut_footer'], :]

        image = image[:p['cut_footer'], :]

        try:
            no_start = np.where(np.min(image_t, axis=0) < 255)[0][0]
        except IndexError:
            print 'skipped, empty page'
            continue
        if no_start < p['min_dist_no']:
            print 'skipped, not a sentence page 1'
            continue

        if p['mode'] == 'flexible_no':
            no_slice = slice(no_start, no_start + p['width_no'])
            marker_slice = slice(no_start + p['dist_marker'],
                    no_start + p['dist_marker'] +p['width_marker'])
            sents_slice = slice(no_start + p['dist_sents'], None)

        elif p['mode'] == 'flexible_ma':
            """
            if filename == 'p-364.png':
                pass
                cv2.imwrite('test.png', 255 - image_t)
                print np.sum((255 - image_t) / 255.0, axis=0)
            else:
                pass
                continue
                """
            try:
                ma_start = np.where(
                        np.sum((255 - image_t) / 255.0, axis=0) >
                        2 * p['width_marker'])[0][0] + p['hori_ma_offset']
            except IndexError:
                print 'skipped, not a sentence page 2'
                continue
            no_slice = slice(ma_start - p['width_no'], ma_start)
            marker_slice = slice(ma_start, ma_start + p['width_marker'])
            sents_slice = slice(ma_start + p['dist_sents'], None)

        else:
            no_slice = slice(p['dist_marker'] - p['width_no'],
                    p['dist_marker'])
            marker_slice = slice(p['dist_marker'],
                    p['dist_marker'] + p['width_marker'])
            sents_slice = slice(p['dist_sents'], None)


        blocks = slice_image(image, no_slice, marker_slice,
                sents_slice, items, p['cut_thresh'])
        if not blocks:
            print 'skipped, not a sentence page 3'
            continue
        for block_no, block in enumerate(blocks):
            for name, image in block.iteritems():
                # Postprocessing
                image[image >= THRESHOLD] = 255
                # add white border at top and bottom after cutting off everything
                image_mins = np.min(image, axis=1)
                black = np.where(image_mins != 255)[0]
                image = image[black[0]:black[-1] + 1, :]
                new_shape = list(image.shape)
                new_shape[0] += BORDER * 2
                border_image = np.zeros(new_shape, np.uint8) + 255
                border_image[BORDER:border_image.shape[0] - BORDER, :] = image
                cv2.imwrite(foldername + '/' + name + '/' +
                        '{0:04d}'.format(total_no) + '.png', border_image)
            total_no += 1
        #print total_no

if __name__ == '__main__':
    main()
