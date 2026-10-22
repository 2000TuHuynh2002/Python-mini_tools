#!/usr/bin/env python3

"""Tách nét chữ viết tay khỏi nền giấy, xuất PNG nền trong suốt.
Developer:
    Claude: Opus 5.5
Cách dùng:
    python3 ink2png.py input.jpg output.png [--scale 2] [--color keep|black|#RRGGBB]
"""



import argparse
import cv2
import numpy as np



def _candidate(v, s, w):
    """Ứng viên vùng giấy: Otsu trên (độ sáng - w * độ bão hoà), lấy vùng lớn nhất, bao lồi."""
    sc = cv2.normalize(cv2.GaussianBlur(v - w * s, (11, 11), 0), None, 0, 255,
                       cv2.NORM_MINMAX).astype(np.uint8)
    _, th = cv2.threshold(sc, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(th, 8)
    
    if n < 2:
        return None
    
    big = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    cnts, _ = cv2.findContours(big, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    m = np.zeros_like(big)
    cv2.fillPoly(m, [cv2.convexHull(max(cnts, key=cv2.contourArea))], 1)
    
    return m


def paper_mask(img, debug=None):
    """
    Tìm vùng tờ giấy.
    1. Sinh vài ứng viên bằng ngưỡng Otsu (độ sáng / độ bão hoà màu).
    2. GrabCut khởi tạo từ các ứng viên để tách giấy khỏi nền (bàn, vải, bút, hộp...).
    3. Xấp xỉ biên giấy thành đa giác lồi; chỉ giữ các cạnh có tương phản thật
       (mép giấy). Cạnh yếu (do bóng đổ, hoặc giấy tràn ra ngoài khung) bị bỏ,
       nên vùng giấy = giao các nửa mặt phẳng của cạnh mạnh.
    """

    H, W = img.shape[:2]
    f = 600.0 / max(H, W)
    sm = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    sm = cv2.morphologyEx(sm, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    hsv = cv2.cvtColor(sm, cv2.COLOR_BGR2HSV).astype(np.float32)
    v = hsv[..., 2]
    s = cv2.medianBlur(hsv[..., 1].astype(np.uint8), 9).astype(np.float32)
    h, w_ = v.shape
    full = np.full((H, W), 255, np.uint8)
    ms = [m for m in (_candidate(v, s, w) for w in range(5)) if m is not None and m.mean() < 0.9]
    
    if not ms:
        return full
    
    union, inter = np.max(ms, 0), np.min(ms, 0)
    gm = np.full((h, w_), cv2.GC_PR_BGD, np.uint8)
    gm[union > 0] = cv2.GC_PR_FGD
    gm[cv2.erode(inter, np.ones((15, 15), np.uint8)) > 0] = cv2.GC_FGD
    border = np.zeros((h, w_), bool)
    border[:4], border[-4:], border[:, :4], border[:, -4:] = True, True, True, True
    gm[border & (union == 0)] = cv2.GC_BGD
    
    try:
        cv2.grabCut(sm, gm, None, np.zeros((1, 65)), np.zeros((1, 65)), 6, cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        pass
    
    m = np.isin(gm, [cv2.GC_FGD, cv2.GC_PR_FGD]).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)

    if n < 2:
        return full

    big = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    cnts, _ = cv2.findContours(big, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull = cv2.convexHull(max(cnts, key=cv2.contourArea))
    poly = cv2.approxPolyDP(hull, 0.01 * cv2.arcLength(hull, True), True).reshape(-1, 2).astype(np.float32)

    # Đo tương phản trong/ngoài dọc mỗi cạnh
    vb, sb = cv2.GaussianBlur(v, (5, 5), 0), cv2.GaussianBlur(s, (5, 5), 0)
    cx, cy = poly.mean(0)
    yy, xx = np.mgrid[0:h, 0:w_].astype(np.float32)
    region = np.ones((h, w_), bool)
    d = 6.0
    
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        e = b - a
        L = float(np.hypot(*e))
    
        if L < 10:
            continue
    
        nrm = np.array([e[1], -e[0]], np.float32) / L
    
        if np.dot(nrm, np.array([cx, cy]) - a) > 0:   # pháp tuyến hướng ra ngoài
            nrm = -nrm
    
        ts = np.linspace(0.15, 0.85, 25)
        pts = a[None] + ts[:, None] * e[None]
        pin, pout = pts - d * nrm, pts + d * nrm
        ok = (pout[:, 0] >= 0) & (pout[:, 0] < w_) & (pout[:, 1] >= 0) & (pout[:, 1] < h)
    
        if ok.mean() < 0.7:
            continue                                   # cạnh trùng khung ảnh: giấy tràn ra ngoài
    
        pi, po = pin[ok].astype(int), pout[ok].astype(int)
        contrast = np.median(np.abs(vb[pi[:, 1], pi[:, 0]] - vb[po[:, 1], po[:, 0]])
                             + 2 * np.abs(sb[pi[:, 1], pi[:, 0]] - sb[po[:, 1], po[:, 0]]))
        if contrast < 25:
            continue                                   # cạnh yếu: do bóng đổ, không phải mép giấy
    
        region &= ((xx - a[0]) * nrm[0] + (yy - a[1]) * nrm[1]) <= 0
    
    mask = region.astype(np.uint8) * 255
    
    if debug is not None:
        dbg = sm.copy()
        dbg[mask == 0] //= 4
        cv2.imwrite(debug, dbg)
    
    mg = max(3, int(min(h, w_) * 0.015))
    mask = cv2.erode(mask, np.ones((mg, mg), np.uint8))
    
    return cv2.resize(mask, (W, H), interpolation=cv2.INTER_NEAREST)


def extract(img, scale=2.0, color="keep", lo=0.10, hi=0.45, drop_edge=True):
    pmask = paper_mask(img)
    if scale != 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)

    # Làm phẳng nền: chia cho ảnh nền ước lượng (closing + blur) để khử bóng/sáng không đều
    k = int(31 * scale) | 1
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    bg = cv2.GaussianBlur(bg, (k, k), 0)
    norm = np.clip(gray / (bg + 1e-6), 0, 1)          # giấy ~1, mực < 1
    darkness = 1.0 - norm

    # Map độ tối -> alpha với vùng chuyển mềm (giữ khử răng cưa)
    alpha = np.clip((darkness - lo) / (hi - lo), 0, 1)
    pmask = cv2.resize(pmask, (gray.shape[1], gray.shape[0]), interpolation=cv2.INTER_NEAREST)
    alpha *= pmask / 255.0

    # Bỏ chấm nhiễu lẻ tẻ
    a8 = (alpha * 255).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats((a8 > 60).astype(np.uint8), 8)
    min_area = int(6 * scale * scale)
    keep = np.zeros(n, bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_area
    
    # Bỏ vệt quá nhạt (dòng kẻ vở, bóng mờ): nét mực thật luôn có lõi đậm
    peak = np.zeros(n, np.float32)
    np.maximum.at(peak, lab.ravel(), darkness.ravel())
    keep &= peak >= max(hi * 0.8, lo + 0.15)
    
    if drop_edge:
        # Bỏ vật nằm sát mép giấy (lò xo sổ, bóng mép, góc giấy gập):
        # chạm mép VÀ không vươn sâu vào trong. Nét vẽ dài chạm mép vẫn được giữ.
        pm = np.pad(pmask, 1)                                   # coi khung ảnh cũng là mép
        dist = cv2.distanceTransform((pm > 0).astype(np.uint8), cv2.DIST_L2, 5)[1:-1, 1:-1]
        reach = np.zeros(n, np.float32)
        np.maximum.at(reach, lab.ravel(), dist.ravel())
        touch = np.zeros(n, bool)
        touch[np.unique(lab[(dist <= 3) & (lab > 0)])] = True
        band = 0.06 * min(gray.shape)
        keep &= ~(touch & (reach < band))
    
    support = cv2.dilate(keep[lab].astype(np.uint8), np.ones((3, 3), np.uint8))
    alpha *= support

    if color == "keep":
        # tăng độ đậm màu mực gốc để nét không bị nhạt
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32)
        rgb = np.clip(rgb * 0.6, 0, 255)
    else:
        hexc = "#000000" if color == "black" else color
        c = tuple(int(hexc.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        rgb = np.zeros((*gray.shape, 3), np.float32) + c

    rgba = np.dstack([rgb, alpha * 255]).astype(np.uint8)
    
    return rgba


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--color", default="keep")
    ap.add_argument("--lo", type=float, default=0.10)
    ap.add_argument("--hi", type=float, default=0.45)
    ap.add_argument("--crop", action="store_true", help="cắt sát vùng có chữ (chừa lề nhỏ)")
    ap.add_argument("--keep-edge", action="store_true",
                    help="giữ cả các nét chạm mép giấy (mặc định bỏ, để loại lò xo sổ)")
    a = ap.parse_args()
    img = cv2.imread(a.input)
    
    if img is None:
        raise SystemExit(f"Không đọc được ảnh: {a.input}")
    
    rgba = extract(img, a.scale, a.color, a.lo, a.hi, not a.keep_edge)
    
    if a.crop:
        ys, xs = np.nonzero(rgba[..., 3] > 10)
        if ys.size:
            pad = int(0.03 * max(rgba.shape[:2]))
            y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, rgba.shape[0])
            x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, rgba.shape[1])
            rgba = rgba[y0:y1, x0:x1]
    
    cv2.imwrite(a.output, cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))


if __name__ == "__main__":
    main()
