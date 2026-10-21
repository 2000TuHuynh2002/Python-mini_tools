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



def paper_mask(img):
    """
    Tìm vùng tờ giấy: giấy sáng và ít bão hoà màu hơn mặt bàn.
    Lấy bao lồi của vùng lớn nhất rồi co mép vào để bỏ viền giấy.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    v = cv2.morphologyEx(hsv[..., 2], cv2.MORPH_CLOSE, k)
    s = cv2.medianBlur(hsv[..., 1].astype(np.uint8), 15).astype(np.float32)
    score = cv2.normalize(cv2.GaussianBlur(v - 4 * s, (15, 15), 0), 
                          None, 0, 255,
                          cv2.NORM_MINMAX).astype(np.uint8)
    _, th = cv2.threshold(score, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    H, W = th.shape

    # Lấy thành phần lớn nhất
    n, lab, stats, _ = cv2.connectedComponentsWithStats(th, 8)
    if n < 2:
        return np.full((H, W), 255, np.uint8)
    big = (lab == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])).astype(np.uint8)


    # Dò 3 mép giấy (trái, phải, trên) ở nửa trên ảnh — nơi mép rõ nhất —
    # rồi ngoại suy thành tứ giác kéo tới đáy ảnh (mép dưới thường bị cắt khung).    
    def fit(xs, ys):
        return np.polyfit(ys, xs, 1) if len(ys) > 10 else None


    rows = np.arange(int(H * 0.05), int(H * 0.45))
    lx, rx, ry = [], [], []

    for y in rows:
        xs = np.flatnonzero(big[y])
        if xs.size:
            lx.append(xs[0]); rx.append(xs[-1]); ry.append(y)

    left, right = fit(np.array(lx), np.array(ry)), fit(np.array(rx), np.array(ry))
    cols = np.arange(W)
    top_y = np.array([np.flatnonzero(big[:, x])[0] if big[:, x].any() else H for x in cols])

    if left is None or right is None:
        mask = big * 255
    else:
        xl0, xr0 = np.polyval(left, 0), np.polyval(right, 0)
        xlH, xrH = np.polyval(left, H), np.polyval(right, H)
        inner = (cols > max(xl0, xlH) + 20) & (cols < min(xr0, xrH) - 20)
        tfit = np.polyfit(cols[inner], top_y[inner], 1)
        yl, yr = np.polyval(tfit, xl0), np.polyval(tfit, xr0)
        quad = np.array([[np.polyval(left, yl), yl],
                         [np.polyval(right, yr), yr],
                         [xrH, H], [xlH, H]], np.int32)
        mask = np.zeros((H, W), np.uint8)
        cv2.fillPoly(mask, [quad], 255)

    m = max(5, int(min(H, W) * 0.012))

    return cv2.erode(mask, np.ones((m, m), np.uint8))


def extract(img, scale=2.0, color="keep", lo=0.10, hi=0.45):
    pmask = paper_mask(img)
    if scale != 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)

    # Làm phẳng nền: chia cho ảnh nền ước lượng (closing + blur) để khử bóng/sáng không đều
    k = int(31 * scale) | 1
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    bg = cv2.GaussianBlur(bg, (k, k), 0)

    # giấy ~1, mực < 1
    norm = np.clip(gray / (bg + 1e-6), 0, 1)
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
    a = ap.parse_args()
    img = cv2.imread(a.input)
    rgba = extract(img, a.scale, a.color, a.lo, a.hi)
    cv2.imwrite(a.output, cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))


if __name__ == "__main__":
    main()
