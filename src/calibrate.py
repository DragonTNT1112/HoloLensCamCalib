#!/usr/bin/env python

'''
calibrate.py

This script is adapted from OpenCV.
Changes include parsing more parameters, and formatting the json and yaml saving of calibration results.

Revision by Long Qian
Contact: lqian8@jhu.edu


camera calibration for distorted images with chess board samples
reads distorted images, calculates the calibration and write undistorted images

usage:
    calibrate.py [--debug <output path>] [--square_size] [--pattern_width] [--pattern_height] [<image mask>]

default values:
    --debug:    ./output/
    --square_size: 1.0
    --pattern_width: 7
    --pattern_height: 5
    <image mask> defaults to data/*.jpg
'''

# Python 2/3 compatibility
from __future__ import print_function

import numpy as np
import cv2
import json, yaml

# local modules
from common import splitfn

# built-in modules
import os

if __name__ == '__main__':
    import sys
    import getopt
    from glob import glob

    args, img_mask = getopt.getopt(sys.argv[1:], '', ['debug=', 'square_size=', 'pattern_width=', 'pattern_height='])
    args = dict(args)
    args.setdefault('--debug', './output/')
    args.setdefault('--square_size', 1.0)
    args.setdefault('--pattern_width', 7)
    args.setdefault('--pattern_height', 5)
    if not img_mask:
        img_mask = 'data/*.jpg'  # default
    else:
        img_mask = img_mask[0]
    print(img_mask)

    img_names = glob(img_mask)
    debug_dir = args.get('--debug')
    if not os.path.isdir(debug_dir):
        os.mkdir(debug_dir)
    square_size = float(args.get('--square_size'))

    # pattern_size should be set to the pattern used for calibration
    # 7x5 is the default opencv setup
    pattern_size = (int(args.get('--pattern_width')), int(args.get('--pattern_height')))
    pattern_points = np.zeros((np.prod(pattern_size), 3), np.float32)
    pattern_points[:, :2] = np.indices(pattern_size).T.reshape(-1, 2)
    pattern_points *= square_size

    print(square_size)

    obj_points = []
    img_points = []
    h, w = 0, 0
    img_names_undistort = []
    for fn in img_names:
        print('processing %s... ' % fn, end='')
        img = cv2.imread(fn, 0)
        if img is None:
            print("Failed to load", fn)
            continue

        h, w = img.shape[:2]
        found, corners = cv2.findChessboardCorners(img, pattern_size)
        if found:
            term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.1)
            cv2.cornerSubPix(img, corners, (5, 5), (-1, -1), term)

        if debug_dir:
            vis = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            cv2.drawChessboardCorners(vis, pattern_size, corners, found)
            path, name, ext = splitfn(fn)
            outfile = debug_dir + name + '_chess.png'
            cv2.imwrite(outfile, vis)
            if found:
                img_names_undistort.append(outfile)

        if not found:
            print('chessboard not found')
            continue

        img_points.append(corners.reshape(-1, 2))
        obj_points.append(pattern_points)

        print('ok')

    # calculate camera distortion
    rms, camera_matrix, dist_coefs, rvecs, tvecs = cv2.calibrateCamera(obj_points, img_points, (w, h), None, None, flags=cv2.CALIB_FIX_K3)

    print("\nRMS:", rms)
    print("camera matrix:\n", camera_matrix)
    print("distortion coefficients: ", dist_coefs.ravel())


    data = {"camera_matrix": camera_matrix.tolist(), "dist_coeff": dist_coefs.tolist(), "height": h, "width": w}
    yname = "data.yaml"
    with open(yname, "w") as f:
        yaml.dump(data, f)
    jname = "data.json"
    with open(jname, "w") as f:
        json.dump(data, f)


    # undistort the image with the calibration
    print('')
    for img_found in img_names_undistort:
        img = cv2.imread(img_found)

        h,  w = img.shape[:2]
        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(camera_matrix, dist_coefs, (w, h), 1, (w, h))

        dst = cv2.undistort(img, camera_matrix, dist_coefs, None, newcameramtx)

        # crop and save the image
        x, y, w, h = roi
        dst = dst[y:y+h, x:x+w]
        outfile = img_found + '_undistorted.png'
        print('Undistorted image written to: %s' % outfile)
        cv2.imwrite(outfile, dst)

    cv2.destroyAllWindows()


