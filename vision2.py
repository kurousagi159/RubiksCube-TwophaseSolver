# ######################## analyse the webcam input and retrieve the facelet colors of a single cube face ##############


# pip install opencv_python-3.2.0-cp36-cp36m-win_amd64.whl

import cv2
import numpy as np
import vision_params

grid_N = 25  # number of grid-squares in vertical direction


def drawgrid(img, n):
    """draw grid onto the webcam output. Only used for debugging purposes."""
    h, w = img.shape[:2]
    sz = h // n
    border = 1 * sz
    for y in range(border, h - border, sz):
        for x in range(border, w - border, sz):
            cv2.rectangle(img, (x, y), (x + sz, y + sz), (0, 0, 0), 1)  # plot small squares in black and white
            cv2.rectangle(img, (x - 1, y - 1), (x + 1 + sz, y + 1 + sz), (255, 255, 255), 1)


def del_duplicates(pts):
    """if two potential facelet centers stored in pts are too close together, one of them is deleted"""
    delta = width/12  # width is defined global in grabcolors()
    dele = True
    while dele:
        dele = False
        r = range(len(pts))
        for i in r:
            for j in r[i + 1:]:
                if np.linalg.norm(pts[i] - pts[j]) < delta:
                    del pts[j]
                    dele = True
                if dele:
                    break
            if dele:
                break


def medoid(pts):
    """ The mediod is the point with the smallest summed distance from the other points.
    This is a candidate for the center facelet."""
    res = np.array([0.0, 0.0])
    smin = 100000
    for i in pts:
        s = 0
        for j in pts:
            s += np.linalg.norm(i - j)
        if s < smin:
            smin = s
            res = i

    return res


def facelets(pts, med):
    """Separate the candidates into edge and corner facelets by their distance from the medoid."""
    ed = []
    co = []
    if med[0] == 0:
        return co, ed  # no edgefacelets detected
    # find shortest distance
    dmin = 10000
    for p in pts:
        d = np.linalg.norm(p - med)
        if 1 < d < dmin:
            dmin = d
    # edgefacelets should be in a distance not more than dmin*1.3
    for p in pts:
        d = np.linalg.norm(p - med)
        if dmin - 1 < d < dmin * 1.3:
            ed.append(p)
    # now find the corner facelets
    for p in pts:
        d = np.linalg.norm(p - med)
        if dmin * 1.3 < d < dmin * 1.7:
            co.append(p)
    return co, ed


def mirr_facelet(co, ed, med):
    """If we have detected a facelet position, the point reflection at the center also gives a facelet position.
     We can use this position in case the other facelet was not detected directly."""
    aef = []
    acf = []
    for p in ed:
        pa = 2 * med - p
        aef.append(pa)
    for p in co:
        pa = 2 * med - p
        acf.append(pa)

    # delete duplicates
    delta = width / 12  # width is defined global in grabcolors()
    for k in range(len(aef) - 1, -1, -1):
        for p in ed:
            if np.linalg.norm(aef[k] - p) < delta:
                del aef[k]
                break

    for k in range(len(acf) - 1, -1, -1):
        for p in co:
            if np.linalg.norm(acf[k] - p) < delta:
                del acf[k]
                break

    return acf, aef


def display_colorname(bgrcap, p):
    """ Display the colornames on the webcam picture"""
    p = p.astype(np.uint16)
    col = getcolor(p)
    if col in('blue', 'green', 'red'):
        txtcol = (255, 255, 255)
    else:
        txtcol = (0, 0, 0)
    font = cv2.FONT_HERSHEY_SIMPLEX
    tz = cv2.getTextSize(col, font, 0.4, 1)[0]
    cv2.putText(
        bgrcap, getcolor(p), tuple(p - (tz[0]//2, -tz[1]//2)), font, 0.4, txtcol, 1)


def getcolor(p):
    """ Decide the color of a facelet by its h value (non white) or by s and v (white)"""
    sz = 10
    p = p.astype(np.uint16)
    rect = hsv[p[1] - sz:p[1] + sz, p[0] - sz:p[0] + sz]
    median = np.sum(rect, axis=(0, 1)) / sz / sz / 4
    mh, ms, mv = median
    if ms < vision_params.sat_W and mv > vision_params.val_W:
        return 'white'
    elif vision_params.orange_L <= mh < vision_params.orange_H:
        return 'orange'
    elif vision_params.orange_H <= mh < vision_params.yellow_H:
        return 'yellow'
    elif vision_params.yellow_H <= mh < vision_params.green_H:
        return 'green'
    elif vision_params.green_H <= mh < vision_params.blue_H:
        return 'blue'
    else:
        return 'red'


def getcolors(co, ed, aco, aed, m):
    """Find the colors of the 9 facelets and decide their position on the cube face"""
    centers = [[m for y in range(3)] for x in range(3)]
    colors = [['red' for y in range(3)] for x in range(3)]
    cocents = co + aco
    if len(cocents) != 4:
        return []
    edcents = ed + aed
    if len(edcents) != 4:
        return
    for i in cocents:
        if i[0] < m[0] and i[1] < m[1]:
            centers[0][0] = i
        elif i[0] > m[0] and i[1] < m[1]:
            centers[0][2] = i
        elif i[0] < m[0] and i[1] > m[1]:
            centers[2][0] = i
        elif i[0] > m[0] and i[1] > m[1]:
            centers[2][2] = i

    for i in edcents:
        if i[1] < centers[0][1][1]:
            centers[0][1] = i
    for i in edcents:
        if i[0] < centers[1][0][0]:
            centers[1][0] = i
    for i in edcents:
        if i[0] > centers[1][2][0]:
            centers[1][2] = i
    for i in edcents:
        if i[1] > centers[2][1][1]:
            centers[2][1] = i
    for x in range(3):
        for y in range(3):
            colors[x][y] = getcolor(centers[x][y])
    return colors


def find_squares(bgrcap, n):
    """ Find the positions of squares in the webcam picture"""
    global r_mask, color_filter, white_filter, black_filter

    h, s, v = cv2.split(hsv)
    h_sqr = np.square(h)

    sz = height // n
    border = 1 * sz

    varmax_edges = 20  # wichtig
    for y in range(border, height - border, sz):
        for x in range(border, width - border, sz):

            # rect_h = h[y:y + sz, x:x + sz]
            rect_h = h[y:y + sz, x:x + sz]
            rect_h_sqr = h_sqr[y:y + sz, x:x + sz]

            median_h = np.sum(rect_h) / sz / sz

            sqr_median_hf = median_h * median_h
            median_hf_sqr = np.sum(rect_h_sqr) / sz / sz
            var = median_hf_sqr - sqr_median_hf

            sigma = np.sqrt(var)

            delta = vision_params.delta_C

            if sigma < vision_params.sigma_W:  # sigma liegt für weiß höher, 10-100

                ex_rect = hsv[y - 1 * sz:y + 2 * sz, x - 1 * sz:x + 2 * sz].copy()  # warum copy?
                r_mask = cv2.inRange(ex_rect, (0, 0, vision_params.val_W),
                                     (255, vision_params.sat_W, 255))  # saturation high 30, value low 180
                r_mask = cv2.bitwise_or(r_mask, white_filter[y - 1 * sz:y + 2 * sz, x - 1 * sz:x + 2 * sz])
                white_filter[y - 1 * sz:y + 2 * sz, x - 1 * sz:x + 2 * sz] = r_mask

            if sigma < vision_params.sigma_C:  # übrigen echten Farben  1-3
                ex_rect = h[y - 1 * sz:y + 2 * sz, x - 1 * sz:x + 2 * sz].copy()  # warum copy?
                if median_h + delta >= 180:
                    r_mask = cv2.inRange(ex_rect, 0, median_h + delta - 180)
                    r_mask = cv2.bitwise_or(r_mask, cv2.inRange(ex_rect, median_h - delta, 180))
                elif median_h - delta < 0:
                    r_mask = cv2.inRange(ex_rect, median_h - delta + 180, 180)
                    r_mask = cv2.bitwise_or(r_mask, cv2.inRange(ex_rect, 0, median_h + delta))
                else:
                    r_mask = cv2.inRange(ex_rect, median_h - delta, median_h + delta)

                r_mask = cv2.bitwise_or(r_mask, color_filter[y - 1 * sz:y + 2 * sz, x - 1 * sz:x + 2 * sz])
                color_filter[y - 1 * sz:y + 2 * sz, x - 1 * sz:x + 2 * sz] = r_mask

            # else:
            #     continue

    black_filter = cv2.inRange(bgrcap, (0, 0, 0), (vision_params.rgb_L, vision_params.rgb_L, vision_params.rgb_L))
    black_filter = cv2.bitwise_not(black_filter)

    color_filter = cv2.bitwise_and(color_filter, black_filter)
    color_filter = cv2.blur(color_filter, (20, 20))
    color_filter = cv2.inRange(color_filter, 240, 255)

    white_filter = cv2.bitwise_and(white_filter, black_filter)
    white_filter = cv2.blur(white_filter, (20, 20))
    white_filter = cv2.inRange(white_filter, 240, 255)

    itr = iter([color_filter, white_filter])

    for j in itr:
        im2, contours, hierarchy = cv2.findContours(j, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for n in range(len(contours)):
            approx = cv2.approxPolyDP(contours[n], sz // 2, True)
            if approx.shape[0] < 4 or approx.shape[0] > 4:
                continue
            corners = approx[:, 0]

            edges = np.array(
                [cv2.norm(corners[0] - corners[1], cv2.NORM_L2), cv2.norm(corners[1] - corners[2], cv2.NORM_L2),
                 cv2.norm(corners[2] - corners[3], cv2.NORM_L2),
                 cv2.norm(corners[3] - corners[0], cv2.NORM_L2)])
            edges_mean_sq = (np.sum(edges) / 4) ** 2
            edges_sq_mean = np.sum(np.square(edges)) / 4
            if edges_sq_mean - edges_mean_sq > varmax_edges:
                continue
            # cv2.drawContours(bgrcap, [approx], -1, (0, 0, 255), 8)
            middle = np.sum(corners, axis=0) / 4
            cent.append(np.asarray(middle))


def grab_colors():
    """Find the cube in the webcam picture and grab the colors of the facelets"""
    global cent, width, height, hsv, color_filter, white_filter
    cap = cv2.VideoCapture(0)
    _, bgrcap = cap.read()
    if bgrcap is None:
        print('Cannot connect to webcam!')
        return
    height, width = bgrcap.shape[:2]
    while 1:

        # Take each frame
        _, bgrcap = cap.read()  #
        bgrcap = cv2.blur(bgrcap, (5, 5))
        hsv = cv2.cvtColor(bgrcap, cv2.COLOR_BGR2HSV).astype(float)
        color_filter = cv2.inRange(bgrcap, np.array([1, 1, 1]), np.array([0, 0, 0]))  # mask for colors
        white_filter = cv2.inRange(bgrcap, np.array([1, 1, 1]), np.array([0, 0, 0]))  # special mask for white

        cent = []
        find_squares(bgrcap, grid_N)
        del_duplicates(cent)

        m = medoid(cent)

        cf, ef = facelets(cent, m)
        acf, aef = mirr_facelet(cf, ef, m)

        display_colorname(bgrcap, m)
        for i in ef:
            display_colorname(bgrcap, i)
        for i in cf:
            display_colorname(bgrcap, i)
        for i in aef:
            display_colorname(bgrcap, i)
        for i in acf:
            display_colorname(bgrcap, i)

        vision_params.fc = getcolors(cf, ef, acf, aef, m)

        # drawgrid(bgrcap, grid_N)
        cv2.imshow('color_filter', cv2.resize(color_filter, (width // 2, height // 2)))
        cv2.imshow('white_filter', cv2.resize(white_filter, (width // 2, height // 2)))
        cv2.imshow('black_filter', cv2.resize(black_filter, (width // 2, height // 2)))
        cv2.imshow('Webcam - type "x" to quit.', bgrcap)

        k = cv2.waitKey(5) & 0xFF
        if k == 120:  # x
            break


cv2.destroyAllWindows()